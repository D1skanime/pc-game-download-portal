"""Verify storage migrations on isolated supported database containers."""

# trunk-ignore-all(bandit/B404,bandit/B105,bandit/B108,bandit/B603,bandit/B607,bandit/B608)

import argparse
import json
import subprocess
import time
import uuid
from typing import TypedDict


class DialectConfig(TypedDict):
    image: str
    port: str
    env: dict[str, str]
    health: list[str]


DIALECTS: dict[str, DialectConfig] = {
    "mariadb": {
        "image": "mariadb:10.11",
        "port": "3306/tcp",
        "env": {
            "MARIADB_DATABASE": "romm_migration",
            "MARIADB_USER": "romm",
            "MARIADB_PASSWORD": "romm",
            "MARIADB_ROOT_PASSWORD": "root",
        },
        "health": ["mariadb-admin", "ping", "-h", "127.0.0.1", "-uroot", "-proot"],
    },
    "mysql": {
        "image": "mysql:8.4",
        "port": "3306/tcp",
        "env": {
            "MYSQL_DATABASE": "romm_migration",
            "MYSQL_USER": "romm",
            "MYSQL_PASSWORD": "romm",
            "MYSQL_ROOT_PASSWORD": "root",
        },
        "health": ["mysqladmin", "ping", "-h", "127.0.0.1", "-uroot", "-proot"],
    },
    "postgresql": {
        "image": "postgres:15",
        "port": "5432/tcp",
        "env": {
            "POSTGRES_DB": "romm_migration",
            "POSTGRES_USER": "romm",
            "POSTGRES_PASSWORD": "romm",
        },
        "health": ["pg_isready", "-U", "romm", "-d", "romm_migration"],
    },
}


def _run(args: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=capture)
    return result.stdout.strip() if capture else ""


def _wait_until_ready(name: str, command: list[str]) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["docker", "exec", name, *command],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    logs = _run(["docker", "logs", name], capture=True)
    raise RuntimeError(f"Database container {name} did not become ready:\n{logs}")


def _runner_gateway(runner: str) -> str:
    raw = _run(["docker", "inspect", runner], capture=True)
    networks = json.loads(raw)[0]["NetworkSettings"]["Networks"]
    gateways = [
        network["Gateway"] for network in networks.values() if network["Gateway"]
    ]
    if not gateways:
        raise RuntimeError(f"No Docker gateway found for runner container {runner}")
    return gateways[0]


def _mapped_port(name: str, container_port: str) -> str:
    output = _run(["docker", "port", name, container_port], capture=True)
    return output.splitlines()[0].rsplit(":", 1)[1]


def _database_environment(
    dialect: str, host: str, port: str, database: str
) -> dict[str, str]:
    return {
        "ROMM_DB_DRIVER": dialect,
        "DB_HOST": host,
        "DB_PORT": port,
        "DB_USER": "romm",
        "DB_PASSWD": "romm",
        "DB_NAME": database,
        "ROMM_AUTH_SECRET_KEY": "storage-migration-verifier-only",
        "ROMM_BASE_PATH": "/tmp/romm-storage-migration-verifier",
    }


def _runner_command(
    runner: str,
    dialect: str,
    host: str,
    port: str,
    database: str,
    command: list[str],
) -> list[str]:
    result = ["docker", "exec"]
    for key, value in _database_environment(dialect, host, port, database).items():
        result.extend(["-e", f"{key}={value}"])
    result.extend(["--workdir", "/app/backend", runner, *command])
    return result


def _alembic(
    runner: str,
    dialect: str,
    host: str,
    port: str,
    database: str,
    *args: str,
) -> None:
    _run(
        _runner_command(
            runner,
            dialect,
            host,
            port,
            database,
            ["/app/.venv/bin/alembic", *args],
        )
    )


