"""Regenerate and verify the Phase 6 backend-owned frontend contract."""

# trunk-ignore-all(bandit/B108,bandit/B404,bandit/B603)

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import Any

PHASE6_PORT = 39006
NODE_IMAGE = "node:24-bookworm"
VOLUME_PREFIX = "romm-phase06-openapi-node-modules-"
APPROVED_SOURCE_IMAGE_TAG = "romm-romm-dev"
APPROVED_NETWORK = "romm_default"
OWNERSHIP_LABEL = "io.romm.phase6.contract"
RUNNER_ENV_ALLOWLIST = (
    "DB_HOST",
    "DB_NAME",
    "DB_PASSWD",
    "DB_PORT",
    "DB_USER",
    "REDIS_DB",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_SSL",
    "ROMM_BASE_PATH",
)

Command = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _command(
    args: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=check,
        capture_output=True,
        text=True,
    )


def _inspection(stdout: str, subject: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        raise RuntimeError(f"{subject} inspection was malformed") from None
    if not isinstance(payload, list) or len(payload) != 1:
        raise RuntimeError(f"{subject} inspection was ambiguous")
    inspection = payload[0]
    if not isinstance(inspection, dict):
        raise RuntimeError(f"{subject} inspection was malformed")
    return inspection


def _environment(entries: object) -> dict[str, str]:
    if not isinstance(entries, list):
        return {}
    environment: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, str) or "=" not in entry:
            continue
        name, value = entry.split("=", 1)
        environment[name] = value
    return environment


