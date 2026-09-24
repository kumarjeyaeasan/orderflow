"""Public interface of the order module, and the Phase 0 "Place Order" flow.

Everything below runs in ONE database transaction owned by the caller (the API layer). That single
transaction is what gives Phase 0 its guarantees for free: if payment fails, the stock taken a
moment earlier is rolled back with it. Each later phase removes one of these guarantees.
"""

from collections.abc import Sequence
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from monolith.modules.customer import service as customer_service
from monolith.modules.inventory import service as inventory_service
from monolith.modules.notification import service as notification_service
from monolith.modules.order.domain.model import (
    InvalidOrderError,
    InvalidTransitionError,
    Order,
    OrderLine,
    OrderStatus,
)
from monolith.modules.order.infra import repository
from monolith.modules.payment import service as payment_service
from monolith.modules.shipping import service as shipping_service

__all__ = [
    "CustomerNotFoundError",
    "InvalidOrderError",
    "InvalidTransitionError",
    "Order",
    "OrderNotFoundError",
    "OrderStatus",
    "cancel_order",
    "get_order",
    "place_order",
]

log = structlog.get_logger(__name__)


class CustomerNotFoundError(Exception):
    def __init__(self, customer_id: UUID) -> None:
        super().__init__(f"unknown customer {customer_id}")
        self.customer_id = customer_id


class OrderNotFoundError(Exception):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(f"unknown order {order_id}")
        self.order_id = order_id


async def place_order(
    session: AsyncSession,
    customer_id: UUID,
    requested: Sequence[tuple[UUID, int]],
    currency: str,
    *,
    atomic_reservation: bool = True,
) -> Order:
    """Create the order, then reserve → charge → approve → ship, notifying on each outcome.

    Raises (nothing written): CustomerNotFoundError, inventory ProductNotFoundError,
    InvalidOrderError. A business failure (no stock, no money) is NOT an exception to the caller:
    the order is stored as REJECTED with a reason.
    """
    if await customer_service.get_customer(session, customer_id) is None:
        raise CustomerNotFoundError(customer_id)

    products = await inventory_service.get_products(session, [pid for pid, _ in requested])
    for pid in products:
        if products[pid].currency != currency:
            raise InvalidOrderError(f"product {pid} is priced in {products[pid].currency}")
    order = Order.create(
        customer_id,
        currency,
        [OrderLine(pid, qty, products[pid].price_minor) for pid, qty in requested],
    )
    await repository.add(session, order)  # PENDING, with prices snapshotted

    try:
        # Savepoint: if either step fails, stock and wallet go back to where they were,
        # but the PENDING order row (written before the savepoint) survives to be REJECTED.
        async with session.begin_nested():
            await inventory_service.reserve(
                session,
                [inventory_service.StockLine(ln.product_id, ln.quantity) for ln in order.lines],
                atomic=atomic_reservation,
            )
            await payment_service.charge(
                session, order.id, customer_id, order.total_minor, currency
            )
    except inventory_service.InsufficientStockError as exc:
        order.reject(f"insufficient stock for product {exc.product_id}")
    except payment_service.InsufficientFundsError:
        order.reject("insufficient funds")

    if order.status is OrderStatus.REJECTED:
        await repository.save_status(session, order)
        await notification_service.notify_order_status(
            session, order.id, customer_id, order.status, order.rejection_reason
        )
        log.info("order_rejected", order_id=str(order.id), reason=order.rejection_reason)
        return order

    order.approve()
    await notification_service.notify_order_status(session, order.id, customer_id, order.status)
    await shipping_service.create_shipment(session, order.id)
    order.ship()
    await repository.save_status(session, order)
    await notification_service.notify_order_status(session, order.id, customer_id, order.status)
    log.info("order_shipped", order_id=str(order.id), total_minor=order.total_minor)
    return order


async def get_order(session: AsyncSession, order_id: UUID) -> Order:
    order = await repository.get(session, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order


async def cancel_order(session: AsyncSession, order_id: UUID) -> Order:
    """Cancel an order if the state machine allows it.

    In Phase 0 every order leaves place_order as SHIPPED or REJECTED (both terminal), so a cancel
    always ends in InvalidTransitionError (HTTP 409). Cancelling PENDING/APPROVED needs
    compensation (refund + release), which arrives in Phase 5 when orders really wait in those
    states. Until then that path fails loudly instead of cancelling without refunding.
    """
    order = await get_order(session, order_id)
    if order.status in (OrderStatus.PENDING, OrderStatus.APPROVED):
        raise NotImplementedError("cancel with compensation arrives in Phase 5")
    order.cancel()  # every remaining state is terminal: raises InvalidTransitionError
    return order