def _bootstrap_mysql_0107(name: str) -> None:
    statement = (
        "CREATE TABLE platforms (id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY);"
        "CREATE TABLE users (id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY);"
        "CREATE TABLE roms ("
        "id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,"
        "platform_id INTEGER NOT NULL,"
        "missing_from_fs BOOLEAN NOT NULL DEFAULT FALSE,"
        "CONSTRAINT fk_verifier_rom_platform FOREIGN KEY (platform_id) "
        "REFERENCES platforms(id) ON DELETE CASCADE);"
        "CREATE TABLE rom_files ("
        "id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,"
        "rom_id INTEGER NOT NULL,"
        "file_name VARCHAR(450) NOT NULL,"
        "file_path VARCHAR(1000) NOT NULL,"
        "file_size_bytes BIGINT NOT NULL,"
        "missing_from_fs BOOLEAN NOT NULL DEFAULT FALSE,"
        "CONSTRAINT fk_verifier_file_rom FOREIGN KEY (rom_id) "
        "REFERENCES roms(id) ON DELETE CASCADE);"
        "CREATE TABLE saves ("
        "id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,"
        "rom_id INTEGER NOT NULL,"
        "user_id INTEGER NOT NULL,"
        "CONSTRAINT fk_verifier_save_rom FOREIGN KEY (rom_id) "
        "REFERENCES roms(id) ON DELETE CASCADE);"
        "CREATE TABLE states ("
        "id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,"
        "rom_id INTEGER NOT NULL,"
        "user_id INTEGER NOT NULL,"
        "CONSTRAINT fk_verifier_state_rom FOREIGN KEY (rom_id) "
        "REFERENCES roms(id) ON DELETE CASCADE);"
        "CREATE TABLE play_sessions ("
        "id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,"
        "rom_id INTEGER NULL,"
        "CONSTRAINT fk_verifier_session_rom FOREIGN KEY (rom_id) "
        "REFERENCES roms(id) ON DELETE SET NULL);"
        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);"
        "INSERT INTO alembic_version (version_num) "
        "VALUES ('0107_roms_dedup_cover_index');"
    )
    _run(
        [
            "docker",
            "exec",
            name,
            "sh",
            "-lc",
            f'mysql -uroot -proot "$MYSQL_DATABASE" -e {statement!r}',
        ]
    )


def _execute_sql(
    runner: str,
    dialect: str,
    host: str,
    port: str,
    database: str,
    sql: str,
) -> None:
    program = (
        "from config.config_manager import ConfigManager; "
        "from sqlalchemy import create_engine, text; "
        "engine=create_engine(ConfigManager.get_db_engine()); "
        f"sql={sql!r}; "
        "connection=engine.connect(); transaction=connection.begin(); "
        "connection.execute(text(sql)); transaction.commit(); connection.close(); "
        "engine.dispose()"
    )
    _run(
        _runner_command(
            runner,
            dialect,
            host,
            port,
            database,
            ["/app/.venv/bin/python", "-c", program],
        )
    )


def _query_scalar(
    runner: str,
    dialect: str,
    host: str,
    port: str,
    database: str,
    sql: str,
) -> str:
    program = (
        "from config.config_manager import ConfigManager; "
        "from sqlalchemy import create_engine, text; "
        "engine=create_engine(ConfigManager.get_db_engine()); "
        f"sql={sql!r}; "
        "connection=engine.connect(); value=connection.scalar(text(sql)); "
        "print(value); connection.close(); engine.dispose()"
    )
    return _run(
        _runner_command(
            runner,
            dialect,
            host,
            port,
            database,
            ["/app/.venv/bin/python", "-c", program],
        ),
        capture=True,
    )


def _wait_until_queryable(
    runner: str,
    dialect: str,
    host: str,
    port: str,
    database: str,
) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            _query_scalar(
                runner,
                dialect,
                host,
                port,
                database,
                "SELECT 1",
            )
            return
        except subprocess.CalledProcessError:
            time.sleep(1)
    raise RuntimeError(f"{dialect}: database did not become queryable after restart")


