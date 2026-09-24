from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from monolith import health
from monolith.config import Settings, get_settings
from monolith.db import make_engine, make_sessionmaker
from monolith.modules.inventory.api.routes import router as inventory_router
from monolith.modules.order.api.routes import router as order_router
from monolith.modules.payment.api.routes import router as payment_router
from orderflow_common.correlation import CorrelationIdMiddleware
from orderflow_common.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.service_name, settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Creating the engine does not connect, so the app starts (and /health/live answers)
        # even if Postgres is down; /health/ready reports it.
        engine = make_engine(settings.database_url)
        app.state.settings = settings
        app.state.engine = engine
        app.state.sessionmaker = make_sessionmaker(engine)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="OrderFlow monolith", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(health.router)
    app.include_router(inventory_router)
    app.include_router(order_router)
    app.include_router(payment_router)
    return app
