#!/usr/bin/env python3
"""Run CI gates through canonical validation's disposable target authority."""

import argparse
import configparser
import fnmatch
import hashlib
import json
import os
import platform
import subprocess  # nosec B404, fixed read-only Git commands
from pathlib import Path

import phase34
from phase34_fixtures import backend_command
from phase34_fixtures import prepare as prepare_snapshot
from phase34_fixtures import schema_commands

ORIGIN = "https://github.com/D1skanime/pc-game-download-portal.git"


def preflight():
    root = Path(__file__).resolve().parents[2]
    if platform.system() != "Linux" or Path.cwd().resolve() != root:
        raise RuntimeError("CI runner requires its Linux repository root")
    canonical = Path("/home/d1sk/pc-game-download-portal")
    if root != canonical and (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != "D1skanime/pc-game-download-portal"
        or Path(os.environ.get("GITHUB_WORKSPACE", "/")).resolve() != root
    ):
        raise RuntimeError("unverified CI workspace")
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
        "PYTEST_ADDOPTS",
    ):
        if os.environ.get(key):
            raise RuntimeError("refusing inherited target override: " + key)
    for args, expected in (
        (["rev-parse", "--show-toplevel"], str(root)),
        (["remote", "get-url", "origin"], ORIGIN),
    ):
        # trunk-ignore(bandit/B603): Fixed read-only Git argv without a shell.
        actual = subprocess.check_output(
            ["git", *args], text=True
        ).strip()  # nosec B603,B607
        if args[0] == "remote":
            actual = actual.removesuffix(".git")
            expected = expected.removesuffix(".git")
        if actual != expected:
            raise RuntimeError("CI repository identity mismatch")
    if not (root / "backend/tools/phase34_target_guard.py").is_file():
        raise RuntimeError("missing disposable target authority")
    phase34.REPO = root
    return root


VALIDATOR = ".planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-evidence-validate.py"


def prepare_ci_snapshot(root, repo):
    games, snapshot = prepare_snapshot(root, repo)
    # trunk-ignore(bandit/B603): Fixed read-only Git index enumeration.
    tracked = set(
        subprocess.check_output(  # nosec B603,B607
            ["git", "ls-files", "--cached", "-z"],
            cwd=repo,
            text=True,
        ).split("\0")
    )
    for path in snapshot.rglob("*"):
        if (path.is_file() or path.is_symlink()) and path.relative_to(
            snapshot
        ).as_posix() not in tracked:
            path.unlink()
    return games, snapshot


class CIRun(phase34.Run):
    def start(self):
        original = phase34.prepare
        phase34.prepare = prepare_ci_snapshot
        try:
            super().start()
        finally:
            phase34.prepare = original

    def __init__(self, dialect):
        super().__init__(dialect)
        source = phase34.REPO / VALIDATOR
        if source.is_symlink() or not source.is_file():
            raise RuntimeError("missing tracked Phase 33 test validator")
        content = source.read_bytes()
        support = self.evidence / "phase33-test-validator.py"
        support.write_bytes(content)
        (self.evidence / "test-support.json").write_text(
            json.dumps(
                {"path": VALIDATOR, "sha256": hashlib.sha256(content).hexdigest()}
            )
        )
        self.override = self.control / "ci.compose.json"
        self.override.write_text(
            json.dumps(
                {
                    "services": {
                        "runner": {
                            "volumes": [
                                {
                                    "type": "bind",
                                    "source": str(support),
                                    "target": "/app/" + VALIDATOR,
                                    "read_only": True,
                                }
                            ]
                        }
                    }
                }
            )
        )

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
                str(phase34.COMPOSE),
                "-f",
                str(self.override),
                *args,
            ],
            **kwargs
        )


SHARDS = 8


def tracked_test_files(repo):
    config = configparser.ConfigParser(interpolation=None)
    config.read(repo / "backend/pytest.ini")
    patterns = config.get(
        "pytest", "python_files", fallback="test_*.py *_test.py"
    ).split()
    # trunk-ignore(bandit/B603): Fixed read-only Git test-file enumeration.
    tracked = subprocess.check_output(  # nosec B603,B607
        ["git", "ls-files", "--cached", "-z", "backend"],
        cwd=repo,
        text=True,
    ).split("\0")
    return sorted(
        name.removeprefix("backend/")
        for name in tracked
        if name.startswith("backend/")
        and any(fnmatch.fnmatchcase(Path(name).name, pattern) for pattern in patterns)
    )


def shard_files(files, shard):
    if not 1 <= shard <= SHARDS:
        raise RuntimeError("invalid CI shard")
    return files[shard - 1 :: SHARDS]


def execute(dialect, gate, shard=None):
    repo = preflight()
    files = tracked_test_files(repo) if shard is not None else []
    selected = shard_files(files, shard) if shard is not None else ["."]
    if not selected:
        raise RuntimeError("empty CI test shard")
    run = CIRun(dialect)
    run.image = "pgdp-ci:latest"
    (run.evidence / "shard-files.json").write_text(
        json.dumps(
            {
                "shard": shard,
                "shards": SHARDS if shard is not None else 1,
                "all_files": files,
                "selected_files": selected,
            },
            indent=2,
        )
    )
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a") as stream:
            stream.write("evidence=" + str(run.evidence) + "\n")
    succeeded = False
    try:
        run.start()
        if gate == "schema":
            for command in schema_commands():
                run.exec(command, timeout=600)
        else:
            run.exec(
                backend_command(
                    [
                        "-vv",
                        "--maxfail=10",
                        "--cov",
                        "--cov-report=xml:/phase34/evidence/coverage.xml",
                        "--cov-config=.coveragerc",
                        *selected,
                    ]
                ),
                timeout=2400,
                extra={
                    "HYPOTHESIS_PROFILE": "ci",
                    "HYPOTHESIS_STORAGE_DIRECTORY": "/phase34/owned/hypothesis",
                    "COVERAGE_FILE": "/phase34/owned/.coverage",
                },
            )
        succeeded = True
    finally:
        try:
            run.close()
        finally:
            (run.evidence / "ci-result.json").write_text(
                json.dumps({"gate": gate, "dialect": dialect, "passed": succeeded})
            )
            print("CI evidence:", run.evidence, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dialect", choices=tuple(phase34.SQL_IMAGES), required=True)
    parser.add_argument("--shard", type=int, choices=range(1, SHARDS + 1))
    parser.add_argument("gate", choices=("pytest", "schema"))
    args = parser.parse_args()
    if args.shard is not None and args.gate != "pytest":
        parser.error("--shard is available only for pytest")
    execute(args.dialect, args.gate, args.shard)


if __name__ == "__main__":
    main()
