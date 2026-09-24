from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from .seed import ALICE, KEYBOARD, LAMP

UNKNOWN = "30000000-0000-4000-8000-000000000000"
Scalar = Callable[..., Awaitable[Any]]


async def test_list_products(client: httpx.AsyncClient) -> None:
    r = await client.get("/products")
    assert r.status_code == 200
    products = r.json()
    assert len(products) == 10
    assert all(isinstance(p["price_minor"], int) and p["currency"] == "USD" for p in products)


async def test_get_product(client: httpx.AsyncClient) -> None:
    r = await client.get(f"/products/{LAMP}")
    assert r.status_code == 200
    assert r.json()["stock_qty"] == 1


async def test_get_unknown_product_is_404(client: httpx.AsyncClient) -> None:
    assert (await client.get(f"/products/{UNKNOWN}")).status_code == 404


async def test_adjust_stock_up_and_down(client: httpx.AsyncClient) -> None:
    r = await client.post(f"/admin/products/{KEYBOARD}/stock", json={"delta": 5})
    assert r.json() == {"product_id": str(KEYBOARD), "stock_qty": 55}
    r = await client.post(f"/admin/products/{KEYBOARD}/stock", json={"delta": -55})
    assert r.json()["stock_qty"] == 0


async def test_adjust_stock_below_zero_is_refused(client: httpx.AsyncClient) -> None:
    r = await client.post(f"/admin/products/{LAMP}/stock", json={"delta": -2})
    assert r.status_code == 422
    assert (await client.get(f"/products/{LAMP}")).json()["stock_qty"] == 1


async def test_adjust_stock_of_unknown_product_is_404(client: httpx.AsyncClient) -> None:
    r = await client.post(f"/admin/products/{UNKNOWN}/stock", json={"delta": 1})
    assert r.status_code == 404


async def test_wallet_top_up(client: httpx.AsyncClient) -> None:
    r = await client.post(f"/admin/customers/{ALICE}/wallet", json={"amount_minor": 500})
    assert r.json() == {"customer_id": str(ALICE), "balance_minor": 1_000_500}


async def test_wallet_top_up_must_be_positive(client: httpx.AsyncClient, scalar: Scalar) -> None:
    for amount in (0, -100):
        r = await client.post(f"/admin/customers/{ALICE}/wallet", json={"amount_minor": amount})
        assert r.status_code == 422
    balance = await scalar(
        "SELECT balance_minor FROM payment.wallets WHERE customer_id = :id", id=ALICE
    )
    assert balance == 1_000_000


async def test_wallet_top_up_for_unknown_customer_is_404(client: httpx.AsyncClient) -> None:
    r = await client.post(f"/admin/customers/{UNKNOWN}/wallet", json={"amount_minor": 1})
    assert r.status_code == 404
