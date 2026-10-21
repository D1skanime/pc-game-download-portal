"""Fail-closed exact-source browser and quality acceptance receipts."""

import fcntl
import fnmatch
import hashlib
import json
import os
import tempfile
from pathlib import Path

import phase34

INDEX = (
    phase34.REPO
    / ".planning/phases/35-incremental-windows-quick-scans-and-unidentified-game-status/35-12-receipts.json"
)
REQUIRED = {
    "actual_ui_submit",
    "actual_scheduler",
    "durable_counts",
    "paged_details",
    "terminal_unknown",
    "reload",
    "reconnect",
    "keyboard",
    "mouse",
    "touch",
    "gamepad_bridge",
    "geometry",
    "targets",
    "overflow",
    "polite",
    "contrast",
    "state_projection",
    "auth_isolation",
    "stale_monotonic",
    "status_only",
    "fault_only",
    "focus_restoration",
}


def validate_browser(receipt):
    checks = receipt.get("checks", {})
    if (
        receipt.get("passed") is not True
        or not REQUIRED.issubset(checks)
        or any(checks[key] is not True for key in REQUIRED)
    ):
        raise RuntimeError("missing or failed browser scenarios")
    screenshots = receipt.get("screenshots", [])
    expected = {
        str(width) + "-" + theme
        for width in (320, 600, 960, 1280, 1920, 3840)
        for theme in ("dark", "light")
    }
    if not expected.issubset({row["case"] for row in screenshots}):
        raise RuntimeError("incomplete responsive/theme screenshots")
    if not {"de_DE", "zh_CN", "zoom200", "reduced-motion"}.issubset(
        receipt.get("variants", [])
    ):
        raise RuntimeError("incomplete locale/accessibility variants")
    return receipt


def current_sources(record):
    files = record.get("files", {})
    relevant = {
        name: digest
        for name, digest in files.items()
        if name.startswith(("backend/", "frontend/"))
    }
    if not relevant:
        raise RuntimeError("empty source manifest")
    actual = set()
    ignored = {
        "node_modules",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        "pgdp_test",
        "Media",
        "dist",
        "test-results",
    }
    for folder in ("backend", "frontend"):
        for directory, dirs, names in os.walk(phase34.REPO / folder, followlinks=False):
            dirs[:] = [
                name
                for name in dirs
                if name not in ignored and not (Path(directory) / name).is_symlink()
            ]
            for name in names:
                path = Path(directory) / name
                if (
                    path.is_symlink()
                    or name == ".env"
                    or fnmatch.fnmatch(name, ".env.*")
                ):
                    continue
                actual.add(path.relative_to(phase34.REPO).as_posix())
    if actual != set(relevant):
        raise RuntimeError("source manifest omits or adds source files")
    for name, digest in relevant.items():
        path = (phase34.REPO / name).resolve()
        if (
            not path.is_relative_to(phase34.REPO)
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("stale or invalid tested source: " + name)


def validate_result(evidence, *, exact=True):
    evidence = Path(evidence)
    result = json.loads((evidence / "phase35-browser-result.json").read_text())
    cleanup = json.loads((evidence / "cleanup.json").read_text())
    commands = json.loads((evidence / "commands.json").read_text())
    if (
        result.get("passed") is not True
        or not commands
        or any(row["exit"] for row in commands)
        or cleanup.get("clean") is not True
        or cleanup.get("source_unchanged") is not True
        or cleanup.get("snapshot_removed") is not True
        or set(cleanup.get("remaining", {})) != {"container", "network", "volume"}
        or any(cleanup["remaining"].values())
    ):
        raise RuntimeError("failed commands or incomplete cleanup")
    if exact:
        current_sources(json.loads((evidence / "code-before.json").read_text()))
    if result["kind"] == "browser":
        validate_browser(result["browser"])
        for row in result["browser"]["screenshots"]:
            path = evidence / row["file"]
            if (
                path.parent != evidence
                or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]
            ):
                raise RuntimeError("missing or tampered screenshot")
    elif result["kind"] == "quality":
        expected = {"generate", "typecheck", "test", "build", "v2:maintainability"}
        observed = {
            row["command"][2]
            for row in result.get("checks", [])
            if row["command"][:2] == ["npm", "run"]
        }
        locale = {
            tuple(row["command"])
            for row in result.get("checks", [])
            if row["command"][0] == "python3"
        }
        if (
            not expected.issubset(observed)
            or len(locale) != 2
            or any(row["exit"] for row in result["checks"])
        ):
            raise RuntimeError("incomplete quality results")
    else:
        raise RuntimeError("unknown receipt kind")
    return result


