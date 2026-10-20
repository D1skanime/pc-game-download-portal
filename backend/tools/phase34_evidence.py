#!/usr/bin/env python3
"""Retain exact disposable-run receipts and reject incomplete acceptance."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = (
    REPO / ".planning/phases/34-reliable-fresh-installation-and-scan-lifecycle/evidence"
)
REQUIRED = {
    "schema:mariadb",
    "schema:mysql",
    "schema:postgresql",
    "quality",
    "faults",
    "browser",
    "production",
}
MAX_RECEIPT_BYTES = 16 * 1024 * 1024


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("missing or unsafe evidence receipt: " + str(path))
    if path.stat().st_size > MAX_RECEIPT_BYTES:
        raise RuntimeError("oversized evidence receipt")
    return json.loads(path.read_text())


def evidence_root():
    root = Path(os.environ.get("PHASE34_EVIDENCE_ROOT", str(DEFAULT_ROOT)))
    if not root.is_absolute() or root.is_symlink():
        raise RuntimeError("absolute non-symlink evidence directory required")
    if root.exists() and any(parent.is_symlink() for parent in root.parents):
        raise RuntimeError("symlink evidence ancestor refused")
    return root


def run_directory(path):
    directory = Path(path)
    temp = Path(tempfile.gettempdir()).resolve()
    name = directory.parent.name
    if (
        directory.is_symlink()
        or directory.parent.is_symlink()
        or directory.name != "evidence"
        or directory.parent.parent.resolve() != temp
        or not re.fullmatch(r"pgdp34-[a-f0-9]{32}-.+", name)
    ):
        raise RuntimeError("receipt is outside an exact disposable run")
    return directory


def receipt_digest(path):
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > 64 * 1024 * 1024:
        raise RuntimeError("unsafe retained evidence file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retain_run(run, gate, succeeded, detail=None):
    """Only an observed success may become a passing gate."""
    directory = run_directory(run.evidence)
    cleanup = read_json(directory / "cleanup.json")
    commands = read_json(directory / "commands.json")
    clean = (
        cleanup.get("clean") is True
        and cleanup.get("snapshot_removed") is True
        and cleanup.get("source_unchanged") is True
        and not any(cleanup.get("remaining", {}).values())
    )
    successful_commands = bool(commands) and all(
        item.get("exit") == 0 for item in commands
    )
    code = read_json(directory / "code-before.json")
    revision = run.command(["git", "rev-parse", "HEAD"], cwd=REPO).stdout.strip()
    commands = read_json(directory / "commands.json")
    files = {
        p.name: receipt_digest(p)
        for p in sorted(directory.iterdir())
        if p.is_file() and p.suffix in {".json", ".xml", ".log", ".conf"}
    }
    row = {
        "gate": gate,
        "project": run.project,
        "revision": revision,
        "code_sha256": code["sha256"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "evidence": str(directory),
        "passed": bool(succeeded and clean and successful_commands),
        "cleanup": clean,
        "detail": detail,
        "files": files,
    }
    root = evidence_root()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".index.lock"
    if lock_path.is_symlink():
        raise RuntimeError("unsafe evidence index lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        index_path = root / "index.json"
        index = read_json(index_path) if index_path.exists() else {"runs": []}
        index["runs"].append(row)
        with tempfile.NamedTemporaryFile(mode="w", dir=root, delete=False) as handle:
            json.dump(index, handle, indent=2)
            replacement = Path(handle.name)
        replacement.replace(index_path)
    return row


def validate_fault_receipts(directory):
    receipt = read_json(directory / "stable-output-faults.json")
    required = {
        (family, order)
        for family in ("ra", "gamelist", "pegasus")
        for order in (
            "stale_after_cancel",
            "fence_before_cancel_ack",
            "crash_before_replace",
            "crash_after_replace",
        )
    }
    proven = set()
    for row in receipt.get("proofs", []):
        digest = row.get("expected_sha256")
        if (
            row.get("passed") is not True
            or row.get("verifier_exit_confirmed") is not True
            or not isinstance(digest, str)
            or not re.fullmatch(r"[a-f0-9]{64}", digest)
            or row.get("observed_sha256") != digest
        ):
            raise RuntimeError("invalid stable-output process proof")
        key = (row.get("family"), row.get("order"))
        if key in proven:
            raise RuntimeError("duplicate stable-output process proof")
        proven.add(key)
    if proven != required:
        raise RuntimeError("missing stable-output family or cancellation/crash order")
    fixture = read_json(directory / "http-files.json")
    if fixture.get("provider_streams") != 5 or len(fixture.get("private", [])) < 10:
        raise RuntimeError("missing real streaming capability paths")
    if read_json(directory / "http-worker-exit.json").get("confirmed_exit") is not True:
        raise RuntimeError("HTTP proof does not confirm worker exit")
    for phase in ("live", "after-crash", "after-restart"):
        rows = read_json(directory / ("http-" + phase + ".json"))
        statuses = {row.get("status") for row in rows}
        if not {200, 206, 404}.issubset(statuses) or any(
            row.get("on_disk") is not True for row in rows
        ):
            raise RuntimeError("missing existing-file HTTP negative/positive controls")
    config = directory / "nginx-effective.conf"
    if config.is_symlink() or not config.is_file() or not config.stat().st_size:
        raise RuntimeError("missing effective nginx configuration")


def validate_index(index):
    errors = []
    passed = set()
    revisions = set()
    code_hashes = set()
    latest = {row.get("gate", ""): row for row in index.get("runs", [])}
    for row in latest.values():
        gate = row.get("gate", "")
        try:
            directory = run_directory(row["evidence"])
            if not row.get("files"):
                raise RuntimeError("missing receipt fingerprints")
            for name, expected in row["files"].items():
                if (
                    Path(name).name != name
                    or receipt_digest(directory / name) != expected
                ):
                    raise RuntimeError("retained receipt changed")
            cleanup = read_json(directory / "cleanup.json")
            if (
                cleanup.get("clean") is not True
                or cleanup.get("snapshot_removed") is not True
                or cleanup.get("source_unchanged") is not True
                or any(cleanup.get("remaining", {}).values())
            ):
                raise RuntimeError("cleanup/source preservation failed")
            commands = read_json(directory / "commands.json")
            observed_pass = bool(commands) and all(
                command.get("exit") == 0 for command in commands
            )
            if row.get("passed") is True and not observed_pass:
                raise RuntimeError("passing gate contains failed commands")
            if row.get("passed") is True and gate in REQUIRED:
                if gate == "faults":
                    validate_fault_receipts(directory)
                passed.add(gate)
                revisions.add(row.get("revision"))
                code_hashes.add(row.get("code_sha256"))
        except (KeyError, OSError, ValueError, RuntimeError) as exc:
            errors.append(gate + ": " + str(exc))
    for gate in sorted(REQUIRED - passed):
        errors.append("missing passing gate: " + gate)
    if len(revisions) > 1:
        errors.append("passing gates reference different Git revisions")
    if None in code_hashes or len(code_hashes) > 1:
        errors.append("passing gates do not prove the same complete code snapshot")
    # Human visual/input UAT is separate from automated browser execution.
    uat = index.get("human_uat")
    if not isinstance(uat, dict) or uat.get("accepted") is not True:
        errors.append("shared live UAT has not been accepted")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assert-complete", action="store_true", required=True)
    args = parser.parse_args()
    if not args.assert_complete:
        parser.error("--assert-complete required")
    from phase34 import host_preflight

    host_preflight()
    path = evidence_root() / "index.json"
    if not path.exists():
        raise RuntimeError("no retained execution index; no gate may be inferred")
    errors = validate_index(read_json(path))
    report = {"complete": not errors, "errors": errors}
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print("INCOMPLETE: " + str(error))
        raise SystemExit(1) from error
