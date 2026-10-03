"""Architecture guardrails for the modular-monolith dependency direction."""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).parents[2] / "src" / "decision_os"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_domain_has_no_infrastructure_or_application_dependencies() -> None:
    forbidden = (
        "decision_os.application",
        "decision_os.infrastructure",
        "fastapi",
        "sqlalchemy",
        "psycopg",
    )
    violations: list[str] = []
    for path in sorted((ROOT / "domain").rglob("*.py")):
        for imported in _imports(path):
            if any(imported == prefix or imported.startswith(prefix + ".") for prefix in forbidden):
                violations.append(f"{path}: {imported}")
    assert violations == []


def test_application_core_has_no_infrastructure_dependency() -> None:
    forbidden = "decision_os.infrastructure"
    violations: list[str] = []
    for path in sorted((ROOT / "application").rglob("*.py")):
        if "api" in path.parts:
            continue
        for imported in _imports(path):
            if imported == forbidden or imported.startswith(forbidden + "."):
                violations.append(f"{path}: {imported}")
    assert violations == []


def test_domain_to_application_to_infrastructure_dependency_direction_is_explicit() -> None:
    assert (ROOT / "domain").is_dir()
    assert (ROOT / "application").is_dir()
    assert (ROOT / "infrastructure").is_dir()
