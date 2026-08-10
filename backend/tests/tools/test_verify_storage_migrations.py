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
    monkeypatch.setattr(
        verifier, "_run", lambda *args, **kwargs: calls.append(args[0]) or ""
    )
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
    verifier.verify_dialect("mariadb", "romm-dev")
    assert any(
        isinstance(call, tuple)
        and call[-2:] == ("downgrade", "0108_storage_foundation")
        for call in calls
    )
    assert any(
        isinstance(call, tuple) and call and call[0] == "mariadb" for call in calls
    )
