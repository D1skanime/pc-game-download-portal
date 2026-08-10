"""Exercise revision 0108 on isolated supported database containers."""

# trunk-ignore-all(bandit/B404,bandit/B105,bandit/B108,bandit/B603,bandit/B607)

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


def _alembic(runner: str, dialect: str, host: str, port: str, *args: str) -> None:
    environment = {
        "ROMM_DB_DRIVER": dialect,
        "DB_HOST": host,
        "DB_PORT": port,
        "DB_USER": "romm",
        "DB_PASSWD": "romm",
        "DB_NAME": "romm_migration",
        "ROMM_AUTH_SECRET_KEY": "storage-migration-verifier-only",
        "ROMM_BASE_PATH": "/tmp/romm-storage-migration-verifier",
    }
    command = ["docker", "exec"]
    for key, value in environment.items():
        command.extend(["-e", f"{key}={value}"])
    command.extend(
        [runner, "sh", "-lc", f"cd /app/backend && uv run alembic {' '.join(args)}"]
    )
    _run(command)


def _bootstrap_mysql_0107(name: str) -> None:
    statement = (
        "CREATE DATABASE IF NOT EXISTS romm_migration;"
        "USE romm_migration;"
        "CREATE TABLE platforms (id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY);"
        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);"
        "INSERT INTO alembic_version (version_num) VALUES ('0107_roms_dedup_cover_index');"
    )
    _run(["docker", "exec", name, "mysql", "-uroot", "-proot", "-e", statement])


def _handler_tests(
    runner: str, dialect: str, host: str, port: str, repetitions: int = 1
) -> None:
    environment = {
        "ROMM_DB_DRIVER": dialect,
        "DB_HOST": host,
        "DB_PORT": port,
        "DB_USER": "romm",
        "DB_PASSWD": "romm",
        "DB_NAME": "romm_migration",
        "ROMM_AUTH_SECRET_KEY": "storage-handler-verifier-only",
        "ROMM_BASE_PATH": "/tmp/romm-storage-handler-verifier",
    }
    command = ["docker", "exec"]
    for key, value in environment.items():
        command.extend(["-e", f"{key}={value}"])
    command.extend(
        [
            runner,
            "sh",
            "-lc",
            "cd /app/backend && uv run pytest -c /dev/null tests/models/test_storage.py tests/handler/database/test_storage_handler.py -x",
        ]
    )
    for _ in range(repetitions):
        _run(command)


def _database_environment(dialect: str, host: str, port: str) -> dict[str, str]:
    return {
        "ROMM_DB_DRIVER": dialect,
        "DB_HOST": host,
        "DB_PORT": port,
        "DB_USER": "romm",
        "DB_PASSWD": "romm",
        "DB_NAME": "romm_migration",
        "ROMM_AUTH_SECRET_KEY": "storage-migration-verifier-only",
        "ROMM_BASE_PATH": "/tmp/romm-storage-migration-verifier",
    }


def _execute_sql(runner: str, dialect: str, host: str, port: str, sql: str) -> None:
    command = ["docker", "exec"]
    for key, value in _database_environment(dialect, host, port).items():
        command.extend(["-e", f"{key}={value}"])
    program = (
        "from config.config_manager import ConfigManager; "
        "from sqlalchemy import create_engine, text; "
        "engine=create_engine(ConfigManager.get_db_engine()); "
        f"sql={sql!r}; "
        "connection=engine.connect(); transaction=connection.begin(); "
        "connection.execute(text(sql)); transaction.commit(); connection.close()"
    )
    command.extend(
        ["--workdir", "/app/backend", runner, "/app/.venv/bin/python", "-c", program]
    )
    _run(command)


def _verify_lifecycle_downgrade_rejected(
    dialect: str, runner: str, host: str, port: str
) -> None:
    platform_statements = (
        [
            "INSERT INTO platforms (id) VALUES (900001)",
            "INSERT INTO platforms (id) VALUES (900002)",
        ]
        if dialect == "mysql"
        else [
            "INSERT INTO platforms (id, name, slug, fs_slug, missing_from_fs) VALUES (900001, 'Verifier One', 'verifier-one', 'verifier-one', FALSE)",
            "INSERT INTO platforms (id, name, slug, fs_slug, missing_from_fs) VALUES (900002, 'Verifier Two', 'verifier-two', 'verifier-two', FALSE)",
        ]
    )
    statements = [
        *platform_statements,
        "INSERT INTO storage_roots (id, name, container_path, mode, active) VALUES (900001, 'Verifier', '/verifier', 'external_read_only', TRUE)",
        "INSERT INTO platform_storage_mappings (id, platform_id, storage_root_id, relative_path, active, version) VALUES (900001, 900001, 900001, 'History', FALSE, 2)",
        "INSERT INTO platform_storage_mappings (id, platform_id, storage_root_id, relative_path, active, version) VALUES (900002, 900001, 900001, 'Replacement', TRUE, 1)",
        "INSERT INTO platform_storage_mappings (id, platform_id, storage_root_id, relative_path, active, version) VALUES (900003, 900002, 900001, 'History', TRUE, 1)",
        "INSERT INTO storage_mapping_audits (actor_user_id, actor_display_name, platform_id, mapping_id, action, old_storage_root_id, old_relative_path, old_version, old_active, new_storage_root_id, new_relative_path, new_version, new_active) VALUES (1, 'Verifier', 900001, 900001, 'deactivate', 900001, 'History', 1, TRUE, 900001, 'History', 2, FALSE)",
    ]
    for statement in statements:
        _execute_sql(runner, dialect, host, port, statement)
    try:
        _alembic(runner, dialect, host, port, "downgrade", "0108_storage_foundation")
    except subprocess.CalledProcessError:
        return
    raise RuntimeError(f"{dialect}: lifecycle downgrade unexpectedly succeeded")


def verify_dialect(
    dialect: str,
    runner: str,
    *,
    handler_tests: bool = False,
    handler_test_repetitions: int = 1,
) -> None:
    config = DIALECTS[dialect]
    name = f"romm-storage-migration-{dialect}-{uuid.uuid4().hex[:10]}"
    command = [
        "docker",
        "run",
        "--detach",
        "--name",
        name,
        "--publish",
        f"0:{config['port']}",
    ]
    for key, value in config["env"].items():
        command.extend(["--env", f"{key}={value}"])
    command.append(config["image"])

    try:
        _run(command)
        _wait_until_ready(name, config["health"])
        host = _runner_gateway(runner)
        port = _mapped_port(name, config["port"])
        if dialect == "mysql":
            _bootstrap_mysql_0107(name)
        _alembic(runner, dialect, host, port, "upgrade", "head")
        _alembic(runner, dialect, host, port, "downgrade", "0108_storage_foundation")
        _alembic(runner, dialect, host, port, "upgrade", "head")
        _verify_lifecycle_downgrade_rejected(dialect, runner, host, port)
        if handler_tests and dialect != "mysql":
            _handler_tests(runner, dialect, host, port, handler_test_repetitions)
        elif handler_tests:
            print("mysql: handler tests skipped on the minimal 0107 baseline")
        print(f"{dialect}: upgrade/downgrade/re-upgrade passed")
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
