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


def _fake_workflow_result(module, spec, artifacts_root: Path) -> dict:
    workflow_root = artifacts_root / "workflows" / spec.slug
    payload = {
        "schema_version": module.RUN_SCHEMA_VERSION,
        "run_id": "phase9-run",
        "compose_project": "phase9-project",
        "workflow": spec.slug,
        "category": spec.category,
        "requirements": list(spec.requirements),
        "fixture_root": "source-library",
        "run_started_at": "2026-08-28T15:00:00+00:00",
        "completed_at": "2026-08-28T15:00:01+00:00",
        "status": "passed",
        "before_manifest_digest": "a" * 64,
        "after_manifest_digest": "a" * 64,
        "diff_status": "unchanged",
        "service_witness": {
            "app": {"marker": f"app:{spec.slug}", "status": "observed"},
        },
    }
    if spec.needs_nginx_witness:
        payload["service_witness"]["nginx"] = {
            "marker": f"nginx:{spec.slug}",
            "authorized_status": 200,
            "direct_library_status": 404,
            "direct_cache_status": 404,
            "internal_redirect_path": f"/library/{spec.slug}.bin",
        }
    if spec.needs_worker_witness:
        payload["service_witness"]["worker"] = {
            "marker": f"worker:{spec.slug}",
            "queue": "default",
            "job_name": spec.slug.replace("-", "_"),
            "status": "observed",
        }
    if spec.needs_restart_witness:
        payload["service_witness"]["restart"] = {
            "marker": f"restart:{spec.slug}",
            "preserved_mapping_id": 41,
            "preserved_mapping_version": 2,
            "post_restart_resolution": "mapping-create",
            "mounts_reattested": True,
        }
    workflow_root.mkdir(parents=True, exist_ok=True)
    for name in ("before.json", "after.json", "diff.json", "result.json"):
        (workflow_root / name).write_text("{}\n", encoding="utf-8")
    return payload


def _write_browser_artifacts(module, artifacts_root: Path) -> None:
    for spec in module.WORKFLOW_SPECS:
        workflow_root = artifacts_root / "workflows" / spec.slug
        workflow_root.mkdir(parents=True, exist_ok=True)
        (workflow_root / "browser.json").write_text(
            json.dumps(
                {
                    "schema_version": "phase9.browser.v1",
                    "workflow": spec.slug,
                    "status": "passed",
                    "route_hint": f"/{spec.slug}",
                    "started_at": "2026-08-28T15:00:00+00:00",
                    "completed_at": "2026-08-28T15:00:01+00:00",
                    "final_url": f"http://127.0.0.1:39009/{spec.slug}",
                }
            )
            + "\n",
            encoding="utf-8",
        )


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


def test_wait_for_base_url_checks_the_backend_heartbeat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    requested: list[str] = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    def open_url(url, timeout):
        requested.append(url)
        return Response()

    monkeypatch.setattr(module.urllib_request, "urlopen", open_url)

    module._wait_for_base_url("http://127.0.0.1:39009", timeout_seconds=1)

    assert requested == ["http://127.0.0.1:39009/api/heartbeat"]


def test_wait_for_base_url_retries_after_connection_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    attempts = 0

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    def open_url(url, timeout):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionResetError("connection reset by peer")
        return Response()

    monkeypatch.setattr(module.urllib_request, "urlopen", open_url)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)

    module._wait_for_base_url("http://127.0.0.1:39009", timeout_seconds=1)

    assert attempts == 2


def test_delivery_probe_records_observed_nginx_response_statuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    requested: list[str] = []

    class Response:
        def __init__(self, status: int):
            self.status = status
            self.headers = {"x-phase9": "test"}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    def open_url(url, timeout):
        requested.append(url)
        if url.endswith("/api/heartbeat"):
            return Response(200)
        raise module.urllib_error.HTTPError(url, 404, "missing", {}, None)

    monkeypatch.setattr(module.urllib_request, "urlopen", open_url)

    probes = module._workflow_http_probes(
        "single-download", base_url="http://127.0.0.1:39009"
    )

    assert probes["authorized_status"] == 200
    assert probes["direct_library_status"] == 404
    assert probes["direct_cache_status"] == 404
    assert probes["response_headers"] == {"x-phase9": "test"}
    assert requested == [
        "http://127.0.0.1:39009/api/heartbeat",
        "http://127.0.0.1:39009/library/single-download.bin",
        "http://127.0.0.1:39009/cache/single-download.zip",
    ]


