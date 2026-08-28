from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "backend" / "tools" / "verify_operational_immutability.py"


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """This integration slice verifies the harness without a live database."""


@pytest.fixture(autouse=True)
def clear_database() -> None:
    """Override shared cleanup hooks for this db-free suite."""


def _run_harness(tmp_path: Path, *args: str) -> Path:
    artifacts = tmp_path / "artifacts"
    subprocess.run(
        ["python3", str(SCRIPT), *args, "--artifacts", str(artifacts)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return artifacts


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_operational_immutability", SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_restart_persistence_writes_run_level_and_workflow_artifacts(tmp_path: Path):
    artifacts = _run_harness(tmp_path, "--workflow", "restart-persistence")

    assert (artifacts / "run.json").is_file()
    assert (artifacts / "aggregate.json").is_file()
    assert (artifacts / "cleanup.json").is_file()

    workflow_root = artifacts / "workflows" / "restart-persistence"
    for name in ("before.json", "after.json", "diff.json", "result.json"):
        assert (workflow_root / name).is_file()

    result = _read_json(workflow_root / "result.json")
    assert result["status"] == "passed"
    assert result["service_witness"]["restart"]["mounts_reattested"] is True
    assert (
        result["service_witness"]["restart"]["post_restart_resolution"]
        == "mapping-create"
    )


def test_requirement_run_keeps_separate_workflow_evidence_and_delivery_witnesses(
    tmp_path: Path,
):
    artifacts = _run_harness(tmp_path, "--requirement", "TEST-06")

    workflow_names = {
        path.name for path in (artifacts / "workflows").iterdir() if path.is_dir()
    }
    assert {
        "scan-hash",
        "metadata-match",
        "stream-play",
        "single-download",
        "multi-download",
    } <= workflow_names

    stream_result = _read_json(artifacts / "workflows" / "stream-play" / "result.json")
    assert stream_result["service_witness"]["nginx"]["authorized_status"] == 200
    assert stream_result["service_witness"]["nginx"]["direct_library_status"] == 404
    assert stream_result["service_witness"]["nginx"]["direct_cache_status"] == 404

    scan_result = _read_json(artifacts / "workflows" / "scan-hash" / "result.json")
    assert scan_result["service_witness"]["worker"]["status"] == "observed"


def test_result_validation_fails_closed_when_required_witness_is_missing():
    module = _load_module()
    result = {
        "schema_version": "phase9.run.v1",
        "status": "passed",
        "run_id": "r1",
        "compose_project": "p1",
        "workflow": "single-download",
        "service_witness": {"app": {"marker": "ok"}},
    }

    try:
        module.validate_workflow_result(result)
    except ValueError as exc:
        assert str(exc) == "workflow result missing nginx witness marker"
    else:
        raise AssertionError("validate_workflow_result should fail closed")
