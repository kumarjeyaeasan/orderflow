"""X-Correlation-ID handling.

Every request reads the incoming X-Correlation-ID or creates a new UUIDv4, binds it to the
structlog context for the lifetime of the request, and echoes it on the response.
Written as pure ASGI middleware (not BaseHTTPMiddleware) so the context variable is visible
to the endpoint and to everything it calls.
"""

import uuid
from contextvars import ContextVar

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CORRELATION_HEADER = "X-Correlation-ID"

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Return the correlation ID of the current request, if any (for outbound propagation)."""
    return _correlation_id.get()


def _is_valid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = None
        for name, value in scope["headers"]:
            if name.decode("latin-1").lower() == CORRELATION_HEADER.lower():
                incoming = value.decode("latin-1")
                break
        # Reject malformed values rather than logging arbitrary client input as an ID.
        correlation_id = incoming if incoming and _is_valid(incoming) else str(uuid.uuid4())

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[CORRELATION_HEADER] = correlation_id
            await send(message)

        token = _correlation_id.set(correlation_id)
        try:
            with structlog.contextvars.bound_contextvars(correlation_id=correlation_id):
                await self.app(scope, receive, send_with_header)
        finally:
            _correlation_id.reset(token)
