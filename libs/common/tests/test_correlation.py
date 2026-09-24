import uuid

import httpx
import structlog
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from orderflow_common.correlation import (
    CORRELATION_HEADER,
    CorrelationIdMiddleware,
    get_correlation_id,
)


async def _echo(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "from_accessor": get_correlation_id(),
            "from_log_context": structlog.contextvars.get_contextvars().get("correlation_id"),
        }
    )


def _client() -> httpx.AsyncClient:
    app = CorrelationIdMiddleware(Starlette(routes=[Route("/", _echo)]))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_generates_id_when_missing() -> None:
    async with _client() as c:
        r = await c.get("/")
    cid = r.headers[CORRELATION_HEADER]
    uuid.UUID(cid)  # raises if not a UUID
    assert r.json() == {"from_accessor": cid, "from_log_context": cid}


async def test_propagates_incoming_id() -> None:
    cid = str(uuid.uuid4())
    async with _client() as c:
        r = await c.get("/", headers={CORRELATION_HEADER: cid})
    assert r.headers[CORRELATION_HEADER] == cid
    assert r.json()["from_log_context"] == cid


async def test_replaces_malformed_id() -> None:
    async with _client() as c:
        r = await c.get("/", headers={CORRELATION_HEADER: "not-a-uuid <script>"})
    cid = r.headers[CORRELATION_HEADER]
    assert cid != "not-a-uuid"
    uuid.UUID(cid)


async def test_context_is_cleared_after_request() -> None:
    async with _client() as c:
        await c.get("/")
    assert get_correlation_id() is None
    assert "correlation_id" not in structlog.contextvars.get_contextvars()
