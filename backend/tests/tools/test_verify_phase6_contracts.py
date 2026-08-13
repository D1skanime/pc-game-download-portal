import json
import subprocess
from pathlib import Path

import pytest
from tools import verify_phase6_contracts as verifier


class FakeCommand:
    def __init__(
        self,
        checkout: Path,
        *,
        mounts: list[dict[str, str]] | None = None,
        port_available: bool = True,
        ready_after: int = 1,
    ) -> None:
        self.checkout = checkout
        self.mounts = mounts or [
            {
                "Type": "bind",
                "Source": str(checkout),
                "Destination": "/app",
            }
        ]
        self.port_available = port_available
        self.ready_after = ready_after
        self.readiness_attempts = 0
        self.calls: list[list[str]] = []

    def __call__(
        self, args: list[str], *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        returncode = 0
        stdout = ""
        if args[:3] == ["git", "rev-parse", "--show-toplevel"]:
            stdout = f"{self.checkout}\n"
        elif args[:2] == ["docker", "inspect"]:
            stdout = json.dumps(
                [
                    {
                        "State": {"Running": True},
                        "Mounts": self.mounts,
                    }
                ]
            )
        elif any("socket.socket" in part for part in args):
            returncode = 0 if self.port_available else 1
        elif args[:3] == ["docker", "exec", "romm-dev"] and args[-2:] == [
            "cat",
            "/tmp/romm-phase06-openapi-39006.pid",
        ]:
            stdout = "4242\n"
        elif args[:3] == ["docker", "exec", "romm-dev"] and any(
            "http://127.0.0.1:39006/openapi.json" in part for part in args
        ):
            self.readiness_attempts += 1
            returncode = 0 if self.readiness_attempts >= self.ready_after else 1

        result = subprocess.CompletedProcess(args, returncode, stdout, "")
        if check and returncode:
            raise subprocess.CalledProcessError(returncode, args)
        return result


def _harness(
    checkout: Path,
    command: FakeCommand,
) -> verifier.Phase6ContractHarness:
    return verifier.Phase6ContractHarness(
        runner_container="romm-dev",
        port=39006,
        checkout=checkout,
        node_volume="romm-phase06-openapi-node-modules-test",
        command=command,
        sleeper=lambda _: None,
        readiness_attempts=3,
    )


def test_parser_locks_generation_to_phase6_loopback_port() -> None:
    parser = verifier.build_parser()
    args = parser.parse_args(["--runner-container", "romm-dev"])
    assert args.port == 39006
    with pytest.raises(SystemExit):
        parser.parse_args(["--runner-container", "romm-dev", "--port", "3000"])


def test_preflight_rejects_runner_without_exact_checkout_mount(
    tmp_path: Path,
) -> None:
    command = FakeCommand(
        tmp_path,
        mounts=[
            {
                "Type": "bind",
                "Source": str(tmp_path / "backend"),
                "Destination": "/app/backend",
            }
        ],
    )

    with pytest.raises(RuntimeError, match="exact checkout"):
        _harness(tmp_path, command).preflight()


def test_preflight_rejects_occupied_runner_loopback_port(
    tmp_path: Path,
) -> None:
    command = FakeCommand(tmp_path, port_available=False)

    with pytest.raises(RuntimeError, match="39006.*occupied"):
        _harness(tmp_path, command).preflight()


def test_harness_records_one_pid_and_runs_exact_contract_commands(
    tmp_path: Path,
) -> None:
    command = FakeCommand(tmp_path, ready_after=2)
    harness = _harness(tmp_path, command)

    harness.run()

    launch = next(
        call
        for call in command.calls
        if call[:3] == ["docker", "exec", "romm-dev"]
        and any("uvicorn main:app" in part for part in call)
    )
    launch_script = launch[-1]
    assert "cd /app/backend" in launch_script
    assert (
        "uv run uvicorn main:app --host 127.0.0.1 --port 39006 " "--no-access-log"
    ) in launch_script
    assert "/tmp/romm-phase06-openapi-39006.pid" in launch_script
    assert "/tmp/romm-phase06-openapi-39006.log" in launch_script

    pid_reads = [
        call
        for call in command.calls
        if call[-2:] == ["cat", "/tmp/romm-phase06-openapi-39006.pid"]
    ]
    assert len(pid_reads) == 1
    assert harness.uvicorn_pid == 4242
    assert command.readiness_attempts == 2

    node = next(
        call
        for call in command.calls
        if call[:3] == ["docker", "run", "--rm"] and "--network" in call
    )
    assert ["--network", "container:romm-dev"] == node[3:5]
    assert [
        "--user",
        f"{tmp_path.stat().st_uid}:{tmp_path.stat().st_gid}",
    ] == node[5:7]
    volume_init = next(
        call
        for call in command.calls
        if call[:3] == ["docker", "run", "--rm"] and "chown" in call
    )
    assert "romm-phase06-openapi-node-modules-test" in volume_init[4]
    assert f"{tmp_path.stat().st_uid}:{tmp_path.stat().st_gid}" in volume_init
    assert f"type=bind,src={tmp_path / 'frontend'},dst=/app" in node
    assert (
        "type=volume,src=romm-phase06-openapi-node-modules-test,"
        "dst=/app/node_modules" in node
    )
    assert "node:24-bookworm" in node
    generation = node[-1]
    assert (
        "./node_modules/.bin/openapi "
        "--input http://127.0.0.1:39006/openapi.json "
        "--output ./src/__generated__ --client axios --useOptions "
        "--useUnionTypes --exportServices false --exportSchemas false "
        "--exportCore false"
    ) in generation
    assert generation.endswith("npm run typecheck")


def test_failure_cleanup_targets_only_recorded_pid_files_and_owned_volume(
    tmp_path: Path,
) -> None:
    command = FakeCommand(tmp_path, ready_after=99)
    harness = _harness(tmp_path, command)

    with pytest.raises(RuntimeError, match="did not become ready"):
        harness.run()

    cleanup = next(
        call
        for call in command.calls
        if call[:3] == ["docker", "exec", "romm-dev"]
        and any("4242" == part for part in call)
    )
    assert "4242" in cleanup
    cleanup_script = cleanup[-2]
    assert "/proc/$pid/cmdline" in cleanup_script
    assert "uvicorn main:app --host 127.0.0.1 --port 39006" in cleanup_script
    assert "/tmp/romm-phase06-openapi-39006.pid" in cleanup_script
    assert "/tmp/romm-phase06-openapi-39006.log" in cleanup_script
