from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import TopupRequest, TopupStatus, Transaction, TransactionType, Wallet
from ..schemas import StripeWebhookAck, StripeWebhookEvent

router = APIRouter(prefix="/wallet/webhooks", tags=["webhooks"])


@router.post("/stripe", response_model=StripeWebhookAck)
def stripe_topup_webhook(
    payload: StripeWebhookEvent,
    db: Session = Depends(get_db),
    x_wallet_webhook_secret: str | None = Header(default=None, alias="X-Wallet-Webhook-Secret"),
) -> StripeWebhookAck:
    settings = get_settings()
    if x_wallet_webhook_secret != settings.stripe_webhook_shared_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")

    already = db.execute(select(TopupRequest).where(TopupRequest.stripe_event_id == payload.event_id)).scalar_one_or_none()
    if already is not None:
        return StripeWebhookAck(received=True, processed=False, topup_id=already.topup_id)

    topup = db.execute(
        select(TopupRequest).where(TopupRequest.reference_id == payload.reference_id).with_for_update()
    ).scalar_one_or_none()
    if topup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown topup reference")

    topup.stripe_event_id = payload.event_id

    if payload.payment_status.lower() != "paid":
        db.commit()
        return StripeWebhookAck(received=True, processed=False, topup_id=topup.topup_id)

    if topup.status == TopupStatus.SETTLED.value:
        db.commit()
        return StripeWebhookAck(received=True, processed=False, topup_id=topup.topup_id)

    wallet = db.execute(select(Wallet).where(Wallet.id == topup.wallet_id).with_for_update()).scalar_one()
    wallet.balance_cents += topup.amount_cents
    topup.status = TopupStatus.SETTLED.value
    topup.settled_at = datetime.utcnow()

    db.add(
        Transaction(
            wallet_id=wallet.id,
            transaction_type=TransactionType.TOPUP_SETTLED.value,
            amount_cents=topup.amount_cents,
            topup_request_id=topup.id,
            description="Top-up settled by Stripe webhook",
        )
    )
    db.commit()

    return StripeWebhookAck(received=True, processed=True, topup_id=topup.topup_id)

