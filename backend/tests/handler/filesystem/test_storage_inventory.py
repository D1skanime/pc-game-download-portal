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


MUTATION_CALLS = {
    "chmod",
    "copy",
    "copy2",
    "copyfile",
    "copytree",
    "create_subprocess_exec",
    "mkdir",
    "move",
    "open",
    "Popen",
    "remove",
    "rename",
    "replace",
    "rmdir",
    "rmtree",
    "run",
    "touch",
    "unlink",
    "write_bytes",
    "write_text",
}
FORBIDDEN_EXTERNAL_ADAPTERS = {
    "FileRedirectResponse",
    "FileResponse",
    "LIBRARY_BASE_PATH",
    "X-Accel-Redirect",
}


def _module_path(module: str) -> Path:
    relative = Path(*module.split("."))
    module_file = BACKEND / relative.with_suffix(".py")
    return module_file if module_file.is_file() else BACKEND / relative / "__init__.py"


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _discovered_mutations() -> set[tuple[str, str]]:
    registered_modules = {
        row.module for row in INVENTORY if row.kind is InventoryKind.MUTATION
    }
    registered_classes = {
        (row.module, row.symbol)
        for row in INVENTORY
        if row.kind is InventoryKind.MUTATION and "." not in row.symbol
    }
    discovered: set[tuple[str, str]] = set()
    for module in registered_modules:
        path = _module_path(module)
        tree = ast.parse(path.read_text())
        parents: list[str] = []

        class Visitor(ast.NodeVisitor):
            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                parents.append(node.name)
                self.generic_visit(node)
                parents.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._visit_function(node)

            visit_AsyncFunctionDef = visit_FunctionDef

            def _visit_function(
                self, node: ast.FunctionDef | ast.AsyncFunctionDef
            ) -> None:
                symbol = ".".join((*parents, node.name))
                normalized = (
                    parents[0]
                    if parents and (module, parents[0]) in registered_classes
                    else symbol
                )
                if any(
                    isinstance(child, ast.Call) and _call_name(child) in MUTATION_CALLS
                    for child in ast.walk(node)
                ):
                    discovered.add((module, normalized))

        Visitor().visit(tree)
    return discovered


def test_discovered_mutation_symbols_exactly_match_inventory() -> None:
    registered = {
        (row.module, row.symbol)
        for row in INVENTORY
        if row.kind is InventoryKind.MUTATION
    }
    assert _discovered_mutations() == registered


def test_external_reads_have_no_raw_path_or_response_adapter() -> None:
    for row in INVENTORY:
        if row.kind is not InventoryKind.READ:
            continue
        source = _module_path(row.module).read_text()
        assert "authorize_external_access" in source or (
            row.module == "handler.filesystem.storage_composition"
            and "get_legacy_external_storage_descriptor" in source
        )
    consumers = "\n".join(
        _module_path(row.module).read_text()
        for row in INVENTORY
        if row.kind is InventoryKind.READ
        and row.family in {"direct-download", "stream"}
    )
    for adapter in FORBIDDEN_EXTERNAL_ADAPTERS:
        assert adapter not in consumers


def test_inventory_enforcement_links_resolve_to_real_symbols() -> None:
    for row in INVENTORY:
        if not row.enforcement:
            continue
        module, symbol = row.enforcement.split(":", maxsplit=1)
        tree = ast.parse(_module_path(module).read_text())
        definitions = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert symbol in definitions

    assert "0019_resources_refactor" not in runtime_sources
    assert "0040_migrate_assets_paths" not in runtime_sources
