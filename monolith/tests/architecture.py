"""Static import checks for the modular monolith (constraint C2).

Rule 1 (boundary): code in module A may import from module B only `<pkg>.B.service`
           (e.g. `from monolith.modules.inventory import service`),
           never B's api/, domain/ or infra/.
Rule 2 (purity):   code under any `domain/` package imports no framework or infrastructure library.

Uses only `ast`, so it runs without importing (or even being able to import) the code it checks.
"""

import ast
from dataclasses import dataclass
from pathlib import Path

FRAMEWORK_PREFIXES = (
    "fastapi",
    "starlette",
    "sqlalchemy",
    "alembic",
    "asyncpg",
    "pydantic",
    "pydantic_settings",
    "httpx",
    "structlog",
    "uvicorn",
)


@dataclass(frozen=True)
class Violation:
    file: Path
    line: int
    imported: str
    rule: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.rule}: imports {self.imported}"


def _imports(tree: ast.Module, module_name: str, is_package: bool) -> list[tuple[int, str]]:
    """Every imported dotted name, with relative imports resolved to absolute ones.

    `from x import y` yields `x.y`; y may be a submodule or a symbol, and both count as
    reaching into x.
    """
    package_parts = module_name.split(".") if is_package else module_name.split(".")[:-1]
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = package_parts[: len(package_parts) - (node.level - 1)]
                base = ".".join(base_parts + ([node.module] if node.module else []))
            else:
                base = node.module or ""
            found.extend((node.lineno, f"{base}.{alias.name}") for alias in node.names)
    return found


def find_violations(modules_dir: Path, modules_package: str) -> list[Violation]:
    """Check every .py file under `modules_dir` (whose import path is `modules_package`)."""
    violations: list[Violation] = []
    for path in sorted(modules_dir.rglob("*.py")):
        rel = path.relative_to(modules_dir)
        if len(rel.parts) < 2:  # modules/__init__.py itself
            continue
        own_module = rel.parts[0]
        is_package = path.name == "__init__.py"
        dotted = ".".join((modules_package, *rel.with_suffix("").parts))
        if is_package:
            dotted = dotted.removesuffix(".__init__")
        tree = ast.parse(path.read_text(), filename=str(path))
        in_domain = "domain" in rel.parts[1:-1] or (is_package and rel.parts[-2] == "domain")

        for lineno, name in _imports(tree, dotted, is_package):
            if name.startswith(modules_package + "."):
                parts = name.removeprefix(modules_package + ".").split(".")
                target = parts[0]
                if target != own_module and parts[:2] != [target, "service"]:
                    violations.append(Violation(path, lineno, name, "cross-module internals"))
            if in_domain and name.split(".")[0] in FRAMEWORK_PREFIXES:
                violations.append(Violation(path, lineno, name, "framework import in domain"))
    return violations
