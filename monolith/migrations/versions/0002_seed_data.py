"""Seed data (PROJECT_BRIEF §8), with fixed UUIDs so .http files and demos can refer to them.

- 10 products; "Last Unit Lamp" has stock 1 (concurrency test).
- 5 customers with wallets; "Zero Zoe" has balance 0 (payment failure path).
Money is integer minor units in the configured CURRENCY (default USD).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24
"""

import os
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENCY = os.environ.get("CURRENCY", "USD")

# (id, name, price_minor, stock_qty)
PRODUCTS = [
    ("10000000-0000-4000-8000-000000000001", "Mechanical Keyboard", 8999, 50),
    ("10000000-0000-4000-8000-000000000002", "Wireless Mouse", 2499, 100),
    ("10000000-0000-4000-8000-000000000003", "27in Monitor", 24900, 20),
    ("10000000-0000-4000-8000-000000000004", "USB-C Hub", 3999, 75),
    ("10000000-0000-4000-8000-000000000005", "Laptop Stand", 4599, 40),
    ("10000000-0000-4000-8000-000000000006", "Noise-Cancelling Headphones", 19999, 15),
    ("10000000-0000-4000-8000-000000000007", "Webcam 1080p", 5999, 30),
    ("10000000-0000-4000-8000-000000000008", "Desk Mat", 1999, 200),
    ("10000000-0000-4000-8000-000000000009", "Ergonomic Chair", 34900, 5),
    ("10000000-0000-4000-8000-00000000000a", "Last Unit Lamp", 2999, 1),
]

# (id, name, email, wallet balance_minor)
CUSTOMERS = [
    ("20000000-0000-4000-8000-000000000001", "Alice Rich", "alice@example.com", 1_000_000),
    ("20000000-0000-4000-8000-000000000002", "Bob Modest", "bob@example.com", 50_000),
    ("20000000-0000-4000-8000-000000000003", "Carol Careful", "carol@example.com", 10_000),
    ("20000000-0000-4000-8000-000000000004", "Dan Tight", "dan@example.com", 3_000),
    ("20000000-0000-4000-8000-000000000005", "Zero Zoe", "zoe@example.com", 0),
]


def upgrade() -> None:
    products = sa.table(
        "products",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.Text()),
        sa.column("price_minor", sa.BigInteger()),
        sa.column("currency", sa.CHAR(3)),
        sa.column("stock_qty", sa.Integer()),
        schema="inventory",
    )
    customers = sa.table(
        "customers",
        sa.column("cust_id", sa.Uuid()),
        sa.column("cust_nm", sa.Text()),
        sa.column("cust_eml", sa.Text()),
        schema="customer",
    )
    wallets = sa.table(
        "wallets",
        sa.column("customer_id", sa.Uuid()),
        sa.column("balance_minor", sa.BigInteger()),
        sa.column("currency", sa.CHAR(3)),
        schema="payment",
    )
    op.bulk_insert(
        products,
        [
            {"id": uuid.UUID(i), "name": n, "price_minor": p, "currency": CURRENCY, "stock_qty": s}
            for i, n, p, s in PRODUCTS
        ],
    )
    op.bulk_insert(
        customers,
        [{"cust_id": uuid.UUID(i), "cust_nm": n, "cust_eml": e} for i, n, e, _ in CUSTOMERS],
    )
    op.bulk_insert(
        wallets,
        [
            {"customer_id": uuid.UUID(i), "balance_minor": b, "currency": CURRENCY}
            for i, _, _, b in CUSTOMERS
        ],
    )


def downgrade() -> None:
    ids = [i for i, *_ in CUSTOMERS]
    op.execute(
        sa.text(
            "DELETE FROM payment.wallets WHERE customer_id = ANY(CAST(:ids AS uuid[]))"
        ).bindparams(ids=ids)
    )
    op.execute(
        sa.text(
            "DELETE FROM customer.customers WHERE cust_id = ANY(CAST(:ids AS uuid[]))"
        ).bindparams(ids=ids)
    )
    op.execute(
        sa.text("DELETE FROM inventory.products WHERE id = ANY(CAST(:ids AS uuid[]))").bindparams(
            ids=[i for i, *_ in PRODUCTS]
        )
    )
