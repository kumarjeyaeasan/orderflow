"""Module boundaries are enforced by a test, not good intentions (Phase 0 acceptance criterion)."""

from pathlib import Path

import pytest

from ..architecture import Violation, find_violations

MODULES_DIR = Path(__file__).resolve().parents[2] / "src" / "monolith" / "modules"
PKG = "monolith.modules"


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


@pytest.fixture
def fake_modules(tmp_path: Path) -> Path:
    """A tiny two-module tree that follows the rules."""
    root = tmp_path / "modules"
    for m in ("order", "inventory"):
        for layer in ("api", "domain", "infra"):
            _write(root, f"{m}/{layer}/__init__.py", "")
        _write(root, f"{m}/__init__.py", "")
    _write(root, "inventory/service.py", "def reserve(): ...\n")
    _write(root, "inventory/infra/models.py", "import sqlalchemy\n")
    _write(root, "order/service.py", f"from {PKG}.inventory import service\n")
    return root


def test_real_codebase_respects_module_boundaries() -> None:
    violations = find_violations(MODULES_DIR, PKG)
    assert violations == [], "\n".join(map(str, violations))


def test_allowed_imports_pass(fake_modules: Path) -> None:
    _write(fake_modules, "order/api/routes.py", f"import {PKG}.inventory.service\n")
    _write(fake_modules, "order/infra/repo.py", "from ..domain import model\n")  # own module
    assert find_violations(fake_modules, PKG) == []


@pytest.mark.parametrize(
    "source",
    [
        f"from {PKG}.inventory.infra.models import ProductRow\n",
        f"from {PKG}.inventory.domain import model\n",
        f"import {PKG}.inventory.infra.models\n",
        f"from {PKG}.inventory import infra\n",
        "from ...inventory.infra.models import ProductRow\n",  # relative import, same violation
    ],
)
def test_reaching_into_another_modules_internals_fails(fake_modules: Path, source: str) -> None:
    _write(fake_modules, "order/infra/repo.py", source)
    violations = find_violations(fake_modules, PKG)
    assert len(violations) == 1
    assert violations[0].rule == "cross-module internals"
    assert "inventory" in violations[0].imported


@pytest.mark.parametrize("source", ["import sqlalchemy\n", "from fastapi import HTTPException\n"])
def test_framework_import_in_domain_fails(fake_modules: Path, source: str) -> None:
    _write(fake_modules, "order/domain/model.py", source)
    violations = find_violations(fake_modules, PKG)
    assert [v.rule for v in violations] == ["framework import in domain"]


def test_violation_message_points_at_file_and_line(fake_modules: Path) -> None:
    _write(fake_modules, "order/api/x.py", f"\n\nfrom {PKG}.inventory.infra import models\n")
    (v,) = find_violations(fake_modules, PKG)
    assert isinstance(v, Violation)
    assert str(v).endswith(f"x.py:3: cross-module internals: imports {PKG}.inventory.infra.models")