def _platform_statements(dialect: str, platform_id: int) -> list[str]:
    if dialect == "mysql":
        return [f"INSERT INTO platforms (id) VALUES ({platform_id})"]
    return [
        "INSERT INTO platforms "
        "(id, name, slug, fs_slug, missing_from_fs) "
        f"VALUES ({platform_id}, 'Verifier {platform_id}', "
        f"'verifier-{platform_id}', 'verifier-{platform_id}', FALSE)"
    ]


def _verify_lifecycle_downgrade_rejected(
    dialect: str,
    runner: str,
    host: str,
    port: str,
    database: str,
) -> None:
    statements = [
        *_platform_statements(dialect, 900001),
        *_platform_statements(dialect, 900002),
        "INSERT INTO storage_roots "
        "(id, name, container_path, mode, active) "
        "VALUES (900001, 'Verifier', '/verifier', 'external_read_only', TRUE)",
        "INSERT INTO platform_storage_mappings "
        "(id, platform_id, storage_root_id, relative_path, active, version) "
        "VALUES (900001, 900001, 900001, 'History', FALSE, 2)",
        "INSERT INTO platform_storage_mappings "
        "(id, platform_id, storage_root_id, relative_path, active, version) "
        "VALUES (900002, 900001, 900001, 'Replacement', TRUE, 1)",
        "INSERT INTO platform_storage_mappings "
        "(id, platform_id, storage_root_id, relative_path, active, version) "
        "VALUES (900003, 900002, 900001, 'History', TRUE, 1)",
        "INSERT INTO storage_mapping_audits "
        "(actor_user_id, actor_display_name, platform_id, mapping_id, action, "
        "old_storage_root_id, old_relative_path, old_version, old_active, "
        "new_storage_root_id, new_relative_path, new_version, new_active) "
        "VALUES (1, 'Verifier', 900001, 900001, 'deactivate', 900001, "
        "'History', 1, TRUE, 900001, 'History', 2, FALSE)",
    ]
    for statement in statements:
        _execute_sql(runner, dialect, host, port, database, statement)
    try:
        _alembic(
            runner,
            dialect,
            host,
            port,
            database,
            "downgrade",
            "0108_storage_foundation",
        )
    except subprocess.CalledProcessError:
        return
    raise RuntimeError(f"{dialect}: lifecycle downgrade unexpectedly succeeded")


def _seed_0110_state(
    dialect: str,
    runner: str,
    host: str,
    port: str,
    database: str,
) -> None:
    statements = [
        *_platform_statements(dialect, 910001),
        "INSERT INTO storage_roots "
        "(id, name, container_path, mode, active) "
        "VALUES (910001, 'Seeded 0110', '/seeded-0110', "
        "'external_read_only', TRUE)",
        "INSERT INTO platform_storage_mappings "
        "(id, platform_id, storage_root_id, relative_path, active, version) "
        "VALUES (910001, 910001, 910001, 'roms/verifier-910001', TRUE, 4)",
        "INSERT INTO mapping_previews "
        "(id, mapping_id, state, observed_files, observed_directories, "
        "observed_bytes, lower_bound, budget_reason, problems, "
        "observed_revision, stale, completed_at) "
        "VALUES (910001, 910001, 'complete', 2, 1, 4096, FALSE, NULL, "
        "'[]', 4, FALSE, CURRENT_TIMESTAMP)",
    ]
    for statement in statements:
        _execute_sql(runner, dialect, host, port, database, statement)


def _verify_seeded_0110_state(
    dialect: str,
    runner: str,
    host: str,
    port: str,
    database: str,
) -> None:
    mapping_version = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT version FROM platform_storage_mappings WHERE id = 910001",
    )
    preview_revision = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT observed_revision FROM mapping_previews WHERE id = 910001",
    )
    if mapping_version != "4" or preview_revision != "4":
        raise RuntimeError(f"{dialect}: seeded 0110 state did not survive")


