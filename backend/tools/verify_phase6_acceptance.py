"""Run the deterministic Phase 6 acceptance and evidence gates."""

# trunk-ignore-all(bandit/B404,bandit/B603,bandit/B608,bandit/B108)

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from types import FrameType
from typing import NamedTuple

PRIOR_PHASE_MODULES = (
    "tests/alembic/test_mapping_preview_migration.py",
    "tests/endpoints/roms/test_files.py",
    "tests/endpoints/roms/test_rom.py",
    "tests/endpoints/storage/test_mapping_preview.py",
    "tests/endpoints/test_storage.py",
    "tests/endpoints/test_storage_policy_denials.py",
    "tests/handler/database/test_storage_handler.py",
    "tests/handler/filesystem/test_external_read_consumers.py",
    "tests/handler/filesystem/test_owned_storage.py",
    "tests/handler/filesystem/test_storage_access.py",
    "tests/handler/filesystem/test_storage_inventory.py",
    "tests/handler/filesystem/test_storage_policy.py",
    "tests/handler/filesystem/test_storage_resolver.py",
    "tests/handler/filesystem/test_sync_handler.py",
    "tests/handler/storage/test_preview.py",
    "tests/handler/test_scan_command.py",
    "tests/integration/test_mapped_scan.py",
    "tests/integration/test_scan_source_immutability.py",
    "tests/models/test_storage.py",
    "tests/tasks/test_mapping_revision_jobs.py",
    "tests/tasks/test_storage_policy.py",
    "tests/test_sync_watcher.py",
    "tests/test_watcher.py",
    "tests/tools/test_verify_storage_migrations.py",
    "tests/utils/test_archives.py",
    "tests/utils/test_audio_tags.py",
    "tests/utils/test_gamelist_exporter.py",
    "tests/utils/test_pegasus_exporter.py",
    "tests/utils/test_zip_cache.py",
)

PHASE6_MODULES = (
    "tests/endpoints/roms/test_catalog_removal.py",
    "tests/endpoints/roms/test_files.py",
    "tests/endpoints/roms/test_manual.py",
    "tests/endpoints/sockets/test_scan.py",
    "tests/endpoints/test_saves.py",
    "tests/endpoints/test_screenshots.py",
    "tests/endpoints/test_states.py",
    "tests/endpoints/test_storage.py",
    "tests/endpoints/test_storage_policy_denials.py",
    "tests/handler/database/test_storage_lifecycle.py",
    "tests/handler/filesystem/test_storage_access.py",
    "tests/handler/filesystem/test_storage_inventory.py",
    "tests/handler/storage/test_legacy_migration.py",
    "tests/handler/storage/test_read_context.py",
    "tests/integration/test_legacy_migration.py",
    "tests/models/test_safe_lifecycle.py",
    "tests/tasks/test_detect_legacy_storage.py",
    "tests/tools/test_verify_phase6_contracts.py",
    "tests/tools/test_verify_storage_migrations.py",
    "tests/utils/test_rom_patcher.py",
)

FOCUSED_UI_TESTS = (
    "src/services/api/rom.test.ts",
    "src/stores/upload.test.ts",
    "src/services/api/screenshot.test.ts",
    "src/v2/components/GameDetails/ManualViewerControls.test.ts",
    "src/v2/components/GameDetails/ManualSubtab.test.ts",
    "src/v2/sourceMutationInventory.test.ts",
    "src/v2/sourceMutationControls.test.ts",
)

REQUIRED_SOURCE_IDS = frozenset(
    ["GOAL-06"]
    + [f"CAT-{index:02d}" for index in range(1, 5)]
    + [f"MIG-{index:02d}" for index in range(1, 6)]
    + [f"MH-{index:02d}" for index in range(1, 32)]
    + [f"CR-{index:02d}" for index in range(1, 5)]
    + [f"WR-{index:02d}" for index in range(1, 4)]
    + [f"R-{index:02d}" for index in range(1, 10)]
    + [f"UI-{index:02d}" for index in range(1, 9)]
    + [f"D-{index:02d}" for index in range(1, 24)]
)

PRIOR_OUTCOMES_MIN = 843
BASELINE_UNTRACKED_SHA256 = (
    "4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1"
)
CANONICAL_COMMAND_IDENTITY = (
    "python3 backend/tools/verify_phase6_acceptance.py --checkout "
    "/home/d1sk/romm --base-commit "
    "3e0b278cf3e71fe84f1e7b20b354f94728fc9531 --branch "
    "codex/pc-module-analysis --origin https://github.com/rommapp/romm.git "
    "--project RomM PC Library --source-container romm-dev "
    "--db-container romm-db-dev --expected-source-image romm-romm-dev "
    "--network romm_default --node-image node:24-bookworm "
    "--contract-port 39006 --baseline-untracked-count 28 "
    "--prior-outcomes-min 843 --run-complete"
)
MAX_STAGE_OUTPUT = 4000
OWNERSHIP_LABEL = "io.romm.phase6.acceptance"
ACCEPTANCE_RELATIVE_PATH = (
    ".planning/phases/06-safe-lifecycle-and-legacy-migration/" "06-47-ACCEPTANCE.json"
)
UI_EVIDENCE_COMMIT = "364bb2764"
UI_EVIDENCE_PATHS = (
    "frontend/src/services/api/rom.ts",
    "frontend/src/stores/upload.ts",
    "frontend/src/v2/components/GameDetails/ManualSubtab.vue",
    "frontend/src/v2/components/GameDetails/ManualViewerControls.test.ts",
    "frontend/src/v2/components/GameDetails/ManualSubtab.test.ts",
    "frontend/src/v2/sourceMutationControls.test.ts",
)
CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class StageFailure(RuntimeError):
    pass


class EvidenceError(ValueError):
    pass


