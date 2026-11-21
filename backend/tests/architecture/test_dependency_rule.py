"""TDD aplicado à arquitetura (ADR-0003): o domínio só usa a stdlib e o próprio domínio."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "developer_myself"
FORBIDDEN = ("fastapi", "pymongo", "bson", "aio_pika", "pydantic", "starlette", "argon2")
DOMAIN_FILES = sorted(SRC.glob("*/domain/**/*.py"))
APPLICATION_FILES = sorted(SRC.glob("*/application/**/*.py"))
ALL_FILES = sorted(SRC.rglob("*.py"))
# Contextos de orquestração (ADR-0013): leem domain/application dos outros, nunca adapters.
COMPOSERS = {"planning"}
# Quem monta e quem roda o sistema: ninguém de dentro dos contextos depende deles.
OUTER = {"composition": {"composition", "entrypoints"}, "entrypoints": {"entrypoints"}}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def violations(path: Path, *, allow_application: bool) -> list[str]:
    context = path.relative_to(SRC).parts[0]
    bad = []
    for module in imported_modules(path):
        root = module.split(".")[0]
        if root in FORBIDDEN or ".adapters" in module or module.endswith("bootstrap"):
            bad.append(module)
        parts = module.split(".")
        if parts[0] == "developer_myself" and len(parts) > 1:
            other = parts[1]
            if other not in {context, "shared"} and context not in COMPOSERS:
                bad.append(f"{module} (outro contexto)")
            if not allow_application and ".application" in module:
                bad.append(module)
    return bad


def test_domain_files_exist() -> None:
    assert DOMAIN_FILES, "nenhum arquivo de domínio encontrado"


@pytest.mark.parametrize("path", DOMAIN_FILES, ids=lambda p: str(p.relative_to(SRC)))
def test_domain_is_pure(path: Path) -> None:
    assert violations(path, allow_application=False) == []


@pytest.mark.parametrize("path", APPLICATION_FILES, ids=lambda p: str(p.relative_to(SRC)))
def test_application_does_not_know_adapters(path: Path) -> None:
    assert violations(path, allow_application=True) == []


def test_rule_detects_violation() -> None:
    """O próprio teste precisa falhar quando alguém importa pymongo no domínio."""
    fake = SRC / "learning" / "domain" / "_tmp_violation.py"
    try:
        fake.write_text("import pymongo\n")
        assert violations(fake, allow_application=False) == ["pymongo"]
    finally:
        fake.unlink()


def test_package_root_has_no_loose_modules() -> None:
    """Todo módulo mora num contexto, em `composition/` ou em `entrypoints/` (ADR-0013)."""
    assert sorted(p.name for p in SRC.glob("*.py")) == []


def outer_violations(path: Path) -> list[str]:
    owner = path.relative_to(SRC).parts[0]
    bad = []
    for module in imported_modules(path):
        parts = module.split(".")
        if (
            parts[0] == "developer_myself"
            and len(parts) > 1
            and parts[1] in OUTER
            and owner not in OUTER[parts[1]]
        ):
            bad.append(module)
    return bad


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: str(p.relative_to(SRC)))
def test_inner_code_does_not_know_composition_or_entrypoints(path: Path) -> None:
    assert outer_violations(path) == []


def test_outer_rule_detects_violation() -> None:
    fake = SRC / "insights" / "adapters" / "_tmp_violation.py"
    try:
        fake.write_text("from developer_myself.composition.mongo import build_mongo_container\n")
        assert outer_violations(fake) == ["developer_myself.composition.mongo"]
    finally:
        fake.unlink()