def test_browser_matrix_allows_isolated_stack_startup_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_module()
    commands: list[list[str]] = []

    def run_command(command, **_kwargs):
        commands.append(command)
        return type("Completed", (), {"stdout": ""})()

    monkeypatch.setattr(module, "_run_command", run_command)

    module._run_browser_matrix(
        base_url="http://127.0.0.1:39009", artifacts_root=tmp_path
    )

    assert "--timeout=120000" in commands[0]


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


def test_execute_workflows_records_complete_aggregate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    module = _load_module()
    artifacts_root = tmp_path / "artifacts"

    monkeypatch.setattr(
        module,
        "execute_workflow",
        lambda spec, **kwargs: _fake_workflow_result(module, spec, artifacts_root),
    )
    monkeypatch.setattr(
        module,
        "_resolve_compose_base_url",
        lambda **kwargs: "http://127.0.0.1:39009",
    )
    monkeypatch.setattr(
        module, "_start_stack", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        module, "_wait_for_base_url", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        module, "_seed_database_platforms", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        module, "_seed_e2e_users", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        module,
        "_run_browser_matrix",
        lambda *args, **kwargs: _write_browser_artifacts(module, artifacts_root),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_collect_service_logs",
        lambda *args, **kwargs: module._write_service_logs(
            artifacts_root, "phase9-project", "phase9-run"
        ),
        raising=False,
    )
    monkeypatch.setattr(
        module, "_stop_stack", lambda *args, **kwargs: None, raising=False
    )

    result = module.execute_workflows(
        selected_workflows=module._workflow_selection(None, None, True),
        artifacts_root=artifacts_root,
    )

    aggregate = copy.deepcopy(
        json.loads((artifacts_root / "aggregate.json").read_text())
    )
    cleanup = json.loads((artifacts_root / "cleanup.json").read_text())
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
    artifacts_root = tmp_path / "artifacts"

    def fail_workflow(*args, **kwargs):
        raise RuntimeError("synthetic workflow failure")

    monkeypatch.setattr(module, "execute_workflow", fail_workflow)
    monkeypatch.setattr(
        module,
        "_resolve_compose_base_url",
        lambda **kwargs: "http://127.0.0.1:39009",
    )
    monkeypatch.setattr(
        module, "_start_stack", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        module, "_wait_for_base_url", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        module, "_seed_database_platforms", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        module, "_seed_e2e_users", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        module, "_run_browser_matrix", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        module,
        "validate_browser_artifacts",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        module,
        "_collect_service_logs",
        lambda *args, **kwargs: module._write_service_logs(
            artifacts_root, "phase9-project", "phase9-run"
        ),
        raising=False,
    )
    monkeypatch.setattr(
        module, "_stop_stack", lambda *args, **kwargs: None, raising=False
    )

    with pytest.raises(RuntimeError, match="synthetic workflow failure"):
        module.execute_workflows(
            selected_workflows=(module.WORKFLOW_SPECS[0],),
            artifacts_root=artifacts_root,
        )

    cleanup = json.loads((artifacts_root / "cleanup.json").read_text())
    run_payload = json.loads((artifacts_root / "run.json").read_text())
    assert cleanup["status"] == "failed"
    assert cleanup["failure"]["type"] == "RuntimeError"
    assert run_payload["status"] == "failed"


def test_validate_browser_artifacts_requires_all_workflow_browser_outputs(
    tmp_path: Path,
):
    module = _load_module()
    artifacts_root = tmp_path / "artifacts"
    _write_browser_artifacts(module, artifacts_root)
    (
        artifacts_root / "workflows" / module.WORKFLOW_SPECS[0].slug / "browser.json"
    ).unlink()

    with pytest.raises(ValueError, match="browser artifact"):
        module.validate_browser_artifacts(
            artifacts_root, selected_workflows=module.WORKFLOW_SPECS
        )


