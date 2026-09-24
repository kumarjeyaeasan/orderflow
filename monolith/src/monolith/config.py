from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (and a local .env for dev)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "monolith"
    # No default, so a missing value fails fast at startup.
    # e.g. postgresql+asyncpg://orderflow:orderflow@localhost:5432/orderflow
    database_url: str
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    log_level: str = "INFO"
    # Upper bound for the readiness probe's DB check so /health/ready never hangs.
    db_ready_timeout_s: float = 2.0
    # Phase 0 break-it toggle. false = naive read-check-write stock reservation (oversells under
    # concurrency); true = one conditional UPDATE per line (exactly one winner for the last unit).
    atomic_stock_reservation: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
