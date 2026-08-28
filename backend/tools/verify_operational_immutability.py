#!/usr/bin/env python3
"""Phase 9 operational immutability harness foundation."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = REPO_ROOT / ".planning" / "phases" / "09-operational-immutability-proof"
COMPOSE_FILE = REPO_ROOT / "backend" / "docker-compose.immutability-test.yml"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "operational-immutability"
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


def _encode_path(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


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
        "schema_version": "phase9.manifest.v1",
        "root": {
            "id": "fixture-root",
            "relative_path": ".",
            "encoded_path": _encode_path("."),
            "entry_type": "directory",
            "mode": root.lstat().st_mode,
            "size": root.lstat().st_size,
            "mtime_ns": root.lstat().st_mtime_ns,
            "ctime_ns": root.lstat().st_ctime_ns,
            "birthtime_ns": getattr(root.lstat(), "st_birthtime_ns", None),
            "atime_ns": root.lstat().st_atime_ns,
        },
        "entries": entries,
        "counts": counts,
        "aggregate_digest": aggregate_digest,
    }
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != "phase9.manifest.v1":
        raise ValueError("manifest schema_version must be phase9.manifest.v1")
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


def _volume_source(volume: dict[str, Any]) -> str | None:
    return volume.get("source") if isinstance(volume, dict) else None


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
                if target.startswith(
                    f"{existing_target}/"
                ) or existing_target.startswith(f"{target}/"):
                    raise ValueError(
                        f"mount overlap detected between {target} and {existing_target}"
                    )
            service_targets.append(target)
            if target == SOURCE_TARGET:
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
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Phase 9 operational immutability harness contracts."
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--workflow")
    parser.add_argument("--requirement")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()

    if args.preflight_only:
        print(json.dumps(run_preflight(), sort_keys=True))
        return 0
    if args.workflow or args.requirement or args.all:
        raise SystemExit(
            "Phase 9 foundation complete. Workflow execution lands in Plans 09-02 to 09-04."
        )
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
