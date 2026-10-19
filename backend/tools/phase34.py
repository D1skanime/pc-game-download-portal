#!/usr/bin/env python3
"""Fail-closed disposable Phase 34 command runner. Run from repository root."""

import argparse
import json
import os
import platform
import subprocess  # nosec B404, runner uses explicit argv without a shell
import sys
import tempfile
import uuid
from pathlib import Path

from phase34_fixtures import (
    JOB_IDENTITY,
    LIFECYCLE,
    SQL_IMAGES,
    backend_command,
    cleanup_snapshot,
    code_manifest,
    expected_red,
    frontend_command,
    prepare,
    quality,
    redact_evidence,
    redact_output,
    restore_generated_owner,
    schema_commands,
    source_manifest,
)
from phase34_target_guard import LABEL, expected_environment, validate_target

REPO = Path(__file__).resolve().parents[2]
COMPOSE = Path(__file__).with_name("phase34.compose.yml")
IMAGE = "pgdp-pgdp-dev:latest"
EXEC_PATH = (
    "/app/.venv/bin:/usr/local/bin:/usr/bin:/bin:/root/.nvm/versions/node/v24.16.0/bin"
)
RED_BACKEND = {
    "test_manual_running_job_is_recognized": "P34_RQ_RUNNING",
    "test_manual_queued_job_is_recognized": "P34_RQ_QUEUED",
    "test_stop_finds_manual_job": "P34_RQ_STOP",
}
RED_FRONTEND = {
    "scan lifecycle scope ownership > reinstalls listeners after scope disposal": "P34_REMOUNT",
    "scan lifecycle scope ownership > keeps listeners while another owner survives": "P34_OWNERS",
    "scan lifecycle scope ownership > cancels debounce work on final disposal": "P34_DEBOUNCE",
}


