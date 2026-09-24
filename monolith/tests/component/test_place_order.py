"""The Place Order flow in one transaction (Phase 0), through the HTTP API."""

from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from .seed import ALICE, DAN, KEYBOARD, LAMP, MOUSE, ZOE

Scalar = Callable[..., Awaitable[Any]]


def _order(customer: object, *lines: tuple[object, int]) -> dict[str, Any]:
    return {
        "customer_id": str(customer),
        "lines": [{"product_id": str(p), "quantity": q} for p, q in lines],
    }


async def _stock(scalar: Scalar, product: object) -> int:
    return int(await scalar("SELECT stock_qty FROM inventory.products WHERE id = :id", id=product))


async def _balance(scalar: Scalar, customer: object) -> int:
    return int(
        await scalar(
            "SELECT balance_minor FROM payment.wallets WHERE customer_id = :id", id=customer
        )
    )


async def _count(scalar: Scalar, table: str) -> int:
    return int(await scalar(f"SELECT count(*) FROM {table}"))


# ---------- happy path ----------


async def test_successful_order_is_shipped_and_every_module_did_its_part(
    client: httpx.AsyncClient, scalar: Scalar
) -> None:
    r = await client.post("/orders", json=_order(ALICE, (KEYBOARD, 2), (MOUSE, 1)))

    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "SHIPPED"
    assert body["total_minor"] == 2 * 8999 + 2499
    assert body["currency"] == "USD"
    assert await _stock(scalar, KEYBOARD) == 48
    assert await _stock(scalar, MOUSE) == 99
    assert await _balance(scalar, ALICE) == 1_000_000 - (2 * 8999 + 2499)
    assert await _count(scalar, "payment.payments") == 1
    assert await _count(scalar, "shipping.shipments") == 1
    statuses = await scalar(
        "SELECT string_agg(order_status, ',' ORDER BY order_status) "
        "FROM notification.notification_log WHERE order_id = :id",
        id=body["id"],
    )
    assert statuses == "APPROVED,SHIPPED"

    fetched = await client.get(f"/orders/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


async def test_price_is_snapshotted_at_order_time(
    client: httpx.AsyncClient, scalar: Scalar, engine: Any
) -> None:
    from sqlalchemy import text

    r = await client.post("/orders", json=_order(ALICE, (KEYBOARD, 1)))
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE inventory.products SET price_minor = 1 WHERE id = :id"), {"id": KEYBOARD}
        )

    fetched = (await client.get(f"/orders/{r.json()['id']}")).json()
    assert fetched["lines"][0]["unit_price_minor"] == 8999
    assert fetched["total_minor"] == 8999


# ---------- business failures: order stored as REJECTED, everything else rolled back ----------


async def test_payment_failure_leaves_stock_unchanged(
    client: httpx.AsyncClient, scalar: Scalar
) -> None:
    """Phase 0 acceptance criterion: single-transaction rollback."""
    r = await client.post("/orders", json=_order(ZOE, (KEYBOARD, 1)))

    assert r.status_code == 201
    assert r.json()["status"] == "REJECTED"
    assert r.json()["rejection_reason"] == "insufficient funds"
    assert await _stock(scalar, KEYBOARD) == 50  # reserved, then rolled back with the charge
    assert await _balance(scalar, ZOE) == 0
    assert await _count(scalar, "payment.payments") == 0
    assert await _count(scalar, "shipping.shipments") == 0
    assert await scalar("SELECT status FROM orders.orders WHERE id = :id", id=r.json()["id"]) == (
        "REJECTED"
    )
    assert (
        await scalar(
            "SELECT order_status FROM notification.notification_log WHERE order_id = :id",
            id=r.json()["id"],
        )
        == "REJECTED"
    )


async def test_partial_funds_charge_nothing(client: httpx.AsyncClient, scalar: Scalar) -> None:
    r = await client.post("/orders", json=_order(DAN, (KEYBOARD, 1)))  # 8999 > 3000
    assert r.json()["status"] == "REJECTED"
    assert await _balance(scalar, DAN) == 3000


async def test_insufficient_stock_is_rejected_without_charging(
    client: httpx.AsyncClient, scalar: Scalar
) -> None:
    r = await client.post("/orders", json=_order(ALICE, (LAMP, 2)))

    assert r.status_code == 201
    assert r.json()["status"] == "REJECTED"
    assert r.json()["rejection_reason"] == f"insufficient stock for product {LAMP}"
    assert await _stock(scalar, LAMP) == 1
    assert await _balance(scalar, ALICE) == 1_000_000


async def test_reservation_is_all_or_nothing(client: httpx.AsyncClient, scalar: Scalar) -> None:
    # KEYBOARD sorts before LAMP, so it is decremented first; LAMP then fails.
    r = await client.post("/orders", json=_order(ALICE, (KEYBOARD, 3), (LAMP, 2)))

    assert r.json()["status"] == "REJECTED"
    assert await _stock(scalar, KEYBOARD) == 50
    assert await _stock(scalar, LAMP) == 1


# ---------- invalid requests: 422, nothing stored ----------


async def test_unknown_customer_is_refused_and_nothing_is_stored(
    client: httpx.AsyncClient, scalar: Scalar
) -> None:
    r = await client.post(
        "/orders", json=_order("30000000-0000-4000-8000-000000000000", (KEYBOARD, 1))
    )
    assert r.status_code == 422
    assert "unknown customer" in r.json()["detail"]
    assert await _count(scalar, "orders.orders") == 0


async def test_unknown_product_is_refused(client: httpx.AsyncClient, scalar: Scalar) -> None:
    r = await client.post(
        "/orders", json=_order(ALICE, (KEYBOARD, 1), ("30000000-0000-4000-8000-000000000000", 1))
    )
    assert r.status_code == 422
    assert "unknown product" in r.json()["detail"]
    assert await _count(scalar, "orders.orders") == 0
    assert await _stock(scalar, KEYBOARD) == 50


async def test_malformed_orders_are_refused(client: httpx.AsyncClient, scalar: Scalar) -> None:
    bad = [
        _order(ALICE),  # no lines
        _order(ALICE, (KEYBOARD, 0)),
        _order(ALICE, (KEYBOARD, -1)),
        _order(ALICE, (KEYBOARD, 1), (KEYBOARD, 1)),  # duplicate line
        {"customer_id": "not-a-uuid", "lines": [{"product_id": str(KEYBOARD), "quantity": 1}]},
    ]
    for payload in bad:
        r = await client.post("/orders", json=payload)
        assert r.status_code == 422, payload
    assert await _count(scalar, "orders.orders") == 0


# ---------- read and cancel ----------


async def test_unknown_order_is_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/orders/30000000-0000-4000-8000-000000000000")
    assert r.status_code == 404


async def test_cancel_of_terminal_order_is_409_and_changes_nothing(
    client: httpx.AsyncClient, scalar: Scalar
) -> None:
    shipped = (await client.post("/orders", json=_order(ALICE, (KEYBOARD, 1)))).json()
    rejected = (await client.post("/orders", json=_order(ZOE, (KEYBOARD, 1)))).json()

    for order in (shipped, rejected):
        r = await client.post(f"/orders/{order['id']}/cancel")
        assert r.status_code == 409
        assert (await client.get(f"/orders/{order['id']}")).json()["status"] == order["status"]
    assert await _stock(scalar, KEYBOARD) == 49


async def test_cancel_unknown_order_is_404(client: httpx.AsyncClient) -> None:
    r = await client.post("/orders/30000000-0000-4000-8000-000000000000/cancel")
    assert r.status_code == 404
