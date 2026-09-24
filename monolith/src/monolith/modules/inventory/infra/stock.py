"""Two ways to take stock. The naive one is kept on purpose: it is the Phase 0 break-it experiment.

Toggle: ATOMIC_STOCK_RESERVATION=true (default) | false.
"""

import asyncio
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from monolith.modules.inventory.domain.model import InsufficientStockError, StockLine
from monolith.modules.inventory.infra.models import ProductRow

# Widens the gap between "read" and "write" in the naive path so the race reproduces on every
# run instead of only under unlucky timing. It changes how often the bug shows,
# not whether it exists.
NAIVE_RACE_WINDOW_S = 0.05


def _sorted(lines: Sequence[StockLine]) -> list[StockLine]:
    # Lock rows in a fixed order: two orders touching the same products can't deadlock.
    return sorted(lines, key=lambda line: line.product_id)


async def take_stock_atomic(session: AsyncSession, lines: Sequence[StockLine]) -> None:
    """Check and decrement in ONE statement. Postgres row-locks the product; a concurrent
    transaction waits, then re-evaluates `stock_qty >= :n` against the committed value."""
    for line in _sorted(lines):
        result = await session.execute(
            update(ProductRow)
            .where(ProductRow.id == line.product_id, ProductRow.stock_qty >= line.quantity)
            .values(stock_qty=ProductRow.stock_qty - line.quantity)
            .returning(ProductRow.id)
        )
        if result.scalar_one_or_none() is None:
            raise InsufficientStockError(line.product_id)


async def take_stock_naive(session: AsyncSession, lines: Sequence[StockLine]) -> None:
    """BROKEN ON PURPOSE: read, check in Python, write back an absolute value.

    Two transactions both read stock=1, both pass the check, both write 0: a lost update.
    Both orders succeed, and the stock never goes negative, so the CHECK constraint can't catch it.
    """
    for line in _sorted(lines):
        current = await session.scalar(
            select(ProductRow.stock_qty).where(ProductRow.id == line.product_id)
        )
        if current is None or current < line.quantity:
            raise InsufficientStockError(line.product_id)
        await asyncio.sleep(NAIVE_RACE_WINDOW_S)
        await session.execute(
            update(ProductRow)
            .where(ProductRow.id == line.product_id)
            .values(stock_qty=current - line.quantity)
        )
