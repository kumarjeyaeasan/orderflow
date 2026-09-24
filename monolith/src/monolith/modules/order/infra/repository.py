"""Maps the Order aggregate to and from its rows. The aggregate is always saved as a whole."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from monolith.modules.order.domain.model import Order, OrderLine, OrderStatus
from monolith.modules.order.infra.models import OrderLineRow, OrderRow


async def add(session: AsyncSession, order: Order) -> None:
    session.add(
        OrderRow(
            id=order.id,
            customer_id=order.customer_id,
            status=order.status.value,
            total_minor=order.total_minor,
            currency=order.currency,
            rejection_reason=order.rejection_reason,
            lines=[
                OrderLineRow(
                    product_id=line.product_id,
                    quantity=line.quantity,
                    unit_price_minor=line.unit_price_minor,
                )
                for line in order.lines
            ],
        )
    )
    await session.flush()


async def save_status(session: AsyncSession, order: Order) -> None:
    """Persist the mutable part of the aggregate (lines never change after creation)."""
    row = await session.get(OrderRow, order.id)
    if row is None:
        raise LookupError(f"order {order.id} was never added")
    row.status = order.status.value
    row.rejection_reason = order.rejection_reason
    await session.flush()


async def get(session: AsyncSession, order_id: UUID) -> Order | None:
    row = await session.get(OrderRow, order_id)
    if row is None:
        return None
    return Order(
        id=row.id,
        customer_id=row.customer_id,
        currency=row.currency,
        lines=tuple(
            OrderLine(
                product_id=line.product_id,
                quantity=line.quantity,
                unit_price_minor=line.unit_price_minor,
            )
            for line in row.lines
        ),
        status=OrderStatus(row.status),
        rejection_reason=row.rejection_reason,
    )
