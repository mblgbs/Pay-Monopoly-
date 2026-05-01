from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import CurrentSession, get_current_session
from ..models import TopupRequest, TopupStatus, Transaction, TransactionType, Wallet
from ..schemas import (
    TopupCreateRequest,
    TopupCreateResponse,
    TransactionItem,
    TransactionListResponse,
    TransferP2PRequest,
    TransferP2PResponse,
    WalletMeResponse,
    WalletResponse,
    WalletUserResponse,
)
from ..services.payments_proxy import create_topup_payment_link

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/me", response_model=WalletMeResponse)
def wallet_me(current: CurrentSession = Depends(get_current_session)) -> WalletMeResponse:
    return WalletMeResponse(
        user=WalletUserResponse(
            id=current.user.id,
            franceconnect_sub=current.user.franceconnect_sub,
            email=current.user.email,
            given_name=current.user.given_name,
            family_name=current.user.family_name,
        ),
        wallet=WalletResponse(
            wallet_id=current.wallet.wallet_id,
            balance_cents=current.wallet.balance_cents,
            currency=current.wallet.currency,
        ),
    )


@router.post("/topups", response_model=TopupCreateResponse, status_code=status.HTTP_201_CREATED)
def create_topup(
    payload: TopupCreateRequest,
    current: CurrentSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> TopupCreateResponse:
    topup_id = f"TOPUP{secrets.token_hex(6).upper()}"
    reference_id = f"wallet-topup-{secrets.token_hex(8)}"

    topup = TopupRequest(
        topup_id=topup_id,
        wallet_id=current.wallet.id,
        amount_cents=payload.amount_cents,
        status=TopupStatus.PENDING.value,
        reference_id=reference_id,
    )
    db.add(topup)
    db.flush()

    db.add(
        Transaction(
            wallet_id=current.wallet.id,
            transaction_type=TransactionType.TOPUP_PENDING.value,
            amount_cents=payload.amount_cents,
            topup_request_id=topup.id,
            description="Top-up request created",
        )
    )

    payment_url = create_topup_payment_link(
        reference_id=reference_id,
        amount_cents=payload.amount_cents,
        wallet_id=current.wallet.wallet_id,
    )
    topup.payment_url = payment_url
    db.commit()

    return TopupCreateResponse(topup_id=topup.topup_id, payment_url=payment_url, status=topup.status)


@router.post("/transfers/p2p", response_model=TransferP2PResponse)
def transfer_p2p(
    payload: TransferP2PRequest,
    current: CurrentSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> TransferP2PResponse:
    recipient = db.execute(select(Wallet).where(Wallet.wallet_id == payload.recipient_wallet_id)).scalar_one_or_none()
    if recipient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient wallet not found")
    if recipient.id == current.wallet.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot transfer to self")

    ids_to_lock = sorted([current.wallet.id, recipient.id])
    locked_wallets = db.execute(
        select(Wallet).where(Wallet.id.in_(ids_to_lock)).order_by(Wallet.id).with_for_update()
    ).scalars().all()
    if len(locked_wallets) != 2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet lock failed")

    wallet_by_id = {wallet.id: wallet for wallet in locked_wallets}
    sender_locked = wallet_by_id[current.wallet.id]
    recipient_locked = wallet_by_id[recipient.id]

    if sender_locked.balance_cents < payload.amount_cents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")

    sender_locked.balance_cents -= payload.amount_cents
    recipient_locked.balance_cents += payload.amount_cents

    db.add(
        Transaction(
            wallet_id=sender_locked.id,
            transaction_type=TransactionType.P2P_OUT.value,
            amount_cents=payload.amount_cents,
            counterparty_wallet_id=recipient_locked.id,
            description=f"Transfer to {recipient_locked.wallet_id}",
        )
    )
    db.add(
        Transaction(
            wallet_id=recipient_locked.id,
            transaction_type=TransactionType.P2P_IN.value,
            amount_cents=payload.amount_cents,
            counterparty_wallet_id=sender_locked.id,
            description=f"Transfer from {sender_locked.wallet_id}",
        )
    )

    db.commit()
    db.refresh(sender_locked)

    return TransferP2PResponse(
        sender_wallet_id=sender_locked.wallet_id,
        recipient_wallet_id=recipient_locked.wallet_id,
        amount_cents=payload.amount_cents,
        sender_balance_cents=sender_locked.balance_cents,
    )


@router.get("/transactions", response_model=TransactionListResponse)
def list_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current: CurrentSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> TransactionListResponse:
    total = db.execute(
        select(func.count(Transaction.id)).where(Transaction.wallet_id == current.wallet.id)
    ).scalar_one()

    rows = (
        db.execute(
            select(Transaction)
            .where(Transaction.wallet_id == current.wallet.id)
            .order_by(Transaction.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    counterparty_ids = {row.counterparty_wallet_id for row in rows if row.counterparty_wallet_id is not None}
    topup_request_ids = {row.topup_request_id for row in rows if row.topup_request_id is not None}

    counterparty_map: dict[int, str] = {}
    if counterparty_ids:
        counterparty_map = {
            wallet.id: wallet.wallet_id
            for wallet in db.execute(select(Wallet).where(Wallet.id.in_(counterparty_ids))).scalars()
        }

    topup_map: dict[int, str] = {}
    if topup_request_ids:
        topup_map = {
            topup.id: topup.topup_id
            for topup in db.execute(select(TopupRequest).where(TopupRequest.id.in_(topup_request_ids))).scalars()
        }

    items = [
        TransactionItem(
            id=row.id,
            transaction_type=row.transaction_type,
            amount_cents=row.amount_cents,
            counterparty_wallet_id=counterparty_map.get(row.counterparty_wallet_id)
            if row.counterparty_wallet_id is not None
            else None,
            topup_id=topup_map.get(row.topup_request_id) if row.topup_request_id is not None else None,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return TransactionListResponse(items=items, page=page, page_size=page_size, total=total)

