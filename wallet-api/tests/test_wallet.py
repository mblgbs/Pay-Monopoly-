from __future__ import annotations

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import TopupRequest, Transaction, TransactionType, User, Wallet


def _fc_response(sub: str, email: str) -> Mock:
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {
        "sub": sub,
        "email": email,
        "given_name": "Test",
        "family_name": "User",
    }
    return mock


def _create_wallet_session(client: TestClient, sub: str, email: str) -> dict[str, str]:
    with patch("app.services.franceconnect_client.httpx.get", return_value=_fc_response(sub, email)):
        response = client.post("/auth/session/sync", cookies={"fc_monopoly_session": f"cookie-{sub}"})
    assert response.status_code == 200
    data = response.json()
    return {"token": data["access_token"], "wallet_id": data["wallet"]["wallet_id"]}


def test_create_topup_pending(client: TestClient, db_session) -> None:
    session = _create_wallet_session(client, "sub-topup", "topup@example.fr")
    mock_payment_response = Mock()
    mock_payment_response.status_code = 200
    mock_payment_response.json.return_value = {"url": "https://buy.stripe.com/test-topup"}

    with patch("app.services.payments_proxy.httpx.post", return_value=mock_payment_response):
        response = client.post(
            "/wallet/topups",
            headers={"Authorization": f"Bearer {session['token']}"},
            json={"amount_cents": 1250},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "PENDING"
    assert payload["payment_url"].startswith("https://")

    topup = db_session.execute(select(TopupRequest).where(TopupRequest.topup_id == payload["topup_id"])).scalar_one()
    assert topup.amount_cents == 1250
    pending_tx = db_session.execute(
        select(Transaction).where(
            Transaction.topup_request_id == topup.id,
            Transaction.transaction_type == TransactionType.TOPUP_PENDING.value,
        )
    ).scalar_one()
    assert pending_tx.amount_cents == 1250


def test_transfer_p2p_with_and_without_balance(client: TestClient, db_session) -> None:
    sender = _create_wallet_session(client, "sub-sender", "sender@example.fr")
    recipient = _create_wallet_session(client, "sub-recipient", "recipient@example.fr")

    fail_response = client.post(
        "/wallet/transfers/p2p",
        headers={"Authorization": f"Bearer {sender['token']}"},
        json={"recipient_wallet_id": recipient["wallet_id"], "amount_cents": 200},
    )
    assert fail_response.status_code == 400

    sender_wallet = db_session.execute(select(Wallet).where(Wallet.wallet_id == sender["wallet_id"])).scalar_one()
    sender_wallet.balance_cents = 1000
    db_session.commit()

    ok_response = client.post(
        "/wallet/transfers/p2p",
        headers={"Authorization": f"Bearer {sender['token']}"},
        json={"recipient_wallet_id": recipient["wallet_id"], "amount_cents": 250},
    )
    assert ok_response.status_code == 200
    payload = ok_response.json()
    assert payload["amount_cents"] == 250
    assert payload["sender_balance_cents"] == 750

    db_session.expire_all()
    sender_wallet = db_session.execute(select(Wallet).where(Wallet.wallet_id == sender["wallet_id"])).scalar_one()
    recipient_wallet = db_session.execute(select(Wallet).where(Wallet.wallet_id == recipient["wallet_id"])).scalar_one()
    assert sender_wallet.balance_cents == 750
    assert recipient_wallet.balance_cents == 250


def test_list_transactions(client: TestClient, db_session) -> None:
    session = _create_wallet_session(client, "sub-history", "history@example.fr")
    user = db_session.execute(select(User).where(User.franceconnect_sub == "sub-history")).scalar_one()
    wallet = db_session.execute(select(Wallet).where(Wallet.user_id == user.id)).scalar_one()
    wallet.balance_cents = 500
    db_session.add(
        Transaction(
            wallet_id=wallet.id,
            transaction_type=TransactionType.P2P_IN.value,
            amount_cents=200,
            description="manual test tx",
        )
    )
    db_session.commit()

    response = client.get(
        "/wallet/transactions?page=1&page_size=20",
        headers={"Authorization": f"Bearer {session['token']}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["transaction_type"] in {
        TransactionType.P2P_IN.value,
        TransactionType.P2P_OUT.value,
        TransactionType.TOPUP_PENDING.value,
        TransactionType.TOPUP_SETTLED.value,
    }
