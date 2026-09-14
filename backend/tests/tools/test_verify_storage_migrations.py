import subprocess
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


def test_0117_downgrade_drops_fk_backed_index_with_the_table():
    migration = Path(
        "alembic/versions/0117_component_owned_media_and_notes.py"
    ).read_text()
    downgrade = migration.split("def downgrade() -> None:", 1)[1]
    assert 'op.drop_table("rom_component_owned_media")' in downgrade
    assert "idx_rom_component_owned_media_component" not in downgrade


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
        command = args[0]
        calls.append(command)
        if command[:2] in (["docker", "create"], ["docker", "inspect"]):
            return "owned-container-id"
        if command[:3] in (
            ["docker", "volume", "create"],
            ["docker", "volume", "inspect"],
        ):
            return command[-1]
        return ""

    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(verifier, "_run", record_run)
    monkeypatch.setattr(verifier, "_wait_until_ready", lambda *args: None)
    monkeypatch.setattr(verifier, "_runner_gateway", lambda runner: "172.17.0.1")
    monkeypatch.setattr(verifier, "_mapped_port", lambda *args: "33060")
    monkeypatch.setattr(verifier, "_bootstrap_mysql_0107", lambda name: None)
    monkeypatch.setattr(verifier, "_remove_owned_container", lambda name: None)
    monkeypatch.setattr(verifier, "_remove_owned_volume", lambda name: None)
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
        "_verify_0113_upgrade_state",
        "_seed_0113_state",
        "_verify_0113_downgrade_rejected",
        "_verify_0114_round_trip",
        "_clear_0114_state",
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
        command = args[0]
        events.append(command)
        if command[:2] in (["docker", "create"], ["docker", "inspect"]):
            return "owned-container-id"
        if command[:3] in (
            ["docker", "volume", "create"],
            ["docker", "volume", "inspect"],
        ):
            return command[-1]
        return ""

    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(verifier, "_run", record_run)
    monkeypatch.setattr(verifier, "_wait_until_ready", lambda *args: None)
    monkeypatch.setattr(verifier, "_runner_gateway", lambda runner: "172.17.0.1")
    monkeypatch.setattr(verifier, "_mapped_port", lambda *args: "33060")
    monkeypatch.setattr(verifier, "_bootstrap_mysql_0107", lambda *args: None)
    monkeypatch.setattr(verifier, "_remove_owned_container", lambda name: None)
    monkeypatch.setattr(verifier, "_remove_owned_volume", lambda name: None)
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
    monkeypatch.setattr(
        verifier,
        "_verify_0113_upgrade_state",
        lambda *args: events.append(("verify-0113", *args)),
    )
    monkeypatch.setattr(
        verifier,
        "_seed_0113_state",
        lambda *args: events.append(("seed-0113", *args)),
    )
    monkeypatch.setattr(
        verifier,
        "_verify_0113_downgrade_rejected",
        lambda *args: events.append(("guard-0113", *args)),
    )
    monkeypatch.setattr(
        verifier,
        "_verify_0114_round_trip",
        lambda *args: events.append(("round-trip-0114", *args)),
    )
    monkeypatch.setattr(
        verifier,
        "_clear_0114_state",
        lambda *args: events.append(("clear-0114", *args)),
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
    assert any(
        event[0] == "verify-0113" for event in events if isinstance(event, tuple)
    )
    assert any(event[0] == "seed-0113" for event in events if isinstance(event, tuple))
    assert any(event[0] == "guard-0113" for event in events if isinstance(event, tuple))
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


def test_0113_migration_orders_backfill_indexes_constraints_and_guarded_downgrade():
    migration = Path("alembic/versions/0113_legacy_change_lineage.py").read_text()
    upgrade = migration.split("def upgrade() -> None:", 1)[1].split(
        "def downgrade() -> None:", 1
    )[0]
    downgrade = migration.split("def downgrade() -> None:", 1)[1]

    assert 'revision = "0113_legacy_change_lineage"' in migration
    assert 'down_revision = "0112_phase6_gap_closure"' in migration
    assert "secrets.token_hex(16)" in migration
    assert upgrade.index("_backfill_incarnation_tokens") < upgrade.index(
        "uq_roms_incarnation_token"
    )
    assert upgrade.index("uq_rom_files_incarnation_token") < upgrade.index(
        "nullable=False"
    )
    assert "ck_lmcc_lineage_shape" in migration
    assert downgrade.index("_ensure_lineage_downgrade_safe") < downgrade.index(
        "op.drop_index"
    )
    assert downgrade.index("ck_lmcc_lineage_shape") < downgrade.index(
        'drop_column("entity_incarnation_token")'
    )
    assert downgrade.index("uq_roms_incarnation_token") < downgrade.index(
        'drop_column("incarnation_token")'
    )


def test_three_dialect_verifier_proves_0113_lineage_lifecycle():
    verifier_source = Path("tools/verify_storage_migrations.py").read_text()

    for marker in (
        "0113_legacy_change_lineage",
        "seeded 0112 lineage was not invalidated",
        "incarnation token backfill is invalid",
        "timestamp-colliding replacement did not reject rollback",
        "lineage rollback state did not survive restart",
    ):
        assert marker in verifier_source


def test_three_dialect_verifier_wires_orm_guard_around_restart():
    verifier_source = Path("tools/verify_storage_migrations.py").read_text()
    verify_dialect = verifier_source.split("def verify_dialect(", 1)[1]

    pre_restart = verify_dialect.index("_verify_orm_incarnation_guard(")
    restart = verify_dialect.index("_verify_restart_persistence(")
    post_restart = verify_dialect.index("_verify_orm_incarnation_tokens_after_restart(")

    assert pre_restart < restart < post_restart
    assert '"orm incarnation guard passed before restart"' in verifier_source
    assert '"orm incarnation tokens survived restart"' in verifier_source
    assert "bulk_update_mappings" in verifier_source
    assert "bulk_save_objects" in verifier_source
    assert "incarnation_token" in verifier_source


def test_verifier_requires_0114_source_identity_round_trip():
    verifier_source = Path("tools/verify_storage_migrations.py").read_text()

    markers = (
        "0114_legacy_source_identities",
        "0114 pristine schema passed",
        "0114 seeded 0113 invalidation passed",
        "0114 evidence constraints passed",
        "0114 private identities survived restart",
        "0114 exact handler selection passed",
        "0114 downgrade invalidation passed",
        "0114 re-upgrade unselectability passed",
        "0114 privacy checks passed",
        "0114 exact cleanup passed",
    )
    positions = [verifier_source.index(marker) for marker in markers]
    assert positions == sorted(positions)
    assert (
        "test_migration_reconnects_only_source_observed_rom_and_sidecar"
        in verifier_source
    )


@pytest.mark.parametrize("dialect", sorted(verifier.DIALECTS))
def test_0114_round_trip_dispatches_every_private_probe(monkeypatch, dialect):
    events = []

    monkeypatch.setattr(
        verifier,
        "_alembic",
        lambda *args: events.append(("alembic", args[-2], args[-1])),
    )
    probe_names = (
        "_verify_0114_pristine_schema",
        "_seed_selectable_0113_result",
        "_verify_0114_seeded_invalidation",
        "_seed_0114_evidence_state",
        "_verify_0114_evidence_constraints",
        "_verify_0114_private_persistence",
        "_verify_0114_downgrade_invalidation",
        "_verify_0114_reupgrade_unselectability",
        "_verify_0114_privacy",
    )
    for probe_name in probe_names:
        monkeypatch.setattr(
            verifier,
            probe_name,
            lambda *args, _probe_name=probe_name: events.append(_probe_name),
        )

    verifier._verify_0114_round_trip(
        dialect,
        "runner",
        "host",
        "3306",
        "database",
        "database-container",
        ["health"],
    )

    assert events == [
        "_verify_0114_pristine_schema",
        ("alembic", "downgrade", "0113_legacy_change_lineage"),
        "_seed_selectable_0113_result",
        ("alembic", "upgrade", "head"),
        "_verify_0114_seeded_invalidation",
        "_seed_0114_evidence_state",
        "_verify_0114_evidence_constraints",
        "_verify_0114_private_persistence",
        ("alembic", "downgrade", "0113_legacy_change_lineage"),
        "_verify_0114_downgrade_invalidation",
        ("alembic", "upgrade", "head"),
        "_verify_0114_reupgrade_unselectability",
        "_verify_0114_privacy",
    ]


def test_verifier_redacts_failed_command_diagnostics(monkeypatch):
    private_command_value = "private-command-value"
    private_output_value = "private-output-value"

    monkeypatch.setattr(
        verifier.subprocess,
        "run",
        lambda *args, **kwargs: verifier.subprocess.CompletedProcess(
            args[0], 23, private_output_value, private_output_value
        ),
    )

    with pytest.raises(subprocess.CalledProcessError) as failure:
        verifier._run(["command", private_command_value])

    diagnostic = str(failure.value)
    assert "verifier command failed with exit 23" in diagnostic
    assert private_command_value not in diagnostic
    assert private_output_value not in diagnostic


def test_verifier_cleanup_removes_only_exact_owned_container(monkeypatch):
    removals = []

    def record(args, **kwargs):
        removals.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(verifier.subprocess, "run", record)
    verifier._remove_owned_container("romm-storage-migration-mariadb-0123456789")
    verifier._remove_owned_volume("romm-storage-migration-mariadb-0123456789-data")
    assert removals == [
        (
            [
                "docker",
                "rm",
                "--force",
                "--volumes",
                "romm-storage-migration-mariadb-0123456789",
            ],
            {
                "check": False,
                "stdout": verifier.subprocess.DEVNULL,
                "stderr": verifier.subprocess.DEVNULL,
            },
        ),
        (
            [
                "docker",
                "volume",
                "rm",
                "romm-storage-migration-mariadb-0123456789-data",
            ],
            {
                "check": False,
                "stdout": verifier.subprocess.DEVNULL,
                "stderr": verifier.subprocess.DEVNULL,
            },
        ),
    ]
    with pytest.raises(ValueError, match="refusing to remove unowned"):
        verifier._remove_owned_container("romm-db-dev")
    with pytest.raises(ValueError, match="refusing to remove unowned"):
        verifier._remove_owned_volume("unrelated-data")
