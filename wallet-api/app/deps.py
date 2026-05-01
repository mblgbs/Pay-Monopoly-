from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, Wallet
from .security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentSession:
    user: User
    wallet: Wallet


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentSession:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    claims = decode_access_token(credentials.credentials)
    user_id = int(claims["sub"])
    wallet_public_id = claims["wallet_id"]

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    wallet = db.execute(select(Wallet).where(Wallet.wallet_id == wallet_public_id)).scalar_one_or_none()
    if wallet is None or wallet.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wallet not found")

    return CurrentSession(user=user, wallet=wallet)

