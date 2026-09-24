"""The Order aggregate: the consistency boundary for an order and its lines.

All state changes go through methods that enforce the state machine in PROJECT_BRIEF section 3.
Pure Python: no framework or database imports.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"


_ALLOWED: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset(
        {OrderStatus.APPROVED, OrderStatus.REJECTED, OrderStatus.CANCELLED}
    ),
    OrderStatus.APPROVED: frozenset({OrderStatus.SHIPPED, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPED: frozenset(),
    OrderStatus.REJECTED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


class InvalidOrderError(ValueError):
    """The order can't be created as requested (empty, bad quantity, duplicate line…)."""


class InvalidTransitionError(Exception):
    def __init__(self, current: OrderStatus, target: OrderStatus) -> None:
        super().__init__(f"cannot move order from {current} to {target}")
        self.current = current
        self.target = target


@dataclass(frozen=True, slots=True)
class OrderLine:
    product_id: UUID
    quantity: int
    unit_price_minor: int  # snapshot of the product price when the order was placed

    @property
    def line_total_minor(self) -> int:
        return self.quantity * self.unit_price_minor


@dataclass(slots=True)
class Order:
    id: UUID
    customer_id: UUID
    currency: str
    lines: tuple[OrderLine, ...]
    status: OrderStatus = OrderStatus.PENDING
    rejection_reason: str | None = None
    history: list[OrderStatus] = field(default_factory=list)

    @classmethod
    def create(cls, customer_id: UUID, currency: str, lines: Sequence[OrderLine]) -> "Order":
        if not lines:
            raise InvalidOrderError("an order needs at least one line")
        seen: set[UUID] = set()
        for line in lines:
            if line.quantity <= 0:
                raise InvalidOrderError(f"quantity must be positive for {line.product_id}")
            if line.unit_price_minor < 0:
                raise InvalidOrderError(f"negative price for {line.product_id}")
            if line.product_id in seen:
                raise InvalidOrderError(f"product {line.product_id} appears more than once")
            seen.add(line.product_id)
        return cls(id=uuid.uuid4(), customer_id=customer_id, currency=currency, lines=tuple(lines))

    @property
    def total_minor(self) -> int:
        return sum(line.line_total_minor for line in self.lines)

    def approve(self) -> None:
        self._move_to(OrderStatus.APPROVED)

    def reject(self, reason: str) -> None:
        self._move_to(OrderStatus.REJECTED)
        self.rejection_reason = reason

    def ship(self) -> None:
        self._move_to(OrderStatus.SHIPPED)

    def cancel(self) -> None:
        self._move_to(OrderStatus.CANCELLED)

    def _move_to(self, target: OrderStatus) -> None:
        if target not in _ALLOWED[self.status]:
            raise InvalidTransitionError(self.status, target)
        self.history.append(self.status)
        self.status = target
