import pytest
from pydantic import ValidationError

from monolith.config import Settings


def test_currency_must_be_iso_4217_shaped() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql+asyncpg://u:p@h/db", currency="usd")


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]