@dataclass
class Phase6ContractHarness:
    runner_container: str
    port: int
    checkout: Path
    node_volume: str = field(
        default_factory=lambda: f"{VOLUME_PREFIX}{uuid.uuid4().hex}"
    )
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex)
    command: Callable[..., subprocess.CompletedProcess[str]] = field(
        default=_command,
        repr=False,
    )
    sleeper: Callable[[float], None] = field(default=time.sleep, repr=False)
    readiness_attempts: int = 60
    uvicorn_pid: int | None = field(default=None, init=False)
    runner_container_id: str | None = field(default=None, init=False)
    _runner_env: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _env_file: Path | None = field(default=None, init=False, repr=False)
    _volume_created: bool = field(default=False, init=False)
    _cleaned: bool = field(default=False, init=False)

    @property
    def runner_name(self) -> str:
        return f"romm-phase06-contract-{self.nonce}"

    @property
    def pid_file(self) -> str:
        return f"/tmp/romm-phase06-openapi-{self.port}.pid"

    @property
    def log_file(self) -> str:
        return f"/tmp/romm-phase06-openapi-{self.port}.log"

    @property
    def checkout_owner(self) -> str:
        checkout_stat = self.checkout.stat()
        return f"{checkout_stat.st_uid}:{checkout_stat.st_gid}"

    def preflight(self) -> tuple[str, dict[str, str]]:
        result = self.command(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
        )
        actual_checkout = Path(result.stdout.strip()).resolve()
        expected_checkout = self.checkout.resolve()
        if actual_checkout != expected_checkout:
            raise RuntimeError("Harness checkout does not match git top-level")

        result = self.command(
            ["docker", "inspect", self.runner_container],
            check=True,
        )
        source = _inspection(result.stdout, "Approved source container")
        config = source.get("Config")
        networks = source.get("NetworkSettings")
        if not isinstance(config, dict) or not isinstance(networks, dict):
            raise RuntimeError("Approved source container configuration is incomplete")
        if config.get("Image") != APPROVED_SOURCE_IMAGE_TAG:
            raise RuntimeError("Approved source container image tag is invalid")
        network_map = networks.get("Networks")
        if not isinstance(network_map, dict) or set(network_map) != {APPROVED_NETWORK}:
            raise RuntimeError("Approved source container network is invalid")
        image_id = source.get("Image")
        if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
            raise RuntimeError("Approved source container image ID is invalid")

        source_environment = _environment(config.get("Env"))
        if any(
            not source_environment.get(name)
            or "\n" in source_environment[name]
            or "\r" in source_environment[name]
            for name in RUNNER_ENV_ALLOWLIST
        ):
            raise RuntimeError("Approved source environment is incomplete")
        return image_id, {
            name: source_environment[name] for name in RUNNER_ENV_ALLOWLIST
        }

    def _write_env_file(self, environment: dict[str, str]) -> None:
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f"{self.runner_name}-",
            suffix=".env",
        )
        self._env_file = Path(raw_path)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as env_file:
                for name in RUNNER_ENV_ALLOWLIST:
                    env_file.write(f"{name}={environment[name]}\n")
        except BaseException:
            os.close(descriptor)
            raise

    def _create_runner(self, image_id: str) -> None:
        if self._env_file is None:
            raise RuntimeError("Runner environment was not prepared")
        result = self.command(
            [
                "docker",
                "create",
                "--name",
                self.runner_name,
                "--label",
                f"{OWNERSHIP_LABEL}={self.nonce}",
                "--entrypoint",
                "/bin/sleep",
                "--env-file",
                str(self._env_file),
                "--network",
                APPROVED_NETWORK,
                "--user",
                "1000:1000",
                "--mount",
                f"type=bind,src={self.checkout.resolve()},dst=/repo,readonly",
                "--workdir",
                "/repo/backend",
                image_id,
                "infinity",
            ],
            check=True,
        )
        container_id = result.stdout.strip()
        if len(container_id) != 64 or any(
            character not in "0123456789abcdef" for character in container_id
        ):
            raise RuntimeError("Docker did not return one full runner container ID")
        self.runner_container_id = container_id

    def _inspect_runner(self, image_id: str) -> None:
        if self.runner_container_id is None:
            raise RuntimeError("Runner container was not created")
        result = self.command(
            ["docker", "inspect", self.runner_container_id],
            check=True,
        )
        runner = _inspection(result.stdout, "Owned runner container")
        config = runner.get("Config")
        host_config = runner.get("HostConfig")
        mounts = runner.get("Mounts")
        networks = runner.get("NetworkSettings", {}).get("Networks")
        if (
            not isinstance(config, dict)
            or not isinstance(host_config, dict)
            or not isinstance(mounts, list)
            or not isinstance(networks, dict)
        ):
            raise RuntimeError("Owned runner configuration is incomplete")

        exact_mount = [
            mount
            for mount in mounts
            if isinstance(mount, dict)
            and mount.get("Type") == "bind"
            and Path(str(mount.get("Source", ""))).resolve() == self.checkout.resolve()
            and mount.get("Destination") == "/repo"
            and mount.get("RW") is False
        ]
        labels = config.get("Labels")
        environment = _environment(config.get("Env"))
        if (
            runner.get("Id") != self.runner_container_id
            or runner.get("Name") != f"/{self.runner_name}"
            or runner.get("Image") != image_id
            or config.get("User") != "1000:1000"
            or config.get("WorkingDir") != "/repo/backend"
            or not isinstance(labels, dict)
            or labels.get(OWNERSHIP_LABEL) != self.nonce
            or config.get("Entrypoint") != ["/bin/sleep"]
            or config.get("Cmd") != ["infinity"]
            or host_config.get("NetworkMode") != APPROVED_NETWORK
            or host_config.get("PortBindings") not in ({}, None)
            or set(networks) != {APPROVED_NETWORK}
            or len(exact_mount) != 1
            or len(mounts) != 1
            or environment != self._runner_env
        ):
            raise RuntimeError("Owned runner configuration did not match")

    def _start_runner(self) -> None:
        if self.runner_container_id is None:
            raise RuntimeError("Runner container was not created")
        self.command(["docker", "start", self.runner_container_id], check=True)

    def _create_volume(self) -> None:
        self.command(
            ["docker", "volume", "create", self.node_volume],
            check=True,
        )
        self._volume_created = True
        self.command(
            [
                "docker",
                "run",
                "--rm",
                "--mount",
                f"type=volume,src={self.node_volume},dst=/app/node_modules",
                NODE_IMAGE,
                "chown",
                self.checkout_owner,
                "/app/node_modules",
            ],
            check=True,
        )

    def _launch_uvicorn(self) -> None:
        if self.runner_container_id is None:
            raise RuntimeError("Runner container was not created")
        launch_script = (
            "set -eu; "
            "cd /repo/backend; "
            "ROMM_AUTH_SECRET_KEY=phase06-openapi-generation-only "
            "nohup uv run uvicorn main:app "
            f"--host 127.0.0.1 --port {self.port} --no-access-log "
            f">{self.log_file} 2>&1 & "
            "api_pid=$!; "
            f"printf '%s\\n' \"$api_pid\" >{self.pid_file}; "
            'kill -0 "$api_pid"'
        )
        self.command(
            [
                "docker",
                "exec",
                self.runner_container_id,
                "sh",
                "-lc",
                launch_script,
            ],
            check=True,
        )
        result = self.command(
            [
                "docker",
                "exec",
                self.runner_container_id,
                "cat",
                self.pid_file,
            ],
            check=False,
        )
        pid_text = result.stdout.strip() if result.returncode == 0 else ""
        if not pid_text.isdecimal() or int(pid_text) <= 1:
            raise RuntimeError("Uvicorn did not record one valid PID")
        self.uvicorn_pid = int(pid_text)

        signature_check = (
            'pid="$0"; '
            'test -r "/proc/$pid/cmdline"; '
            'tr "\\000" " " <"/proc/$pid/cmdline" '
            '| grep -Fq "uvicorn main:app --host 127.0.0.1 '
            f'--port {self.port}"'
        )
        result = self.command(
            [
                "docker",
                "exec",
                self.runner_container_id,
                "sh",
                "-lc",
                signature_check,
                str(self.uvicorn_pid),
            ],
            check=False,
        )
        if result.returncode:
            raise RuntimeError("Uvicorn PID signature did not match")

    def _wait_until_ready(self) -> None:
        if self.runner_container_id is None:
            raise RuntimeError("Runner container was not created")
        readiness_probe = (
            "import urllib.request; "
            "response=urllib.request.urlopen("
            f"'http://127.0.0.1:{self.port}/openapi.json', timeout=1"
            "); "
            "raise SystemExit(0 if response.status == 200 else 1)"
        )
        for _ in range(self.readiness_attempts):
            result = self.command(
                [
                    "docker",
                    "exec",
                    self.runner_container_id,
                    "/repo/.venv/bin/python",
                    "-c",
                    readiness_probe,
                ],
                check=False,
            )
            if result.returncode == 0:
                return
            self.sleeper(1)
        raise RuntimeError(
            f"OpenAPI server did not become ready after "
            f"{self.readiness_attempts} attempts"
        )

    def _run_generation(self) -> None:
        if self.runner_container_id is None:
            raise RuntimeError("Runner container was not created")
        openapi_command = (
            "./node_modules/.bin/openapi "
            f"--input http://127.0.0.1:{self.port}/openapi.json "
            "--output ./src/__generated__ --client axios --useOptions "
            "--useUnionTypes --exportServices false --exportSchemas false "
            "--exportCore false"
        )
        generation_script = (
            f"npm ci && {openapi_command} && "
            "NODE_OPTIONS=--max-old-space-size=4096 npm run typecheck"
        )
        self.command(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                f"container:{self.runner_container_id}",
                "--user",
                self.checkout_owner,
                "--mount",
                f"type=bind,src={self.checkout / 'frontend'},dst=/app",
                "--mount",
                f"type=volume,src={self.node_volume},dst=/app/node_modules",
                "-w",
                "/app",
                NODE_IMAGE,
                "sh",
                "-lc",
                generation_script,
            ],
            check=True,
        )

    def cleanup(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
        cleanup_error: RuntimeError | None = None
        if self.runner_container_id is not None:
            result = self.command(
                ["docker", "rm", "-f", self.runner_container_id],
                check=False,
            )
            if result.returncode:
                cleanup_error = RuntimeError("Failed to remove owned runner container")
        if self._volume_created:
            result = self.command(
                ["docker", "volume", "rm", self.node_volume],
                check=False,
            )
            self._volume_created = False
            if result.returncode and cleanup_error is None:
                cleanup_error = RuntimeError("Failed to remove owned Node volume")
        if self._env_file is not None:
            try:
                self._env_file.unlink(missing_ok=True)
            except OSError:
                if cleanup_error is None:
                    cleanup_error = RuntimeError(
                        "Failed to remove owned runner environment"
                    )
        if cleanup_error is not None:
            raise cleanup_error

    def run(self) -> None:
        try:
            image_id, environment = self.preflight()
            self._runner_env = environment
            self._write_env_file(environment)
            self._create_runner(image_id)
            self._inspect_runner(image_id)
            self._start_runner()
            self._create_volume()
            self._launch_uvicorn()
            self._wait_until_ready()
            self._run_generation()
        finally:
            self.cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the Phase 6 generated frontend contract"
    )
    parser.add_argument("--runner-container", required=True)
    parser.add_argument(
        "--port",
        type=int,
        choices=[PHASE6_PORT],
        default=PHASE6_PORT,
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checkout = Path(__file__).resolve().parents[2]
    harness = Phase6ContractHarness(
        runner_container=args.runner_container,
        port=args.port,
        checkout=checkout,
    )

    def stop(signum: int, _frame: FrameType | None) -> None:
        harness.cleanup()
        raise SystemExit(128 + signum)

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, stop)
    harness.run()


if __name__ == "__main__":
    main()
