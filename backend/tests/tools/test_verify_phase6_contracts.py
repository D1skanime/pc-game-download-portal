import json
import stat
import subprocess
from pathlib import Path

import pytest
from tools import verify_phase6_contracts as verifier

ENV_VALUES = {
    name: f"value-{index}"
    for index, name in enumerate(verifier.RUNNER_ENV_ALLOWLIST, start=1)
}
IMAGE_ENV_VALUES = {"PATH": "/usr/bin", "NVM_DIR": "/root/.nvm"}
SOURCE_IMAGE_ID = "sha256:" + "b" * 64
RUNNER_ID = "a" * 64


class FailOnceUnlink:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def __call__(self, path: Path) -> None:
        self.calls.append(path)
        if len(self.calls) == 1:
            raise OSError(f"failure {ENV_VALUES['DB_PASSWD']}")
        path.unlink(missing_ok=True)


class FakeCommand:
    def __init__(
        self,
        checkout: Path,
        *,
        source_overrides: dict[str, object] | None = None,
        runner_overrides: dict[str, object] | None = None,
        pid_state: str | None = "4242\n",
        pid_signature_valid: bool = True,
        ready_after: int = 1,
        fail_action: str | None = None,
        fail_actions_once: set[str] | None = None,
        already_absent_actions: set[str] | None = None,
    ) -> None:
        self.checkout = checkout
        self.source_overrides = source_overrides or {}
        self.runner_overrides = runner_overrides or {}
        self.pid_state = pid_state
        self.pid_signature_valid = pid_signature_valid
        self.ready_after = ready_after
        self.fail_action = fail_action
        self.fail_actions_once = fail_actions_once or set()
        self.already_absent_actions = already_absent_actions or set()
        self.action_calls: dict[str, int] = {}
        self.readiness_attempts = 0
        self.calls: list[list[str]] = []
        self.env_file: Path | None = None
        self.env_file_mode: int | None = None
        self.runner_name = ""
        self.nonce = ""

    def _source_inspection(self) -> dict[str, object]:
        inspection: dict[str, object] = {
            "Id": "source-id",
            "Image": SOURCE_IMAGE_ID,
            "Config": {
                "Image": verifier.APPROVED_SOURCE_IMAGE_TAG,
                "Env": [f"{name}={value}" for name, value in ENV_VALUES.items()],
            },
            "NetworkSettings": {"Networks": {verifier.APPROVED_NETWORK: {}}},
        }
        for key, value in self.source_overrides.items():
            inspection[key] = value
        return inspection

    def _runner_inspection(self) -> dict[str, object]:
        env_values = dict(IMAGE_ENV_VALUES)
        if self.env_file is not None:
            for line in self.env_file.read_text().splitlines():
                if line:
                    env_name, env_value = line.split("=", 1)
                    env_values[env_name] = env_value
        inspection: dict[str, object] = {
            "Id": RUNNER_ID,
            "Name": f"/{self.runner_name}",
            "Image": SOURCE_IMAGE_ID,
            "Config": {
                "User": "1000:1000",
                "WorkingDir": "/repo/backend",
                "Labels": {verifier.OWNERSHIP_LABEL: self.nonce},
                "Entrypoint": ["/bin/sleep"],
                "Cmd": ["infinity"],
                "Env": [f"{name}={value}" for name, value in env_values.items()],
            },
            "HostConfig": {
                "NetworkMode": verifier.APPROVED_NETWORK,
                "PortBindings": {},
            },
            "NetworkSettings": {"Networks": {verifier.APPROVED_NETWORK: {}}},
            "Mounts": [
                {
                    "Type": "bind",
                    "Source": str(self.checkout),
                    "Destination": "/repo",
                    "RW": False,
                }
            ],
        }
        for key, value in self.runner_overrides.items():
            inspection[key] = value
        return inspection

    def _action(self, args: list[str]) -> str:
        if args[:3] == ["docker", "inspect", "romm-dev"]:
            return "source_inspect"
        if args[:3] == ["docker", "image", "inspect"]:
            return "image_inspect"
        if args[:2] == ["docker", "create"]:
            return "create"
        if args[:2] == ["docker", "inspect"] and args[-1] == RUNNER_ID:
            return "runner_inspect"
        if args[:2] == ["docker", "start"]:
            return "start"
        if args[:3] == ["docker", "exec", RUNNER_ID] and any(
            "/proc/$pid/cmdline" in part for part in args
        ):
            return "pid_signature"
        if args[:3] == ["docker", "exec", RUNNER_ID] and any(
            "uvicorn main:app" in part for part in args
        ):
            return "launch"
        if args[:3] == ["docker", "exec", RUNNER_ID] and args[-2:] == [
            "cat",
            f"/tmp/romm-phase06-openapi-{verifier.PHASE6_PORT}.pid",
        ]:
            return "pid_read"
        if args[:3] == ["docker", "exec", RUNNER_ID] and any(
            "openapi.json" in part for part in args
        ):
            return "readiness"
        if args[:3] == ["docker", "exec", RUNNER_ID] and "tail" in args:
            return "log_read"
        if args[:3] == ["docker", "rm", "-f"]:
            return "remove"
        if args[:3] == ["docker", "volume", "create"]:
            return "volume_create"
        if args[:3] == ["docker", "volume", "rm"]:
            return "volume_remove"
        return "other"

    def __call__(
        self, args: list[str], *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        action = self._action(args)
        self.action_calls[action] = self.action_calls.get(action, 0) + 1
        if action in self.fail_actions_once and self.action_calls[action] == 1:
            result = subprocess.CompletedProcess(
                args, 1, "", f"failure {ENV_VALUES['DB_PASSWD']}"
            )
            if check:
                raise subprocess.CalledProcessError(
                    1, args, output=result.stdout, stderr=result.stderr
                )
            return result
        if action in self.already_absent_actions:
            subject = "container" if action == "remove" else "volume"
            return subprocess.CompletedProcess(
                args,
                1,
                "",
                f"Error response from daemon: No such {subject}: exact-id",
            )
        if action == "create":
            self.runner_name = args[args.index("--name") + 1]
            label = args[args.index("--label") + 1]
            self.nonce = label.split("=", 1)[1]
            self.env_file = Path(args[args.index("--env-file") + 1])
        if action == self.fail_action:
            result = subprocess.CompletedProcess(
                args, 1, "", f"failure {ENV_VALUES['DB_PASSWD']}"
            )
            if check:
                raise subprocess.CalledProcessError(
                    1, args, output=result.stdout, stderr=result.stderr
                )
            return result

        returncode = 0
        stdout = ""
        if args[:3] == ["git", "rev-parse", "--show-toplevel"]:
            stdout = f"{self.checkout}\n"
        elif action == "source_inspect":
            stdout = json.dumps([self._source_inspection()])
        elif action == "image_inspect":
            stdout = json.dumps(
                [
                    {
                        "Config": {
                            "Env": [
                                f"{name}={value}"
                                for name, value in IMAGE_ENV_VALUES.items()
                            ]
                        }
                    }
                ]
            )
        elif action == "create":
            assert self.env_file is not None
            self.env_file_mode = stat.S_IMODE(self.env_file.stat().st_mode)
            stdout = f"{RUNNER_ID}\n"
        elif action == "runner_inspect":
            stdout = json.dumps([self._runner_inspection()])
        elif action == "pid_read":
            if self.pid_state is None:
                returncode = 1
            else:
                stdout = self.pid_state
        elif action == "pid_signature":
            returncode = 0 if self.pid_signature_valid else 1
        elif action == "readiness":
            self.readiness_attempts += 1
            returncode = 0 if self.readiness_attempts >= self.ready_after else 1
        elif action == "log_read":
            stdout = f"startup failed with {ENV_VALUES['DB_PASSWD']}\n"

        result = subprocess.CompletedProcess(args, returncode, stdout, "")
        if check and returncode:
            raise subprocess.CalledProcessError(returncode, args)
        return result


def _harness(
    checkout: Path,
    command: FakeCommand,
    unlinker=None,
) -> verifier.Phase6ContractHarness:
    kwargs = dict(
        runner_container="romm-dev",
        port=verifier.PHASE6_PORT,
        checkout=checkout,
        node_volume="romm-phase06-openapi-node-modules-test",
        nonce="testnonce",
        command=command,
        sleeper=lambda _: None,
        readiness_attempts=3,
    )
    if unlinker is not None:
        kwargs["unlinker"] = unlinker
    return verifier.Phase6ContractHarness(**kwargs)


def _calls(command: FakeCommand, prefix: list[str]) -> list[list[str]]:
    return [call for call in command.calls if call[: len(prefix)] == prefix]


def test_parser_locks_generation_to_phase6_loopback_port() -> None:
    checkout = Path(verifier.__file__).resolve().parents[2]
    required = [
        "--source-container",
        "romm-dev",
        "--checkout",
        str(checkout),
        "--expected-image",
        verifier.APPROVED_SOURCE_IMAGE_TAG,
        "--network",
        verifier.APPROVED_NETWORK,
        "--user",
        "1000:1000",
        "--entrypoint",
        "/bin/sleep",
        "--command",
        "infinity",
        "--env-allowlist",
        ",".join(verifier.RUNNER_ENV_ALLOWLIST),
    ]
    parser = verifier.build_parser()
    args = parser.parse_args(required)
    assert args.port == verifier.PHASE6_PORT
    assert args.source_container == "romm-dev"
    assert args.checkout == checkout
    with pytest.raises(SystemExit):
        parser.parse_args([*required, "--port", "3000"])
    for index in range(0, len(required), 2):
        with pytest.raises(SystemExit):
            parser.parse_args(required[:index] + required[index + 2 :])
    with pytest.raises(SystemExit):
        parser.parse_args([*required[:-1], "DB_HOST"])


def test_harness_creates_inspects_and_removes_exact_owned_runner(
    tmp_path: Path,
) -> None:
    command = FakeCommand(tmp_path, ready_after=2)
    harness = _harness(tmp_path, command)

    harness.run()

    create = _calls(command, ["docker", "create"])[0]
    assert create[create.index("--name") + 1] == "romm-phase06-contract-testnonce"
    assert create[create.index("--label") + 1] == (
        f"{verifier.OWNERSHIP_LABEL}=testnonce"
    )
    assert create[create.index("--entrypoint") + 1] == "/bin/sleep"
    assert create[create.index("--network") + 1] == verifier.APPROVED_NETWORK
    assert create[create.index("--user") + 1] == "1000:1000"
    assert (
        f"type=bind,src={tmp_path},dst=/repo,readonly"
        == create[create.index("--mount") + 1]
    )
    assert create[create.index("--workdir") + 1] == "/repo/backend"
    assert create[-2:] == [SOURCE_IMAGE_ID, "infinity"]
    assert "-p" not in create and "--publish" not in create
    assert command.env_file_mode == 0o600
    assert command.env_file is not None and not command.env_file.exists()
    assert harness.runner_container_id == RUNNER_ID
    assert command.readiness_attempts == 2
    launch = next(
        call
        for call in _calls(command, ["docker", "exec", RUNNER_ID])
        if any("uvicorn main:app" in argument for argument in call)
    )
    assert "UV_CACHE_DIR=/tmp/romm-phase06-uv-cache-testnonce" in launch[-1]
    runtime_setup = next(
        call
        for call in command.calls
        if call[:6] == ["docker", "exec", "--user", "0", RUNNER_ID, "sh"]
    )
    assert "chmod 0711 /root" in runtime_setup[-1]
    assert "readlink -m" in runtime_setup[-1]
    assert 'case "$runtime_path" in /app/*)' in runtime_setup[-1]
    assert 'test ! -L "$ROMM_BASE_PATH"' in runtime_setup[-1]
    assert 'chown 1000:1000 -- "$runtime_path"' in runtime_setup[-1]
    assert [
        "docker",
        "exec",
        RUNNER_ID,
        "/app/.venv/bin/python",
        "--version",
    ] in command.calls

    inspect_index = command.calls.index(["docker", "inspect", RUNNER_ID])
    start_index = command.calls.index(["docker", "start", RUNNER_ID])
    assert inspect_index < start_index
    assert _calls(command, ["docker", "rm", "-f"]) == [
        ["docker", "rm", "-f", RUNNER_ID]
    ]
    node = next(
        call
        for call in command.calls
        if call[:3] == ["docker", "run", "--rm"] and "--network" in call
    )
    assert node[node.index("--network") + 1] == f"container:{RUNNER_ID}"


@pytest.mark.parametrize(
    "source_overrides",
    (
        {"Config": {"Image": "wrong", "Env": []}},
        {"NetworkSettings": {"Networks": {"wrong": {}}}},
        {
            "Config": {
                "Image": verifier.APPROVED_SOURCE_IMAGE_TAG,
                "Env": [
                    f"{name}={value}"
                    for name, value in ENV_VALUES.items()
                    if name != "DB_PASSWD"
                ],
            }
        },
    ),
)
def test_source_preflight_fails_closed_without_secret_disclosure(
    tmp_path: Path,
    source_overrides: dict[str, object],
) -> None:
    command = FakeCommand(tmp_path, source_overrides=source_overrides)

    with pytest.raises(RuntimeError) as error:
        _harness(tmp_path, command).run()

    assert ENV_VALUES["DB_PASSWD"] not in str(error.value)
    assert not _calls(command, ["docker", "create"])


@pytest.mark.parametrize(
    "runner_overrides",
    (
        {"Image": "sha256:" + "c" * 64},
        {"Name": "/reused-name"},
        {"HostConfig": {"NetworkMode": "wrong", "PortBindings": {}}},
        {"Config": {"User": "0:0"}},
        {
            "Mounts": [
                {
                    "Type": "bind",
                    "Source": "/wrong",
                    "Destination": "/repo",
                    "RW": False,
                }
            ]
        },
        {"Config": {"WorkingDir": "/wrong"}},
        {
            "HostConfig": {
                "NetworkMode": verifier.APPROVED_NETWORK,
                "PortBindings": {"39006/tcp": [{}]},
            }
        },
        {"Config": {"Entrypoint": ["/bin/sh"]}},
        {"Config": {"Cmd": ["wrong"]}},
        {"Config": {"Env": ["DB_HOST=changed"]}},
    ),
)
def test_runner_mismatch_fails_before_start_and_cleans_exact_id(
    tmp_path: Path,
    runner_overrides: dict[str, object],
) -> None:
    command = FakeCommand(tmp_path, runner_overrides=runner_overrides)

    with pytest.raises(RuntimeError):
        _harness(tmp_path, command).run()

    assert not _calls(command, ["docker", "start"])
    assert _calls(command, ["docker", "rm", "-f"]) == [
        ["docker", "rm", "-f", RUNNER_ID]
    ]
    assert command.env_file is not None and not command.env_file.exists()


@pytest.mark.parametrize("pid_state", (None, "", "not-a-pid\n", "1\n", "4 2\n"))
def test_missing_or_malformed_pid_never_blocks_exact_container_cleanup(
    tmp_path: Path,
    pid_state: str | None,
) -> None:
    command = FakeCommand(tmp_path, pid_state=pid_state)

    with pytest.raises(RuntimeError, match="valid PID"):
        _harness(tmp_path, command).run()

    assert _calls(command, ["docker", "rm", "-f"]) == [
        ["docker", "rm", "-f", RUNNER_ID]
    ]


def test_reused_pid_signature_mismatch_cleans_exact_container(
    tmp_path: Path,
) -> None:
    command = FakeCommand(tmp_path, pid_signature_valid=False)

    with pytest.raises(RuntimeError, match="signature"):
        _harness(tmp_path, command).run()

    assert _calls(command, ["docker", "rm", "-f"]) == [
        ["docker", "rm", "-f", RUNNER_ID]
    ]


def test_readiness_failure_reports_only_redacted_log_and_cleans(
    tmp_path: Path,
) -> None:
    command = FakeCommand(tmp_path, ready_after=99)

    with pytest.raises(RuntimeError, match="redacted log tail") as error:
        _harness(tmp_path, command).run()

    assert ENV_VALUES["DB_PASSWD"] not in str(error.value)
    assert "<redacted>" in str(error.value)
    assert _calls(command, ["docker", "rm", "-f"]) == [
        ["docker", "rm", "-f", RUNNER_ID]
    ]


@pytest.mark.parametrize("fail_action", ("create", "start", "launch"))
def test_command_failures_clean_only_owned_resources(
    tmp_path: Path,
    fail_action: str,
) -> None:
    command = FakeCommand(tmp_path, fail_action=fail_action)

    with pytest.raises((RuntimeError, subprocess.CalledProcessError)) as error:
        _harness(tmp_path, command).run()

    assert ENV_VALUES["DB_PASSWD"] not in str(error.value)
    removals = _calls(command, ["docker", "rm", "-f"])
    assert removals == (
        [] if fail_action == "create" else [["docker", "rm", "-f", RUNNER_ID]]
    )
    assert command.env_file is not None and not command.env_file.exists()


def test_cleanup_is_idempotent_and_never_uses_name_pid_or_label_lookup(
    tmp_path: Path,
) -> None:
    command = FakeCommand(tmp_path)
    harness = _harness(tmp_path, command)
    harness.run()

    harness.cleanup()
    harness.cleanup()

    assert _calls(command, ["docker", "rm", "-f"]) == [
        ["docker", "rm", "-f", RUNNER_ID]
    ]
    assert not any(
        call[:2] == ["docker", "ps"] or "kill" in call for call in command.calls
    )


@pytest.mark.parametrize(
    ("failed_action", "expected_after_first", "expected_calls"),
    (
        (
            "remove",
            (True, False, True),
            {"remove": 1, "volume_remove": 1},
        ),
        (
            "volume_remove",
            (False, True, True),
            {"remove": 1, "volume_remove": 1},
        ),
    ),
)
def test_cleanup_retries_only_the_failed_exact_docker_resource(
    tmp_path: Path,
    failed_action: str,
    expected_after_first: tuple[bool, bool, bool],
    expected_calls: dict[str, int],
) -> None:
    command = FakeCommand(tmp_path, fail_actions_once={failed_action})
    harness = _harness(tmp_path, command)

    with pytest.raises(RuntimeError) as error:
        harness.run()

    assert ENV_VALUES["DB_PASSWD"] not in str(error.value)
    assert (
        harness.runner_container_id is not None,
        harness._volume_created,
        harness._env_file is not None,
    ) == expected_after_first
    assert harness._cleaned is False
    assert {
        action: command.action_calls[action] for action in expected_calls
    } == expected_calls

    harness.cleanup()

    assert harness.runner_container_id is None
    assert harness._volume_created is False
    assert harness._env_file is None
    assert harness._cleaned is True
    assert command.action_calls[failed_action] == 2
    successful_action = "volume_remove" if failed_action == "remove" else "remove"
    assert command.action_calls[successful_action] == 1


def test_cleanup_retries_only_a_failed_environment_unlink(
    tmp_path: Path,
) -> None:
    command = FakeCommand(tmp_path)
    unlinker = FailOnceUnlink()
    harness = _harness(tmp_path, command, unlinker=unlinker)

    with pytest.raises(RuntimeError) as error:
        harness.run()

    assert ENV_VALUES["DB_PASSWD"] not in str(error.value)
    assert harness.runner_container_id is None
    assert harness._volume_created is False
    assert harness._env_file is not None
    assert harness._cleaned is False
    assert len(unlinker.calls) == 1

    harness.cleanup()

    assert harness._env_file is None
    assert harness._cleaned is True
    assert len(unlinker.calls) == 2
    assert command.action_calls["remove"] == 1
    assert command.action_calls["volume_remove"] == 1


def test_cleanup_aggregates_bounded_failures_then_retries_all_owned_resources(
    tmp_path: Path,
) -> None:
    command = FakeCommand(
        tmp_path,
        fail_actions_once={"remove", "volume_remove"},
    )
    unlinker = FailOnceUnlink()
    harness = _harness(tmp_path, command, unlinker=unlinker)

    with pytest.raises(RuntimeError) as error:
        harness.run()

    message = str(error.value)
    assert ENV_VALUES["DB_PASSWD"] not in message
    assert "runner container" in message
    assert "Node volume" in message
    assert "runner environment" in message
    assert harness.runner_container_id == RUNNER_ID
    assert harness._volume_created is True
    assert harness._env_file is not None
    assert harness._cleaned is False

    harness.cleanup()

    assert harness._cleaned is True
    assert command.action_calls["remove"] == 2
    assert command.action_calls["volume_remove"] == 2
    assert len(unlinker.calls) == 2


def test_cleanup_treats_explicitly_absent_docker_resources_as_complete(
    tmp_path: Path,
) -> None:
    command = FakeCommand(
        tmp_path,
        already_absent_actions={"remove", "volume_remove"},
    )
    harness = _harness(tmp_path, command)

    harness.run()

    assert harness.runner_container_id is None
    assert harness._volume_created is False
    assert harness._env_file is None
    assert harness._cleaned is True
    assert command.action_calls["remove"] == 1
    assert command.action_calls["volume_remove"] == 1
