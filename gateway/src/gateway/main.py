"""The gateway app: the single front door for clients (API Gateway pattern).

In Docker (step 2b) it's started by:
    uvicorn gateway.main:create_app --factory --host 0.0.0.0 --port 8000
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from gateway.config import Settings, get_settings
from gateway.proxy import forward
from gateway.routing import PUBLIC_PREFIXES, resolve_upstream
from orderflow_common.correlation import CorrelationIdMiddleware
from orderflow_common.logging import configure_logging


def create_app(
    settings: Settings | None = None, upstream_transport: httpx.AsyncBaseTransport | None = None
) -> FastAPI:
    """Build and configure the gateway app.

    Args:
        settings: configuration. None (production) = read from env vars via get_settings().
            Tests pass one directly, e.g. Settings(monolith_url="http://monolith.test").
        upstream_transport: how the gateway reaches the upstream. None (production) = the real
            network. Tests pass a fake monolith, e.g. httpx.MockTransport(handler), where
            handler(request) returns httpx.Response(200, json={"ok": True}).

    Returns:
        A FastAPI app with three kinds of routes, e.g. with monolith_url="http://monolith:8010":
            GET  /health/live       -> 200 {"status": "ok"}  (answered by the gateway itself)
            GET  /health/ready      -> 200 {"status": "ok"}  (answered by the gateway itself)
            POST /orders            -> forwarded to http://monolith:8010/orders
            GET  /internal/x, /nope -> 404 {"detail": "not found"} (never reaches the monolith)
    """
    # 1. Configuration and logging. Tests pass their own Settings; production reads env vars.
    settings = settings or get_settings()
    configure_logging(settings.service_name, settings.log_level)

    # 2. Route table: which path prefix goes to which upstream. For now everything public goes to
    #    the monolith, e.g. {"/products": "http://monolith:8010", "/orders": ..., "/admin": ...}.
    #    When a prefix moves to a new service (Phase 2+), only this table changes.
    routes = {prefix: settings.monolith_url for prefix in PUBLIC_PREFIXES}

    # 3. One shared HTTP client for the app's whole life: it reuses connections to the upstream
    #    instead of opening a new one per request. Created at startup, closed at shutdown.
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        client = httpx.AsyncClient(transport=upstream_transport)
        app.state.client = client
        try:
            yield
        finally:
            await client.aclose()

    # 4. The app, with the correlation-ID middleware: every request gets a validated
    #    X-Correlation-ID, which forward() passes on to the upstream.
    app = FastAPI(title="OrderFlow gateway", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CorrelationIdMiddleware)

    # 5. Health routes. They MUST be registered before the catch-all below: FastAPI tries routes
    #    in the order they were added, so a catch-all added first would swallow /health/live too.
    #    Readiness doesn't check the monolith yet; dependency-aware readiness is a Phase 3 topic.
    @app.get("/health/live")
    async def live_probe() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready_probe() -> dict[str, str]:
        return {"status": "ok"}

    # 6. Catch-all: every other path and method lands here. `path` is unused (we read
    #    request.url.path, which keeps the leading "/"), but FastAPI needs it in the signature
    #    because it's part of the route pattern.
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def proxy_catch_all(request: Request, path: str) -> Response:
        upstream = resolve_upstream(request.url.path, routes)
        if upstream is None:
            # Not a public route (e.g. /internal/...): refuse it here; the upstream never sees it.
            return JSONResponse(status_code=404, content={"detail": "not found"})

        client: httpx.AsyncClient = request.app.state.client
        return await forward(client, request, upstream)

    return app