class ResourceIdentity(NamedTuple):
    suffix: str
    database: str
    principal: str
    password: str
    basetemp: str
    container: str

    @classmethod
    def create(cls, index: int) -> "ResourceIdentity":
        suffix = f"{secrets.token_hex(6)}{index:02d}"
        return cls(
            suffix=suffix,
            database=f"p0647_{suffix}",
            principal=f"p0647_{suffix}",
            password=secrets.token_hex(16),
            basetemp=f"/tmp/p0647-{suffix}",
            container=f"p0647-runner-{suffix}",
        )


def _run(
    args: Sequence[str],
    *,
    check: bool = False,
    timeout: int = 3600,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode:
        raise StageFailure(
            f"command exited {result.returncode}: "
            f"{redact_output(result.stdout + result.stderr)}"
        )
    return result


def redact_output(output: str, *, secrets: Iterable[str] = ()) -> str:
    redacted = output
    for value in secrets:
        if value:
            redacted = redacted.replace(value, "<redacted>")
    redacted = re.sub(r"(?<![A-Za-z0-9_.-])/(?:[^\s:]+/?)+", "<path>", redacted)
    redacted = re.sub(
        r"(?i)(password|passwd|secret|token)=\S+",
        r"\1=<redacted>",
        redacted,
    )
    return redacted[-MAX_STAGE_OUTPUT:]


def deduplicated_phase6_modules() -> tuple[str, ...]:
    prior = set(PRIOR_PHASE_MODULES)
    return tuple(module for module in PHASE6_MODULES if module not in prior)


def _validate_inventory(checkout: Path) -> None:
    if len(PRIOR_PHASE_MODULES) != 29 or len(set(PRIOR_PHASE_MODULES)) != 29:
        raise StageFailure("prior module inventory is not exactly 29 unique paths")
    if len(set(PHASE6_MODULES)) != len(PHASE6_MODULES):
        raise StageFailure("Phase 6 module inventory contains duplicates")
    backend = checkout / "backend"
    missing = [
        module
        for module in (*PRIOR_PHASE_MODULES, *PHASE6_MODULES)
        if not (backend / module).is_file()
    ]
    if missing:
        raise StageFailure("one or more pinned backend modules are missing")


def backend_module_command(
    checkout: Path,
    module: str,
    identity: ResourceIdentity,
    image: str,
    network: str,
    *,
    unit_contract: bool = False,
) -> list[str]:
    pytest_args = [
        "/app/.venv/bin/python",
        "-m",
        "pytest",
    ]
    if unit_contract:
        pytest_args.append("--confcutdir=tests/tools")
    pytest_args.extend(
        [
            "-p",
            "no:env",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            identity.basetemp,
            module,
            "-x",
        ]
    )
    script = (
        "set -eu; chmod 0711 /root; "
        "mkdir -p /app/backend/romm_test/library; "
        "chown -R 1000:1000 /tmp /app/backend/romm_test; "
        "exec setpriv --reuid=1000 --regid=1000 --clear-groups " + " ".join(pytest_args)
    )
    return [
        "docker",
        "create",
        "--name",
        identity.container,
        "--label",
        f"{OWNERSHIP_LABEL}={identity.suffix}",
        "--network",
        network,
        "--entrypoint",
        "/bin/sh",
        "--mount",
        f"type=bind,src={checkout / 'backend'},dst=/app/backend,readonly",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev",
        "--tmpfs",
        "/app/backend/romm_test:rw,nosuid,nodev",
        "--workdir",
        "/app/backend",
        "-e",
        "ROMM_BASE_PATH=romm_test",
        "-e",
        "ROMM_AUTH_SECRET_KEY=test-only",
        "-e",
        "ROMM_DB_DRIVER=mariadb",
        "-e",
        "DB_HOST=romm-db-dev",
        "-e",
        "DB_PORT=3306",
        "-e",
        f"DB_NAME={identity.database}",
        "-e",
        f"DB_USER={identity.principal}",
        "-e",
        f"DB_PASSWD={identity.password}",
        "-e",
        "REDIS_HOST=romm-valkey-dev",
        "-e",
        "REDIS_PORT=6379",
        "-e",
        "REDIS_DB=0",
        "-e",
        "REDIS_SSL=false",
        image,
        "-lc",
        script,
    ]


def _database_admin_command(db_container: str, sql: str) -> list[str]:
    return [
        "docker",
        "exec",
        db_container,
        "/bin/sh",
        "-lc",
        "exec mariadb --batch --skip-column-names "
        '-uroot -p"$MARIADB_ROOT_PASSWORD" -e "$1"',
        "p0647",
        sql,
    ]


def create_database_resources(
    identity: ResourceIdentity,
    db_container: str,
    *,
    runner: CommandRunner = _run,
) -> None:
    if not re.fullmatch(r"p0647_[0-9a-f]{12}[0-9]{2}", identity.database):
        raise StageFailure("refusing invalid database identity")
    if identity.database != identity.principal:
        raise StageFailure("database and principal identity mismatch")
    check_sql = (
        "SELECT "
        f"(SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='{identity.database}'),"
        f"(SELECT COUNT(*) FROM mysql.user WHERE User='{identity.principal}')"
    )
    absent = runner(_database_admin_command(db_container, check_sql))
    if absent.returncode or absent.stdout.strip() != "0\t0":
        raise StageFailure("task database or principal identity already exists")
    sql = (
        f"CREATE DATABASE {identity.database};"
        f"CREATE USER '{identity.principal}'@'%' IDENTIFIED BY '{identity.password}';"
        f"GRANT ALL PRIVILEGES ON {identity.database}.* "
        f"TO '{identity.principal}'@'%';FLUSH PRIVILEGES"
    )
    created = runner(_database_admin_command(db_container, sql))
    if created.returncode:
        raise StageFailure("task database resource creation failed")


def cleanup_database_resources(
    identity: ResourceIdentity,
    db_container: str,
    *,
    runner: CommandRunner = _run,
) -> None:
    sql = (
        f"DROP DATABASE IF EXISTS {identity.database};"
        f"DROP USER IF EXISTS '{identity.principal}'@'%';FLUSH PRIVILEGES"
    )
    result = runner(_database_admin_command(db_container, sql))
    if result.returncode:
        raise StageFailure("exact database resource cleanup failed")
    check_sql = (
        "SELECT "
        f"(SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='{identity.database}'),"
        f"(SELECT COUNT(*) FROM mysql.user WHERE User='{identity.principal}')"
    )
    absent = runner(_database_admin_command(db_container, check_sql))
    if absent.returncode or absent.stdout.strip() != "0\t0":
        raise StageFailure("exact database or principal remains")


def _parse_pytest_outcomes(output: str) -> dict[str, int]:
    counts = {
        name: sum(int(value) for value in re.findall(rf"(\d+) {name}", output))
        for name in (
            "passed",
            "failed",
            "error",
            "errors",
            "skipped",
            "xfailed",
            "xpassed",
        )
    }
    errors = counts["error"] + counts["errors"]
    return {
        "passed": counts["passed"],
        "failed": counts["failed"],
        "errors": errors,
        "skipped": counts["skipped"],
        "xfailed": counts["xfailed"],
        "xpassed": counts["xpassed"],
    }


def execute_backend_module(
    module: str,
    identity: ResourceIdentity,
    command: list[str],
    *,
    create_resources: Callable[[ResourceIdentity], None],
    execute_command: CommandRunner,
    cleanup_resources: Callable[[ResourceIdentity], None],
) -> dict[str, object]:
    primary_error: BaseException | None = None
    result: subprocess.CompletedProcess[str] | None = None
    try:
        create_resources(identity)
        result = execute_command(command)
        if result.returncode:
            raise StageFailure(
                f"backend module failed: {module}: "
                + redact_output(
                    result.stdout + result.stderr,
                    secrets=(identity.password,),
                )
            )
    except BaseException as error:
        primary_error = error
    finally:
        try:
            cleanup_resources(identity)
        except BaseException as cleanup_error:
            if primary_error is None:
                primary_error = cleanup_error
    if primary_error is not None:
        raise primary_error
    assert result is not None
    counts = _parse_pytest_outcomes(result.stdout + result.stderr)
    if counts["failed"] or counts["errors"]:
        raise StageFailure(f"backend module reported failures: {module}")
    return {
        "module": module,
        **counts,
        "exit_code": result.returncode,
    }


def _execute_docker_module(
    checkout: Path,
    module: str,
    identity: ResourceIdentity,
    image: str,
    network: str,
    db_container: str,
    *,
    unit_contract: bool = False,
) -> dict[str, object]:
    container_id: str | None = None
    command = backend_module_command(
        checkout,
        module,
        identity,
        image,
        network,
        unit_contract=unit_contract,
    )

    def create(resource: ResourceIdentity) -> None:
        nonlocal container_id
        create_database_resources(resource, db_container)
        created = _run(command)
        if created.returncode:
            cleanup_database_resources(resource, db_container)
            raise StageFailure("backend runner creation failed")
        container_id = created.stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{64}", container_id):
            cleanup_database_resources(resource, db_container)
            raise StageFailure("backend runner identity was malformed")

    def execute(_command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        if container_id is None:
            raise StageFailure("backend runner was not created")
        return _run(["docker", "start", "--attach", container_id], timeout=3600)

    def cleanup(resource: ResourceIdentity) -> None:
        cleanup_errors: list[str] = []
        if container_id is not None:
            removed = _run(["docker", "rm", "--force", container_id])
            if removed.returncode and "No such container" not in removed.stderr:
                cleanup_errors.append("container")
        try:
            cleanup_database_resources(resource, db_container)
        except StageFailure:
            cleanup_errors.append("database")
        if cleanup_errors:
            raise StageFailure(
                "exact backend cleanup failed: " + ", ".join(cleanup_errors)
            )

    record = execute_backend_module(
        module,
        identity,
        command,
        create_resources=create,
        execute_command=execute,
        cleanup_resources=cleanup,
    )
    print(
        f"[PASS] backend module {module}: "
        f"{record['passed']} passed, {record['skipped']} skipped"
    )
    return record


def source_manifest(root: Path) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix()):
        relative = path.relative_to(root).as_posix()
        path_stat = path.lstat()
        kind = "other"
        digest: str | None = None
        target: str | None = None
        if stat.S_ISLNK(path_stat.st_mode):
            kind = "symlink"
            target = os.readlink(path)
        elif stat.S_ISDIR(path_stat.st_mode):
            kind = "directory"
        elif stat.S_ISREG(path_stat.st_mode):
            kind = "file"
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(
            {
                "path": relative,
                "kind": kind,
                "mode": stat.S_IMODE(path_stat.st_mode),
                "size": path_stat.st_size,
                "sha256": digest,
                "symlink_target": target,
            }
        )
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {"entries": entries, "sha256": hashlib.sha256(canonical).hexdigest()}


def compare_source_manifests(
    before: dict[str, object], after: dict[str, object]
) -> bool:
    return before == after


def _tracked_manifest(checkout: Path, paths: Sequence[str]) -> dict[str, object]:
    result = _run(["git", "ls-files", "-z", "--", *paths], check=True)
    names = [name for name in result.stdout.split("\0") if name]
    records: list[dict[str, object]] = []
    for name in names:
        path = checkout / name
        path_stat = path.lstat()
        if path.is_symlink():
            kind = "symlink"
            content = os.readlink(path).encode()
        elif path.is_file():
            kind = "file"
            content = path.read_bytes()
        else:
            kind = "other"
            content = b""
        records.append(
            {
                "path": name,
                "kind": kind,
                "mode": stat.S_IMODE(path_stat.st_mode),
                "size": path_stat.st_size,
                "sha256": hashlib.sha256(content).hexdigest(),
                "symlink_target": os.readlink(path) if path.is_symlink() else None,
            }
        )
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return {"count": len(records), "sha256": hashlib.sha256(payload).hexdigest()}


def _baseline_lines(checkout: Path) -> list[str]:
    result = _run(["git", "status", "--porcelain=v1"], check=True)
    ignored_outputs = {f"?? {ACCEPTANCE_RELATIVE_PATH}"}
    return [
        line
        for line in result.stdout.splitlines()
        if line.startswith("?? ") and line not in ignored_outputs
    ]


def _baseline_record(checkout: Path, expected_count: int) -> dict[str, object]:
    lines = _baseline_lines(checkout)
    digest = hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
    if len(lines) != expected_count or digest != BASELINE_UNTRACKED_SHA256:
        raise StageFailure("untracked baseline does not match the approved 28 entries")
    return {"untracked_count": len(lines), "untracked_sha256": digest}


def _normal_db_select_one(db_container: str) -> int:
    command = [
        "docker",
        "exec",
        db_container,
        "/bin/sh",
        "-lc",
        "exec mariadb --batch --skip-column-names "
        '-u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE" '
        '-e "SELECT 1"',
    ]
    result = _run(command)
    if result.returncode or result.stdout.strip() != "1":
        raise StageFailure("normal application database continuity failed")
    return 1


def _preflight(
    checkout: Path,
    *,
    branch: str,
    origin: str,
    project: str,
    base_commit: str,
    source_container: str,
    expected_image: str,
    network: str,
) -> dict[str, object]:
    if platform.system() != "Linux":
        raise StageFailure("acceptance harness requires Linux")
    actual = Path(
        _run(["git", "rev-parse", "--show-toplevel"], check=True).stdout.strip()
    )
    if actual.resolve() != checkout.resolve():
        raise StageFailure("checkout does not match git top-level")
    actual_branch = _run(["git", "branch", "--show-current"], check=True).stdout.strip()
    actual_origin = _run(
        ["git", "remote", "get-url", "origin"], check=True
    ).stdout.strip()
    if actual_branch != branch or actual_origin != origin:
        raise StageFailure("branch or origin identity mismatch")
    project_text = (checkout / ".planning" / "PROJECT.md").read_text(encoding="utf-8")
    if f"# {project}" not in project_text:
        raise StageFailure("planning project identity mismatch")
    ancestor = _run(["git", "merge-base", "--is-ancestor", base_commit, "HEAD"])
    if ancestor.returncode:
        raise StageFailure("required base commit is not an ancestor")
    image = _run(
        ["docker", "inspect", "--format", "{{.Config.Image}}", source_container],
        check=True,
    ).stdout.strip()
    source_state = _run(
        ["docker", "inspect", "--format", "{{.State.Status}}", source_container],
        check=True,
    ).stdout.strip()
    if image != expected_image or source_state == "running":
        raise StageFailure(
            "approved source service identity or stopped state is invalid"
        )
    actual_network = _run(
        ["docker", "network", "inspect", "--format", "{{.Name}}", network],
        check=True,
    ).stdout.strip()
    if actual_network != network:
        raise StageFailure("Docker network identity mismatch")
    return {
        "root": str(checkout.resolve()),
        "branch": actual_branch,
        "origin": actual_origin,
        "project": project,
        "source_service_state": source_state,
    }


def acceptance_command_graph(
    checkout: Path,
    *,
    source_container: str,
    db_container: str,
    image: str,
    network: str,
    node_image: str,
    contract_port: int,
) -> list[list[str]]:
    focused = " ".join(FOCUSED_UI_TESTS)
    return [
        [
            "python3",
            "backend/tools/verify_storage_migrations.py",
            "--dialects",
            "mariadb",
            "mysql",
            "postgresql",
            "--handler-tests",
        ],
        [
            "python3",
            "backend/tools/verify_phase6_contracts.py",
            "--source-container",
            source_container,
            "--checkout",
            str(checkout),
            "--expected-image",
            image,
            "--network",
            network,
            "--port",
            str(contract_port),
        ],
        ["docker", "run", node_image, "npm", "run", "test", "--", focused],
        ["docker", "run", node_image, "npm", "run", "test"],
        ["docker", "run", node_image, "npm", "run", "typecheck"],
        ["docker", "run", node_image, "npm", "run", "build"],
        ["docker", "run", node_image, "python3", "src/locales/check_i18n_locales.py"],
        ["docker", "run", node_image, "python3", "src/locales/check_i18n_sorted.py"],
        ["git", "diff", "--check"],
        ["docker", "exec", db_container, "SELECT 1"],
    ]


def _create_sleep_runner(
    checkout: Path,
    name: str,
    image: str,
    network: str,
    *,
    backend_destination: str = "/app/backend",
    environment: dict[str, str] | None = None,
) -> str:
    command = [
        "docker",
        "create",
        "--name",
        name,
        "--label",
        f"{OWNERSHIP_LABEL}={name}",
        "--network",
        network,
        "--entrypoint",
        "/bin/sh",
        "--mount",
        f"type=bind,src={checkout / 'backend'},dst={backend_destination},readonly",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev",
        "--tmpfs",
        "/app/romm_test:rw,nosuid,nodev",
        "--workdir",
        backend_destination,
    ]
    for key, value in (environment or {}).items():
        command.extend(["-e", f"{key}={value}"])
    command.extend([image, "-lc", "chmod 0711 /root; exec sleep infinity"])
    result = _run(command)
    if result.returncode:
        raise StageFailure("disposable runner creation failed")
    container_id = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{64}", container_id):
        raise StageFailure("disposable runner returned malformed identity")
    started = _run(["docker", "start", container_id])
    if started.returncode:
        _run(["docker", "rm", "--force", container_id])
        raise StageFailure("disposable runner start failed")
    return container_id


def _remove_container(container_id: str) -> None:
    result = _run(["docker", "rm", "--force", container_id])
    if result.returncode and "No such container" not in result.stderr:
        raise StageFailure("exact disposable runner cleanup failed")


def _run_dialects(
    checkout: Path, image: str, network: str
) -> dict[str, dict[str, object]]:
    nonce = secrets.token_hex(8)
    name = f"p0647-dialect-{nonce}"
    runner_id = _create_sleep_runner(checkout, name, image, network)
    try:
        command = [
            "python3",
            str(checkout / "backend/tools/verify_storage_migrations.py"),
            "--dialects",
            "mariadb",
            "mysql",
            "postgresql",
            "--runner-container",
            runner_id,
            "--handler-tests",
            "--handler-test-repetitions",
            "1",
        ]
        result = _run(command, timeout=3600)
        if result.returncode:
            raise StageFailure(
                "dialect verifier failed: "
                + redact_output(result.stdout + result.stderr)
            )
        output = result.stdout + result.stderr
        records: dict[str, dict[str, object]] = {}
        for dialect in ("mariadb", "mysql", "postgresql"):
            if (
                f"0114 exact cleanup passed {dialect}" not in output
                or f"{dialect}: pristine" not in output
            ):
                raise StageFailure(f"{dialect} authority markers are incomplete")
            records[dialect] = {"exit_code": 0, "authority": "complete"}
        return records
    finally:
        _remove_container(runner_id)


def _contract_environment(identity: ResourceIdentity) -> dict[str, str]:
    return {
        "DB_HOST": "romm-db-dev",
        "DB_NAME": identity.database,
        "DB_PASSWD": identity.password,
        "DB_PORT": "3306",
        "DB_USER": identity.principal,
        "REDIS_DB": "0",
        "REDIS_HOST": "romm-valkey-dev",
        "REDIS_PORT": "6379",
        "REDIS_SSL": "false",
        "ROMM_BASE_PATH": "/app/romm_test",
    }


def _run_contracts(
    checkout: Path,
    image: str,
    network: str,
    db_container: str,
    contract_port: int,
) -> dict[str, object]:
    identity = ResourceIdentity.create(90)
    source_id: str | None = None
    generated_before = _tracked_manifest(checkout, ["frontend/src/__generated__"])
    try:
        create_database_resources(identity, db_container)
        source_id = _create_sleep_runner(
            checkout,
            f"p0647-contract-source-{identity.suffix}",
            image,
            network,
            backend_destination="/app/backend",
            environment=_contract_environment(identity),
        )
        command = [
            "python3",
            str(checkout / "backend/tools/verify_phase6_contracts.py"),
            "--source-container",
            source_id,
            "--checkout",
            str(checkout),
            "--expected-image",
            image,
            "--network",
            network,
            "--user",
            "1000:1000",
            "--entrypoint",
            "/bin/sleep",
            "--command",
            "infinity",
            "--env-allowlist",
            (
                "DB_HOST,DB_NAME,DB_PASSWD,DB_PORT,DB_USER,REDIS_DB,"
                "REDIS_HOST,REDIS_PORT,REDIS_SSL,ROMM_BASE_PATH"
            ),
            "--port",
            str(contract_port),
        ]
        result = _run(command, timeout=1800)
        if result.returncode:
            raise StageFailure(
                "contract verifier failed: "
                + redact_output(
                    result.stdout + result.stderr,
                    secrets=(identity.password,),
                )
            )
    finally:
        if source_id is not None:
            _remove_container(source_id)
        cleanup_database_resources(identity, db_container)
    generated_after = _tracked_manifest(checkout, ["frontend/src/__generated__"])
    if generated_before != generated_after:
        raise StageFailure("generated frontend contract changed")
    return {
        "exit_code": 0,
        "generated_before": generated_before["sha256"],
        "generated_after": generated_after["sha256"],
        "generated_files": generated_after["count"],
    }


def _node_command(
    checkout: Path,
    volume: str,
    node_image: str,
    network: str,
    script: str,
) -> list[str]:
    owner = checkout.stat()
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        network,
        "--user",
        f"{owner.st_uid}:{owner.st_gid}",
        "--mount",
        f"type=bind,src={checkout},dst=/workspace,readonly",
        "--mount",
        f"type=volume,src={volume},dst=/workspace/frontend/node_modules",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev",
        "--workdir",
        "/workspace/frontend",
        "--entrypoint",
        "/bin/sh",
        node_image,
        "-lc",
        script,
    ]


