from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from monolith.db import AppSettings, SessionMaker
from monolith.modules.inventory import service as inventory_service
from monolith.modules.order import service
from monolith.modules.order.domain.model import Order

router = APIRouter(tags=["orders"])


class LineIn(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)


class OrderIn(BaseModel):
    customer_id: UUID
    lines: list[LineIn] = Field(min_length=1)


class LineOut(BaseModel):
    product_id: UUID
    quantity: int
    unit_price_minor: int
    line_total_minor: int


class OrderOut(BaseModel):
    id: UUID
    customer_id: UUID
    status: str
    total_minor: int
    currency: str
    rejection_reason: str | None
    lines: list[LineOut]

    @classmethod
    def from_domain(cls, order: Order) -> "OrderOut":
        return cls(
            id=order.id,
            customer_id=order.customer_id,
            status=order.status.value,
            total_minor=order.total_minor,
            currency=order.currency,
            rejection_reason=order.rejection_reason,
            lines=[
                LineOut(
                    product_id=ln.product_id,
                    quantity=ln.quantity,
                    unit_price_minor=ln.unit_price_minor,
                    line_total_minor=ln.line_total_minor,
                )
                for ln in order.lines
            ],
        )


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def place_order(body: OrderIn, sm: SessionMaker, settings: AppSettings) -> OrderOut:
    """201 for every order that was accepted for processing, including REJECTED ones:
    the order exists and its status says what happened. 422 means nothing was stored."""
    try:
        async with sm() as session, session.begin():
            order = await service.place_order(
                session,
                body.customer_id,
                [(ln.product_id, ln.quantity) for ln in body.lines],
                settings.currency,
                atomic_reservation=settings.atomic_stock_reservation,
            )
    except (
        service.CustomerNotFoundError,
        inventory_service.ProductNotFoundError,
        service.InvalidOrderError,
    ) as exc:
        raise HTTPException(422, str(exc)) from exc
    return OrderOut.from_domain(order)


@router.get("/orders/{order_id}")
async def get_order(order_id: UUID, sm: SessionMaker) -> OrderOut:
    try:
        async with sm() as session:
            order = await service.get_order(session, order_id)
    except service.OrderNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return OrderOut.from_domain(order)


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: UUID, sm: SessionMaker) -> OrderOut:
    try:
        async with sm() as session, session.begin():
            order = await service.cancel_order(session, order_id)
    except service.OrderNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (service.InvalidTransitionError, NotImplementedError) as exc:
        raise HTTPException(409, str(exc)) from exc
    return OrderOut.from_domain(order)
