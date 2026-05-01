from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from .config import get_settings


def create_access_token(*, user_id: int, wallet_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.wallet_access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "wallet_id": wallet_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.wallet_jwt_secret, algorithm=settings.wallet_jwt_algorithm)


def decode_access_token(token: str) -> dict[str, str]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.wallet_jwt_secret, algorithms=[settings.wallet_jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user_sub = payload.get("sub")
    wallet_id = payload.get("wallet_id")
    if not isinstance(user_sub, str) or not user_sub.isdigit() or not isinstance(wallet_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return {"sub": user_sub, "wallet_id": wallet_id}