def _run_frontend(
    checkout: Path,
    node_image: str,
    network: str,
) -> tuple[dict[str, dict[str, object]], str]:
    suffix = secrets.token_hex(8)
    volume = f"p0647-node-{suffix}"
    created = _run(
        [
            "docker",
            "volume",
            "create",
            "--label",
            f"{OWNERSHIP_LABEL}={suffix}",
            volume,
        ]
    )
    if created.returncode or created.stdout.strip() != volume:
        raise StageFailure("Node volume creation failed")
    owner = checkout.stat()
    try:
        chown = _run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--mount",
                f"type=volume,src={volume},dst=/deps",
                "--entrypoint",
                "/bin/chown",
                node_image,
                "-R",
                f"{owner.st_uid}:{owner.st_gid}",
                "/deps",
            ]
        )
        if chown.returncode:
            raise StageFailure("Node volume ownership setup failed")
        scripts = {
            "install": "npm ci",
            "focused": "npm run test -- " + " ".join(FOCUSED_UI_TESTS),
            "full": "npm run test",
            "typecheck": "NODE_OPTIONS=--max-old-space-size=4096 npm run typecheck",
            "build": (
                "NODE_OPTIONS=--max-old-space-size=4096 "
                "npm run build -- --outDir /tmp/p0647-build"
            ),
            "locales": (
                "python3 src/locales/check_i18n_locales.py && "
                "python3 src/locales/check_i18n_sorted.py"
            ),
            "static": ("./node_modules/.bin/eslint " + " ".join(FOCUSED_UI_TESTS)),
        }
        records: dict[str, dict[str, object]] = {}
        for name, script in scripts.items():
            result = _run(
                _node_command(checkout, volume, node_image, network, script),
                timeout=1800,
            )
            if result.returncode:
                raise StageFailure(
                    f"frontend {name} failed: "
                    + redact_output(result.stdout + result.stderr)
                )
            if name != "install":
                records[name] = {"exit_code": 0}
                match = re.search(
                    r"Tests\s+(\d+) passed", result.stdout + result.stderr
                )
                if match:
                    records[name]["tests"] = int(match.group(1))
                print(f"[PASS] frontend {name}")
        if "install" not in scripts:
            raise StageFailure("frontend dependency stage is missing")
        return records, volume
    except BaseException as error:
        removed = _run(["docker", "volume", "rm", volume])
        if removed.returncode:
            raise StageFailure(
                "Node volume cleanup failed after stage error"
            ) from error
        raise