def host_preflight():
    if platform.system() != "Linux" or Path.cwd().resolve() != REPO:
        raise RuntimeError("runner requires canonical Linux repository root")
    if REPO != Path("/home/d1sk/pc-game-download-portal"):
        raise RuntimeError("unexpected repository")
    for key in (
        "DB_HOST",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWD",
        "REDIS_HOST",
        "REDIS_URL",
        "DATABASE_URL",
        "PHASE34_RUN_TOKEN",
        "COMPOSE_FILE",
        "COMPOSE_PROJECT_NAME",
    ):
        if os.environ.get(key):
            raise RuntimeError("refusing inherited target override: " + key)
    # trunk-ignore(bandit/B603): Fixed read-only Git argv, no shell.
    result = subprocess.run(  # nosec B603,B607, fixed Git read-only preflight
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    if Path(result.stdout.strip()) != REPO:
        raise RuntimeError("Git root mismatch")


class Run:
    image: str = IMAGE

    def __init__(self, driver="mariadb"):
        if driver not in SQL_IMAGES:
            raise RuntimeError("unsupported dialect")
        self.token = uuid.uuid4().hex
        self.project = "pgdp34-" + self.token
        self.driver = driver
        self.root = Path(tempfile.mkdtemp(prefix=self.project + "-"))
        self.evidence = self.root / "evidence"
        self.control = self.root / "control"
        self.evidence.mkdir()
        self.control.mkdir()
        self.env = expected_environment(self.token, driver)
        self.env["PHASE34_MANIFEST"] = "/phase34/control/manifest.json"
        self.counter = 0
        self.records = []
        self.before = None
        self.runner = None
        self.manifest = None
        print("RUN", self.project, driver, "evidence:", self.evidence, flush=True)

    def command(self, args, *, timeout=180, check=True, cwd=None):
        self.counter += 1
        expired = None
        try:
            # trunk-ignore(bandit/B603): Generated target and validated fixed tool argv.
            result = subprocess.run(
                args,
                cwd=cwd,
                env=self.process_env(),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            expired = error

            def decoded(value):
                return (
                    value.decode(errors="replace")
                    if isinstance(value, bytes)
                    else value or ""
                )

            result = subprocess.CompletedProcess(
                args, 124, decoded(error.stdout), decoded(error.stderr)
            )
        name = str(self.counter).zfill(2)
        # The run token doubles as disposable credentials. Retain no credentials in logs.
        output = redact_output(result.stdout + result.stderr, self.token)
        (self.evidence / (name + ".log")).write_text(output)
        self.records.append(
            {
                "command": [a.replace(self.token, "<run-token>") for a in args],
                "exit": result.returncode,
                "log": name + ".log",
            }
        )
        (self.evidence / "commands.json").write_text(json.dumps(self.records, indent=2))
        if expired is not None:
            print("TIMEOUT retained in log " + name, flush=True)
            raise expired
        if check and result.returncode:
            print(output[-7000:], flush=True)
            raise RuntimeError(
                "command failed (" + str(result.returncode) + "), log " + name
            )
        return result

    def process_env(self):
        # Compose receives generated values only, with no application env file.
        env = {
            key: os.environ[key]
            for key in ("PATH", "DOCKER_HOST", "DOCKER_CONTEXT", "XDG_RUNTIME_DIR")
            if key in os.environ
        }
        env.update(self.env)
        env.update(
            {
                "P34_SQL_IMAGE": SQL_IMAGES[self.driver],
                "P34_SQL_COMMAND": {
                    "mysql": "mysqld --log-bin-trust-function-creators=1",
                    "mariadb": "mariadbd",
                    "postgresql": "postgres",
                }[self.driver],
                "P34_RUNNER_IMAGE": getattr(self, "image", IMAGE),
                "P34_REPO": str(self.root / "checkout"),
                "P34_CONTROL": str(self.control),
                "P34_EVIDENCE": str(self.evidence),
                "P34_GAMES": str(self.root / "Games"),
            }
        )
        return env

    def compose(self, *args, **kwargs):
        return self.command(
            [
                "docker",
                "compose",
                "--env-file",
                "/dev/null",
                "-p",
                self.project,
                "-f",
                str(COMPOSE),
                *args,
            ],
            **kwargs
        )

    def inspect(self, kind, identity):
        return json.loads(self.command(["docker", kind, "inspect", identity]).stdout)[0]

    def owned(self, kind):
        result = self.command(
            [
                "docker",
                kind,
                "ls",
                "-q",
                "--filter",
                "label=com.docker.compose.project=" + self.project,
            ]
        )
        identities = result.stdout.split()
        for identity in identities:
            item = self.inspect(kind, identity)
            labels = (
                item.get("Config", {}).get("Labels")
                if kind == "container"
                else item.get("Labels")
            )
            if not labels or labels.get(LABEL) != self.token:
                raise RuntimeError("cleanup refused: ownership mismatch for " + kind)
        return identities

    def start(self):
        games, snapshot = prepare(self.root, REPO)
        code = code_manifest(snapshot)
        (self.evidence / "code-before.json").write_text(json.dumps(code, indent=2))
        self.before = source_manifest(games)
        (self.evidence / "source-before.json").write_text(
            json.dumps(self.before, indent=2)
        )
        self.command(["docker", "version", "--format", "{{.Server.Version}}"])
        self.compose("config", "--format", "json")
        self.compose("up", "-d", "--pull", "missing", timeout=300)
        sql = self.compose("ps", "-q", "sql").stdout.strip()
        redis = self.compose("ps", "-q", "redis").stdout.strip()
        self.runner = self.compose("ps", "-q", "runner").stdout.strip()
        if not all((sql, redis, self.runner)):
            raise RuntimeError("missing isolated services")
        # Readiness has a fixed process deadline and never uses the host DB.
        if self.driver == "postgresql":
            ready = ["pg_isready", "-U", self.env["DB_USER"], "-d", self.env["DB_NAME"]]
        else:
            binary = "mariadb-admin" if self.driver == "mariadb" else "mysqladmin"
            ready = [
                binary,
                "ping",
                "-h",
                "127.0.0.1",
                "-u" + self.env["DB_USER"],
                "-p" + self.token,
            ]
        self.command(
            [
                "docker",
                "exec",
                sql,
                "sh",
                "-c",
                'for i in $(seq 1 45); do "$@" >/dev/null 2>&1 && exit 0; sleep 1; done; exit 1',
                "ready",
                *ready,
            ],
            timeout=55,
        )
        network = self.inspect("network", self.project + "_isolated")
        manifest = {
            "token": self.token,
            "project": self.project,
            "environment": expected_environment(self.token, self.driver),
            "network": {
                "name": network["Name"],
                "id": network["Id"],
                "internal": network["Internal"],
                "labels": network["Labels"],
            },
        }
        for service, identity in (("sql", sql), ("redis", redis)):
            item = self.inspect("container", identity)
            manifest[service] = {
                "id": item["Id"],
                "labels": item["Config"]["Labels"],
                "networks": [
                    entry["NetworkID"]
                    for entry in item["NetworkSettings"]["Networks"].values()
                ],
            }
        info = self.command(
            [
                "docker",
                "exec",
                "-e",
                "REDISCLI_AUTH=" + self.token,
                redis,
                "redis-cli",
                "INFO",
                "server",
            ]
        ).stdout
        manifest["redis_run_id"] = dict(
            line.split(":", 1) for line in info.splitlines() if ":" in line
        )["run_id"]
        path = self.control / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2))
        path.chmod(0o600)
        validate_target({**self.env, "PHASE34_MANIFEST": str(path)}, verify_redis=False)
        self.manifest = manifest
        self.exec(
            [
                "uv",
                "run",
                "python",
                "-c",
                "from tools.phase34_target_guard import validate_target; validate_target(); print('PASS pre-import target and Redis identity')",
            ]
        )

    def exec(self, args, *, frontend=False, check=True, timeout=180, extra=None):
        if self.manifest is None:
            raise RuntimeError("target manifest not verified")
        env = {
            **self.env,
            "PATH": EXEC_PATH,
            "UV_PROJECT_ENVIRONMENT": "/app/.venv",
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "ROMM_AUTH_SECRET_KEY": self.token,
            "DEV_MODE": "false",
            "IGDB_CLIENT_ID": "phase34-synthetic",
            "IGDB_CLIENT_SECRET": self.token,
            **(extra or {}),
        }
        return self.command(
            [
                "docker",
                "exec",
                "-w",
                "/app/frontend" if frontend else "/app/backend",
                self.runner,
                "env",
                "-i",
                *[k + "=" + v for k, v in env.items()],
                *args,
            ],
            check=check,
            timeout=timeout,
        )

    def close(self):
        after = (
            source_manifest(self.root / "Games") if self.before is not None else None
        )
        (self.evidence / "source-after.json").write_text(json.dumps(after, indent=2))
        # Enumerate first. Any ownership mismatch stops all deletion.
        resources = {
            kind: self.owned(kind) for kind in ("container", "volume", "network")
        }
        restore_generated_owner(self, resources)
        for kind, identities in resources.items():
            for identity in identities:
                args = ["docker", kind, "rm"]
                if kind == "container":
                    args.append("-f")
                self.command([*args, identity])
        remaining = {kind: self.owned(kind) for kind in resources}
        clean = not any(remaining.values())
        (self.evidence / "cleanup.json").write_text(
            json.dumps(
                {
                    "exact_resources": resources,
                    "remaining": remaining,
                    "clean": clean,
                    "snapshot_removed": False,
                    "source_unchanged": self.before == after,
                },
                indent=2,
            )
        )
        if not clean or self.before != after:
            raise RuntimeError("cleanup or source immutability gate failed")
        redact_evidence(self.evidence, self.token)
        cleanup_snapshot(self.root, self.project)
        cleanup_path = self.evidence / "cleanup.json"
        cleanup = json.loads(cleanup_path.read_text())
        cleanup["snapshot_removed"] = not (self.root / "checkout").exists()
        cleanup_path.write_text(json.dumps(cleanup, indent=2))
        print("PASS cleanup and source immutability", flush=True)


