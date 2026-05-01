from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./wallet_test.db"
os.environ["WALLET_JWT_SECRET"] = "test-wallet-secret"
os.environ["STRIPE_WEBHOOK_SHARED_SECRET"] = "wallet-webhook-secret"

from app.config import clear_settings_cache  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db() -> None:
    clear_settings_cache()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

