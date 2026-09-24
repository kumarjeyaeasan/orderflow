import uuid

import pytest

from monolith.modules.order.domain.model import (
    InvalidOrderError,
    InvalidTransitionError,
    Order,
    OrderLine,
    OrderStatus,
)

P1, P2 = uuid.uuid4(), uuid.uuid4()
CUSTOMER = uuid.uuid4()


def _order() -> Order:
    return Order.create(CUSTOMER, "USD", [OrderLine(P1, 2, 1000), OrderLine(P2, 1, 250)])


def test_new_order_is_pending_with_integer_total() -> None:
    order = _order()
    assert order.status is OrderStatus.PENDING
    assert order.total_minor == 2250
    assert isinstance(order.total_minor, int)


@pytest.mark.parametrize(
    ("lines", "message"),
    [
        ([], "at least one line"),
        ([OrderLine(P1, 0, 100)], "quantity must be positive"),
        ([OrderLine(P1, -1, 100)], "quantity must be positive"),
        ([OrderLine(P1, 1, -5)], "negative price"),
        ([OrderLine(P1, 1, 100), OrderLine(P1, 2, 100)], "more than once"),
    ],
)
def test_invalid_orders_are_refused(lines: list[OrderLine], message: str) -> None:
    with pytest.raises(InvalidOrderError, match=message):
        Order.create(CUSTOMER, "USD", lines)


def test_happy_path_transitions() -> None:
    order = _order()
    order.approve()
    order.ship()
    assert order.status is OrderStatus.SHIPPED
    assert order.history == [OrderStatus.PENDING, OrderStatus.APPROVED]


def test_reject_records_reason() -> None:
    order = _order()
    order.reject("insufficient funds")
    assert (order.status, order.rejection_reason) == (OrderStatus.REJECTED, "insufficient funds")


@pytest.mark.parametrize("start", ["PENDING", "APPROVED"])
def test_cancel_allowed_from_pending_and_approved(start: str) -> None:
    order = _order()
    if start == "APPROVED":
        order.approve()
    order.cancel()
    assert order.status is OrderStatus.CANCELLED


@pytest.mark.parametrize(
    ("path", "illegal"),
    [
        ([], "ship"),  # PENDING -> SHIPPED skips approval
        (["approve"], "reject"),  # APPROVED -> REJECTED isn't in the state machine
        (["approve", "ship"], "cancel"),  # SHIPPED is terminal
        (["reject"], "approve"),  # REJECTED is terminal
        (["cancel"], "approve"),  # CANCELLED is terminal
    ],
)
def test_illegal_transitions_raise_and_leave_state_unchanged(path: list[str], illegal: str) -> None:
    order = _order()
    for step in path:
        getattr(order, step)(*(["r"] if step == "reject" else []))
    before = order.status
    with pytest.raises(InvalidTransitionError):
        getattr(order, illegal)(*(["r"] if illegal == "reject" else []))
    assert order.status is before
