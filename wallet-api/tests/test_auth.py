from __future__ import annotations

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.models import User, Wallet


def _mock_fc_response() -> Mock:
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {
        "sub": "mock-user-001",
        "email": "jean.dupont@example.fr",
        "given_name": "Jean",
        "family_name": "Dupont",
    }
    return mock


def test_sync_requires_cookie(client: TestClient) -> None:
    response = client.post("/auth/session/sync")
    assert response.status_code == 401


def test_sync_creates_user_and_wallet(client: TestClient, db_session) -> None:
    with patch("app.services.franceconnect_client.httpx.get", return_value=_mock_fc_response()):
        response = client.post("/auth/session/sync", cookies={"fc_monopoly_session": "abc123"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["wallet"]["wallet_id"].startswith("WAL")
    assert payload["wallet"]["balance_cents"] == 0

    user_count = db_session.query(User).count()
    wallet_count = db_session.query(Wallet).count()
    assert user_count == 1
    assert wallet_count == 1


def test_sync_is_idempotent_for_same_franceconnect_user(client: TestClient, db_session) -> None:
    with patch("app.services.franceconnect_client.httpx.get", return_value=_mock_fc_response()):
        first = client.post("/auth/session/sync", cookies={"fc_monopoly_session": "cookie-1"})
        second = client.post("/auth/session/sync", cookies={"fc_monopoly_session": "cookie-2"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["wallet"]["wallet_id"] == second.json()["wallet"]["wallet_id"]
    assert db_session.query(User).count() == 1
    assert db_session.query(Wallet).count() == 1

