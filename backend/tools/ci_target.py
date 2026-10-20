#!/usr/bin/env python3
"""Run CI gates through canonical validation's disposable target authority."""

import argparse
import json
import os
import platform
import subprocess  # nosec B404, fixed read-only Git commands
from pathlib import Path

import phase34
from phase34_fixtures import backend_command, schema_commands

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
        if actual != expected:
            raise RuntimeError("CI repository identity mismatch")
    if not (root / "backend/tools/phase34_target_guard.py").is_file():
        raise RuntimeError("missing disposable target authority")
    phase34.REPO = root
    return root


def execute(dialect, gate):
    preflight()
    run = phase34.Run(dialect)
    run.image = "pgdp-ci:latest"
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
                        ".",
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
    parser.add_argument("gate", choices=("pytest", "schema"))
    args = parser.parse_args()
    execute(args.dialect, args.gate)


if __name__ == "__main__":
    main()
