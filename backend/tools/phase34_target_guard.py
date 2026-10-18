"""Dependency-free, pre-import authority for disposable Phase 34 tests."""

import json
import os
import re
import socket
from pathlib import Path

LABEL = "org.pgdp.phase34.run"
DRIVERS = {
    "mariadb": "mariadb+mariadbconnector",
    "mysql": "mysql+mysqlconnector",
    "postgresql": "postgresql+psycopg",
}


def refuse(reason):
    raise RuntimeError("Phase34 target refused: " + reason)


def expected_environment(token, driver):
    if not re.fullmatch(r"[a-f0-9]{32}", token or "") or driver not in DRIVERS:
        refuse("invalid run identity or driver")
    return {
        "PHASE34_RUN_TOKEN": token,
        "ROMM_DB_DRIVER": driver,
        "DB_HOST": "sql-" + token,
        "DB_PORT": "5432" if driver == "postgresql" else "3306",
        "DB_NAME": "p34_" + token,
        "DB_USER": "p34_" + token[:16],
        "DB_PASSWD": token,
        "REDIS_HOST": "redis-" + token,
        "REDIS_PORT": "6379",
        "REDIS_PASSWORD": token,
        "REDIS_DB": "0",
        "ROMM_BASE_PATH": "/phase34/owned",
        "ROMM_TMP_PATH": "/phase34/owned/tmp",
        "PYTHON_DOTENV_DISABLED": "1",
    }


def validate_target(env=None, resolved_url=None, *, verify_redis=True):
    env = os.environ if env is None else env
    token = env.get("PHASE34_RUN_TOKEN", "")
    driver = env.get("ROMM_DB_DRIVER", "")
    expected = expected_environment(token, driver)
    for key, value in expected.items():
        if env.get(key) != value:
            refuse("environment mismatch: " + key)
    for key in (
        "DATABASE_URL",
        "SQLALCHEMY_DATABASE_URI",
        "DB_QUERY_JSON",
        "REDIS_URL",
        "REDIS_USERNAME",
        "REDIS_SSL",
        "PYTEST_ADDOPTS",
    ):
        if env.get(key):
            refuse("inherited override: " + key)
    if env.get("PYTEST_XDIST_WORKER", "master") != "master":
        refuse("xdist requires independently provisioned worker targets")
    try:
        path = Path(env["PHASE34_MANIFEST"])
        if not path.is_absolute() or path.is_symlink():
            refuse("invalid manifest path")
        manifest = json.loads(path.read_text())
    except (KeyError, OSError, ValueError):
        refuse("missing or unreadable target manifest")
    if manifest.get("token") != token or manifest.get("environment") != expected:
        refuse("manifest target mismatch")
    project = "pgdp34-" + token
    if manifest.get("project") != project:
        refuse("manifest project mismatch")
    network = manifest.get("network", {})
    if (
        network.get("name") != project + "_isolated"
        or network.get("internal") is not True
        or network.get("labels", {}).get(LABEL) != token
        or not re.fullmatch(r"[a-f0-9]{64}", network.get("id", ""))
    ):
        refuse("unverified isolated network")
    identities = []
    for service in ("sql", "redis"):
        item = manifest.get(service, {})
        labels = item.get("labels", {})
        if (
            labels.get(LABEL) != token
            or labels.get("com.docker.compose.project") != project
            or labels.get("com.docker.compose.service") != service
            or item.get("networks") != [network["id"]]
            or not re.fullmatch(r"[a-f0-9]{64}", item.get("id", ""))
        ):
            refuse("unverified service: " + service)
        identities.append(item["id"])
    if identities[0] == identities[1]:
        refuse("duplicate service identity")
    if not re.fullmatch(r"[a-f0-9]{40}", manifest.get("redis_run_id", "")):
        refuse("missing Redis instance identity")
    if resolved_url is not None:
        for attr, value in {
            "drivername": DRIVERS[driver],
            "host": expected["DB_HOST"],
            "port": int(expected["DB_PORT"]),
            "database": expected["DB_NAME"],
            "username": expected["DB_USER"],
            "password": expected["DB_PASSWD"],
            "query": {},
        }.items():
            if getattr(resolved_url, attr, None) != value:
                refuse("resolved SQLAlchemy target mismatch: " + attr)
    if verify_redis:
        verify_redis_identity(expected, manifest["redis_run_id"])
    return manifest


def verify_redis_identity(env, run_id):
    """Authenticate only after every static boundary has passed."""

    def command(stream, *args):
        encoded = [str(arg).encode() for arg in args]
        stream.write(
            ("*" + str(len(encoded)) + "\r\n").encode()
            + b"".join(
                ("$" + str(len(arg)) + "\r\n").encode() + arg + b"\r\n"
                for arg in encoded
            )
        )
        stream.flush()
        header = stream.readline(4096)
        if header.startswith(b"+"):
            return header[1:-2]
        if header.startswith(b"$"):
            size = int(header[1:-2])
            if not 0 <= size <= 65536:
                refuse("invalid Redis identity response")
            data = stream.read(size)
            if stream.read(2) != b"\r\n":
                refuse("truncated Redis identity")
            return data
        refuse("Redis identity request failed")

    try:
        with socket.create_connection((env["REDIS_HOST"], 6379), timeout=3) as conn:
            with conn.makefile("rwb") as stream:
                if command(stream, "AUTH", env["REDIS_PASSWORD"]) != b"OK":
                    refuse("Redis authentication mismatch")
                info = command(stream, "INFO", "server")
                actual = dict(
                    row.split(b":", 1) for row in info.split(b"\r\n") if b":" in row
                )
                if actual.get(b"run_id") != run_id.encode():
                    refuse("Redis instance mismatch")
    except (OSError, ValueError):
        refuse("Redis identity unavailable")