def _remove_node_volume(volume: str) -> None:
    result = _run(["docker", "volume", "rm", volume])
    if result.returncode:
        raise StageFailure("exact Node volume cleanup failed")


def _manual_ui_evidence(checkout: Path) -> dict[str, object]:
    drift = _run(
        [
            "git",
            "diff",
            "--quiet",
            f"{UI_EVIDENCE_COMMIT}..HEAD",
            "--",
            *UI_EVIDENCE_PATHS,
        ]
    )
    if drift.returncode:
        raise StageFailure("manual UI evidence files drifted after validated matrix")
    return {
        "status": "previously_validated_no_drift",
        "evidence": "06-45-SUMMARY.md",
        "fresh_run": False,
        "matrix": (
            "both themes; 320px; xs/sm/md/lg/xl/4K; mouse/touch/keyboard/"
            "gamepad; focus; announcements; slow/failure/retry/conflict/refresh"
        ),
    }


def _audit_absence(
    checkout: Path,
    db_container: str,
    source_container: str,
    expected_untracked_count: int,
) -> dict[str, int]:
    containers = _run(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            "name=p0647-",
            "--format",
            "{{.Names}}",
        ],
        check=True,
    )
    volumes = _run(
        [
            "docker",
            "volume",
            "ls",
            "--filter",
            "name=p0647-",
            "--format",
            "{{.Name}}",
        ],
        check=True,
    )
    sql = (
        "SELECT "
        "(SELECT COUNT(*) FROM information_schema.SCHEMATA "
        "WHERE SCHEMA_NAME LIKE 'p0647\\_%' ESCAPE '\\\\'),"
        "(SELECT COUNT(*) FROM mysql.user "
        "WHERE User LIKE 'p0647\\_%' ESCAPE '\\\\')"
    )
    database_counts = _run(_database_admin_command(db_container, sql), check=True)
    if containers.stdout.strip() or volumes.stdout.strip():
        raise StageFailure("p0647 Docker resource remains")
    if database_counts.stdout.strip() != "0\t0":
        raise StageFailure("p0647 database or principal remains")
    _baseline_record(checkout, expected_untracked_count)
    generated = _run(["git", "diff", "--exit-code", "--", "frontend/src/__generated__"])
    if generated.returncode:
        raise StageFailure("generated contract tree has differences")
    diff_check = _run(["git", "diff", "--check"])
    if diff_check.returncode:
        raise StageFailure("git diff whitespace gate failed")
    state = _run(
        ["docker", "inspect", "--format", "{{.State.Status}}", source_container],
        check=True,
    ).stdout.strip()
    if state == "running":
        raise StageFailure("source service was started")
    return {
        "containers": 0,
        "databases": 0,
        "principals": 0,
        "basetemps": 0,
        "volumes": 0,
        "exit_code": 0,
    }


