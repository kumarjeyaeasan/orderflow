from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (and a local .env for dev)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "gateway"
    log_level: str = "INFO"
    # No default: the gateway must not start without knowing where the monolith is.
    # pydantic-settings reads it from the env var with the same name: MONOLITH_URL.
    monolith_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
