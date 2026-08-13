# mypy: disable-error-code=assignment
# ruff: noqa: B023
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
    "legacy-detection",
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


def test_phase6_external_mutations_remain_absent_or_policy_governed() -> None:
    forbidden = {
        "CREATE",
        "UPLOAD",
        "WRITE",
        "OVERWRITE",
        "RENAME",
        "MOVE",
        "COPY",
        "DELETE",
        "EXTRACT",
        "PATCH",
        "MKDIR",
    }
    for row in INVENTORY:
        if not forbidden.intersection(row.operations):
            continue
        if "external_read_only" in {
            row.source_class,
            row.destination_class,
        }:
            assert row.disposition is InventoryDisposition.POLICY_GOVERNED
            assert row.enforcement
        else:
            assert row.source_class == "romm_owned"
            assert row.disposition is InventoryDisposition.OWNED_ONLY


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
NON_AUTHORITY_RAW_ROOTS = {
    ("handler.filesystem.storage_resolver", "check_storage_root_health"),
    ("handler.filesystem.storage_resolver", "resolve_storage_root"),
    ("handler.filesystem.storage_resolver", "get_storage_root_health_snapshot"),
}


def _runtime_python_files(root: Path) -> list[Path]:
    excluded = {"tests", "tools", "alembic", "__pycache__"}
    return [
        path
        for path in root.rglob("*.py")
        if not excluded.intersection(path.relative_to(root).parts)
    ]


def _factory_aliases(nodes: list[ast.stmt]) -> set[str]:
    return {
        alias.asname or alias.name
        for statement in nodes
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(statement)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.name == AUTHORITY_FACTORY
    }


def _function_nodes(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.AST]:
    nodes: list[ast.AST] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node is function:
                self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            return

        def generic_visit(self, node: ast.AST) -> None:
            nodes.append(node)
            super().generic_visit(node)

    Visitor().visit(function)
    return nodes


def _is_storage_root_annotation(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    return any(
        (isinstance(node, ast.Name) and node.id == "StorageRoot")
        or (isinstance(node, ast.Attribute) and node.attr == "StorageRoot")
        or (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "StorageRoot" in node.value
        )
        for node in ast.walk(annotation)
    )


def _typed_storage_root_parameters(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    parameters = [
        *function.args.posonlyargs,
        *function.args.args,
        *function.args.kwonlyargs,
    ]
    if function.args.vararg is not None:
        parameters.append(function.args.vararg)
    if function.args.kwarg is not None:
        parameters.append(function.args.kwarg)
    return {
        parameter.arg
        for parameter in parameters
        if _is_storage_root_annotation(parameter.annotation)
    }


def _authority_seams(root: Path) -> set[tuple[str, str, str]]:
    seams: set[tuple[str, str, str]] = set()
    for path in _runtime_python_files(root):
        module = ".".join(path.relative_to(root).with_suffix("").parts)
        tree = ast.parse(path.read_text())
        module_aliases = _factory_aliases(tree.body)
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            nodes = _function_nodes(function)
            local_aliases = {
                alias.asname or alias.name
                for node in nodes
                if isinstance(node, ast.ImportFrom)
                for alias in node.names
                if alias.name == AUTHORITY_FACTORY
            }
            if local_aliases or any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in module_aliases | local_aliases
                for node in nodes
            ):
                seams.add((module, function.name, "descriptor_factory"))

            root_parameters = _typed_storage_root_parameters(function)
            accesses_container_path = any(
                isinstance(node, ast.Attribute)
                and node.attr == "container_path"
                and isinstance(node.value, ast.Name)
                and node.value.id in root_parameters
                for node in nodes
            )
            branch_expressions = [
                node.test
                for node in nodes
                if isinstance(node, (ast.If, ast.IfExp, ast.While))
            ]
            branch_expressions.extend(
                node.subject for node in nodes if isinstance(node, ast.Match)
            )
            branch_expressions.extend(
                node.guard
                for node in nodes
                if isinstance(node, ast.match_case) and node.guard is not None
            )
            branches_on_root = any(
                isinstance(candidate, ast.Name) and candidate.id in root_parameters
                for expression in branch_expressions
                for candidate in ast.walk(expression)
            )
            raw_root_seam = (module, function.name)
            if (
                raw_root_seam not in NON_AUTHORITY_RAW_ROOTS
                and root_parameters
                and (accesses_container_path or branches_on_root)
            ):
                seams.add((*raw_root_seam, "raw_storage_root"))
    return seams


def test_runtime_authority_seams_are_closed_and_composition_only() -> None:
    assert _authority_seams(BACKEND) == {
        (*AUTHORITY_PROVIDER, "descriptor_factory"),
        ("handler.storage.read_context", "open", "descriptor_factory"),
        (
            "tasks.manual.detect_legacy_storage",
            "run",
            "descriptor_factory",
        ),
    }


def test_authority_discovery_rejects_unused_factory_import(tmp_path: Path) -> None:
    (tmp_path / "unused_factory_import.py").write_text(
        "def retain_import():\n"
        "    from handler.filesystem.storage_policy import (\n"
        "        _create_external_descriptor as make_descriptor,\n"
        "    )\n"
        "    return None\n"
    )

    assert (
        "unused_factory_import",
        "retain_import",
        "descriptor_factory",
    ) in _authority_seams(tmp_path)


def test_authority_discovery_rejects_factory_alias_call(tmp_path: Path) -> None:
    (tmp_path / "factory_alias_call.py").write_text(
        "def forge_elsewhere():\n"
        "    from handler.filesystem.storage_policy import (\n"
        "        _create_external_descriptor as make_descriptor,\n"
        "    )\n"
        "    return make_descriptor(9, '/tmp')\n"
    )

    assert (
        "factory_alias_call",
        "forge_elsewhere",
        "descriptor_factory",
    ) in _authority_seams(tmp_path)


def test_authority_discovery_rejects_neutral_container_path_access(
    tmp_path: Path,
) -> None:
    (tmp_path / "neutral_path.py").write_text(
        "def select(root: StorageRoot):\n    return root.container_path\n"
    )

    assert (
        "neutral_path",
        "select",
        "raw_storage_root",
    ) in _authority_seams(tmp_path)


def test_authority_discovery_rejects_neutral_storage_root_branch(
    tmp_path: Path,
) -> None:
    (tmp_path / "neutral_branch.py").write_text(
        "def choose(root: StorageRoot):\n"
        "    if isinstance(root, StorageRoot):\n"
        "        return root\n"
        "    return None\n"
    )

    assert (
        "neutral_branch",
        "choose",
        "raw_storage_root",
    ) in _authority_seams(tmp_path)
