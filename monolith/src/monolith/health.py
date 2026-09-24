"""Health Check API.

/health/live  — the process is up. Never touches dependencies.
/health/ready — dependencies are reachable (Phase 0: just Postgres). 503 otherwise.
"""

import asyncio

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

router = APIRouter(prefix="/health", tags=["health"])
log = structlog.get_logger(__name__)


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    engine: AsyncEngine = request.app.state.engine
    timeout_s: float = request.app.state.settings.db_ready_timeout_s
    try:
        async with asyncio.timeout(timeout_s), engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    # TimeoutError: DB hangs. OSError: refused / DNS failure. SQLAlchemyError: auth, driver errors.
    except (TimeoutError, OSError, SQLAlchemyError) as exc:
        log.warning("readiness_check_failed", dependency="postgres", error=repr(exc))
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "checks": {"postgres": "down"}},
        )
    return JSONResponse(content={"status": "ok", "checks": {"postgres": "up"}})
