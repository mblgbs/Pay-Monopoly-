from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str


class FranceConnectUser(BaseModel):
    sub: str
    email: str
    given_name: str
    family_name: str


class WalletUserResponse(BaseModel):
    id: int
    franceconnect_sub: str
    email: str
    given_name: str
    family_name: str


class WalletResponse(BaseModel):
    wallet_id: str
    balance_cents: int
    currency: str


class AuthSyncResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: WalletUserResponse
    wallet: WalletResponse


class WalletMeResponse(BaseModel):
    user: WalletUserResponse
    wallet: WalletResponse


class TopupCreateRequest(BaseModel):
    amount_cents: int = Field(gt=0, le=50_000_000)


class TopupCreateResponse(BaseModel):
    topup_id: str
    payment_url: str
    status: str


class TransferP2PRequest(BaseModel):
    recipient_wallet_id: str = Field(min_length=6, max_length=32)
    amount_cents: int = Field(gt=0, le=50_000_000)


class TransferP2PResponse(BaseModel):
    sender_wallet_id: str
    recipient_wallet_id: str
    amount_cents: int
    sender_balance_cents: int


class TransactionItem(BaseModel):
    id: int
    transaction_type: str
    amount_cents: int
    counterparty_wallet_id: str | None = None
    topup_id: str | None = None
    created_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionItem]
    page: int
    page_size: int
    total: int


class StripeWebhookEvent(BaseModel):
    event_id: str = Field(min_length=5, max_length=120)
    event_type: str = Field(min_length=5, max_length=120)
    payment_status: str = Field(min_length=2, max_length=40)
    reference_id: str = Field(min_length=5, max_length=120)
    amount_cents: int = Field(gt=0, le=50_000_000)
    currency: str = Field(default="eur", min_length=3, max_length=8)


class StripeWebhookAck(BaseModel):
    received: bool
    processed: bool
    topup_id: str | None = None

