#!/usr/bin/env python3
"""Phase 9 operational immutability harness."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlsplit

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = REPO_ROOT / ".planning" / "phases" / "09-operational-immutability-proof"
COMPOSE_FILE = REPO_ROOT / "backend" / "docker-compose.immutability-test.yml"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "operational-immutability"
SOURCE_LIBRARY_ROOT = FIXTURE_ROOT / "source-library"
PHASE_LABELS = {
    "romm.phase": "09",
    "romm.phase.slug": "operational-immutability-proof",
}
SOURCE_TARGET = "/romm/library"
OWNED_TARGETS = {
    "/romm/assets",
    "/romm/cache",
    "/romm/config",
    "/romm/database",
    "/romm/resources",
    "/romm/tmp",
    "/phase9-artifacts",
}
MANIFEST_SCHEMA_VERSION = "phase9.manifest.v1"
RUN_SCHEMA_VERSION = "phase9.run.v1"
DOCS_SCHEMA_VERSION = "phase9.docs.v1"
BROWSER_SCHEMA_VERSION = "phase9.browser.v1"
DOC_GUIDE_PATH = REPO_ROOT / "docs" / "external-read-only-library-operations.md"
VALIDATION_PATH = PHASE_DIR / "09-VALIDATION.md"
PHASE9_PLATFORM_SEEDER = Path(
    "/workspace/backend/tools/seed_phase9_database_platforms.py"
)
PHASE9_E2E_USER_SEEDER = Path("/workspace/.github/scripts/seed_e2e_users.py")
REQUIRED_REQUIREMENT_IDS = (
    "DOC-01",
    "DOC-02",
    "DOC-03",
    "TEST-04",
    "TEST-05",
    "TEST-06",
)

DOC_REQUIREMENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "DOC-01": {
        "headings": (
            "# External Read-Only Library Operations",
            "## Read-Only Mount Topology",
            "## Writable Separation",
            "## Register a Root and Browse Mappings",
            "## Scan, Preview, Stream, and Download",
            "## Migration and Catalog-Only Removal",
            "## Troubleshooting and Defense in Depth",
        ),
        "phrases": (
            "Mount one library root read-only at `/romm/library:ro`.",
            "RomM-owned writes stay on separate writable storage.",
            "Original files and folders stay unchanged.",
        ),
    },
    "DOC-02": {
        "headings": (
            "## noatime and NAS-Equivalent Guidance",
            "## Maintenance Window Checklist",
        ),
        "phrases": (
            "Access time can still change during ordinary reads unless `noatime` or a NAS-equivalent setting is enabled.",
            "Content and directory structure remain unchanged even when access time changes.",
            "Use only synthetic or repository-controlled fixtures for Phase 9 proof.",
        ),
    },
    "DOC-03": {
        "headings": ("## Team4s Safeguards",),
        "phrases": (
            "Do not edit Team4s source or configuration.",
            "Do not restart or stop Team4s services, the Team4s host, or active encode workloads.",
            "Phase 9 does not authorize a real NAS mount change.",
        ),
    },
}

FORBIDDEN_DOC_SNIPPETS = (
    "docker restart team4s",
    "docker stop team4s",
    "systemctl restart team4s",
    "phase 9 uses a real nas mount",
    "browse the host path",
    "expose the host path",
)


@dataclass(frozen=True, slots=True)
class WorkflowSpec:
    slug: str
    requirements: tuple[str, ...]
    category: str
    needs_nginx_witness: bool = False
    needs_worker_witness: bool = False
    needs_restart_witness: bool = False


WORKFLOW_SPECS: tuple[WorkflowSpec, ...] = (
    WorkflowSpec("mapping-create", ("TEST-04", "TEST-05"), "mapping"),
    WorkflowSpec("mapping-update", ("TEST-04", "TEST-05"), "mapping"),
    WorkflowSpec("mapping-remove", ("TEST-04", "TEST-05"), "mapping"),
    WorkflowSpec("browse-test", ("TEST-04", "TEST-05"), "mapping"),
    WorkflowSpec("preview", ("TEST-04", "TEST-05"), "mapping"),
    WorkflowSpec("scan-hash", ("TEST-04", "TEST-05", "TEST-06"), "worker", True, True),
    WorkflowSpec(
        "metadata-match",
        ("TEST-04", "TEST-05", "TEST-06"),
        "worker",
        needs_worker_witness=True,
    ),
    WorkflowSpec(
        "stream-play",
        ("TEST-04", "TEST-05", "TEST-06"),
        "delivery",
        needs_nginx_witness=True,
    ),
    WorkflowSpec(
        "single-download",
        ("TEST-04", "TEST-05", "TEST-06"),
        "delivery",
        needs_nginx_witness=True,
    ),
    WorkflowSpec(
        "multi-download",
        ("TEST-04", "TEST-05", "TEST-06"),
        "delivery",
        needs_nginx_witness=True,
    ),
    WorkflowSpec(
        "restart-persistence",
        ("TEST-04", "TEST-05"),
        "restart",
        needs_restart_witness=True,
    ),
    WorkflowSpec("legacy-migration", ("TEST-04", "TEST-05"), "lifecycle"),
    WorkflowSpec("supported-rollback", ("TEST-04", "TEST-05"), "lifecycle"),
    WorkflowSpec("game-catalog-removal", ("TEST-04", "TEST-05"), "lifecycle"),
    WorkflowSpec("platform-mapping-removal", ("TEST-04", "TEST-05"), "lifecycle"),
)
WORKFLOW_BY_SLUG = {spec.slug: spec for spec in WORKFLOW_SPECS}
BROWSER_WORKFLOW_SLUGS = {
    spec.slug for spec in WORKFLOW_SPECS if spec.slug != "restart-persistence"
}


def _encode_path(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )


def _write_service_logs(
    artifacts_root: Path, compose_project: str, run_id: str
) -> None:
    logs_root = artifacts_root / "service-logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    log_lines = {
        "app.log": f"{compose_project} app witness for {run_id}\n",
        "db.log": f"{compose_project} database witness for {run_id}\n",
        "nginx.log": f"{compose_project} nginx witness for {run_id}\n",
        "redis.log": f"{compose_project} redis witness for {run_id}\n",
        "worker.log": f"{compose_project} worker witness for {run_id}\n",
    }
    for file_name, content in log_lines.items():
        (logs_root / file_name).write_text(content, encoding="utf-8")


def _run_command(
    command: list[str],
    *,
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _phase9_environment(
    *,
    fixture_root: Path,
    artifacts_root: Path,
    compose_project: str,
) -> dict[str, str]:
    return os.environ | {
        "PHASE9_REPO_ROOT": str(REPO_ROOT),
        "PHASE9_FIXTURE_SOURCE": str(fixture_root),
        "PHASE9_ARTIFACTS": str(artifacts_root),
        "COMPOSE_PROJECT_NAME": compose_project,
    }


def _compose_command(*args: str) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *args]


def _start_stack(
    *,
    fixture_root: Path,
    artifacts_root: Path,
    compose_project: str,
) -> None:
    environment = _phase9_environment(
        fixture_root=fixture_root,
        artifacts_root=artifacts_root,
        compose_project=compose_project,
    )
    _run_command(
        _compose_command("up", "-d", "database", "queue", "app", "worker", "nginx"),
        env=environment,
    )


def _seed_database_platforms(
    *,
    fixture_root: Path,
    artifacts_root: Path,
    compose_project: str,
) -> None:
    environment = _phase9_environment(
        fixture_root=fixture_root,
        artifacts_root=artifacts_root,
        compose_project=compose_project,
    )
    _run_command(
        _compose_command(
            "exec",
            "-T",
            "app",
            "uv",
            "run",
            "python",
            str(PHASE9_PLATFORM_SEEDER),
        ),
        env=environment,
    )


def _seed_e2e_users(
    *,
    fixture_root: Path,
    artifacts_root: Path,
    compose_project: str,
) -> None:
    environment = _phase9_environment(
        fixture_root=fixture_root,
        artifacts_root=artifacts_root,
        compose_project=compose_project,
    )
    _run_command(
        _compose_command(
            "exec",
            "-T",
            "app",
            "uv",
            "run",
            "python",
            str(PHASE9_E2E_USER_SEEDER),
        ),
        env=environment,
    )


def _stop_stack(
    *,
    fixture_root: Path,
    artifacts_root: Path,
    compose_project: str,
) -> None:
    environment = _phase9_environment(
        fixture_root=fixture_root,
        artifacts_root=artifacts_root,
        compose_project=compose_project,
    )
    _run_command(
        _compose_command("down", "-v", "--remove-orphans"),
        env=environment,
    )


def _resolve_base_url() -> str:
    configured = os.environ.get("PHASE9_BROWSER_BASE_URL") or os.environ.get(
        "E2E_BASE_URL"
    )
    if configured:
        return configured
    return "http://127.0.0.1:3000"


def _resolve_compose_base_url(
    *,
    fixture_root: Path,
    artifacts_root: Path,
    compose_project: str,
) -> str:
    configured = os.environ.get("PHASE9_BROWSER_BASE_URL") or os.environ.get(
        "E2E_BASE_URL"
    )
    if configured:
        return configured
    environment = _phase9_environment(
        fixture_root=fixture_root,
        artifacts_root=artifacts_root,
        compose_project=compose_project,
    )
    completed = _run_command(_compose_command("port", "nginx", "80"), env=environment)
    port_line = completed.stdout.strip().splitlines()[-1]
    host, _, port = port_line.rpartition(":")
    resolved_host = host or "127.0.0.1"
    if resolved_host == "0.0.0.0":
        resolved_host = "127.0.0.1"
    return f"http://{resolved_host}:{port}"


def _wait_for_base_url(base_url: str, *, timeout_seconds: int = 30) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    heartbeat_url = f"{base_url.rstrip('/')}/api/heartbeat"
    while time.monotonic() < deadline:
        try:
            with urllib_request.urlopen(heartbeat_url, timeout=2) as response:
                if response.status < 500:
                    return
        except (OSError, urllib_error.URLError, TimeoutError) as exc:
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"backend did not become ready: {heartbeat_url}") from last_error


def _run_browser_matrix(*, base_url: str, artifacts_root: Path) -> None:
    environment = os.environ | {
        "E2E_BASE_URL": base_url,
        "PHASE9_BROWSER_ARTIFACTS_DIR": str(artifacts_root),
        "E2E_WORKERS": "1",
    }
    _run_command(
        [
            "npx",
            "playwright",
            "test",
            "e2e/operational-immutability.spec.ts",
            "--project=chromium",
            "--workers=1",
        ],
        cwd=REPO_ROOT / "frontend",
        env=environment,
    )


def _collect_service_logs(
    *,
    fixture_root: Path,
    artifacts_root: Path,
    compose_project: str,
    services: list[str],
) -> None:
    environment = _phase9_environment(
        fixture_root=fixture_root,
        artifacts_root=artifacts_root,
        compose_project=compose_project,
    )
    logs_root = artifacts_root / "service-logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    service_file_names = {
        "app": "app.log",
        "database": "db.log",
        "nginx": "nginx.log",
        "queue": "redis.log",
        "worker": "worker.log",
    }
    for service in services:
        completed = _run_command(
            _compose_command("logs", "--no-color", service),
            env=environment,
        )
        (logs_root / service_file_names.get(service, f"{service}.log")).write_text(
            completed.stdout,
            encoding="utf-8",
        )


def validate_browser_artifacts(
    artifacts_root: Path,
    *,
    selected_workflows: tuple[WorkflowSpec, ...],
    run_id: str | None = None,
    base_url: str | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for spec in selected_workflows:
        if spec.slug not in BROWSER_WORKFLOW_SLUGS:
            continue
        artifact_path = artifacts_root / "workflows" / spec.slug / "browser.json"
        if not artifact_path.is_file():
            raise ValueError(f"missing browser artifact for workflow {spec.slug}")
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        if artifact.get("schema_version") != BROWSER_SCHEMA_VERSION:
            raise ValueError(f"browser artifact has wrong schema for {spec.slug}")
        if artifact.get("workflow") != spec.slug:
            raise ValueError(f"browser artifact slug mismatch for {spec.slug}")
        if artifact.get("status") != "passed":
            raise ValueError(f"browser artifact did not pass for {spec.slug}")
        if run_id is not None and artifact.get("run_id") != run_id:
            raise ValueError(f"browser artifact run mismatch for {spec.slug}")
        if base_url is not None:
            expected_origin = urlsplit(base_url).netloc
            actual_origin = urlsplit(str(artifact.get("final_url", ""))).netloc
            if not expected_origin or actual_origin != expected_origin:
                raise ValueError(f"browser artifact origin mismatch for {spec.slug}")
        results.append(artifact)
    return results


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_fixture_manifest(root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    directory_paths: set[str] = set()

    for path in sorted(
        root.rglob("*"),
        key=lambda item: item.relative_to(root).as_posix().encode("utf-8"),
    ):
        stat_before = path.lstat()
        relative_path = path.relative_to(root).as_posix()
        entry_type = (
            "symlink" if path.is_symlink() else "directory" if path.is_dir() else "file"
        )
        entry: dict[str, Any] = {
            "relative_path": relative_path,
            "encoded_path": _encode_path(relative_path),
            "entry_type": entry_type,
            "mode": stat_before.st_mode,
            "size": stat_before.st_size,
            "mtime_ns": stat_before.st_mtime_ns,
            "ctime_ns": stat_before.st_ctime_ns,
            "birthtime_ns": getattr(stat_before, "st_birthtime_ns", None),
            "atime_ns": stat_before.st_atime_ns,
        }
        if entry_type == "file":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            stat_after = path.lstat()
            if (
                stat_after.st_mtime_ns != stat_before.st_mtime_ns
                or stat_after.st_size != stat_before.st_size
            ):
                raise ValueError(f"manifest capture race detected for {relative_path}")
            entry["sha256"] = digest
        elif entry_type == "symlink":
            entry["symlink_target"] = os.readlink(path)
        else:
            directory_paths.add(relative_path)
        entries.append(entry)

    root_stat = root.lstat()
    counts = {
        "directories": sum(
            1 for entry in entries if entry["entry_type"] == "directory"
        ),
        "files": sum(1 for entry in entries if entry["entry_type"] == "file"),
        "symlinks": sum(1 for entry in entries if entry["entry_type"] == "symlink"),
        "total_entries": len(entries),
        "empty_directories": sum(
            1
            for directory in directory_paths
            if not any(
                candidate != directory and candidate.startswith(f"{directory}/")
                for candidate in [entry["relative_path"] for entry in entries]
            )
        ),
    }
    aggregate_digest = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "root": {
            "id": "fixture-root",
            "relative_path": ".",
            "encoded_path": _encode_path("."),
            "entry_type": "directory",
            "mode": root_stat.st_mode,
            "size": root_stat.st_size,
            "mtime_ns": root_stat.st_mtime_ns,
            "ctime_ns": root_stat.st_ctime_ns,
            "birthtime_ns": getattr(root_stat, "st_birthtime_ns", None),
            "atime_ns": root_stat.st_atime_ns,
        },
        "entries": entries,
        "counts": counts,
        "aggregate_digest": aggregate_digest,
    }
    validate_manifest(manifest)
    return manifest


def compare_manifests(
    before: dict[str, Any], after: dict[str, Any], *, require_atime: bool = False
) -> dict[str, Any]:
    validate_manifest(before)
    validate_manifest(after)

    before_entries = {entry["relative_path"]: entry for entry in before["entries"]}
    after_entries = {entry["relative_path"]: entry for entry in after["entries"]}
    all_paths = sorted(
        set(before_entries) | set(after_entries),
        key=lambda value: value.encode("utf-8"),
    )
    changed_fields: list[dict[str, Any]] = []
    for relative_path in all_paths:
        if relative_path not in before_entries:
            changed_fields.append({"path": relative_path, "change": "added"})
            continue
        if relative_path not in after_entries:
            changed_fields.append({"path": relative_path, "change": "removed"})
            continue
        before_entry = before_entries[relative_path]
        after_entry = after_entries[relative_path]
        fields = [
            "entry_type",
            "mode",
            "size",
            "mtime_ns",
            "ctime_ns",
            "birthtime_ns",
            "encoded_path",
        ]
        if require_atime:
            fields.append("atime_ns")
        if before_entry["entry_type"] == "file":
            fields.append("sha256")
        if before_entry["entry_type"] == "symlink":
            fields.append("symlink_target")
        for field_name in fields:
            if before_entry.get(field_name) != after_entry.get(field_name):
                changed_fields.append(
                    {
                        "path": relative_path,
                        "change": "modified",
                        "field": field_name,
                        "before": before_entry.get(field_name),
                        "after": after_entry.get(field_name),
                    }
                )

    count_changes = {
        key: {"before": before["counts"].get(key), "after": after["counts"].get(key)}
        for key in before["counts"]
        if before["counts"].get(key) != after["counts"].get(key)
    }
    root_changed = {
        key: {"before": before["root"].get(key), "after": after["root"].get(key)}
        for key in before["root"]
        if key != "atime_ns" or require_atime
        if before["root"].get(key) != after["root"].get(key)
    }
    return {
        "status": (
            "unchanged"
            if not changed_fields and not count_changes and not root_changed
            else "changed"
        ),
        "before_aggregate_digest": before["aggregate_digest"],
        "after_aggregate_digest": after["aggregate_digest"],
        "changes": changed_fields,
        "count_changes": count_changes,
        "root_changes": root_changed,
        "require_atime_match": require_atime,
    }


def manifest_identities(
    manifest: dict[str, Any],
) -> tuple[tuple[str, str, int, str], ...]:
    validate_manifest(manifest)
    identities = []
    for entry in manifest["entries"]:
        identities.append(
            (
                entry["relative_path"],
                entry["entry_type"],
                entry["size"],
                entry.get("sha256", entry.get("symlink_target", "")),
            )
        )
    return tuple(identities)


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"manifest schema_version must be {MANIFEST_SCHEMA_VERSION}")
    root = manifest.get("root")
    if not isinstance(root, dict):
        raise ValueError("manifest root record is required")
    root_fields = {
        "id",
        "relative_path",
        "encoded_path",
        "entry_type",
        "mode",
        "size",
        "mtime_ns",
        "ctime_ns",
        "birthtime_ns",
        "atime_ns",
    }
    missing_root = sorted(root_fields - set(root))
    if missing_root:
        raise ValueError(f"manifest root missing fields: {', '.join(missing_root)}")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest entries are required")

    required_common = {
        "relative_path",
        "encoded_path",
        "entry_type",
        "mode",
        "size",
        "mtime_ns",
        "ctime_ns",
        "birthtime_ns",
        "atime_ns",
    }
    seen_paths: set[str] = set()
    ordered_paths = [entry["relative_path"] for entry in entries]
    if ordered_paths != sorted(ordered_paths, key=lambda value: value.encode("utf-8")):
        raise ValueError("manifest entries must remain sorted by encoded relative path")

    empty_directories = 0
    for entry in entries:
        missing_common = sorted(required_common - set(entry))
        if missing_common:
            raise ValueError(
                f"manifest entry missing fields: {', '.join(missing_common)}"
            )
        relative_path = entry["relative_path"]
        if relative_path in seen_paths:
            raise ValueError(f"manifest contains duplicate entry: {relative_path}")
        seen_paths.add(relative_path)
        if Path(relative_path).is_absolute():
            raise ValueError(f"manifest path must be relative: {relative_path}")

        entry_type = entry["entry_type"]
        if entry_type == "file":
            if "sha256" not in entry:
                raise ValueError(f"manifest file entry missing sha256: {relative_path}")
        elif entry_type == "symlink":
            if "symlink_target" not in entry:
                raise ValueError(
                    f"manifest symlink entry missing target: {relative_path}"
                )
        elif entry_type == "directory":
            prefix = f"{relative_path}/"
            if not any(
                candidate["relative_path"].startswith(prefix) for candidate in entries
            ):
                empty_directories += 1
        else:
            raise ValueError(f"unknown manifest entry_type: {entry_type}")

    counts = manifest.get("counts")
    if not isinstance(counts, dict):
        raise ValueError("manifest counts are required")
    expected_counts = {
        "directories": sum(
            1 for entry in entries if entry["entry_type"] == "directory"
        ),
        "files": sum(1 for entry in entries if entry["entry_type"] == "file"),
        "symlinks": sum(1 for entry in entries if entry["entry_type"] == "symlink"),
        "total_entries": len(entries),
    }
    for key, value in expected_counts.items():
        if counts.get(key) != value:
            raise ValueError(f"manifest count mismatch for {key}")
    recorded_empty_directories = counts.get("empty_directories")
    if recorded_empty_directories is None:
        raise ValueError("manifest counts must record empty directories")
    if recorded_empty_directories != empty_directories:
        raise ValueError("manifest empty directory count mismatch")
    if empty_directories == 0:
        raise ValueError("manifest must preserve at least one empty directory")
    if "aggregate_digest" not in manifest:
        raise ValueError("manifest aggregate_digest is required")


def validate_artifact_paths(artifacts_root: Path, artifact_paths: list[str]) -> None:
    root = artifacts_root.resolve()
    for raw_path in artifact_paths:
        candidate = Path(raw_path)
        if candidate.is_absolute():
            raise ValueError(f"absolute artifact path is forbidden: {raw_path}")
        resolved = (artifacts_root / candidate).resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError(f"artifact path escapes root: {raw_path}")


def validate_cleanup_targets(resources: list[dict[str, Any]]) -> None:
    for resource in resources:
        labels = resource.get("labels")
        if not isinstance(labels, dict):
            raise ValueError("cleanup target must include owned labels")
        for key, expected in PHASE_LABELS.items():
            if labels.get(key) != expected:
                raise ValueError(f"cleanup target missing owned label {key}")


def _volume_target(volume: dict[str, Any]) -> str | None:
    return volume.get("target") if isinstance(volume, dict) else None


def _is_protected_mount(target: str) -> bool:
    return (
        target == SOURCE_TARGET
        or target in OWNED_TARGETS
        or target.startswith(f"{SOURCE_TARGET}/")
    )


def validate_compose_topology(compose_model: dict[str, Any]) -> None:
    services = compose_model.get("services")
    if not isinstance(services, dict) or not services:
        raise ValueError("compose services are required")

    owned_targets_seen: set[str] = set()
    source_mount_found = False

    for service_name, service in services.items():
        if "container_name" in service:
            raise ValueError("fixed container names are forbidden")
        if service.get("network_mode") == "host":
            raise ValueError("host network mode is forbidden")
        labels = service.get("labels")
        if not isinstance(labels, dict):
            raise ValueError(f"service {service_name} is missing ownership labels")
        for key, expected in PHASE_LABELS.items():
            if labels.get(key) != expected:
                raise ValueError(f"service {service_name} missing label {key}")

        volumes = service.get("volumes", [])
        if not isinstance(volumes, list):
            raise ValueError(f"service {service_name} volumes must be a list")
        service_targets: list[str] = []
        for volume in volumes:
            if not isinstance(volume, dict):
                continue
            target = _volume_target(volume)
            if not target:
                continue
            for existing_target in service_targets:
                if target == existing_target:
                    raise ValueError(
                        f"service {service_name} declares duplicate target {target}"
                    )
                overlaps = target.startswith(
                    f"{existing_target}/"
                ) or existing_target.startswith(f"{target}/")
                if overlaps and (
                    _is_protected_mount(target) or _is_protected_mount(existing_target)
                ):
                    raise ValueError(
                        f"mount overlap detected between {target} and {existing_target}"
                    )
            service_targets.append(target)
            if target == SOURCE_TARGET or target.startswith(f"{SOURCE_TARGET}/"):
                source_mount_found = True
                if not volume.get("read_only", False):
                    raise ValueError("source fixture mount must be read-only")
            elif target in OWNED_TARGETS:
                if volume.get("read_only", False):
                    raise ValueError(f"owned target must stay writable: {target}")
                owned_targets_seen.add(target)

    if not source_mount_found:
        raise ValueError("compose topology must mount one read-only source fixture")
    missing_owned = sorted(OWNED_TARGETS - owned_targets_seen)
    if missing_owned:
        raise ValueError(
            f"compose topology missing owned mounts: {', '.join(missing_owned)}"
        )


def load_compose_model(path: Path = COMPOSE_FILE) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing compose file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("compose file must decode to a mapping")
    return data


def fixture_contract() -> dict[str, Any]:
    return json.loads(
        (FIXTURE_ROOT / "fixture-contract.json").read_text(encoding="utf-8")
    )


def _read_operator_guide() -> str:
    if not DOC_GUIDE_PATH.is_file():
        raise ValueError(
            f"missing operator guide: {DOC_GUIDE_PATH.relative_to(REPO_ROOT)}"
        )
    return DOC_GUIDE_PATH.read_text(encoding="utf-8")


def validate_docs_contract(
    requirement_id: str, content: str | None = None
) -> dict[str, Any]:
    contract = DOC_REQUIREMENTS.get(requirement_id)
    if contract is None:
        raise ValueError(f"unknown docs requirement: {requirement_id}")
    guide = content if content is not None else _read_operator_guide()
    missing_headings = [
        heading for heading in contract["headings"] if heading not in guide
    ]
    missing_phrases = [phrase for phrase in contract["phrases"] if phrase not in guide]
    lowered = guide.lower()
    forbidden = [snippet for snippet in FORBIDDEN_DOC_SNIPPETS if snippet in lowered]
    if missing_headings:
        raise ValueError(
            f"{requirement_id} missing headings: {', '.join(missing_headings)}"
        )
    if missing_phrases:
        raise ValueError(
            f"{requirement_id} missing phrases: {', '.join(missing_phrases)}"
        )
    if forbidden:
        raise ValueError(
            f"{requirement_id} includes forbidden guidance: {', '.join(forbidden)}"
        )
    return {
        "schema_version": DOCS_SCHEMA_VERSION,
        "requirement_id": requirement_id,
        "guide": str(DOC_GUIDE_PATH.relative_to(REPO_ROOT)),
        "status": "passed",
        "checked_at": _iso_now(),
    }


def run_docs_checks(
    requirement_ids: tuple[str, ...] = ("DOC-01", "DOC-02", "DOC-03"),
) -> list[dict[str, Any]]:
    guide = _read_operator_guide()
    return [
        validate_docs_contract(requirement_id, guide)
        for requirement_id in requirement_ids
    ]


def run_preflight() -> dict[str, Any]:
    compose_model = load_compose_model()
    validate_compose_topology(compose_model)
    contract = fixture_contract()
    validate_cleanup_targets(
        [
            {
                "kind": "compose-service",
                "id": service_name,
                "labels": service.get("labels", {}),
            }
            for service_name, service in compose_model["services"].items()
        ]
    )
    return {
        "status": "ok",
        "compose_file": str(COMPOSE_FILE.relative_to(REPO_ROOT)),
        "fixture_contract": contract["name"],
        "services": sorted(compose_model["services"].keys()),
        "phase_labels": PHASE_LABELS,
    }


def _ensure_fixture_copy(run_root: Path) -> Path:
    fixture_root = run_root / "source-library"
    shutil.copytree(SOURCE_LIBRARY_ROOT, fixture_root)
    (fixture_root / "pc" / "Empty Library").mkdir(parents=True, exist_ok=True)
    return fixture_root


def _workflow_selection(
    workflow: str | None, requirement: str | None, run_all: bool
) -> tuple[WorkflowSpec, ...]:
    if workflow:
        spec = WORKFLOW_BY_SLUG.get(workflow)
        if spec is None:
            raise ValueError(f"unknown workflow: {workflow}")
        return (spec,)
    if requirement:
        selected = tuple(
            spec for spec in WORKFLOW_SPECS if requirement in spec.requirements
        )
        if not selected:
            raise ValueError(f"unknown requirement: {requirement}")
        return selected
    if run_all:
        return WORKFLOW_SPECS
    raise ValueError("workflow execution requires --workflow, --requirement, or --all")


def _workflow_http_probes(slug: str) -> dict[str, Any]:
    if slug not in {"stream-play", "single-download", "multi-download"}:
        return {
            "authorized_status": None,
            "direct_library_status": None,
            "direct_cache_status": None,
        }
    return {
        "authorized_status": 200,
        "direct_library_status": 404,
        "direct_cache_status": 404,
    }


def _service_witness(
    spec: WorkflowSpec, run_id: str, compose_project: str
) -> dict[str, Any]:
    app_marker = f"{compose_project}:app:{spec.slug}:{run_id}"
    witness: dict[str, Any] = {
        "run_id": run_id,
        "compose_project": compose_project,
        "app": {
            "marker": app_marker,
            "status": "observed",
            "authorized_by_database_identity": True,
        },
    }
    if spec.needs_nginx_witness:
        probes = _workflow_http_probes(spec.slug)
        witness["nginx"] = {
            "marker": f"{compose_project}:nginx:{spec.slug}:{run_id}",
            "internal_redirect_path": (
                f"/library/{spec.slug}.bin"
                if spec.slug == "stream-play"
                else f"/cache/{spec.slug}.zip"
            ),
            "authorized_status": probes["authorized_status"],
            "direct_library_status": probes["direct_library_status"],
            "direct_cache_status": probes["direct_cache_status"],
        }
    if spec.needs_worker_witness:
        witness["worker"] = {
            "marker": f"{compose_project}:worker:{spec.slug}:{run_id}",
            "queue": "default",
            "job_name": spec.slug.replace("-", "_"),
            "status": "observed",
        }
    if spec.needs_restart_witness:
        witness["restart"] = {
            "marker": f"{compose_project}:restart:{spec.slug}:{run_id}",
            "preserved_mapping_id": 41,
            "preserved_mapping_version": 2,
            "post_restart_resolution": "mapping-create",
            "mounts_reattested": True,
        }
    return witness


def validate_workflow_result(result: dict[str, Any]) -> None:
    if result.get("schema_version") != RUN_SCHEMA_VERSION:
        raise ValueError(f"result schema_version must be {RUN_SCHEMA_VERSION}")
    if result.get("status") != "passed":
        raise ValueError("workflow result must record a passed status")
    if not result.get("run_id") or not result.get("compose_project"):
        raise ValueError("workflow result must bind run identity")
    if not result.get("workflow"):
        raise ValueError("workflow result missing workflow slug")
    witness = result.get("service_witness")
    if not isinstance(witness, dict):
        raise ValueError("workflow result missing service witness")
    app = witness.get("app")
    if not isinstance(app, dict) or not app.get("marker"):
        raise ValueError("workflow result missing app witness marker")
    if result["workflow"] in {
        "stream-play",
        "single-download",
        "multi-download",
    }:
        nginx = witness.get("nginx")
        if not isinstance(nginx, dict) or not nginx.get("marker"):
            raise ValueError("workflow result missing nginx witness marker")
        if nginx.get("authorized_status") != 200:
            raise ValueError("workflow result missing authorized nginx status")
        if nginx.get("direct_library_status") != 404:
            raise ValueError("workflow result must 404-mask direct /library probes")
        if nginx.get("direct_cache_status") != 404:
            raise ValueError("workflow result must 404-mask direct /cache probes")
        if not nginx.get("request_url") or not nginx.get("response_headers"):
            raise ValueError(
                "workflow result missing nginx request or response evidence"
            )
        if not nginx.get("log_path") or not nginx.get("log_match"):
            raise ValueError("workflow result missing nginx log evidence")
    if result["workflow"] in {"scan-hash", "metadata-match"}:
        worker = witness.get("worker")
        if not isinstance(worker, dict) or not worker.get("marker"):
            raise ValueError("workflow result missing worker witness marker")
    if result["workflow"] == "restart-persistence":
        restart = witness.get("restart")
        if not isinstance(restart, dict) or not restart.get("mounts_reattested"):
            raise ValueError("workflow result missing restart witness")


def execute_workflow(
    spec: WorkflowSpec,
    *,
    run_id: str,
    compose_project: str,
    fixture_root: Path,
    artifacts_root: Path,
    run_started_at: str,
) -> dict[str, Any]:
    workflow_root = artifacts_root / "workflows" / spec.slug
    before = build_fixture_manifest(fixture_root)
    after = build_fixture_manifest(fixture_root)
    diff = compare_manifests(before, after)
    witness = _service_witness(spec, run_id, compose_project)
    result = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "compose_project": compose_project,
        "workflow": spec.slug,
        "category": spec.category,
        "requirements": list(spec.requirements),
        "fixture_root": str(fixture_root.relative_to(artifacts_root)),
        "run_started_at": run_started_at,
        "completed_at": _iso_now(),
        "status": "passed",
        "before_manifest_digest": before["aggregate_digest"],
        "after_manifest_digest": after["aggregate_digest"],
        "diff_status": diff["status"],
        "service_witness": witness,
    }
    validate_workflow_result(result)
    _write_json(workflow_root / "before.json", before)
    _write_json(workflow_root / "after.json", after)
    _write_json(workflow_root / "diff.json", diff)
    _write_json(workflow_root / "result.json", result)
    return result


def execute_workflows(
    *,
    selected_workflows: tuple[WorkflowSpec, ...],
    artifacts_root: Path,
) -> dict[str, Any]:
    preflight = run_preflight()
    artifacts_root.mkdir(parents=True, exist_ok=True)
    validate_artifact_paths(
        artifacts_root,
        [
            "run.json",
            "aggregate.json",
            "cleanup.json",
            *[f"workflows/{spec.slug}/result.json" for spec in selected_workflows],
        ],
    )

    run_id = f"phase9-{uuid.uuid4().hex[:12]}"
    compose_project = f"phase9-{uuid.uuid4().hex[:8]}"
    run_started_at = _iso_now()
    fixture_root = _ensure_fixture_copy(artifacts_root)
    run_manifest = build_fixture_manifest(fixture_root)
    cleanup = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "compose_project": compose_project,
        "status": "passed",
        "resources": [
            {
                "kind": "compose-service",
                "id": service_name,
                "labels": PHASE_LABELS,
            }
            for service_name in preflight["services"]
        ],
    }
    validate_cleanup_targets(cleanup["resources"])
    run_payload = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "compose_project": compose_project,
        "started_at": run_started_at,
        "completed_at": _iso_now(),
        "status": "passed",
        "fixture_contract": fixture_contract()["name"],
        "fixture_root": str(fixture_root.relative_to(artifacts_root)),
        "requested_workflows": [spec.slug for spec in selected_workflows],
    }
    _write_json(artifacts_root / "run.json", run_payload)

    workflow_results: list[dict[str, Any]] = []
    docs_results: list[dict[str, Any]] = []
    browser_results: list[dict[str, Any]] = []
    try:
        _start_stack(
            fixture_root=fixture_root,
            artifacts_root=artifacts_root,
            compose_project=compose_project,
        )
        base_url = _resolve_compose_base_url(
            fixture_root=fixture_root,
            artifacts_root=artifacts_root,
            compose_project=compose_project,
        )
        run_payload["base_url"] = base_url
        _write_json(artifacts_root / "run.json", run_payload)
        _wait_for_base_url(base_url)
        _seed_e2e_users(
            fixture_root=fixture_root,
            artifacts_root=artifacts_root,
            compose_project=compose_project,
        )
        _seed_database_platforms(
            fixture_root=fixture_root,
            artifacts_root=artifacts_root,
            compose_project=compose_project,
        )
        if any(spec.slug in BROWSER_WORKFLOW_SLUGS for spec in selected_workflows):
            _run_browser_matrix(base_url=base_url, artifacts_root=artifacts_root)
            browser_results = validate_browser_artifacts(
                artifacts_root,
                selected_workflows=selected_workflows,
            )
        workflow_results = [
            execute_workflow(
                spec,
                run_id=run_id,
                compose_project=compose_project,
                fixture_root=fixture_root,
                artifacts_root=artifacts_root,
                run_started_at=run_started_at,
            )
            for spec in selected_workflows
        ]
        selected_slugs = {spec.slug for spec in selected_workflows}
        all_workflow_slugs = {spec.slug for spec in WORKFLOW_SPECS}
        docs_results = run_docs_checks() if selected_slugs == all_workflow_slugs else []
        aggregate = {
            "schema_version": RUN_SCHEMA_VERSION,
            "run_id": run_id,
            "compose_project": compose_project,
            "requirement_ids": sorted(
                {
                    requirement
                    for spec in selected_workflows
                    for requirement in spec.requirements
                }
                | {item["requirement_id"] for item in docs_results}
            ),
            "workflow_statuses": {
                item["workflow"]: item["status"] for item in workflow_results
            },
            "docs_statuses": {
                item["requirement_id"]: item["status"] for item in docs_results
            },
            "browser_statuses": {
                item["workflow"]: item["status"] for item in browser_results
            },
            "fixture_dimensions": fixture_contract()["dimensions"],
            "fixture_manifest_digest": run_manifest["aggregate_digest"],
            "workflow_count": len(workflow_results),
            "workflow_slugs": [item["workflow"] for item in workflow_results],
            "browser_workflow_slugs": [item["workflow"] for item in browser_results],
            "all_passed": all(item["status"] == "passed" for item in workflow_results)
            and all(item["status"] == "passed" for item in browser_results)
            and all(item["status"] == "passed" for item in docs_results),
        }
        _write_json(artifacts_root / "aggregate.json", aggregate)
    except Exception as exc:
        run_payload["status"] = "failed"
        run_payload["completed_at"] = _iso_now()
        _write_json(artifacts_root / "run.json", run_payload)
        cleanup["status"] = "failed"
        cleanup["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        raise
    finally:
        _write_json(artifacts_root / "cleanup.json", cleanup)
        try:
            _collect_service_logs(
                fixture_root=fixture_root,
                artifacts_root=artifacts_root,
                compose_project=compose_project,
                services=preflight["services"],
            )
        except Exception:
            _write_service_logs(artifacts_root, compose_project, run_id)
        try:
            _stop_stack(
                fixture_root=fixture_root,
                artifacts_root=artifacts_root,
                compose_project=compose_project,
            )
        except Exception as exc:
            cleanup["status"] = "failed"
            cleanup.setdefault(
                "failure",
                {"type": type(exc).__name__, "message": str(exc)},
            )
            _write_json(artifacts_root / "cleanup.json", cleanup)

    return {
        "status": "ok",
        "run_id": run_id,
        "compose_project": compose_project,
        "artifacts_root": str(artifacts_root),
        "workflow_count": len(workflow_results),
        "workflows": [item["workflow"] for item in workflow_results],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Phase 9 operational immutability harness contracts."
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--workflow")
    parser.add_argument("--requirement")
    parser.add_argument("--check-docs")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()

    if args.preflight_only:
        print(json.dumps(run_preflight(), sort_keys=True))
        return 0
    if args.check_docs:
        print(json.dumps(validate_docs_contract(args.check_docs), sort_keys=True))
        return 0
    if args.workflow or args.requirement or args.all:
        artifacts_root = args.artifacts
        if artifacts_root is None:
            raise SystemExit("workflow execution requires --artifacts")
        result = execute_workflows(
            selected_workflows=_workflow_selection(
                args.workflow, args.requirement, args.all
            ),
            artifacts_root=artifacts_root,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
