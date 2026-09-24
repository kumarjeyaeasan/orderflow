"""Component-test fixtures: one throwaway Postgres 16 per test session, migrated to head."""

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
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


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    with PostgresContainer("postgres:16", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        cfg = Config(str(ALEMBIC_INI))
        cfg.set_main_option("sqlalchemy.url", url)
        cfg.attributes["configure_logger"] = False  # keep pytest's logging setup
        command.upgrade(cfg, "head")
        yield url


@pytest.fixture(scope="session")
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(database_url)
    yield eng
    await eng.dispose()


@pytest.fixture
async def client(database_url: str) -> AsyncIterator[httpx.AsyncClient]:
    async with running_app(create_app(Settings(database_url=database_url))) as c:
        yield c
