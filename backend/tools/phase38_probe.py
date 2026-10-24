#!/usr/bin/env python3
"""Run fixed owned acceptance profiles with the existing disposable authority."""

import argparse
import json
import shutil

from ci_target import SHARDS, CIRun, shard_files, tracked_test_files
from phase34_fixtures import backend_command, schema_commands
from phase38_authority import PHASE, ROOT, preflight, protected

AFFECTED = (
    "tests/test_product_identity.py",
    "tests/config/test_product_identity.py",
    "tests/endpoints/test_product_identity.py",
)


def execute(gate, dialect, profile="complete"):
    identity = preflight()
    before = protected()
    if gate in ("browser", "install", "upgrade"):
        if gate == "browser":
            from phase38_browser import execute as run_gate
        else:
            from phase38_install import execute as run_gate
        return run_gate(gate, dialect, identity)
    run = CIRun(dialect)
    run.image = "pgdp-ci:latest"
    receipt = {
        "gate": gate,
        "dialect": dialect,
        "profile": profile,
        "identity": identity,
        "passed": False,
        "membership": [],
    }
    try:
        run.start()
        receipt["source_code_sha256"] = json.loads(
            (run.evidence / "code-before.json").read_text()
        )["sha256"]
        if gate == "schema":
            for command in schema_commands():
                run.exec(command, timeout=600)
        else:
            tracked = tracked_test_files(ROOT)
            groups = (
                [list(AFFECTED)]
                if profile == "affected"
                else [shard_files(tracked, index) for index in range(1, SHARDS + 1)]
            )
            for index, selected in enumerate(groups, 1):
                if not selected or not set(selected).issubset(tracked):
                    raise RuntimeError("invalid fixed tracked test membership")
                receipt["membership"].append({"shard": index, "files": selected})
                run.exec(
                    backend_command(["-vv", *selected], "backend-" + str(index)),
                    timeout=2400,
                    extra={
                        "HYPOTHESIS_PROFILE": "ci",
                        "HYPOTHESIS_STORAGE_DIRECTORY": "/phase34/owned/hypothesis",
                    },
                )
        receipt["passed"] = True
    finally:
        try:
            run.close()
        finally:
            receipt["protected_unchanged"] = before == protected()
            cleanup = run.evidence / "cleanup.json"
            receipt["cleanup"] = (
                json.loads(cleanup.read_text()) if cleanup.exists() else None
            )
            destination = PHASE / "evidence/owned" / run.project
            destination.mkdir(parents=True, exist_ok=True)
            for source in run.evidence.iterdir():
                if source.is_file() and source.name not in ("code-before.json",):
                    shutil.copy2(source, destination / source.name)
            (destination / "result.json").write_text(json.dumps(receipt, indent=2))
            print("PHASE38_EVIDENCE", destination, flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gate",
        choices=("backend", "schema", "browser", "install", "upgrade"),
        required=True,
    )
    parser.add_argument(
        "--dialect", choices=("mariadb", "postgresql", "mysql"), required=True
    )
    parser.add_argument(
        "--profile", choices=("complete", "affected"), default="complete"
    )
    args = parser.parse_args()
    if args.profile != "complete" and args.gate != "backend":
        parser.error("--profile applies only to backend")
    execute(args.gate, args.dialect, args.profile)


if __name__ == "__main__":
    main()
