"""Tables for the Place Order flow: orders, order lines, payments, shipments, notification log.

Still no foreign keys across schemas (constraint C2); order_lines -> orders is inside one module.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORDER_STATUSES = ("PENDING", "APPROVED", "REJECTED", "SHIPPED", "CANCELLED")


def _ts(name: str) -> sa.Column[sa.DateTime]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("total_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{s}'" for s in ORDER_STATUSES) + ")",
            name="ck_orders_status",
        ),
        sa.CheckConstraint("total_minor >= 0", name="ck_orders_total_non_negative"),
        schema="orders",
    )
    op.create_table(
        "order_lines",
        sa.Column(
            "order_id",
            sa.Uuid(),
            sa.ForeignKey("orders.orders.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("product_id", sa.Uuid(), primary_key=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_minor", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_lines_quantity_positive"),
        sa.CheckConstraint("unit_price_minor >= 0", name="ck_order_lines_price_non_negative"),
        schema="orders",
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        # One charge per order: a second charge for the same order fails at the database.
        sa.Column("order_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        _ts("created_at"),
        sa.CheckConstraint("amount_minor >= 0", name="ck_payments_amount_non_negative"),
        schema="payment",
    )
    op.create_table(
        "shipments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("order_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("status", sa.Text(), nullable=False),
        _ts("created_at"),
        schema="shipping",
    )
    op.create_table(
        "notification_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("order_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("order_status", sa.Text(), nullable=False),
        sa.Column("recipient", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        _ts("created_at"),
        schema="notification",
    )


def downgrade() -> None:
    op.drop_table("notification_log", schema="notification")
    op.drop_table("shipments", schema="shipping")
    op.drop_table("payments", schema="payment")
    op.drop_table("order_lines", schema="orders")
    op.drop_table("orders", schema="orders")