def _seed_0111_state(
    dialect: str,
    runner: str,
    host: str,
    port: str,
    database: str,
) -> None:
    if dialect == "mysql":
        rom_values = (
            "(920011, 910001, FALSE), "
            "(920012, 910001, FALSE), "
            "(920013, 910001, TRUE)"
        )
        later_rom_values = "(920014, 910001, FALSE)"
        rom_insert = "INSERT INTO roms (id, platform_id, missing_from_fs) VALUES "
    else:
        rom_values = (
            "(920011, 910001, 'changed.bin', 'changed', 'changed', 'bin', "
            "'roms/verifier-910001', 1, 'Changed', FALSE), "
            "(920012, 910001, 'visible.bin', 'visible', 'visible', 'bin', "
            "'roms/verifier-910001', 1, 'Visible', FALSE), "
            "(920013, 910001, 'unmatched.bin', 'unmatched', 'unmatched', 'bin', "
            "'roms/verifier-910001', 1, 'Unmatched', TRUE)"
        )
        later_rom_values = (
            "(920014, 910001, 'later.bin', 'later', 'later', 'bin', "
            "'roms/verifier-910001', 1, 'Later', FALSE)"
        )
        rom_insert = (
            "INSERT INTO roms "
            "(id, platform_id, fs_name, fs_name_no_tags, fs_name_no_ext, "
            "fs_extension, fs_path, fs_size_bytes, name, missing_from_fs) VALUES "
        )
    file_insert = (
        "INSERT INTO rom_files "
        "(id, rom_id, file_name, file_path, file_size_bytes, missing_from_fs) "
        "VALUES "
    )
    statements = [
        "INSERT INTO legacy_detection_results "
        "(id, platform_id, storage_root_id, state, proposed_relative_path, "
        "observed_files, observed_bytes, lower_bound, selectable, "
        "source_fingerprint, observed_mapping_id, observed_mapping_version, "
        "version, actor_user_id, expires_at) "
        "VALUES (920001, 910001, 910001, 'detected', "
        "'roms/verifier-910001', 2, 4096, FALSE, TRUE, "
        "'0000000000000000000000000000000000000000000000000000000000000000', "
        "910001, 4, 1, 1, '2037-01-01 00:00:00')",
        "INSERT INTO legacy_migrations "
        "(id, detection_result_id, platform_id, storage_root_id, mapping_id, "
        "relative_path, state, version, actor_user_id, "
        "reconnected_catalog_count, unmatched_catalog_count, expires_at) "
        "VALUES (920001, 920001, 910001, 910001, 910001, "
        "'roms/verifier-910001', 'completed', 1, 1, 0, 0, "
        "'2037-01-01 00:00:00')",
        rom_insert + rom_values,
        file_insert
        + "(920021, 920011, 'changed.bin', 'roms/verifier-910001', 1, FALSE), "
        "(920022, 920012, 'visible.bin', 'roms/verifier-910001', 1, FALSE), "
        "(920023, 920013, 'unmatched.bin', 'roms/verifier-910001', 1, TRUE)",
        "INSERT INTO legacy_migration_catalog_changes "
        "(migration_id, entity_kind, entity_id, prior_missing_from_fs) VALUES "
        "(920001, 'rom', 920011, TRUE), "
        "(920001, 'rom_file', 920021, TRUE)",
        rom_insert + later_rom_values,
        file_insert + "(920024, 920014, 'later.bin', 'roms/verifier-910001', 1, FALSE)",
    ]
    for statement in statements:
        _execute_sql(runner, dialect, host, port, database, statement)


