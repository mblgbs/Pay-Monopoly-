from __future__ import annotations

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import TopupRequest, TopupStatus, Wallet


def _fc_response() -> Mock:
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {
        "sub": "sub-webhook",
        "email": "webhook@example.fr",
        "given_name": "Webhook",
        "family_name": "User",
    }
    return mock


def _session_and_topup(client: TestClient) -> tuple[str, str]:
    with patch("app.services.franceconnect_client.httpx.get", return_value=_fc_response()):
        sync_resp = client.post("/auth/session/sync", cookies={"fc_monopoly_session": "cookie-webhook"})
    token = sync_resp.json()["access_token"]

    mock_payment_response = Mock()
    mock_payment_response.status_code = 200
    mock_payment_response.json.return_value = {"url": "https://buy.stripe.com/webhook-link"}
    with patch("app.services.payments_proxy.httpx.post", return_value=mock_payment_response):
        topup_resp = client.post(
            "/wallet/topups",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount_cents": 3000},
        )
    topup_id = topup_resp.json()["topup_id"]
    return token, topup_id


def test_webhook_settles_topup_once(client: TestClient, db_session) -> None:
    token, topup_id = _session_and_topup(client)
    assert token

    topup = db_session.execute(select(TopupRequest).where(TopupRequest.topup_id == topup_id)).scalar_one()
    wallet = db_session.get(Wallet, topup.wallet_id)
    assert wallet is not None
    assert wallet.balance_cents == 0

    payload = {
        "event_id": "evt_test_1",
        "event_type": "checkout.session.completed",
        "payment_status": "paid",
        "reference_id": topup.reference_id,
        "amount_cents": 3000,
        "currency": "eur",
    }
    response = client.post(
        "/wallet/webhooks/stripe",
        headers={"X-Wallet-Webhook-Secret": "wallet-webhook-secret"},
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["processed"] is True

    db_session.refresh(topup)
    db_session.refresh(wallet)
    assert topup.status == TopupStatus.SETTLED.value
    assert wallet.balance_cents == 3000

    duplicate = client.post(
        "/wallet/webhooks/stripe",
        headers={"X-Wallet-Webhook-Secret": "wallet-webhook-secret"},
        json=payload,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["processed"] is False