def safe_test_args(args, frontend=False):
    if not args:
        raise RuntimeError("explicit test paths required (or backend --smoke)")
    paths = []
    expression = False
    base = REPO / ("frontend" if frontend else "backend")
    for arg in args:
        if expression:
            if "\x00" in arg or "\n" in arg:
                raise RuntimeError("unsafe test expression")
            expression = False
            continue
        if arg in ("-k", "-m"):
            expression = True
            continue
        if arg in ("-q", "-v", "-vv", "-x", "--collect-only"):
            continue
        if arg.startswith("--maxfail=") and arg.split("=", 1)[1].isdigit():
            continue
        name = arg.split("::", 1)[0]
        target = (base / name).resolve()
        if (
            not name.startswith("src/" if frontend else "tests/")
            or "\x00" in name
            or "\n" in name
            or ".." in Path(name).parts
            or not target.is_relative_to(base)
            or not target.is_file()
        ):
            raise RuntimeError("unsafe or missing test file")
        paths.append(name)
    if not paths or expression:
        raise RuntimeError("explicit existing test files required")


def execute(mode, args):
    run = Run(args.dialect if hasattr(args, "dialect") else "mariadb")
    succeeded = False
    try:
        run.start()
        if mode == "backend":
            if args.tests == ["--smoke"]:
                # Uses real conftest, pytest-env, migrations and destructive fixture guards.
                probe = run.root / "checkout/backend/tests/test_phase34_smoke.py"
                probe.write_text(
                    "def test_disposable_target():\n"
                    "    from config.config_manager import ConfigManager\n"
                    "    from tools.phase34_target_guard import validate_target\n"
                    "    validate_target(resolved_url=ConfigManager.get_db_engine())\n"
                )
                run.exec(backend_command(["tests/test_phase34_smoke.py", "-q"]))
            else:
                run.exec(
                    backend_command(args.tests), timeout=getattr(args, "timeout", 180)
                )
        elif mode == "frontend":
            run.exec(frontend_command(args.tests), frontend=True)
        elif mode == "schema":
            for command in schema_commands():
                run.exec(command)
        elif mode == "reproduce":
            back = run.exec(
                backend_command([JOB_IDENTITY, "-q"], "rq-red"), check=False
            )
            front = run.exec(
                frontend_command([LIFECYCLE], "vue-red"), frontend=True, check=False
            )
            if back.returncode != 1 or front.returncode != 1:
                raise RuntimeError(
                    "RED rejected: both suites must fail assertions with exit 1"
                )
            proof = {
                "backend": expected_red(run.evidence / "rq-red.xml", RED_BACKEND),
                "frontend": expected_red(run.evidence / "vue-red.xml", RED_FRONTEND),
            }
            (run.evidence / "red-proof.json").write_text(json.dumps(proof, indent=2))
            print(json.dumps(proof), flush=True)
        elif mode == "quality":
            quality(run, args, REPO)
        succeeded = True
    finally:
        try:
            run.close()
        finally:
            if (run.evidence / "cleanup.json").exists():
                from phase34_evidence import retain_run

                gate = "schema:" + run.driver if mode == "schema" else mode
                retain_run(run, gate, succeeded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("guard-test")
    for mode in ("backend", "frontend"):
        item = sub.add_parser(mode)
        if mode == "backend":
            item.add_argument("--dialect", choices=tuple(SQL_IMAGES), default="mariadb")
            item.add_argument("--timeout", type=int, default=180)
        item.add_argument("--smoke", action="store_true")
        item.add_argument("tests", nargs=argparse.REMAINDER)
    schema = sub.add_parser("schema")
    schema.add_argument("--dialects", default="mariadb,mysql,postgresql")
    reproduce = sub.add_parser("reproduce")
    reproduce.add_argument("--expect-defects", action="store_true", required=True)
    quality_parser = sub.add_parser("quality")
    quality_parser.add_argument("--scope", choices=("setup-locales", "scan-locales"))
    quality_parser.add_argument("--locales")
    e2e = sub.add_parser("e2e")
    e2e.add_argument("--suite", choices=("lifecycle",), required=True)
    prod = sub.add_parser("production")
    prod.add_argument(
        "--mode", dest="deployment_mode", choices=("portainer",), required=True
    )
    prod.add_argument("--suite", choices=("fresh-install",), required=True)
    evidence = sub.add_parser("evidence")
    evidence.add_argument("--assert-complete", action="store_true", required=True)
    args = parser.parse_args()
    if getattr(args, "smoke", False):
        if args.mode != "backend" or args.tests:
            parser.error("--smoke is an exclusive backend option")
        args.tests = ["--smoke"]
    if args.mode == "backend" and not 1 <= args.timeout <= 900:
        parser.error("backend aggregate timeout must be 1..900 seconds")
    host_preflight()
    if args.mode == "guard-test":
        return subprocess.call(  # nosec B603, fixed unittest command
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "backend/tools/tests",
                "-p",
                "test_phase34*.py",
                "-v",
            ]
        )
    if args.mode in ("e2e", "production", "evidence"):
        helper, options = {
            "e2e": ("phase34_faults.py", ["--suite", "lifecycle"]),
            "production": (
                "phase34_portainer.py",
                ["--mode", "portainer", "--suite", "fresh-install"],
            ),
            "evidence": ("phase34_evidence.py", ["--assert-complete"]),
        }[args.mode]
        entry = Path(__file__).with_name(helper)
        if not entry.is_file():
            raise RuntimeError("34-08 gate requires missing helper: " + helper)
        # trunk-ignore(bandit/B603): Exact repository-owned helper and fixed options.
        return subprocess.call([sys.executable, str(entry), *options], cwd=REPO)
    if args.mode in ("backend", "frontend") and args.tests != ["--smoke"]:
        safe_test_args(args.tests, args.mode == "frontend")
    if args.mode == "schema":
        dialects = args.dialects.split(",")
        if set(dialects) != set(SQL_IMAGES) or len(dialects) != 3:
            raise RuntimeError(
                "schema gate requires mariadb,mysql,postgresql independently"
            )
        failures = []
        for driver in dialects:
            args.dialect = driver
            try:
                execute("schema", args)
            except (RuntimeError, subprocess.SubprocessError) as exc:
                failures.append(driver + ": " + str(exc))
        if failures:
            raise RuntimeError("; ".join(failures))
    else:
        execute(args.mode, args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print("BLOCKED:", error, file=sys.stderr)
        raise SystemExit(1) from error
