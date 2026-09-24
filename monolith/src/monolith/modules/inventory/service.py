"""Public interface of the inventory module.

Other modules may import ONLY this file from inventory; never its api/, domain/ or infra/.
All functions run inside the caller's session/transaction and never commit.
"""

from collections.abc import Iterable, Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from monolith.modules.inventory.domain.model import (
    InsufficientStockError,
    Product,
    ProductNotFoundError,
    StockLine,
)
from monolith.modules.inventory.infra.models import ProductRow
from monolith.modules.inventory.infra.stock import take_stock_atomic, take_stock_naive

__all__ = [
    "InsufficientStockError",
    "Product",
    "ProductNotFoundError",
    "StockLine",
    "adjust_stock",
    "get_product",
    "get_products",
    "list_products",
    "reserve",
]


def _to_product(row: ProductRow) -> Product:
    return Product(
        id=row.id,
        name=row.name,
        price_minor=row.price_minor,
        currency=row.currency,
        stock_qty=row.stock_qty,
    )


async def list_products(session: AsyncSession) -> list[Product]:
    rows = await session.scalars(select(ProductRow).order_by(ProductRow.name))
    return [_to_product(r) for r in rows]


async def get_product(session: AsyncSession, product_id: UUID) -> Product | None:
    row = await session.get(ProductRow, product_id, populate_existing=True)
    return _to_product(row) if row else None


async def get_products(session: AsyncSession, product_ids: Iterable[UUID]) -> dict[UUID, Product]:
    """Look up several products; raises ProductNotFoundError listing any unknown IDs."""
    wanted = set(product_ids)
    rows = await session.scalars(select(ProductRow).where(ProductRow.id.in_(wanted)))
    found = {r.id: _to_product(r) for r in rows}
    missing = sorted(wanted - found.keys())
    if missing:
        raise ProductNotFoundError(missing)
    return found


async def reserve(
    session: AsyncSession, lines: Sequence[StockLine], *, atomic: bool = True
) -> None:
    """Take stock for every line or raise InsufficientStockError.

    All-or-nothing relies on the CALLER's transaction: run this inside a savepoint or transaction
    that is rolled back on error, so lines already taken are put back.
    """
    if atomic:
        await take_stock_atomic(session, lines)
    else:
        await take_stock_naive(session, lines)


async def adjust_stock(session: AsyncSession, product_id: UUID, delta: int) -> int:
    """Admin stock change by `delta` (may be negative). Returns the new quantity."""
    new_qty = await session.scalar(
        update(ProductRow)
        .where(ProductRow.id == product_id, ProductRow.stock_qty + delta >= 0)
        .values(stock_qty=ProductRow.stock_qty + delta)
        .returning(ProductRow.stock_qty)
    )
    if new_qty is not None:
        return new_qty
    if await session.get(ProductRow, product_id) is None:
        raise ProductNotFoundError([product_id])
    raise InsufficientStockError(product_id)