def test_browser_artifacts_require_the_live_run_and_nginx_origin(tmp_path: Path):
    module = _load_module()
    artifacts_root = tmp_path / "artifacts"
    _write_browser_artifacts(module, artifacts_root)
    artifact_path = (
        artifacts_root / "workflows" / module.WORKFLOW_SPECS[0].slug / "browser.json"
    )
    artifact = json.loads(artifact_path.read_text())
    artifact["run_id"] = "another-run"
    artifact["final_url"] = "http://unrelated.example.invalid/storage"
    artifact_path.write_text(json.dumps(artifact))

    with pytest.raises(ValueError, match="run|origin"):
        module.validate_browser_artifacts(
            artifacts_root,
            selected_workflows=(module.WORKFLOW_SPECS[0],),
            run_id="phase9-run",
            base_url="http://127.0.0.1:39009",
        )


def test_delivery_result_rejects_static_status_without_live_request_evidence():
    module = _load_module()
    result = _fake_workflow_result(
        module,
        module.WORKFLOW_BY_SLUG["single-download"],
        Path("/tmp/unused"),
    )

    with pytest.raises(ValueError, match="request|response|log"):
        module.validate_workflow_result(result)


def test_seed_database_platforms_executes_app_container_seeder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    module = _load_module()
    commands: list[list[str]] = []

    def fake_run(command, *, cwd=None, env=None):
        commands.append(command)
        return None

    monkeypatch.setattr(module, "_run_command", fake_run)

    module._seed_database_platforms(
        fixture_root=tmp_path / "fixture",
        artifacts_root=tmp_path / "artifacts",
        compose_project="phase9-project",
    )

    assert commands == [
        [
            "docker",
            "compose",
            "-f",
            str(module.COMPOSE_FILE),
            "exec",
            "-T",
            "app",
            "uv",
            "run",
            "python",
            str(module.PHASE9_PLATFORM_SEEDER),
        ]
    ]


def test_seed_e2e_users_executes_isolated_app_container_seeder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    module = _load_module()
    commands: list[list[str]] = []

    def fake_run(command, *, cwd=None, env=None):
        commands.append(command)
        return None

    monkeypatch.setattr(module, "_run_command", fake_run)

    module._seed_e2e_users(
        fixture_root=tmp_path / "fixture",
        artifacts_root=tmp_path / "artifacts",
        compose_project="phase9-project",
    )

    assert commands == [
        [
            "docker",
            "compose",
            "-f",
            str(module.COMPOSE_FILE),
            "exec",
            "-T",
            "app",
            "uv",
            "run",
            "python",
            str(module.PHASE9_E2E_USER_SEEDER),
        ]
    ]


def test_execute_workflows_runs_stack_browser_and_log_collection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    module = _load_module()
    artifacts_root = tmp_path / "artifacts"
    calls: list[str] = []

    monkeypatch.setattr(
        module,
        "execute_workflow",
        lambda spec, **kwargs: _fake_workflow_result(module, spec, artifacts_root),
    )
    monkeypatch.setattr(
        module,
        "_resolve_compose_base_url",
        lambda **kwargs: "http://127.0.0.1:39009",
    )
    monkeypatch.setattr(
        module,
        "_start_stack",
        lambda *args, **kwargs: calls.append("start"),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_wait_for_base_url",
        lambda *args, **kwargs: calls.append("wait"),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_seed_database_platforms",
        lambda *args, **kwargs: calls.append("seed"),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_seed_e2e_users",
        lambda *args, **kwargs: calls.append("users"),
        raising=False,
    )

    def fake_browser(*args, **kwargs):
        calls.append("browser")
        _write_browser_artifacts(module, artifacts_root)

    monkeypatch.setattr(
        module,
        "_run_browser_matrix",
        fake_browser,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_collect_service_logs",
        lambda *args, **kwargs: calls.append("logs"),
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "_stop_stack",
        lambda *args, **kwargs: calls.append("stop"),
        raising=False,
    )

    result = module.execute_workflows(
        selected_workflows=module._workflow_selection(None, None, True),
        artifacts_root=artifacts_root,
    )

    aggregate = json.loads((artifacts_root / "aggregate.json").read_text())
    assert result["status"] == "ok"
    assert calls == ["start", "wait", "users", "seed", "browser", "logs", "stop"]
    assert sorted(aggregate["browser_workflow_slugs"]) == sorted(
        module.BROWSER_WORKFLOW_SLUGS
    )
