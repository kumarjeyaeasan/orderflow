"""Component-test fixtures: one throwaway Postgres 16 per test session.

Every test starts from a freshly migrated and seeded database (downgrade to base, upgrade to head),
so tests can't leak state into each other, and every migration's downgrade() is exercised too.
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from monolith.config import Settings
from monolith.main import create_app

from ..helpers import running_app

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "component" in str(item.path):
            item.add_marker(pytest.mark.component)


def _alembic(url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False  # keep pytest's logging setup
    return cfg


def _reset_schema(url: str) -> None:
    cfg = _alembic(url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    with PostgresContainer("postgres:16", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        command.upgrade(_alembic(url), "head")
        yield url


@pytest.fixture(scope="session")
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(database_url)
    yield eng
    await eng.dispose()


@pytest.fixture(autouse=True)
async def fresh_db(database_url: str, engine: AsyncEngine) -> None:
    await engine.dispose()  # no pooled connection survives into the reset
    # Alembic's async env calls asyncio.run(), which can't run inside this event loop: use a thread.
    await asyncio.to_thread(_reset_schema, database_url)


@pytest.fixture
def app_client(
    database_url: str,
) -> Callable[..., AbstractAsyncContextManager[httpx.AsyncClient]]:
    """A client factory for custom settings: app_client(atomic_stock_reservation=False)."""

    def make(**overrides: Any) -> AbstractAsyncContextManager[httpx.AsyncClient]:
        return running_app(create_app(Settings(database_url=database_url, **overrides)))

    return make


@pytest.fixture
async def client(
    app_client: Callable[..., AbstractAsyncContextManager[httpx.AsyncClient]],
) -> AsyncIterator[httpx.AsyncClient]:
    async with app_client() as c:
        yield c


@pytest.fixture
def scalar(engine: AsyncEngine) -> Callable[..., Awaitable[Any]]:
    """Run one read-only SQL query and return the first column of the first row."""

    async def run(sql: str, **params: Any) -> Any:
        async with engine.connect() as conn:
            return (await conn.execute(text(sql), params)).scalar()

    return run
