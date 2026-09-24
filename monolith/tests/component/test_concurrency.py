"""Phase 0 break-it: 10 concurrent orders compete for the last lamp (constraint C1).

ATOMIC_STOCK_RESERVATION=false  -> naive read-check-write: more than one order wins (oversold).
ATOMIC_STOCK_RESERVATION=true   -> one conditional UPDATE: exactly one winner.

Both tests pass: the first one *documents* the bug, so it stays reproducible.
"""

import asyncio
from collections import Counter
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

import httpx

from .seed import ALICE, LAMP

N = 10
ORDER = {"customer_id": str(ALICE), "lines": [{"product_id": str(LAMP), "quantity": 1}]}
LAMP_PRICE = 2999

AppClient = Callable[..., AbstractAsyncContextManager[httpx.AsyncClient]]
Scalar = Callable[..., Awaitable[Any]]


async def _race(client: httpx.AsyncClient) -> Counter[str]:
    responses = await asyncio.gather(*(client.post("/orders", json=ORDER) for _ in range(N)))
    assert all(r.status_code == 201 for r in responses), [r.text for r in responses]
    return Counter(r.json()["status"] for r in responses)


async def test_naive_reservation_oversells_the_last_unit(
    app_client: AppClient, scalar: Scalar
) -> None:
    async with app_client(atomic_stock_reservation=False) as client:
        outcome = await _race(client)

    shipped = outcome["SHIPPED"]
    stock = await scalar("SELECT stock_qty FROM inventory.products WHERE id = :id", id=LAMP)
    print(f"\nnaive: {dict(outcome)}, stock left = {stock}")  # visible with pytest -s
    # The bug: one lamp, several paid-for shipments. Stock still reads 0 (lost update), so
    # neither the CHECK constraint nor a stock report would notice.
    assert shipped > 1
    assert stock == 0
    assert await scalar("SELECT count(*) FROM shipping.shipments") == shipped


async def test_atomic_reservation_has_exactly_one_winner(
    app_client: AppClient, scalar: Scalar
) -> None:
    async with app_client(atomic_stock_reservation=True) as client:
        outcome = await _race(client)

    print(f"\natomic: {dict(outcome)}")
    assert outcome == Counter({"SHIPPED": 1, "REJECTED": N - 1})
    assert await scalar("SELECT stock_qty FROM inventory.products WHERE id = :id", id=LAMP) == 0
    assert await scalar("SELECT count(*) FROM payment.payments") == 1
    assert await scalar("SELECT count(*) FROM shipping.shipments") == 1
    balance = await scalar(
        "SELECT balance_minor FROM payment.wallets WHERE customer_id = :id", id=ALICE
    )
    assert balance == 1_000_000 - LAMP_PRICE  # charged once, not ten times
