from __future__ import annotations

import ast
from pathlib import Path

from handler.filesystem.storage_inventory import (
    EXTERNAL_AUTHORITY_PROVIDER,
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


MUTATION_CALLS = {
    "chmod",
    "copy",
    "copy2",
    "copyfile",
    "copytree",
    "mkdir",
    "move",
    "remove",
    "rename",
    "rmdir",
    "rmtree",
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


BOUNDARY_ONLY_MUTATIONS = {
    ("endpoints.roms", "delete_roms"),
    ("endpoints.roms.upload", "upload_rom"),
    (
        "handler.filesystem.platforms_handler",
        "FSPlatformsHandler.create_setup_platforms",
    ),
    ("handler.sync.ssh_handler", "SSHHandler"),
    ("sync_watcher", "SyncWatcher.move_to_conflict"),
    ("tasks.scheduled.cleanup_zip_cache", "CleanupZipCacheTask.run"),
    ("tasks.tasks", "Task.run"),
    ("utils.archives", "extract_file"),
    ("utils.audio_tags", "write_audio_cover"),
    ("utils.gamelist_exporter", "export_platform_to_file"),
    ("utils.pegasus_exporter", "export_platform_to_file"),
    ("utils.rom_patcher.patcher", "RomPatcher.apply_patch"),
    ("utils.zip_cache", "build_cached_zip"),
}


def test_discovered_mutation_symbols_exactly_match_inventory() -> None:
    registered = {
        (row.module, row.symbol)
        for row in INVENTORY
        if row.kind is InventoryKind.MUTATION
    }
    assert _discovered_mutations() == registered - BOUNDARY_ONLY_MUTATIONS


def test_external_reads_have_no_raw_path_or_response_adapter() -> None:
    for row in INVENTORY:
        if row.kind is not InventoryKind.READ:
            continue
        assert row.enforcement == (
            "handler.filesystem.storage_access:open_storage_access"
        )
        if row.family != "direct-download":
            continue
        tree = ast.parse(_module_path(row.module).read_text())
        symbol = row.symbol.rsplit(".", maxsplit=1)[-1]
        candidates = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == symbol
        ]
        assert len(candidates) == 1, row
        names = {
            node.id for node in ast.walk(candidates[0]) if isinstance(node, ast.Name)
        }
        strings = {
            node.value
            for node in ast.walk(candidates[0])
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        assert not (FORBIDDEN_EXTERNAL_ADAPTERS & (names | strings))


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


AUTHORITY_FACTORY = "_create_external_descriptor"
AUTHORITY_PROVIDER = EXTERNAL_AUTHORITY_PROVIDER


def _runtime_python_files(root: Path) -> list[Path]:
    excluded = {"tests", "tools", "alembic", "__pycache__"}
    return [
        path
        for path in root.rglob("*.py")
        if not excluded.intersection(path.relative_to(root).parts)
    ]


def _authority_seams(root: Path) -> set[tuple[str, str, str]]:
    seams: set[tuple[str, str, str]] = set()
    for path in _runtime_python_files(root):
        module = ".".join(path.relative_to(root).with_suffix("").parts)
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names = {
                    child.id for child in ast.walk(node) if isinstance(child, ast.Name)
                }
                attrs = {
                    child.attr
                    for child in ast.walk(node)
                    if isinstance(child, ast.Attribute)
                }
                annotations = ast.unparse(node.args)
                if AUTHORITY_FACTORY in names:
                    seams.add((module, node.name, "descriptor_factory"))
                branches_on_root = any(
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == "isinstance"
                    and "StorageRoot"
                    in {
                        name.id
                        for name in ast.walk(child)
                        if isinstance(name, ast.Name)
                    }
                    for child in ast.walk(node)
                )
                access_function = any(
                    term in node.name
                    for term in ("open", "access", "authorize", "descriptor")
                )
                if (
                    access_function
                    and "StorageRoot" in annotations
                    and ("container_path" in attrs or branches_on_root)
                ):
                    seams.add((module, node.name, "raw_storage_root"))
    return seams


def test_runtime_authority_seams_are_closed_and_composition_only() -> None:
    assert _authority_seams(BACKEND) == {(*AUTHORITY_PROVIDER, "descriptor_factory")}


def test_authority_discovery_rejects_seeded_factory_and_raw_root_mutants(
    tmp_path: Path,
) -> None:
    (tmp_path / "factory.py").write_text(
        "def forge():\n    return _create_external_descriptor(9, '/tmp')\n"
    )
    (tmp_path / "raw.py").write_text(
        "def open_any(root: StorageRoot):\n    return root.container_path\n"
    )
    seams = _authority_seams(tmp_path)
    assert ("factory", "forge", "descriptor_factory") in seams
    assert ("raw", "open_any", "raw_storage_root") in seams
