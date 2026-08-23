from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
HARNESS_PATH = BACKEND_ROOT / "tools" / "verify_phase6_acceptance.py"

EXPECTED_PRIOR_MODULES = (
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

EXPECTED_PHASE6_MODULES = (
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


def load_verifier() -> ModuleType:
    assert HARNESS_PATH.exists(), "acceptance harness is not implemented"
    spec = importlib.util.spec_from_file_location(
        "verify_phase6_acceptance", HARNESS_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_record(verifier: ModuleType) -> dict[str, object]:
    prior = [
        {"module": module, "passed": 33, "failed": 0, "errors": 0, "exit_code": 0}
        for module in verifier.PRIOR_PHASE_MODULES
    ]
    prior[0]["passed"] = 939 - 33 * (len(prior) - 1)
    phase6 = [
        {"module": module, "passed": 1, "failed": 0, "errors": 0, "exit_code": 0}
        for module in verifier.deduplicated_phase6_modules()
    ]
    record: dict[str, object] = {
        "schema_version": 1,
        "run_id": "a" * 32,
        "command_identity": verifier.CANONICAL_COMMAND_IDENTITY,
        "checkout": {
            "root": "/home/d1sk/romm",
            "branch": "codex/pc-module-analysis",
            "origin": "https://github.com/rommapp/romm.git",
            "project": "RomM PC Library",
        },
        "stages": {
            "db_continuity": {"before": 1, "after": 1, "exit_code": 0},
            "prior_backend": {"modules": prior, "outcomes": 939, "exit_code": 0},
            "phase6_backend": {"modules": phase6, "exit_code": 0},
            "dialects": {
                name: {"exit_code": 0, "authority": "complete"}
                for name in ("mariadb", "mysql", "postgresql")
            },
            "contracts": {
                "exit_code": 0,
                "generated_before": "b" * 64,
                "generated_after": "b" * 64,
            },
            "frontend": {
                name: {"exit_code": 0}
                for name in (
                    "focused",
                    "full",
                    "typecheck",
                    "build",
                    "locales",
                    "static",
                )
            },
            "manifests": {"before": "c" * 64, "after": "c" * 64, "equal": True},
            "cleanup": {
                "containers": 0,
                "databases": 0,
                "principals": 0,
                "basetemps": 0,
                "volumes": 0,
                "exit_code": 0,
            },
            "baseline": {
                "untracked_count": 28,
                "untracked_sha256": verifier.BASELINE_UNTRACKED_SHA256,
            },
            "git": {"diff_check": 0},
            "manual_ui": {
                "status": "previously_validated_no_drift",
                "evidence": "06-45-SUMMARY.md",
            },
        },
    }
    record["run_digest"] = verifier.canonical_run_digest(record)
    return record


def source_audit_text(verifier: ModuleType) -> str:
    rows = [
        "| Source | ID | Required item | Coverage | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    rows.extend(
        f"| CURRENT | {source_id} | Current contract | 47 | COVERED |"
        for source_id in sorted(verifier.REQUIRED_SOURCE_IDS)
    )
    return "\n".join(rows)


def validation_text(record: dict[str, object]) -> str:
    return (
        "# Phase 6 Validation\n\n"
        f"Run ID: `{record['run_id']}`\n\n"
        f"Run Digest: `{record['run_digest']}`\n\n"
        "Prior modules: 29\n\nPrior outcomes: 939\n"
    )


def test_harness_pins_29_prior_modules_and_isolates_each() -> None:
    verifier = load_verifier()
    assert verifier.PRIOR_PHASE_MODULES == EXPECTED_PRIOR_MODULES
    assert len(verifier.PRIOR_PHASE_MODULES) == 29
    assert len(set(verifier.PRIOR_PHASE_MODULES)) == 29
    assert all((BACKEND_ROOT / path).is_file() for path in verifier.PRIOR_PHASE_MODULES)
    assert verifier.PRIOR_OUTCOMES_MIN == 939

    identities = [
        verifier.ResourceIdentity.create(index)
        for index in range(len(EXPECTED_PRIOR_MODULES))
    ]
    assert len({identity.database for identity in identities}) == 29
    assert len({identity.principal for identity in identities}) == 29
    assert len({identity.basetemp for identity in identities}) == 29
    assert len({identity.container for identity in identities}) == 29
    for module, identity in zip(EXPECTED_PRIOR_MODULES, identities, strict=True):
        command = verifier.backend_module_command(
            Path("/home/d1sk/romm"),
            module,
            identity,
            "romm-romm-dev",
            "romm_default",
        )
        rendered = " ".join(command)
        assert identity.database in rendered
        assert identity.principal in rendered
        assert identity.basetemp in rendered
        assert identity.container in rendered
        assert "ROMM_BASE_PATH=romm_test" in command
        assert "-p no:env" in rendered
        assert "-p no:cacheprovider" in rendered
        assert "--network none" not in rendered
        assert "--network romm_default" in rendered
        assert "--entrypoint /bin/sh" in rendered
        assert "--publish" not in command


def test_phase6_inventory_is_exact_deduplicated_and_unfiltered() -> None:
    verifier = load_verifier()
    assert verifier.PHASE6_MODULES == EXPECTED_PHASE6_MODULES
    expected = tuple(
        path for path in EXPECTED_PHASE6_MODULES if path not in EXPECTED_PRIOR_MODULES
    )
    assert verifier.deduplicated_phase6_modules() == expected
    assert all((BACKEND_ROOT / path).is_file() for path in EXPECTED_PHASE6_MODULES)
    for index, module in enumerate(expected):
        command = verifier.backend_module_command(
            Path("/home/d1sk/romm"),
            module,
            verifier.ResourceIdentity.create(index),
            "romm-romm-dev",
            "romm_default",
        )
        assert "-k" not in command


def test_module_lifecycle_cleans_exact_resources_after_failure() -> None:
    verifier = load_verifier()
    calls: list[tuple[str, str]] = []
    identity = verifier.ResourceIdentity.create(3)

    def create(resource: object) -> None:
        calls.append(("create", resource.database))

    def execute(_command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(("execute", identity.container))
        return subprocess.CompletedProcess([], 7, "1 failed", "")

    def cleanup(resource: object) -> None:
        calls.append(("cleanup", resource.database))

    with pytest.raises(verifier.StageFailure, match="backend module"):
        verifier.execute_backend_module(
            "tests/example.py",
            identity,
            ["pytest", "tests/example.py"],
            create_resources=create,
            execute_command=execute,
            cleanup_resources=cleanup,
        )
    assert calls == [
        ("create", identity.database),
        ("execute", identity.container),
        ("cleanup", identity.database),
    ]


def test_command_graph_contains_every_required_gate_and_forbids_service_mutation() -> (
    None
):
    verifier = load_verifier()
    graph = verifier.acceptance_command_graph(
        Path("/home/d1sk/romm"),
        source_container="romm-dev",
        db_container="romm-db-dev",
        image="romm-romm-dev",
        network="romm_default",
        node_image="node:24-bookworm",
        contract_port=39006,
    )
    rendered = "\n".join(" ".join(command) for command in graph)
    for filename in (
        "rom.test.ts",
        "upload.test.ts",
        "screenshot.test.ts",
        "ManualViewerControls.test.ts",
        "ManualSubtab.test.ts",
        "sourceMutationInventory.test.ts",
        "sourceMutationControls.test.ts",
    ):
        assert filename in rendered
    for required in (
        "verify_storage_migrations.py",
        "mariadb mysql postgresql",
        "verify_phase6_contracts.py",
        "node:24-bookworm",
        "npm run test",
        "npm run typecheck",
        "npm run build",
        "check_i18n_locales.py",
        "check_i18n_sorted.py",
        "git diff --check",
    ):
        assert required in rendered
    for forbidden in (
        "docker compose up",
        "docker restart",
        "--network host",
        "--publish",
        " 3000",
    ):
        assert forbidden not in rendered


def test_source_manifest_schema_and_comparison_are_complete(tmp_path: Path) -> None:
    verifier = load_verifier()
    root = tmp_path / "source"
    root.mkdir()
    (root / "game.bin").write_bytes(b"game")
    (root / "folder").mkdir()
    (root / "link").symlink_to("game.bin")

    before = verifier.source_manifest(root)
    assert {entry["kind"] for entry in before["entries"]} == {
        "directory",
        "file",
        "symlink",
    }
    for entry in before["entries"]:
        assert set(entry) == {
            "path",
            "kind",
            "mode",
            "size",
            "sha256",
            "symlink_target",
        }
    assert verifier.compare_source_manifests(before, verifier.source_manifest(root))
    (root / "game.bin").write_bytes(b"changed")
    assert not verifier.compare_source_manifests(before, verifier.source_manifest(root))


def test_source_audit_parser_requires_exact_unique_covered_current_set() -> None:
    verifier = load_verifier()
    valid = source_audit_text(verifier)
    assert verifier.parse_source_audit(valid) == verifier.REQUIRED_SOURCE_IDS
    first_id = sorted(verifier.REQUIRED_SOURCE_IDS)[0]
    cases = (
        valid.replace(f"| CURRENT | {first_id} |", "", 1),
        valid + f"\n| CURRENT | {first_id} | Duplicate | 47 | COVERED |",
        valid + "\n| CURRENT | UNKNOWN-99 | Unknown | 47 | COVERED |",
        valid.replace("| COVERED |", "| DEFERRED |", 1),
        valid.replace("| COVERED |", "| PARTIAL |", 1),
    )
    for invalid in cases:
        with pytest.raises(verifier.EvidenceError):
            verifier.parse_source_audit(invalid)


def test_validation_binding_rejects_stale_or_digest_mismatched_run() -> None:
    verifier = load_verifier()
    record = valid_record(verifier)
    source_audit = source_audit_text(verifier)
    validation = validation_text(record)
    verifier.verify_evidence_record(record, validation, source_audit)

    tampered = json.loads(json.dumps(record))
    tampered["stages"]["prior_backend"]["outcomes"] = 938
    with pytest.raises(verifier.EvidenceError, match="digest"):
        verifier.verify_evidence_record(tampered, validation, source_audit)

    stale = validation.replace(str(record["run_id"]), "d" * 32)
    with pytest.raises(verifier.EvidenceError, match="run_id"):
        verifier.verify_evidence_record(record, stale, source_audit)

    stale_counts = validation.replace("Prior outcomes: 939", "Prior outcomes: 940")
    with pytest.raises(verifier.EvidenceError, match="structured stage"):
        verifier.verify_evidence_record(record, stale_counts, source_audit)


def test_acceptance_record_rejects_missing_or_failed_structured_stages() -> None:
    verifier = load_verifier()
    record = valid_record(verifier)
    verifier.validate_acceptance_record(record)

    missing = json.loads(json.dumps(record))
    del missing["stages"]["cleanup"]
    missing["run_digest"] = verifier.canonical_run_digest(missing)
    with pytest.raises(verifier.EvidenceError, match="cleanup"):
        verifier.validate_acceptance_record(missing)

    failed = json.loads(json.dumps(record))
    failed["stages"]["frontend"]["build"]["exit_code"] = 1
    failed["run_digest"] = verifier.canonical_run_digest(failed)
    with pytest.raises(verifier.EvidenceError, match="build"):
        verifier.validate_acceptance_record(failed)


def test_redaction_is_bounded_and_removes_sensitive_values() -> None:
    verifier = load_verifier()
    secret = "private-password-value"
    output = verifier.redact_output(
        f"prefix {secret} /home/d1sk/romm/source/private.iso " + "x" * 10000,
        secrets=(secret,),
    )
    assert secret not in output
    assert "private.iso" not in output
    assert len(output) <= verifier.MAX_STAGE_OUTPUT


def test_parser_exposes_locked_modes() -> None:
    verifier = load_verifier()
    parser = verifier.build_parser()
    assert parser.parse_args(["--self-test"]).self_test
    assert parser.parse_args(["--audit-only"]).audit_only
    assert parser.parse_args(
        [
            "--verify-evidence",
            "--evidence-json",
            "record.json",
            "--validation",
            "validation.md",
            "--source-audit",
            "audit.md",
        ]
    ).verify_evidence
