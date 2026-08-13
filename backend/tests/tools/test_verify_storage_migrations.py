from pathlib import Path

import pytest
from tools import verify_storage_migrations as verifier


def test_0109_migration_declares_lifecycle_preflight_before_ddl():
    migration = Path(
        "alembic/versions/0109_mapping_administration_contracts.py"
    ).read_text()
    preflight = migration.index("_ensure_pristine_lifecycle_for_downgrade")
    ddl_positions = [
        migration.index(token)
        for token in ("op.drop_table", "op.drop_column", "op.create_unique_constraint")
    ]
    assert preflight < min(ddl_positions)
    assert "storage_mapping_audits" in migration
    assert "version != 1" in migration


def test_0110_downgrade_drops_fk_backed_index_with_the_table():
    migration = Path("alembic/versions/0110_mapping_preview_results.py").read_text()
    downgrade = migration.split("def downgrade() -> None:", 1)[1]
    assert 'op.drop_table("mapping_previews")' in downgrade
    assert "op.drop_index" not in downgrade


def test_handler_test_repetitions_must_be_positive():
    parser = verifier.build_parser()
    assert (
        parser.parse_args(
            ["--dialects", "mariadb", "--handler-tests"]
        ).handler_test_repetitions
        == 1
    )
    assert (
        parser.parse_args(
            [
                "--dialects",
                "postgresql",
                "--handler-tests",
                "--handler-test-repetitions",
                "10",
            ]
        ).handler_test_repetitions
        == 10
    )
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--dialects",
                "mariadb",
                "--handler-tests",
                "--handler-test-repetitions",
                "0",
            ]
        )


def test_verify_dialect_exercises_pristine_and_history_paths(monkeypatch):
    calls = []

    def record_run(*args, **kwargs):
        calls.append(args[0])
        return ""

    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(verifier, "_run", record_run)
    monkeypatch.setattr(verifier, "_wait_until_ready", lambda *args: None)
    monkeypatch.setattr(verifier, "_runner_gateway", lambda runner: "172.17.0.1")
    monkeypatch.setattr(verifier, "_mapped_port", lambda *args: "33060")
    monkeypatch.setattr(verifier, "_bootstrap_mysql_0107", lambda name: None)
    monkeypatch.setattr(verifier, "_alembic", lambda *args: calls.append(args))
    monkeypatch.setattr(
        verifier,
        "_verify_lifecycle_downgrade_rejected",
        lambda *args: calls.append(args),
    )
    for helper_name in (
        "_seed_0110_state",
        "_verify_seeded_0110_state",
        "_verify_restart_persistence",
        "_verify_safe_lifecycle_downgrade_rejected",
        "_clear_0111_state",
        "_seed_selectable_0111_results",
        "_verify_seeded_0111_invalidated",
        "_verify_seeded_0111_restored",
    ):
        monkeypatch.setattr(verifier, helper_name, lambda *args: calls.append(args))
    verifier.verify_dialect("mariadb", "romm-dev")
    assert any(
        isinstance(call, tuple)
        and call[-2:] == ("downgrade", "0108_storage_foundation")
        for call in calls
    )
    assert any(
        isinstance(call, tuple) and call and call[0] == "mariadb" for call in calls
    )


def test_0111_migration_guards_lifecycle_state_before_downgrade_ddl():
    migration = Path(
        "alembic/versions/0111_safe_lifecycle_legacy_migration.py"
    ).read_text()
    preflight = migration.index("_ensure_safe_lifecycle_downgrade")
    ddl_positions = [
        migration.index(token)
        for token in (
            "op.drop_table",
            "batch_op.drop_column",
            "batch_op.alter_column",
        )
    ]
    assert preflight < min(ddl_positions)
    assert "retained_catalog_identities" in migration
    assert "owned_cleanup_intents" in migration
    assert "legacy_detection_results" in migration
    assert "legacy_migrations" in migration


def test_0112_downgrade_removes_selectable_constraint_before_marker_restore():
    migration = Path("alembic/versions/0112_phase6_gap_closure.py").read_text()
    downgrade = migration.split("def downgrade() -> None:", 1)[1]

    selectable_drop = downgrade.index(
        "ck_legacy_detection_results_source_fingerprint_selectable"
    )
    marker_restore = downgrade.index("_restore_fingerprint_refresh_markers()")
    column_drop = downgrade.index('batch_op.drop_column("source_fingerprint")')

    assert selectable_drop < marker_restore < column_drop


