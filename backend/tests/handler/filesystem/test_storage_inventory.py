from __future__ import annotations

import ast
from pathlib import Path

from handler.filesystem.storage_inventory import (
    INVENTORY,
    InventoryDisposition,
    InventoryKind,
)

BACKEND = Path(__file__).parents[3]
REQUIRED_FAMILIES = {
    "composition",
    "firmware",
    "platform",
    "heartbeat",
    "config",
    "scan",
    "socket",
    "watcher",
    "rom",
    "hash",
    "stream",
    "direct-download",
    "zip",
    "endpoint-mutation",
    "archive",
    "patch",
    "export",
    "audio",
    "sync",
    "bootstrap",
    "cleanup",
    "task",
    "migration-exclusion",
}


def _defined_tests(path: str) -> set[str]:
    tree = ast.parse((BACKEND / path).read_text())
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def test_inventory_covers_every_required_surface_family() -> None:
    assert {row.family for row in INVENTORY} == REQUIRED_FAMILIES
    assert {row.kind for row in INVENTORY} == {
        InventoryKind.READ,
        InventoryKind.MUTATION,
        InventoryKind.EXCLUSION,
    }


def test_every_inventory_row_has_one_disposition_and_runnable_evidence() -> None:
    keys = [(row.module, row.symbol) for row in INVENTORY]
    assert len(keys) == len(set(keys))
    for row in INVENTORY:
        if row.kind is InventoryKind.EXCLUSION:
            assert row.disposition is InventoryDisposition.NON_RUNTIME
            assert row.explanation
        else:
            assert row.disposition in {
                InventoryDisposition.POLICY_GOVERNED,
                InventoryDisposition.OWNED_ONLY,
            }
            assert row.enforcement
        assert row.source_class
        assert row.destination_class
        assert row.operations
        assert row.evidence.test in _defined_tests(row.evidence.path)


def test_historical_migrations_are_explicit_non_runtime_exclusions() -> None:
    migration_files = {
        "alembic/versions/0019_resources_refactor.py",
        "alembic/versions/0040_migrate_assets_paths.py",
    }
    assert all((BACKEND / path).is_file() for path in migration_files)
    runtime_sources = "\n".join(
        path.read_text()
        for path in BACKEND.rglob("*.py")
        if "alembic" not in path.parts and "tests" not in path.parts
    )
    assert "0019_resources_refactor" not in runtime_sources
    assert "0040_migrate_assets_paths" not in runtime_sources