def _rollback_seeded_exact_state(
    dialect: str,
    runner: str,
    host: str,
    port: str,
    database: str,
) -> None:
    program = """
from config.config_manager import ConfigManager
from sqlalchemy import create_engine, text

engine = create_engine(ConfigManager.get_db_engine())
with engine.begin() as connection:
    changes = connection.execute(text(
        "SELECT entity_kind, entity_id, prior_missing_from_fs "
        "FROM legacy_migration_catalog_changes "
        "WHERE migration_id = 920001 ORDER BY entity_kind, entity_id FOR UPDATE"
    )).all()
    expected = [("rom", 920011, True), ("rom_file", 920021, True)]
    if [(kind, entity_id, bool(prior)) for kind, entity_id, prior in changes] != expected:
        raise RuntimeError("seeded exact catalog change set is stale")
    rom = connection.execute(text(
        "SELECT id, platform_id, missing_from_fs FROM roms "
        "WHERE id = 920011 FOR UPDATE"
    )).one()
    rom_file = connection.execute(text(
        "SELECT rom_files.id, roms.platform_id, rom_files.missing_from_fs "
        "FROM rom_files JOIN roms ON roms.id = rom_files.rom_id "
        "WHERE rom_files.id = 920021 FOR UPDATE"
    )).one()
    if rom[1] != 910001 or bool(rom[2]):
        raise RuntimeError("seeded exact ROM state is stale")
    if rom_file[1] != 910001 or bool(rom_file[2]):
        raise RuntimeError("seeded exact RomFile state is stale")
    connection.execute(text(
        "UPDATE roms SET missing_from_fs = TRUE WHERE id = 920011"
    ))
    connection.execute(text(
        "UPDATE rom_files SET missing_from_fs = TRUE WHERE id = 920021"
    ))
    mapping = connection.execute(text(
        "UPDATE platform_storage_mappings SET active = FALSE, version = 5 "
        "WHERE id = 910001 AND platform_id = 910001 "
        "AND active = TRUE AND version = 4"
    ))
    migration = connection.execute(text(
        "UPDATE legacy_migrations SET state = 'rolled_back', version = 2, "
        "rolled_back_at = CURRENT_TIMESTAMP "
        "WHERE id = 920001 AND platform_id = 910001 "
        "AND state = 'completed' AND version = 1"
    ))
    if mapping.rowcount != 1 or migration.rowcount != 1:
        raise RuntimeError("seeded exact rollback lineage is stale")
engine.dispose()
"""
    _run(
        _runner_command(
            runner,
            dialect,
            host,
            port,
            database,
            ["/app/.venv/bin/python", "-c", program],
        )
    )


def _verify_exact_catalog_state(
    dialect: str,
    runner: str,
    host: str,
    port: str,
    database: str,
) -> None:
    recorded = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT COUNT(*) FROM legacy_migration_catalog_changes "
        "WHERE migration_id = 920001 AND prior_missing_from_fs = TRUE",
    )
    restored = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT COUNT(*) FROM roms WHERE id = 920011 AND missing_from_fs = TRUE",
    )
    restored_files = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT COUNT(*) FROM rom_files "
        "WHERE id = 920021 AND missing_from_fs = TRUE",
    )
    if recorded != "2" or restored != "1" or restored_files != "1":
        raise RuntimeError(
            f"{dialect}: exact catalog rollback did not restore recorded rows"
        )
    unchanged = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT COUNT(*) FROM roms WHERE "
        "(id = 920012 AND missing_from_fs = FALSE) OR "
        "(id = 920013 AND missing_from_fs = TRUE) OR "
        "(id = 920014 AND missing_from_fs = FALSE)",
    )
    unchanged_files = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT COUNT(*) FROM rom_files WHERE "
        "(id = 920022 AND missing_from_fs = FALSE) OR "
        "(id = 920023 AND missing_from_fs = TRUE) OR "
        "(id = 920024 AND missing_from_fs = FALSE)",
    )
    if unchanged != "3" or unchanged_files != "3":
        raise RuntimeError(f"{dialect}: exact catalog rollback changed unrelated rows")


