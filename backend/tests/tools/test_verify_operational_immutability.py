from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "backend" / "tools" / "verify_operational_immutability.py"


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """This focused tool suite is database free."""


@pytest.fixture(autouse=True)
def clear_database() -> None:
    """Override shared database cleanup for this suite."""


def _load_module():
    if not MODULE_PATH.is_file():
        pytest.fail(
            f"Phase 9 RED: missing harness module at {MODULE_PATH.relative_to(REPO_ROOT)}"
        )

    spec = importlib.util.spec_from_file_location(
        "verify_operational_immutability", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sample_manifest() -> dict:
    return {
        "schema_version": "phase9.manifest.v1",
        "root": {
            "id": "fixture-root",
            "relative_path": ".",
            "entry_type": "directory",
            "mode": 16877,
            "size": 0,
            "mtime_ns": 1,
            "ctime_ns": 1,
            "birthtime_ns": None,
            "atime_ns": 1,
            "encoded_path": "Li4=",
        },
        "entries": [
            {
                "relative_path": "Alpha",
                "encoded_path": "QWxwaGE=",
                "entry_type": "directory",
                "mode": 16877,
                "size": 0,
                "mtime_ns": 2,
                "ctime_ns": 2,
                "birthtime_ns": None,
                "atime_ns": 2,
            },
            {
                "relative_path": "Alpha/empty",
                "encoded_path": "QWxwaGEvZW1wdHk=",
                "entry_type": "directory",
                "mode": 16877,
                "size": 0,
                "mtime_ns": 3,
                "ctime_ns": 3,
                "birthtime_ns": None,
                "atime_ns": 3,
            },
            {
                "relative_path": "game.iso",
                "encoded_path": "Z2FtZS5pc28=",
                "entry_type": "file",
                "mode": 33188,
                "size": 15,
                "sha256": "0" * 64,
                "mtime_ns": 4,
                "ctime_ns": 4,
                "birthtime_ns": None,
                "atime_ns": 4,
            },
            {
                "relative_path": "link",
                "encoded_path": "bGluaw==",
                "entry_type": "symlink",
                "mode": 41471,
                "size": 0,
                "symlink_target": "game.iso",
                "mtime_ns": 5,
                "ctime_ns": 5,
                "birthtime_ns": None,
                "atime_ns": 5,
            },
        ],
        "counts": {
            "directories": 2,
            "files": 1,
            "symlinks": 1,
            "total_entries": 4,
            "empty_directories": 1,
        },
        "aggregate_digest": "1" * 64,
    }


def test_validation_rows_reference_exact_plan_tasks():
    validation = (
        REPO_ROOT
        / ".planning"
        / "phases"
        / "09-operational-immutability-proof"
        / "09-VALIDATION.md"
    ).read_text(encoding="utf-8")
    assert "TBD" not in validation
    assert "09-W1-01 | 09-01 Task 1" in validation
    assert "09-W1-02 | 09-01 Task 2" in validation


def test_manifest_validation_requires_root_record():
    module = _load_module()
    manifest = _sample_manifest()
    manifest.pop("root")

    with pytest.raises(ValueError, match="root"):
        module.validate_manifest(manifest)


def test_manifest_validation_rejects_missing_empty_directory():
    module = _load_module()
    manifest = _sample_manifest()
    manifest["entries"] = [
        entry
        for entry in manifest["entries"]
        if entry["relative_path"] != "Alpha/empty"
    ]
    manifest["counts"]["directories"] = 1
    manifest["counts"]["total_entries"] = 3
    manifest["counts"]["empty_directories"] = 0

    with pytest.raises(ValueError, match="empty"):
        module.validate_manifest(manifest)


def test_manifest_validation_rejects_unsorted_or_duplicate_entries():
    module = _load_module()
    manifest = _sample_manifest()
    duplicate = copy.deepcopy(manifest["entries"][1])
    manifest["entries"] = [
        manifest["entries"][2],
        manifest["entries"][0],
        duplicate,
        manifest["entries"][1],
    ]

    with pytest.raises(ValueError, match="sorted|duplicate"):
        module.validate_manifest(manifest)


def test_manifest_validation_rejects_missing_required_fields():
    module = _load_module()
    manifest = _sample_manifest()
    manifest["entries"][2].pop("sha256")

    with pytest.raises(ValueError, match="sha256"):
        module.validate_manifest(manifest)


def test_artifact_paths_reject_absolute_or_repo_escape_targets(tmp_path: Path):
    module = _load_module()
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()

    with pytest.raises(ValueError, match="absolute"):
        module.validate_artifact_paths(
            artifacts_root,
            ["/tmp/escape.json", str(artifacts_root / ".." / "escape.json")],
        )


def test_cleanup_targets_require_owned_phase9_labels():
    module = _load_module()
    resources = [
        {
            "kind": "container",
            "id": "phase9-app",
            "labels": {"com.docker.compose.project": "phase9"},
        }
    ]

    with pytest.raises(ValueError, match="owned|label"):
        module.validate_cleanup_targets(resources)


def test_preflight_rejects_writable_source_mount_and_overlap():
    module = _load_module()
    compose_model = {
        "services": {
            "app": {
                "volumes": [
                    {
                        "type": "bind",
                        "source": "/tmp/source",
                        "target": "/romm/library",
                    },
                    {
                        "type": "bind",
                        "source": "/tmp/owned",
                        "target": "/romm/library/cache",
                    },
                ],
                "labels": {
                    "romm.phase": "09",
                    "romm.phase.slug": "operational-immutability-proof",
                },
            }
        }
    }

    with pytest.raises(ValueError, match="read-only|overlap"):
        module.validate_compose_topology(compose_model)


def test_docs_contract_checks_pass_for_repository_guide():
    module = _load_module()

    result = module.validate_docs_contract("DOC-01")

    assert result["status"] == "passed"
    assert result["requirement_id"] == "DOC-01"


def test_docs_contract_rejects_forbidden_team4s_guidance():
    module = _load_module()
    content = """
# External Read-Only Library Operations
## Read-Only Mount Topology
## Writable Separation
## Register a Root and Browse Mappings
## Scan, Preview, Stream, and Download
## Migration and Catalog-Only Removal
## noatime and NAS-Equivalent Guidance
## Troubleshooting and Defense in Depth
## Maintenance Window Checklist
## Team4s Safeguards
Mount one library root read-only at `/romm/library:ro`.
RomM-owned writes stay on separate writable storage.
Original files and folders stay unchanged.
Access time can still change during ordinary reads unless `noatime` or a NAS-equivalent setting is enabled.
Content and directory structure remain unchanged even when access time changes.
Use only synthetic or repository-controlled fixtures for Phase 9 proof.
Do not edit Team4s source or configuration.
Do not restart or stop Team4s services, the Team4s host, or active encode workloads.
Phase 9 does not authorize a real NAS mount change.
docker restart team4s
"""

    with pytest.raises(ValueError, match="forbidden guidance"):
        module.validate_docs_contract("DOC-03", content)


def test_execute_workflows_records_complete_aggregate(tmp_path: Path):
    module = _load_module()

    result = module.execute_workflows(
        selected_workflows=module._workflow_selection(None, None, True),
        artifacts_root=tmp_path / "artifacts",
    )

    aggregate = copy.deepcopy(
        json.loads((tmp_path / "artifacts" / "aggregate.json").read_text())
    )
    cleanup = json.loads((tmp_path / "artifacts" / "cleanup.json").read_text())
    assert result["status"] == "ok"
    assert aggregate["all_passed"] is True
    assert aggregate["requirement_ids"] == [
        "DOC-01",
        "DOC-02",
        "DOC-03",
        "TEST-04",
        "TEST-05",
        "TEST-06",
    ]
    assert sorted(aggregate["workflow_slugs"]) == sorted(
        spec.slug for spec in module.WORKFLOW_SPECS
    )
    assert cleanup["status"] == "passed"
    for name in ("app.log", "db.log", "nginx.log", "redis.log", "worker.log"):
        assert (tmp_path / "artifacts" / "service-logs" / name).is_file()


def test_execute_workflows_emits_cleanup_on_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    module = _load_module()

    def fail_workflow(*args, **kwargs):
        raise RuntimeError("synthetic workflow failure")

    monkeypatch.setattr(module, "execute_workflow", fail_workflow)

    with pytest.raises(RuntimeError, match="synthetic workflow failure"):
        module.execute_workflows(
            selected_workflows=(module.WORKFLOW_SPECS[0],),
            artifacts_root=tmp_path / "artifacts",
        )

    cleanup = json.loads((tmp_path / "artifacts" / "cleanup.json").read_text())
    run_payload = json.loads((tmp_path / "artifacts" / "run.json").read_text())
    assert cleanup["status"] == "failed"
    assert cleanup["failure"]["type"] == "RuntimeError"
    assert run_payload["status"] == "failed"
