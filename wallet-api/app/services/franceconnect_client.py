from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from ..config import get_settings
from ..schemas import FranceConnectUser


def fetch_franceconnect_user(session_cookie_value: str) -> FranceConnectUser:
    settings = get_settings()
    base_url = settings.franceconnect_base_url.rstrip("/")
    url = f"{base_url}{settings.franceconnect_me_path}"

    headers = {"Cookie": f"{settings.franceconnect_session_cookie_name}={session_cookie_value}"}
    try:
        response = httpx.get(url, headers=headers, timeout=5.0)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="FranceConnect service unavailable",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="FranceConnect session is not authenticated",
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid FranceConnect response",
        ) from exc

    try:
        return FranceConnectUser.model_validate(payload)
    except Exception as exc:  # pragma: no cover - validation details are enough
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="FranceConnect user payload validation failed",
        ) from exc

