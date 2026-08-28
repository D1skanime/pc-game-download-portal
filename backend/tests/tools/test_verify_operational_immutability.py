from __future__ import annotations

import copy
import importlib.util
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
        "counts": {"directories": 2, "files": 1, "symlinks": 1, "total_entries": 4},
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