def _verify_restart_persistence(
    dialect: str,
    runner: str,
    host: str,
    port: str,
    database: str,
    database_container: str,
    health: list[str],
) -> str:
    _seed_0111_state(dialect, runner, host, port, database)
    _run(["docker", "restart", database_container])
    _wait_until_ready(database_container, health)
    port = _mapped_port(database_container, DIALECTS[dialect]["port"])
    _wait_until_queryable(runner, dialect, host, port, database)
    first_use = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT first_used_at FROM legacy_migrations WHERE id = 920001",
    )
    migration_version = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT version FROM legacy_migrations WHERE id = 920001",
    )
    if first_use != "None" or migration_version != "1":
        raise RuntimeError(f"{dialect}: lifecycle state did not survive restart")

    _rollback_seeded_exact_state(dialect, runner, host, port, database)
    _verify_exact_catalog_state(dialect, runner, host, port, database)
    _run(["docker", "restart", database_container])
    _wait_until_ready(database_container, health)
    port = _mapped_port(database_container, DIALECTS[dialect]["port"])
    _wait_until_queryable(runner, dialect, host, port, database)
    _verify_exact_catalog_state(dialect, runner, host, port, database)

    migration_state = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT state FROM legacy_migrations WHERE id = 920001",
    )
    rolled_back_at = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT rolled_back_at FROM legacy_migrations WHERE id = 920001",
    )
    if migration_state != "rolled_back" or rolled_back_at == "None":
        raise RuntimeError(f"{dialect}: legacy rollback state did not survive restart")

    mapping_version = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT version FROM platform_storage_mappings WHERE id = 910001",
    )
    mapping_active = _query_scalar(
        runner,
        dialect,
        host,
        port,
        database,
        "SELECT active FROM platform_storage_mappings WHERE id = 910001",
    )
    if mapping_version != "5" or mapping_active not in {"0", "False", "false"}:
        raise RuntimeError(
            f"{dialect}: mapping rollback revision did not survive restart"
        )
    return port


def _verify_safe_lifecycle_downgrade_rejected(
    dialect: str,
    runner: str,
    host: str,
    port: str,
    database: str,
) -> None:
    try:
        _alembic(
            runner,
            dialect,
            host,
            port,
            database,
            "downgrade",
            "0110_mapping_preview_results",
        )
    except subprocess.CalledProcessError:
        return
    raise RuntimeError(f"{dialect}: safe lifecycle downgrade unexpectedly succeeded")


def _clear_0111_state(
    dialect: str,
    runner: str,
    host: str,
    port: str,
    database: str,
) -> None:
    for statement in (
        "UPDATE platform_storage_mappings "
        "SET active = TRUE, version = 4 WHERE id = 910001",
        "DELETE FROM legacy_migrations",
        "DELETE FROM legacy_detection_results",
        "DELETE FROM rom_files WHERE id BETWEEN 920021 AND 920024",
        "DELETE FROM roms WHERE id BETWEEN 920011 AND 920014",
        "DELETE FROM owned_cleanup_intents",
        "UPDATE saves SET retained_catalog_id = NULL WHERE retained_catalog_id IS NOT NULL",
        "UPDATE states SET retained_catalog_id = NULL WHERE retained_catalog_id IS NOT NULL",
        "UPDATE play_sessions SET retained_catalog_id = NULL "
        "WHERE retained_catalog_id IS NOT NULL",
        "DELETE FROM retained_catalog_identities",
    ):
        _execute_sql(runner, dialect, host, port, database, statement)


def _handler_tests(
    runner: str,
    dialect: str,
    host: str,
    port: str,
    database: str,
    repetitions: int = 1,
) -> None:
    command = _runner_command(
        runner,
        dialect,
        host,
        port,
        database,
        [
            "/app/.venv/bin/pytest",
            "-c",
            "/dev/null",
            "tests/models/test_storage.py",
            "tests/models/test_safe_lifecycle.py",
            "tests/handler/database/test_storage_handler.py",
            "tests/integration/test_legacy_migration.py::test_exact_rollback_restores_only_recorded_rows_and_preserves_later_rows",
            "tests/integration/test_legacy_migration.py::test_exact_rollback_rejects_stale_recorded_rows_atomically",
            "-x",
        ],
    )
    for _ in range(repetitions):
        _run(command)


