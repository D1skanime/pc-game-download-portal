"""Regenerate and verify the Phase 6 backend-owned frontend contract."""

# trunk-ignore-all(bandit/B108,bandit/B404,bandit/B603)

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType

PHASE6_PORT = 39006
NODE_IMAGE = "node:24-bookworm"
VOLUME_PREFIX = "romm-phase06-openapi-node-modules-"
UVICORN_SIGNATURE = "uvicorn main:app --host 127.0.0.1 --port 39006"

Command = Callable[
    [list[str]],
    subprocess.CompletedProcess[str],
]


def _command(
    args: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=check,
        capture_output=True,
        text=True,
    )


@dataclass
class Phase6ContractHarness:
    runner_container: str
    port: int
    checkout: Path
    node_volume: str = field(
        default_factory=lambda: f"{VOLUME_PREFIX}{uuid.uuid4().hex}"
    )
    command: Callable[..., subprocess.CompletedProcess[str]] = field(
        default=_command,
        repr=False,
    )
    sleeper: Callable[[float], None] = field(default=time.sleep, repr=False)
    readiness_attempts: int = 60
    uvicorn_pid: int | None = field(default=None, init=False)
    _volume_created: bool = field(default=False, init=False)
    _cleaned: bool = field(default=False, init=False)

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

    def preflight(self) -> None:
        result = self.command(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
        )
        actual_checkout = Path(result.stdout.strip()).resolve()
        expected_checkout = self.checkout.resolve()
        if actual_checkout != expected_checkout:
            raise RuntimeError(
                "Harness checkout does not match git top-level: "
                f"{expected_checkout} != {actual_checkout}"
            )

        result = self.command(
            ["docker", "inspect", self.runner_container],
            check=True,
        )
        inspection = json.loads(result.stdout)
        if len(inspection) != 1 or not inspection[0].get("State", {}).get("Running"):
            raise RuntimeError(
                f"Runner container {self.runner_container} is not running"
            )
        exact_mount = any(
            mount.get("Type") == "bind"
            and Path(str(mount.get("Source", ""))).resolve() == expected_checkout
            and mount.get("Destination") == "/app"
            for mount in inspection[0].get("Mounts", [])
        )
        if not exact_mount:
            raise RuntimeError(
                f"Runner {self.runner_container} does not bind the exact "
                f"checkout {expected_checkout} to /app"
            )

        port_probe = (
            "import socket; "
            "sock=socket.socket(); "
            f"sock.bind(('127.0.0.1', {self.port})); "
            "sock.close()"
        )
        result = self.command(
            [
                "docker",
                "exec",
                self.runner_container,
                "/app/.venv/bin/python",
                "-c",
                port_probe,
            ],
            check=False,
        )
        if result.returncode:
            raise RuntimeError(
                f"Loopback port {self.port} is occupied in " f"{self.runner_container}"
            )

        self.command(
            [
                "docker",
                "exec",
                self.runner_container,
                "test",
                "!",
                "-e",
                self.pid_file,
            ],
            check=True,
        )
        self.command(
            [
                "docker",
                "exec",
                self.runner_container,
                "test",
                "!",
                "-e",
                self.log_file,
            ],
            check=True,
        )

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
        launch_script = (
            "set -eu; "
            "cd /app/backend; "
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
                self.runner_container,
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
                self.runner_container,
                "cat",
                self.pid_file,
            ],
            check=True,
        )
        pid_text = result.stdout.strip()
        if not pid_text.isdecimal() or int(pid_text) <= 1:
            raise RuntimeError("Uvicorn did not record one valid PID")
        self.uvicorn_pid = int(pid_text)

    def _wait_until_ready(self) -> None:
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
                    self.runner_container,
                    "/app/.venv/bin/python",
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
                f"container:{self.runner_container}",
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
        try:
            if self.uvicorn_pid is not None:
                cleanup_script = (
                    'pid="$0"; '
                    f"pidfile={self.pid_file!r}; "
                    f"logfile={self.log_file!r}; "
                    f"signature={UVICORN_SIGNATURE!r}; "
                    'test -r "/proc/$pid/cmdline"; '
                    'tr "\\000" " " <"/proc/$pid/cmdline" '
                    '| grep -Fq "$signature"; '
                    'kill "$pid"; '
                    "for attempt in $(seq 1 50); do "
                    'kill -0 "$pid" 2>/dev/null || break; '
                    "sleep 0.1; "
                    "done; "
                    '! kill -0 "$pid" 2>/dev/null; '
                    'rm -f "$pidfile" "$logfile"'
                )
                result = self.command(
                    [
                        "docker",
                        "exec",
                        self.runner_container,
                        "sh",
                        "-lc",
                        cleanup_script,
                        str(self.uvicorn_pid),
                    ],
                    check=False,
                )
                if result.returncode:
                    cleanup_error = RuntimeError("Refused unsafe Uvicorn cleanup")
        finally:
            if self._volume_created:
                result = self.command(
                    ["docker", "volume", "rm", self.node_volume],
                    check=False,
                )
                self._volume_created = False
                if result.returncode and cleanup_error is None:
                    cleanup_error = RuntimeError(
                        f"Failed to remove owned volume {self.node_volume}"
                    )
        if cleanup_error is not None:
            raise cleanup_error

    def run(self) -> None:
        self.preflight()
        try:
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
