from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import User, Wallet
from ..schemas import AuthSyncResponse, WalletResponse, WalletUserResponse
from ..security import create_access_token
from ..services.franceconnect_client import fetch_franceconnect_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _generate_wallet_id(db: Session) -> str:
    for _ in range(8):
        candidate = f"WAL{secrets.token_hex(4).upper()}"
        exists = db.execute(select(Wallet).where(Wallet.wallet_id == candidate)).scalar_one_or_none()
        if exists is None:
            return candidate
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Wallet ID generation failed")


@router.post("/session/sync", response_model=AuthSyncResponse)
def sync_franceconnect_session(request: Request, db: Session = Depends(get_db)) -> AuthSyncResponse:
    settings = get_settings()
    session_cookie = request.cookies.get(settings.franceconnect_session_cookie_name)
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing FranceConnect session cookie",
        )

    fc_user = fetch_franceconnect_user(session_cookie)

    user = db.execute(select(User).where(User.franceconnect_sub == fc_user.sub)).scalar_one_or_none()
    if user is None:
        user = User(
            franceconnect_sub=fc_user.sub,
            email=fc_user.email,
            given_name=fc_user.given_name,
            family_name=fc_user.family_name,
        )
        db.add(user)
        db.flush()
    else:
        user.email = fc_user.email
        user.given_name = fc_user.given_name
        user.family_name = fc_user.family_name

    wallet = db.execute(select(Wallet).where(Wallet.user_id == user.id)).scalar_one_or_none()
    if wallet is None:
        wallet = Wallet(
            user_id=user.id,
            wallet_id=_generate_wallet_id(db),
            balance_cents=0,
            currency="EUR",
        )
        db.add(wallet)
        db.flush()

    db.commit()

    token = create_access_token(user_id=user.id, wallet_id=wallet.wallet_id)
    return AuthSyncResponse(
        access_token=token,
        user=WalletUserResponse(
            id=user.id,
            franceconnect_sub=user.franceconnect_sub,
            email=user.email,
            given_name=user.given_name,
            family_name=user.family_name,
        ),
        wallet=WalletResponse(
            wallet_id=wallet.wallet_id,
            balance_cents=wallet.balance_cents,
            currency=wallet.currency,
        ),
    )

