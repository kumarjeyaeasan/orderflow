"""The whole gateway app, tested against a fake monolith (no network, no Docker)."""

import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

import httpx

from gateway.config import Settings
from gateway.main import create_app

Handler = Callable[[httpx.Request], httpx.Response]


@asynccontextmanager
async def gateway_client(handler: Handler) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Context manager that provisions a completely in-memory API Gateway instance.

    Uses ASGITransport to pipe client requests into the gateway app, and binds
    MockTransport to reroute gateway outbound traffic into a programmable monolith stub.
    """
    # Initialize the custom application using the provided network mock handler
    settings = Settings(
        service_name="gateway-test", log_level="WARNING", monolith_url="http://monolith.test"
    )
    app = create_app(settings=settings, upstream_transport=httpx.MockTransport(handler))

    # Execute the application lifespan context safely
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway.test"
        ) as client,
    ):
        yield client


def fake_monolith(recorded: list[httpx.Request], response: httpx.Response) -> Handler:
    """A fake monolith: remembers every request it receives and always answers `response`."""

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return response

    return handler


# ---------- requests that are passed on ----------


async def test_get_is_forwarded_with_path_and_query() -> None:
    recorded: list[httpx.Request] = []
    handler = fake_monolith(recorded, httpx.Response(200, json={"ok": True}))

    async with gateway_client(handler) as client:
        r = await client.get("/products/abc?x=1")

    assert len(recorded) == 1
    assert recorded[0].method == "GET"
    assert str(recorded[0].url) == "http://monolith.test/products/abc?x=1"
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_post_body_and_status_are_passed_through() -> None:
    recorded: list[httpx.Request] = []
    handler = fake_monolith(recorded, httpx.Response(201, json={"status": "SHIPPED"}))
    body = {"customer_id": "c1", "lines": [{"product_id": "p1", "quantity": 2}]}

    async with gateway_client(handler) as client:
        r = await client.post("/orders", json=body)

    assert recorded[0].method == "POST"
    assert httpx.Response(200, content=recorded[0].content).json() == body
    assert r.status_code == 201
    assert r.json() == {"status": "SHIPPED"}


async def test_upstream_error_status_is_not_changed() -> None:
    """A 422 from the monolith is a valid answer: it must reach the client as 422, not 502."""
    recorded: list[httpx.Request] = []
    handler = fake_monolith(recorded, httpx.Response(422, json={"detail": "bad"}))

    async with gateway_client(handler) as client:
        r = await client.post("/orders", json={})

    assert r.status_code == 422
    assert r.json() == {"detail": "bad"}


# ---------- headers ----------


async def test_correlation_id_goes_upstream_and_back() -> None:
    recorded: list[httpx.Request] = []
    handler = fake_monolith(recorded, httpx.Response(200))
    cid = str(uuid.uuid4())

    async with gateway_client(handler) as client:
        r = await client.get("/orders/1", headers={"X-Correlation-ID": cid})

    assert recorded[0].headers["x-correlation-id"] == cid
    assert r.headers["x-correlation-id"] == cid


async def test_malformed_correlation_id_is_replaced_not_duplicated() -> None:
    """A bad incoming ID is replaced by a valid one, and the monolith gets exactly one ID."""
    recorded: list[httpx.Request] = []
    handler = fake_monolith(recorded, httpx.Response(200))

    async with gateway_client(handler) as client:
        await client.get("/orders/1", headers={"X-Correlation-ID": "garbage"})

    sent = recorded[0].headers.get_list("x-correlation-id")
    assert len(sent) == 1
    assert sent[0] != "garbage"
    uuid.UUID(sent[0])  # raises if it isn't a valid UUID


async def test_host_header_is_the_monolith() -> None:
    """The client's Host (the gateway) must not be copied; the monolith gets its own name."""
    recorded: list[httpx.Request] = []
    handler = fake_monolith(recorded, httpx.Response(200))

    async with gateway_client(handler) as client:
        await client.get("/products")

    assert recorded[0].headers["host"] == "monolith.test"


# ---------- requests that are refused (never reach the monolith) ----------


async def test_internal_path_is_404_and_never_forwarded() -> None:
    recorded: list[httpx.Request] = []
    handler = fake_monolith(recorded, httpx.Response(200))

    async with gateway_client(handler) as client:
        r = await client.get("/internal/customers/x")

    assert r.status_code == 404
    assert r.json() == {"detail": "not found"}
    assert recorded == []


async def test_unknown_path_is_404() -> None:
    recorded: list[httpx.Request] = []
    handler = fake_monolith(recorded, httpx.Response(200))

    async with gateway_client(handler) as client:
        r = await client.get("/nope")

    assert r.status_code == 404
    assert recorded == []


# ---------- the monolith is down ----------


async def test_unreachable_monolith_gives_502() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with gateway_client(refuse) as client:
        r = await client.get("/products")

    assert r.status_code == 502
    assert r.json() == {"detail": "upstream unavailable"}


# ---------- the gateway's own routes ----------


async def test_health_live_does_not_call_the_monolith() -> None:
    recorded: list[httpx.Request] = []
    handler = fake_monolith(recorded, httpx.Response(200))

    async with gateway_client(handler) as client:
        r = await client.get("/health/live")

    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert recorded == []
