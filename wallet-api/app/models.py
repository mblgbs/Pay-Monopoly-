from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class TopupStatus(str, enum.Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"


class TransactionType(str, enum.Enum):
    TOPUP_PENDING = "topup_pending"
    TOPUP_SETTLED = "topup_settled"
    P2P_IN = "p2p_in"
    P2P_OUT = "p2p_out"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    franceconnect_sub: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255))
    given_name: Mapped[str] = mapped_column(String(120))
    family_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    wallet: Mapped["Wallet"] = relationship(back_populates="user", uselist=False)


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    wallet_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    balance_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user: Mapped[User] = relationship(back_populates="wallet")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="wallet",
        foreign_keys="Transaction.wallet_id",
    )


class TopupRequest(Base):
    __tablename__ = "topup_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    topup_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default=TopupStatus.PENDING.value, index=True)
    reference_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    payment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stripe_event_id: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    wallet: Mapped[Wallet] = relationship()
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="topup_request")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("wallet_id", "transaction_type", "topup_request_id", name="uq_wallet_tx_topup"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(24), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    counterparty_wallet_id: Mapped[int | None] = mapped_column(ForeignKey("wallets.id"), nullable=True)
    topup_request_id: Mapped[int | None] = mapped_column(ForeignKey("topup_requests.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    wallet: Mapped[Wallet] = relationship(foreign_keys=[wallet_id], back_populates="transactions")
    topup_request: Mapped[TopupRequest | None] = relationship(back_populates="transactions")
    counterparty_wallet: Mapped[Wallet | None] = relationship(foreign_keys=[counterparty_wallet_id])