def retain(run, result):
    (run.evidence / "phase35-browser-result.json").write_text(
        json.dumps(result, indent=2)
    )
    files = {}
    for path in run.evidence.rglob("*"):
        if path.is_symlink():
            raise RuntimeError("evidence symlink rejected")
        if path.is_file():
            files[path.relative_to(run.evidence).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    with INDEX.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        entries = json.loads(INDEX.read_text()) if INDEX.exists() else []
        entries.append(
            {
                "kind": result["kind"],
                "dialect": run.driver,
                "evidence": str(run.evidence),
                "passed": result["passed"],
                "files": files,
            }
        )
        INDEX.write_text(json.dumps(entries, indent=2) + "\n")
    print("RETAINED", run.evidence, "passed", result["passed"], flush=True)


def verify_retained(entry):
    from phase34_evidence import run_directory

    evidence = run_directory(entry["evidence"])
    if not entry.get("files"):
        raise RuntimeError("missing receipt hashes")
    for name, digest in entry["files"].items():
        path = (evidence / name).resolve()
        if (
            not path.is_relative_to(evidence)
            or not path.is_file()
            or path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("tampered retained evidence: " + name)
    return validate_result(evidence)


def assert_receipts():
    entries = json.loads(INDEX.read_text())
    required = {
        ("browser", "mariadb"),
        ("browser", "postgresql"),
        ("quality", "mariadb"),
    }
    found = set()
    for pair in required:
        matches = [
            row
            for row in entries
            if (row["kind"], row["dialect"]) == pair and row["passed"]
        ]
        if not matches:
            raise RuntimeError("missing successful gate: " + repr(pair))
        result = verify_retained(matches[-1])
        if (result["kind"], result["dialect"]) != pair:
            raise RuntimeError("receipt gate/dialect mismatch")
        found.add(pair)
    if found != required:
        raise RuntimeError("missing final acceptance gates")
    assert_external_gates()
    print(
        "PASS exact browser/quality/backend/schema/connected source and cleanup receipts"
    )


def checked_subset(record, prefixes):
    files = record.get("files", {})
    selected = {
        name: digest for name, digest in files.items() if name.startswith(prefixes)
    }
    if not selected:
        raise RuntimeError("missing relevant source hashes")
    for name, digest in selected.items():
        path = (phase34.REPO / name).resolve()
        if (
            not path.is_relative_to(phase34.REPO)
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("stale relevant source: " + name)


def clean_commands(evidence):
    from phase34_evidence import read_json, run_directory

    evidence = run_directory(evidence)
    cleanup = read_json(evidence / "cleanup.json")
    commands = read_json(evidence / "commands.json")
    if (
        not commands
        or any(row["exit"] for row in commands)
        or cleanup.get("clean") is not True
        or cleanup.get("snapshot_removed") is not True
        or cleanup.get("source_unchanged") is not True
        or set(cleanup.get("remaining", {})) != {"container", "network", "volume"}
        or any(cleanup["remaining"].values())
    ):
        raise RuntimeError("external gate lacks successful commands and exact cleanup")
    return evidence, commands


def assert_external_gates():
    from xml.etree import (  # nosec B405, bounded local report with declarations rejected
        ElementTree,
    )

    from phase34_evidence import DEFAULT_ROOT, read_json, receipt_digest
    from phase35_incremental_scan_probe import validate_receipt

    index = read_json(DEFAULT_ROOT / "index.json")["runs"]
    gates = []
    for dialect in ("mariadb", "postgresql"):
        matches = []
        for row in index:
            if row["gate"] != "backend" or row["passed"] is not True:
                continue
            evidence = Path(row["evidence"])
            commands = read_json(evidence / "commands.json")
            if not any(
                "ROMM_DB_DRIVER=" + dialect in item["command"] for item in commands
            ):
                continue
            report = read_json(evidence / "code-before.json")
            try:
                checked_subset(
                    report,
                    (
                        "backend/handler/",
                        "backend/endpoints/",
                        "backend/tests/",
                        "backend/models/",
                        "backend/tasks/",
                        "backend/utils/",
                        "backend/adapters/",
                    ),
                )
            except RuntimeError:
                continue
            payload = (evidence / "backend.xml").read_bytes()
            if (
                len(payload) > 16000000
                or b"<!DOCTYPE" in payload
                or b"<!ENTITY" in payload
            ):
                raise RuntimeError("unsafe backend XML")
            root = ElementTree.fromstring(
                payload
            )  # nosec B314, declarations and size rejected
            suites = [root] if root.tag == "testsuite" else list(root)
            if sum(int(s.attrib.get("tests", 0)) for s in suites) >= 500 and not any(
                int(s.attrib.get(k, 0))
                for s in suites
                for k in ("failures", "errors", "skipped")
            ):
                matches.append(row)
        if not matches:
            raise RuntimeError("missing final full backend gate: " + dialect)
        row = matches[-1]
        clean_commands(row["evidence"])
        for name, digest in row["files"].items():
            if receipt_digest(Path(row["evidence"]) / name) != digest:
                raise RuntimeError("tampered backend evidence")
        gates.append(row)
    for dialect in ("mariadb", "mysql", "postgresql"):
        rows = [
            row for row in index if row["gate"] == "schema:" + dialect and row["passed"]
        ]
        if not rows:
            raise RuntimeError("missing schema cycle: " + dialect)
        row = rows[-1]
        clean_commands(row["evidence"])
        checked_subset(
            read_json(Path(row["evidence"]) / "code-before.json"),
            ("backend/models/", "backend/alembic/"),
        )
        for name, digest in row["files"].items():
            if receipt_digest(Path(row["evidence"]) / name) != digest:
                raise RuntimeError("tampered schema evidence")
        gates.append(row)
    for dialect in ("mariadb", "postgresql"):
        for scenario in ("incremental", "authority"):
            candidates = []
            for path in Path(tempfile.gettempdir()).glob(
                "pgdp34-*/evidence/phase35-result.json"
            ):
                proof = read_json(path)
                if (
                    proof.get("dialect") != dialect
                    or proof.get("scenario") != scenario
                    or proof.get("passed") is not True
                ):
                    continue
                try:
                    checked_subset(
                        read_json(path.parent / "code-before.json"),
                        (
                            "backend/handler/",
                            "backend/endpoints/",
                            "backend/models/",
                            "backend/tasks/",
                            "backend/utils/",
                            "backend/adapters/",
                        ),
                    )
                except RuntimeError:
                    continue
                validate_receipt(proof)
                candidates.append(path)
            if not candidates:
                raise RuntimeError(
                    "missing final connected gate: " + dialect + "/" + scenario
                )
            path = max(candidates, key=lambda item: item.stat().st_mtime_ns)
            clean_commands(path.parent)
            gates.append(
                {
                    "gate": "connected:" + dialect + ":" + scenario,
                    "evidence": str(path.parent),
                }
            )
    return gates
