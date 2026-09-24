from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from monolith.config import Settings


def make_engine(database_url: str) -> AsyncEngine:
    # pool_pre_ping: replace dead pooled connections (e.g. after a Postgres restart)
    # instead of failing the request that picks one up.
    return create_async_engine(database_url, pool_pre_ping=True)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def get_sessionmaker(request: Request) -> async_sessionmaker[AsyncSession]:
    """FastAPI dependency. Routes open the session and the transaction themselves, so the
    commit happens (or fails) before the response is built: no 201 for a rolled-back order."""
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    return sessionmaker


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SessionMaker = Annotated[async_sessionmaker[AsyncSession], Depends(get_sessionmaker)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
