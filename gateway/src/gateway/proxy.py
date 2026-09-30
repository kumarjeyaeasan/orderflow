"""Forwarding (reverse proxy): pass a client's request to an upstream service, return its answer."""

from collections.abc import Iterable

import httpx
import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from orderflow_common.correlation import get_correlation_id

logger = structlog.get_logger()

# "Hop-by-hop" headers describe ONE network connection (client <-> gateway), so they must not be
# copied onto the next one (gateway <-> upstream). Lowercase, because filter_headers() compares
# names in lowercase.
HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)

# Request headers we don't copy to the upstream:
# - host: must be the upstream's own name ("monolith:8010"), not "localhost:8000";
#   httpx sets it from the URL.
# - content-length: httpx recalculates it for the body it sends.
# - x-correlation-id: forward() sets the *validated* ID from the middleware instead. Copying the
#   raw one as well would send two correlation headers (e.g. "garbage" and the real UUID).
REQUEST_HEADERS_TO_DROP = HOP_BY_HOP | {"host", "content-length", "x-correlation-id"}

# Response headers we don't copy back to the client:
# - content-length: Starlette recalculates it for the body we return.
# - content-encoding: httpx has already unzipped the body, so "gzip" would no longer be true.
RESPONSE_HEADERS_TO_DROP = HOP_BY_HOP | {"content-length", "content-encoding"}


def filter_headers(headers: Iterable[tuple[str, str]], drop: frozenset[str]) -> dict[str, str]:
    """Return a new dict with every (name, value) whose lowercase name is not in `drop`.

    Args:
        headers: (name, value) pairs, e.g.
            [("host", "localhost:8000"),
             ("content-type", "application/json"),
             ("connection", "keep-alive")]
        drop: lowercase names to leave out, e.g. REQUEST_HEADERS_TO_DROP.

    Returns:
        The remaining headers. With the example above and REQUEST_HEADERS_TO_DROP:
            {"content-type": "application/json"}

    Known limitation (accepted): a header that appears twice (e.g. two Set-Cookie) keeps only
    the last value. OrderFlow doesn't send repeated headers.
    """
    return {name: value for name, value in headers if name.lower() not in drop}


async def forward(client: httpx.AsyncClient, request: Request, upstream_base: str) -> Response:
    """Send the client's request to the upstream and return the upstream's answer unchanged.

    Args:
        client: the shared httpx client created in main.py's lifespan (a fake one in tests).
        request: the incoming client request, e.g. POST /orders?dry=1 with a JSON body.
        upstream_base: base URL from resolve_upstream(), e.g. "http://monolith:8010".

    Returns:
        - The upstream's response: same status code, body and (filtered) headers. Error statuses
          pass through too, e.g. 201 {"status": "SHIPPED", ...}, 404 {"detail": "unknown
          order ..."} or 422.
        - 502 {"detail": "upstream unavailable"} only when the upstream gave no answer at all
          (connection refused, DNS failure, timeout).

    Example: POST /orders?dry=1 with upstream_base "http://monolith:8010"
        -> sends POST http://monolith:8010/orders?dry=1 with the same body and the validated
           X-Correlation-ID.
    """
    # 1. Target URL = upstream base + the same path + the same query string.
    #    e.g. "http://monolith:8010" + "/orders/123" + "?x=1"
    url = upstream_base.rstrip("/") + request.url.path
    if request.url.query:
        url += f"?{request.url.query}"

    # 2. Copy the client's headers, minus those that must not travel onwards (see constants above).
    headers = filter_headers(request.headers.items(), REQUEST_HEADERS_TO_DROP)

    # Pass on the correlation ID that CorrelationIdMiddleware validated (or created), so the
    # gateway's and the upstream's log lines for one request share the same ID.
    cid = get_correlation_id()
    if cid is not None:
        headers["X-Correlation-ID"] = cid

    # 3. Read the client's body (empty bytes for GET).
    body = await request.body()

    # 4. Call the upstream. Only "no answer at all" is an error here: TransportError covers
    #    connection refused, DNS failure and timeouts (httpx 0.28). No explicit timeout yet:
    #    httpx's default of 5 s applies until Phase 3. Don't catch plain Exception: a bug in our
    #    code must surface as a 500, not look like "upstream down".
    try:
        upstream = await client.request(
            method=request.method, url=url, headers=headers, content=body
        )
    except httpx.TransportError as exc:
        logger.warning("upstream_unavailable", upstream=upstream_base, error=repr(exc))
        return JSONResponse(status_code=502, content={"detail": "upstream unavailable"})

    # 5. Return the upstream's answer as it is. No raise_for_status(): a 404 or 422 from the
    #    upstream is a valid answer for the client, not a gateway failure.
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=filter_headers(upstream.headers.items(), RESPONSE_HEADERS_TO_DROP),
    )
