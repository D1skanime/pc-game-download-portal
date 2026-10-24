#!/usr/bin/env python3
"""Run full-checkout contracts on the CI host without application dependencies.

Git, Node and Docker Compose are host prerequisites. Compose is used only for
configuration rendering. SQL suites remain inside the existing isolated runner.
"""

import json
import os
import subprocess  # nosec B404, fixed host prerequisite argv
import tempfile
import unittest
from pathlib import Path

import ci_target
import phase38_cutover_source as source
from ci_test_profiles import classify_test_files


def workflow_contract(text):
    """Check the required host job without adding a YAML runtime dependency."""
    if "  host-contracts:\n" not in text:
        raise RuntimeError("missing required host-contracts job")
    block = text.split("  host-contracts:\n", 1)[1].split("\n  pytest:", 1)[0]
    required = (
        "actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955",
        "fetch-depth: 0",
        "actions/setup-python@e797f83bcb11b83ae66e0230d6156d7c80228e7c",
        'python-version: "3.13"',
        "actions/setup-node@a0853c24544627f65ddf259abe73b1d18a591444",
        'node-version: "24"',
        "python3 backend/tools/ci_host_contracts.py",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "name: host-contracts-evidence",
    )
    if not all(value in block for value in required) or any(
        value in block for value in ("continue-on-error:", "if: false", "if: never")
    ):
        raise RuntimeError("incomplete required host-contracts workflow")


def prerequisites():
    observed = {}
    for key, argv in (
        ("git", ["git", "--version"]),
        ("node", ["node", "--version"]),
        ("compose", ["docker", "compose", "version", "--short"]),
    ):
        # trunk-ignore(bandit/B603): Fixed version commands, no services or shell.
        observed[key] = subprocess.check_output(  # nosec B603,B607
            argv, text=True, stderr=subprocess.PIPE, timeout=30
        ).strip()
    if not observed["node"].startswith("v24.") or not all(observed.values()):
        raise RuntimeError("missing Git/Node24/DockerCompose prerequisites")
    return observed


def run_contracts(root, evidence):
    profiles = classify_test_files(ci_target.tracked_test_files(root))
    source.ROOT = root
    commit = source.git("rev-parse", "HEAD").strip()
    source.git("diff", "--exit-code", "HEAD", "--", ".", ":!.planning")
    proof = {"commit": commit, "manifest": source.manifest(commit, "full")}
    receipt = {
        "schema": 1,
        "repository_id": 1415481891,
        "job": "host-contracts",
        "source": proof,
        "membership": profiles,
        "file_results": [],
        "passed": False,
        "prerequisites": prerequisites(),
    }
    workflow_contract((root / ".github/workflows/pytest.yml").read_text())
    try:
        with (evidence / "unittest.log").open("w") as stream:
            for name in profiles["host"]:
                suite = unittest.defaultTestLoader.discover(
                    str(root / "backend/tools/tests"),
                    pattern=Path(name).name,
                )
                result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
                receipt["file_results"].append(
                    {
                        "file": name,
                        "tests": result.testsRun,
                        "failures": len(result.failures),
                        "errors": len(result.errors),
                        "skipped": len(result.skipped),
                        "passed": result.wasSuccessful() and not result.skipped,
                    }
                )
        source.git("diff", "--exit-code", "HEAD", "--", ".", ":!.planning")
        if commit != source.git("rev-parse", "HEAD").strip():
            raise RuntimeError("source changed during host contracts")
        receipt["passed"] = all(
            row["passed"] and row["tests"] > 0 for row in receipt["file_results"]
        )
    finally:
        (evidence / "host-contracts.json").write_text(json.dumps(receipt, indent=2))
    if not receipt["passed"]:
        raise RuntimeError("host contract test failed or skipped")
    return receipt


def main():
    root = ci_target.preflight()
    evidence = Path(tempfile.mkdtemp(prefix="za-host-contracts-"))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a") as stream:
            stream.write("evidence=" + str(evidence) + "\n")
    print("Host contract evidence:", evidence, flush=True)
    run_contracts(root, evidence)


if __name__ == "__main__":
    main()
