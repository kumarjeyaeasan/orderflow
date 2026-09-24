"""Health endpoints without a real database."""

import time

from monolith.config import Settings
from monolith.main import create_app

from ..helpers import running_app

# Nothing listens on port 1: connection refused immediately.
REFUSED_URL = "postgresql+asyncpg://u:p@127.0.0.1:1/db"
# A non-routable address: the TCP connect hangs, so only our timeout ends it.
BLACKHOLE_URL = "postgresql+asyncpg://u:p@10.255.255.1:5432/db"


async def test_live_is_ok_even_when_db_is_down() -> None:
    async with running_app(create_app(Settings(database_url=REFUSED_URL))) as client:
        r = await client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_ready_returns_503_when_db_refuses_connections() -> None:
    async with running_app(create_app(Settings(database_url=REFUSED_URL))) as client:
        r = await client.get("/health/ready")
    assert r.status_code == 503
    assert r.json() == {"status": "unavailable", "checks": {"postgres": "down"}}


async def test_ready_returns_503_within_timeout_when_db_hangs() -> None:
    settings = Settings(database_url=BLACKHOLE_URL, db_ready_timeout_s=0.3)
    async with running_app(create_app(settings)) as client:
        start = time.monotonic()
        r = await client.get("/health/ready")
        elapsed = time.monotonic() - start
    assert r.status_code == 503
    assert elapsed < 2.0, f"readiness probe hung for {elapsed:.1f}s"


async def test_responses_carry_a_correlation_id() -> None:
    async with running_app(create_app(Settings(database_url=REFUSED_URL))) as client:
        r = await client.get("/health/live")
    assert r.headers["X-Correlation-ID"]