def verify_dialect(
    dialect: str,
    runner: str,
    *,
    handler_tests: bool = False,
    handler_test_repetitions: int = 1,
) -> None:
    config = DIALECTS[dialect]
    suffix = uuid.uuid4().hex[:10]
    name = f"romm-storage-migration-{dialect}-{suffix}"
    database = f"romm_migration_{suffix}"
    environment = dict(config["env"])
    database_key = {
        "mariadb": "MARIADB_DATABASE",
        "mysql": "MYSQL_DATABASE",
        "postgresql": "POSTGRES_DB",
    }[dialect]
    environment[database_key] = database
    health = list(config["health"])
    if dialect == "postgresql":
        health[-1] = database

    command = [
        "docker",
        "run",
        "--detach",
        "--name",
        name,
        "--publish",
        f"0:{config['port']}",
    ]
    for key, value in environment.items():
        command.extend(["--env", f"{key}={value}"])
    command.append(config["image"])

    try:
        _run(command)
        _wait_until_ready(name, health)
        host = _runner_gateway(runner)
        port = _mapped_port(name, config["port"])
        if dialect == "mysql":
            _bootstrap_mysql_0107(name)

        _alembic(runner, dialect, host, port, database, "upgrade", "head")
        _alembic(
            runner,
            dialect,
            host,
            port,
            database,
            "downgrade",
            "0108_storage_foundation",
        )
        _alembic(runner, dialect, host, port, database, "upgrade", "head")
        _verify_lifecycle_downgrade_rejected(dialect, runner, host, port, database)
        _alembic(runner, dialect, host, port, database, "upgrade", "head")

        _alembic(
            runner,
            dialect,
            host,
            port,
            database,
            "downgrade",
            "0110_mapping_preview_results",
        )
        _seed_0110_state(dialect, runner, host, port, database)
        _alembic(runner, dialect, host, port, database, "upgrade", "head")
        _verify_seeded_0110_state(dialect, runner, host, port, database)
        port = _verify_restart_persistence(
            dialect,
            runner,
            host,
            port,
            database,
            name,
            health,
        )
        _verify_safe_lifecycle_downgrade_rejected(dialect, runner, host, port, database)
        _clear_0111_state(dialect, runner, host, port, database)
        _alembic(
            runner,
            dialect,
            host,
            port,
            database,
            "downgrade",
            "0110_mapping_preview_results",
        )
        _verify_seeded_0110_state(dialect, runner, host, port, database)
        _alembic(runner, dialect, host, port, database, "upgrade", "head")
        _verify_seeded_0110_state(dialect, runner, host, port, database)

        if handler_tests and dialect != "mysql":
            _handler_tests(
                runner,
                dialect,
                host,
                port,
                database,
                handler_test_repetitions,
            )
        elif handler_tests:
            print("mysql: handler tests skipped on the minimal 0107 baseline")
        print(f"{dialect}: pristine and seeded-0110 round-trips passed")
    finally:
        subprocess.run(
            ["docker", "rm", "--force", name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dialects", nargs="+", choices=sorted(DIALECTS), required=True
    )
    parser.add_argument("--runner-container", default="romm-dev")
    parser.add_argument("--handler-tests", action="store_true")
    parser.add_argument("--handler-test-repetitions", type=_positive_integer, default=1)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    for dialect in args.dialects:
        verify_dialect(
            dialect,
            args.runner_container,
            handler_tests=args.handler_tests,
            handler_test_repetitions=args.handler_test_repetitions,
        )


if __name__ == "__main__":
    main()
