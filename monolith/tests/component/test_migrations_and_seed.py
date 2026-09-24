"""The schema and seed data that later steps (and the demo) rely on."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from .seed import LAMP, ZOE

MODULE_SCHEMAS = {"customer", "orders", "inventory", "payment", "shipping", "notification"}
LAST_UNIT_PRODUCT = LAMP
ZERO_BALANCE_CUSTOMER = ZOE


async def test_one_schema_per_module(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT schema_name FROM information_schema.schemata"))
        schemas = {r[0] for r in rows}
    assert schemas >= MODULE_SCHEMAS


async def test_seed_products(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        rows = (await conn.execute(text("SELECT id, stock_qty FROM inventory.products"))).all()
    assert len(rows) == 10
    assert [r.id for r in rows if r.stock_qty == 1] == [LAST_UNIT_PRODUCT]


async def test_seed_customers_have_wallets(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT c.cust_id, w.balance_minor FROM customer.customers c "
                    "JOIN payment.wallets w ON w.customer_id = c.cust_id"
                )
            )
        ).all()
    assert len(rows) == 5
    assert [r.cust_id for r in rows if r.balance_minor == 0] == [ZERO_BALANCE_CUSTOMER]


async def test_customer_table_uses_legacy_column_names(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'customer' AND table_name = 'customers'"
            )
        )
        columns = {r[0] for r in rows}
    assert {"cust_id", "cust_nm", "cust_eml"} <= columns


async def test_database_rejects_negative_stock(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        with pytest.raises(IntegrityError, match="ck_products_stock_non_negative"):
            await conn.execute(
                text("UPDATE inventory.products SET stock_qty = stock_qty - 2 WHERE id = :id"),
                {"id": LAST_UNIT_PRODUCT},
            )
        await conn.rollback()


async def test_database_rejects_negative_wallet_balance(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        with pytest.raises(IntegrityError, match="ck_wallets_balance_non_negative"):
            await conn.execute(
                text(
                    "UPDATE payment.wallets SET balance_minor = balance_minor - 1 "
                    "WHERE customer_id = :id"
                ),
                {"id": ZERO_BALANCE_CUSTOMER},
            )
        await conn.rollback()
