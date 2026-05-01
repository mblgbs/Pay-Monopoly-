from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from ..config import get_settings


def create_topup_payment_link(*, reference_id: str, amount_cents: int, wallet_id: str) -> str:
    settings = get_settings()
    base_url = settings.services_monopoly_base_url.rstrip("/")
    endpoint = f"{base_url}/payments/link"

    payload = {
        "app": "wallet",
        "context": "topup",
        "reference_id": reference_id,
        "metadata": {
            "flow": "wallet_topup",
            "reference_id": reference_id,
            "wallet_id": wallet_id,
            "amount_cents": amount_cents,
        },
        "amount_hint_eur": round(amount_cents / 100, 2),
        "amount_hint_cents": amount_cents,
    }

    try:
        response = httpx.post(endpoint, json=payload, timeout=10.0)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payments service unavailable",
        ) from exc

    if response.status_code >= 400:
        detail = "Payments service error"
        try:
            data = response.json()
            if isinstance(data, dict):
                detail = str(data.get("detail") or data.get("error") or detail)
        except ValueError:
            pass
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid payments response",
        ) from exc

    payment_url = data.get("url") if isinstance(data, dict) else None
    if not isinstance(payment_url, str) or not payment_url.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Missing payment URL in response",
        )
    return payment_url

