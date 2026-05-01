"""initial wallet schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("franceconnect_sub", sa.String(length=120), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("given_name", sa.String(length=120), nullable=False),
        sa.Column("family_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_franceconnect_sub", "users", ["franceconnect_sub"], unique=True)

    op.create_table(
        "wallets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("wallet_id", sa.String(length=32), nullable=False, unique=True),
        sa.Column("balance_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_wallets_wallet_id", "wallets", ["wallet_id"], unique=True)
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"], unique=True)

    op.create_table(
        "topup_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topup_id", sa.String(length=40), nullable=False, unique=True),
        sa.Column("wallet_id", sa.Integer(), sa.ForeignKey("wallets.id"), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reference_id", sa.String(length=80), nullable=False, unique=True),
        sa.Column("payment_url", sa.String(length=500), nullable=True),
        sa.Column("stripe_event_id", sa.String(length=80), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_topup_requests_reference_id", "topup_requests", ["reference_id"], unique=True)
    op.create_index("ix_topup_requests_status", "topup_requests", ["status"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wallet_id", sa.Integer(), sa.ForeignKey("wallets.id"), nullable=False),
        sa.Column("transaction_type", sa.String(length=24), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("counterparty_wallet_id", sa.Integer(), sa.ForeignKey("wallets.id"), nullable=True),
        sa.Column("topup_request_id", sa.Integer(), sa.ForeignKey("topup_requests.id"), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "wallet_id",
            "transaction_type",
            "topup_request_id",
            name="uq_wallet_tx_topup",
        ),
    )
    op.create_index("ix_transactions_wallet_id", "transactions", ["wallet_id"], unique=False)
    op.create_index("ix_transactions_transaction_type", "transactions", ["transaction_type"], unique=False)


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("topup_requests")
    op.drop_table("wallets")
    op.drop_table("users")

