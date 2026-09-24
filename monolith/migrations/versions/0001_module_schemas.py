"""One schema per module, plus the tables that seed data needs.

Order, payment, shipment and notification-log tables arrive in the step that uses them.
No foreign keys cross schemas: modules reference each other by ID only (constraint C2),
so a module can later be extracted with its data.

Revision ID: 0001
Revises:
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = ("customer", "orders", "inventory", "payment", "shipping", "notification")


def _created_at() -> sa.Column[sa.DateTime]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # Legacy model: these column names are deliberate (Anti-Corruption Layer target, Phase 1).
    op.create_table(
        "customers",
        sa.Column("cust_id", sa.Uuid(), primary_key=True),
        sa.Column("cust_nm", sa.Text(), nullable=False),
        sa.Column("cust_eml", sa.Text(), nullable=False, unique=True),
        _created_at(),
        schema="customer",
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("stock_qty", sa.Integer(), nullable=False),
        _created_at(),
        sa.CheckConstraint("price_minor >= 0", name="ck_products_price_non_negative"),
        # C1 backstop: the database refuses negative stock whatever the application does.
        sa.CheckConstraint("stock_qty >= 0", name="ck_products_stock_non_negative"),
        schema="inventory",
    )

    op.create_table(
        "wallets",
        sa.Column("customer_id", sa.Uuid(), primary_key=True),
        sa.Column("balance_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        _created_at(),
        sa.CheckConstraint("balance_minor >= 0", name="ck_wallets_balance_non_negative"),
        schema="payment",
    )


def downgrade() -> None:
    op.drop_table("wallets", schema="payment")
    op.drop_table("products", schema="inventory")
    op.drop_table("customers", schema="customer")
    for schema in reversed(SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema}")