def test_verify_dialect_exercises_seeded_0110_and_restart_paths(monkeypatch):
    events = []

    def record_run(*args, **kwargs):
        events.append(args[0])
        return ""

    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(verifier, "_run", record_run)
    monkeypatch.setattr(verifier, "_wait_until_ready", lambda *args: None)
    monkeypatch.setattr(verifier, "_runner_gateway", lambda runner: "172.17.0.1")
    monkeypatch.setattr(verifier, "_mapped_port", lambda *args: "33060")
    monkeypatch.setattr(verifier, "_bootstrap_mysql_0107", lambda *args: None)
    monkeypatch.setattr(
        verifier, "_alembic", lambda *args: events.append(("alembic", *args))
    )
    monkeypatch.setattr(
        verifier, "_verify_lifecycle_downgrade_rejected", lambda *args: None
    )
    monkeypatch.setattr(
        verifier, "_verify_safe_lifecycle_downgrade_rejected", lambda *args: None
    )
    monkeypatch.setattr(
        verifier,
        "_seed_0110_state",
        lambda *args: events.append(("seed-0110", *args)),
    )
    monkeypatch.setattr(
        verifier,
        "_verify_seeded_0110_state",
        lambda *args: events.append(("verify-0110", *args)),
    )
    monkeypatch.setattr(
        verifier,
        "_verify_restart_persistence",
        lambda *args: events.append(("restart", *args)),
    )
    monkeypatch.setattr(
        verifier, "_clear_0111_state", lambda *args: events.append(("clear", *args))
    )
    monkeypatch.setattr(
        verifier,
        "_seed_selectable_0111_results",
        lambda *args: events.append(("seed-0111", *args)),
    )
    monkeypatch.setattr(
        verifier,
        "_verify_seeded_0111_invalidated",
        lambda *args: events.append(("invalidated-0111", *args)),
    )
    monkeypatch.setattr(
        verifier,
        "_verify_seeded_0111_restored",
        lambda *args: events.append(("restored-0111", *args)),
    )

    verifier.verify_dialect("postgresql", "romm-dev")

    assert any(event[0] == "seed-0110" for event in events if isinstance(event, tuple))
    assert any(
        event[0] == "verify-0110" for event in events if isinstance(event, tuple)
    )
    assert any(event[0] == "restart" for event in events if isinstance(event, tuple))
    assert any(
        event[:2] == ("alembic", "romm-dev")
        and event[-2:] == ("downgrade", "0110_mapping_preview_results")
        for event in events
        if isinstance(event, tuple)
    )
    seed_index = next(
        index for index, event in enumerate(events) if event[0] == "seed-0111"
    )
    invalidated_indexes = [
        index for index, event in enumerate(events) if event[0] == "invalidated-0111"
    ]
    restored_index = next(
        index for index, event in enumerate(events) if event[0] == "restored-0111"
    )
    assert seed_index < invalidated_indexes[0] < restored_index < invalidated_indexes[1]
    alembic_events = [
        event
        for event in events
        if isinstance(event, tuple) and event[:2] == ("alembic", "romm-dev")
    ]
    assert (
        sum(
            event[-2:] == ("downgrade", "0111_safe_lifecycle")
            for event in alembic_events
        )
        >= 2
    )


def test_restart_verifier_proves_rollback_state_and_mapping_revision():
    verifier_source = Path("tools/verify_storage_migrations.py").read_text()
    assert "rolled_back_at" in verifier_source
    assert "legacy rollback state did not survive restart" in verifier_source
    assert "mapping rollback revision did not survive restart" in verifier_source


def test_clear_0111_state_restores_seeded_mapping_baseline(monkeypatch):
    statements = []
    monkeypatch.setattr(
        verifier, "_execute_sql", lambda *args: statements.append(args[-1])
    )
    verifier._clear_0111_state("mariadb", "romm-dev", "host", "3306", "db")
    assert statements[0] == (
        "UPDATE platform_storage_mappings "
        "SET active = TRUE, version = 4 WHERE id = 910001"
    )
    assert statements[1] == "DELETE FROM legacy_migrations"


def test_seeded_0111_fixture_is_fingerprintless_and_mixed(monkeypatch):
    statements = []
    monkeypatch.setattr(
        verifier, "_execute_sql", lambda *args: statements.append(args[-1])
    )

    verifier._seed_selectable_0111_results("mariadb", "romm-dev", "host", "3306", "db")

    combined = "\n".join(statements)
    assert "source_fingerprint" not in combined
    assert "'detected'" in combined
    assert "FALSE, TRUE, NULL" in combined
    assert "'manual_mapping_required'" in combined
    assert "'empty'" in combined


def test_seeded_0111_verifiers_require_narrow_marker_and_exact_restore(monkeypatch):
    statements = []

    def query(*args):
        statements.append(args[-1])
        return "3"

    monkeypatch.setattr(verifier, "_query_scalar", query)
    verifier._verify_seeded_0111_invalidated(
        "mariadb", "romm-dev", "host", "3306", "db"
    )
    verifier._verify_seeded_0111_restored("mariadb", "romm-dev", "host", "3306", "db")

    combined = "\n".join(statements)
    assert "fingerprint_refresh_required" in combined
    assert "version = 8" in combined
    assert "version = 7" in combined
    assert "source_fingerprint" in statements[0]


def test_seeded_0111_fixture_satisfies_fingerprint_constraints(monkeypatch):
    statements = []
    monkeypatch.setattr(
        verifier, "_execute_sql", lambda *args: statements.append(args[-1])
    )

    verifier._seed_0111_state("mariadb", "romm-dev", "host", "3306", "db")

    detection = statements[0]
    assert "source_fingerprint" in detection
    assert "0" * 64 in detection


def test_seeded_0111_fixture_records_exact_mixed_catalog_state(monkeypatch):
    statements = []
    monkeypatch.setattr(
        verifier, "_execute_sql", lambda *args: statements.append(args[-1])
    )

    verifier._seed_0111_state("mariadb", "romm-dev", "host", "3306", "db")

    combined = "\n".join(statements)
    assert "legacy_migration_catalog_changes" in combined
    assert "'rom', 920011, TRUE" in combined
    assert "'rom_file', 920021, TRUE" in combined
    assert all(str(entity_id) in combined for entity_id in range(920011, 920015))
    assert all(str(entity_id) in combined for entity_id in range(920021, 920025))
    change_index = next(
        index
        for index, statement in enumerate(statements)
        if "legacy_migration_catalog_changes" in statement
    )
    later_index = next(
        index for index, statement in enumerate(statements) if "920014" in statement
    )
    assert change_index < later_index


def test_restart_verifier_proves_exact_catalog_restoration():
    verifier_source = Path("tools/verify_storage_migrations.py").read_text()
    assert "exact catalog rollback did not restore recorded rows" in verifier_source
    assert "exact catalog rollback changed unrelated rows" in verifier_source
    assert "legacy_migration_catalog_changes" in verifier_source
    assert "920014" in verifier_source