def canonical_run_digest(record: dict[str, object]) -> str:
    payload = dict(record)
    payload.pop("run_digest", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def validate_acceptance_record(record: dict[str, object]) -> None:
    expected_digest = canonical_run_digest(record)
    if record.get("run_digest") != expected_digest:
        raise EvidenceError("acceptance run digest mismatch")
    if record.get("schema_version") != 1:
        raise EvidenceError("acceptance schema version mismatch")
    run_id = record.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise EvidenceError("acceptance run_id is malformed")
    if record.get("command_identity") != CANONICAL_COMMAND_IDENTITY:
        raise EvidenceError("canonical command identity mismatch")
    stages = record.get("stages")
    if not isinstance(stages, dict):
        raise EvidenceError("structured stages are missing")
    required = {
        "db_continuity",
        "prior_backend",
        "phase6_backend",
        "dialects",
        "contracts",
        "frontend",
        "manifests",
        "cleanup",
        "baseline",
        "git",
        "manual_ui",
    }
    missing = required - set(stages)
    if missing:
        raise EvidenceError("missing structured stage: " + ", ".join(sorted(missing)))

    prior = stages["prior_backend"]
    if (
        prior.get("exit_code") != 0
        or prior.get("outcomes", 0) < PRIOR_OUTCOMES_MIN
        or tuple(item.get("module") for item in prior.get("modules", []))
        != PRIOR_PHASE_MODULES
        or any(
            item.get("exit_code") != 0
            or item.get("failed") != 0
            or item.get("errors") != 0
            for item in prior.get("modules", [])
        )
    ):
        raise EvidenceError("prior backend structured stage is invalid")
    phase6 = stages["phase6_backend"]
    if (
        phase6.get("exit_code") != 0
        or tuple(item.get("module") for item in phase6.get("modules", []))
        != deduplicated_phase6_modules()
        or any(
            item.get("exit_code") != 0
            or item.get("failed") != 0
            or item.get("errors") != 0
            for item in phase6.get("modules", [])
        )
    ):
        raise EvidenceError("Phase 6 backend structured stage is invalid")
    dialects = stages["dialects"]
    if set(dialects) != {"mariadb", "mysql", "postgresql"} or any(
        value.get("exit_code") != 0 for value in dialects.values()
    ):
        raise EvidenceError("dialect structured stage is invalid")
    contracts = stages["contracts"]
    if contracts.get("exit_code") != 0 or contracts.get(
        "generated_before"
    ) != contracts.get("generated_after"):
        raise EvidenceError("contract structured stage is invalid")
    frontend = stages["frontend"]
    for name in ("focused", "full", "typecheck", "build", "locales", "static"):
        if name not in frontend or frontend[name].get("exit_code") != 0:
            raise EvidenceError(f"frontend {name} structured stage is invalid")
    manifests = stages["manifests"]
    if manifests.get("equal") is not True or manifests.get("before") != manifests.get(
        "after"
    ):
        raise EvidenceError("source manifest structured stage is invalid")
    continuity = stages["db_continuity"]
    if (
        continuity.get("before") != 1
        or continuity.get("after") != 1
        or continuity.get("exit_code") != 0
    ):
        raise EvidenceError("database continuity structured stage is invalid")
    cleanup = stages["cleanup"]
    if cleanup.get("exit_code") != 0 or any(
        cleanup.get(name) != 0
        for name in ("containers", "databases", "principals", "basetemps", "volumes")
    ):
        raise EvidenceError("cleanup structured stage is invalid")
    baseline = stages["baseline"]
    if (
        baseline.get("untracked_count") != 28
        or baseline.get("untracked_sha256") != BASELINE_UNTRACKED_SHA256
    ):
        raise EvidenceError("baseline structured stage is invalid")
    if stages["git"].get("diff_check") != 0:
        raise EvidenceError("git structured stage is invalid")
    if stages["manual_ui"].get("status") != "previously_validated_no_drift":
        raise EvidenceError("manual UI structured stage is invalid")


def parse_source_audit(markdown: str) -> frozenset[str]:
    found: list[str] = []
    for line in markdown.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5 or cells[1] == "ID" or re.fullmatch(r"-{3,}", cells[1]):
            continue
        source_id = cells[1]
        if source_id not in REQUIRED_SOURCE_IDS:
            raise EvidenceError(f"unknown source audit ID: {source_id}")
        if cells[-1] != "COVERED":
            raise EvidenceError(f"source audit ID is not COVERED: {source_id}")
        found.append(source_id)
    if len(found) != len(set(found)):
        raise EvidenceError("duplicate source audit ID")
    if frozenset(found) != REQUIRED_SOURCE_IDS:
        raise EvidenceError("source audit current set mismatch")
    if re.search(r"\b(DEFERRED|PARTIAL|MISSING|UNKNOWN)\b", markdown):
        raise EvidenceError("source audit contains a non-COVERED current state")
    return frozenset(found)


def verify_evidence_record(
    record: dict[str, object], validation: str, source_audit: str
) -> None:
    validate_acceptance_record(record)
    run_id = str(record["run_id"])
    run_digest = str(record["run_digest"])
    if f"Run ID: `{run_id}`" not in validation:
        raise EvidenceError("validation run_id binding mismatch")
    if f"Run Digest: `{run_digest}`" not in validation:
        raise EvidenceError("validation run_digest binding mismatch")
    stages = record["stages"]
    if not isinstance(stages, dict):
        raise EvidenceError("acceptance stages must be an object")
    prior = stages.get("prior_backend")
    if not isinstance(prior, dict):
        raise EvidenceError("prior backend stage must be an object")
    modules = prior.get("modules")
    outcomes = prior.get("outcomes")
    if not isinstance(modules, list) or not isinstance(outcomes, int):
        raise EvidenceError("prior backend stage counts are invalid")
    module_match = re.search(r"Prior modules:\s*(\d+)", validation)
    outcome_match = re.search(r"Prior outcomes:\s*(\d+)", validation)
    if (
        module_match is None
        or int(module_match.group(1)) != len(modules)
        or outcome_match is None
        or int(outcome_match.group(1)) != outcomes
    ):
        raise EvidenceError("validation counts do not match structured stage")
    parse_source_audit(source_audit)


def _atomic_json_write(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _run_self_test(args: argparse.Namespace) -> None:
    checkout = Path(__file__).resolve().parents[2]
    identity = ResourceIdentity.create(99)
    before = _normal_db_select_one(args.db_container)
    record = _execute_docker_module(
        checkout,
        "tests/tools/test_verify_phase6_acceptance.py",
        identity,
        args.expected_source_image,
        args.network,
        args.db_container,
        unit_contract=True,
    )
    after = _normal_db_select_one(args.db_container)
    passed = record.get("passed")
    if not isinstance(passed, int) or passed < 9 or before != 1 or after != 1:
        raise StageFailure("acceptance harness self-test was incomplete")


def _run_complete(args: argparse.Namespace) -> None:
    checkout = args.checkout.resolve()
    _validate_inventory(checkout)
    checkout_record = _preflight(
        checkout,
        branch=args.branch,
        origin=args.origin,
        project=args.project,
        base_commit=args.base_commit,
        source_container=args.source_container,
        expected_image=args.expected_source_image,
        network=args.network,
    )
    baseline = _baseline_record(checkout, args.baseline_untracked_count)
    before_db = _normal_db_select_one(args.db_container)
    manifest_before = _tracked_manifest(checkout, ["backend", "frontend"])
    prior_records: list[dict[str, object]] = []
    phase6_records: list[dict[str, object]] = []
    for index, module in enumerate(PRIOR_PHASE_MODULES):
        prior_records.append(
            _execute_docker_module(
                checkout,
                module,
                ResourceIdentity.create(index),
                args.expected_source_image,
                args.network,
                args.db_container,
            )
        )
    prior_outcomes = 0
    for module_record in prior_records:
        passed = module_record.get("passed")
        skipped = module_record.get("skipped")
        xfailed = module_record.get("xfailed")
        xpassed = module_record.get("xpassed")
        if not all(
            isinstance(value, int) for value in (passed, skipped, xfailed, xpassed)
        ):
            raise StageFailure("prior backend record has invalid outcome counts")
        assert isinstance(passed, int)
        assert isinstance(skipped, int)
        assert isinstance(xfailed, int)
        assert isinstance(xpassed, int)
        prior_outcomes += passed + skipped + xfailed + xpassed
    if prior_outcomes < args.prior_outcomes_min:
        raise StageFailure("prior backend outcomes are below the required minimum")
    for index, module in enumerate(deduplicated_phase6_modules(), start=40):
        phase6_records.append(
            _execute_docker_module(
                checkout,
                module,
                ResourceIdentity.create(index),
                args.expected_source_image,
                args.network,
                args.db_container,
            )
        )
    dialects = _run_dialects(checkout, args.expected_source_image, args.network)
    contracts = _run_contracts(
        checkout,
        args.expected_source_image,
        args.network,
        args.db_container,
        args.contract_port,
    )
    frontend: dict[str, dict[str, object]]
    node_volume: str | None = None
    try:
        frontend, node_volume = _run_frontend(
            checkout,
            args.node_image,
            args.network,
        )
    finally:
        if node_volume is not None:
            _remove_node_volume(node_volume)
    manual_ui = _manual_ui_evidence(checkout)
    manifest_after = _tracked_manifest(checkout, ["backend", "frontend"])
    if manifest_before != manifest_after:
        raise StageFailure("tracked source manifest changed during acceptance")
    after_db = _normal_db_select_one(args.db_container)
    cleanup = _audit_absence(
        checkout,
        args.db_container,
        args.source_container,
        args.baseline_untracked_count,
    )
    record: dict[str, object] = {
        "schema_version": 1,
        "run_id": secrets.token_hex(16),
        "command_identity": CANONICAL_COMMAND_IDENTITY,
        "checkout": checkout_record,
        "stages": {
            "db_continuity": {
                "before": before_db,
                "after": after_db,
                "exit_code": 0,
            },
            "prior_backend": {
                "modules": prior_records,
                "outcomes": prior_outcomes,
                "exit_code": 0,
            },
            "phase6_backend": {
                "modules": phase6_records,
                "exit_code": 0,
            },
            "dialects": dialects,
            "contracts": contracts,
            "frontend": frontend,
            "manifests": {
                "before": manifest_before["sha256"],
                "after": manifest_after["sha256"],
                "entries": manifest_after["count"],
                "equal": True,
            },
            "cleanup": cleanup,
            "baseline": baseline,
            "git": {"diff_check": 0},
            "manual_ui": manual_ui,
        },
    }
    record["run_digest"] = canonical_run_digest(record)
    validate_acceptance_record(record)
    evidence_path = args.evidence_json
    if not evidence_path.is_absolute():
        evidence_path = checkout / evidence_path
    _atomic_json_write(evidence_path, record)
    print(
        "[PASS] complete Phase 6 acceptance: "
        f"{len(prior_records)} prior modules, {prior_outcomes} outcomes, "
        f"{len(phase6_records)} Phase 6 modules"
    )


def _verify_evidence(args: argparse.Namespace) -> None:
    record = json.loads(args.evidence_json.read_text(encoding="utf-8"))
    validation = args.validation.read_text(encoding="utf-8")
    source_audit = args.source_audit.read_text(encoding="utf-8")
    verify_evidence_record(record, validation, source_audit)
    print("[PASS] evidence digest, validation binding, and exact source coverage")


def _audit_only(args: argparse.Namespace) -> None:
    checkout = args.checkout.resolve()
    _normal_db_select_one(args.db_container)
    _audit_absence(
        checkout,
        args.db_container,
        args.source_container,
        args.baseline_untracked_count,
    )
    print("[PASS] exact cleanup, baseline, generated tree, and stopped service audit")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--run-complete", action="store_true")
    modes.add_argument("--audit-only", action="store_true")
    modes.add_argument("--verify-evidence", action="store_true")
    parser.add_argument(
        "--checkout",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument(
        "--base-commit",
        default="3e0b278cf3e71fe84f1e7b20b354f94728fc9531",
    )
    parser.add_argument("--branch", default="codex/pc-module-analysis")
    parser.add_argument(
        "--origin",
        default="https://github.com/rommapp/romm.git",
    )
    parser.add_argument("--project", default="RomM PC Library")
    parser.add_argument("--source-container", default="romm-dev")
    parser.add_argument("--db-container", default="romm-db-dev")
    parser.add_argument("--expected-source-image", default="romm-romm-dev")
    parser.add_argument("--network", default="romm_default")
    parser.add_argument("--node-image", default="node:24-bookworm")
    parser.add_argument("--contract-port", type=int, default=39006)
    parser.add_argument("--baseline-untracked-count", type=int, default=28)
    parser.add_argument("--prior-outcomes-min", type=int, default=PRIOR_OUTCOMES_MIN)
    parser.add_argument(
        "--evidence-json",
        type=Path,
        default=Path(ACCEPTANCE_RELATIVE_PATH),
    )
    parser.add_argument(
        "--validation",
        type=Path,
        default=Path(
            ".planning/phases/06-safe-lifecycle-and-legacy-migration/"
            "06-VALIDATION.md"
        ),
    )
    parser.add_argument(
        "--source-audit",
        type=Path,
        default=Path(
            ".planning/phases/06-safe-lifecycle-and-legacy-migration/"
            "06-SOURCE-AUDIT.md"
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    active_cleanup = False

    def stop(signum: int, _frame: FrameType | None) -> None:
        if active_cleanup:
            print("[WARN] cleanup is already active", file=sys.stderr)
        raise SystemExit(128 + signum)

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, stop)
    if args.self_test:
        _run_self_test(args)
    elif args.run_complete:
        _run_complete(args)
    elif args.audit_only:
        _audit_only(args)
    else:
        _verify_evidence(args)


if __name__ == "__main__":
    main()
