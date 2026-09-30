from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI


@asynccontextmanager
async def running_app(app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """An httpx client against the app with its lifespan started (ASGITransport doesn't run it)."""
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client
