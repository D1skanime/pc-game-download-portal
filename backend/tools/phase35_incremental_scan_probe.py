#!/usr/bin/env python3
"""Fail-closed isolated manual/scheduled incremental scan acceptance."""

import argparse
import json

import phase34
from phase34_evidence import read_json
from phase34_faults import start_process, wait_http
from phase35_incremental_assertions import (
    assert_game_files,
    assert_preserved,
    assert_stage_counts,
)
from phase35_incremental_scan_fixture import (
    assert_immutable,
    manifest,
    prepare,
    segment_edit,
)

BRANCH = "codex/phase-35-incremental-windows-scans"
ORIGIN = "https://github.com/D1skanime/zockarchive.git"
CLIENT = "tools/phase35_incremental_client.py"
WORKER = "tools/phase35_incremental_worker.py"


def git_value(*args):
    # Fixed Git argv is run only after the canonical host/root preflight.
    return phase34.subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, cwd=phase34.REPO
    ).stdout.strip()


def preflight():
    phase34.host_preflight()
    if git_value("branch", "--show-current") != BRANCH:
        raise RuntimeError("unexpected execution branch")
    if git_value("remote", "get-url", "origin") != ORIGIN:
        raise RuntimeError("unexpected execution origin")
    project = (phase34.REPO / ".planning/PROJECT.md").read_text()
    state = (phase34.REPO / ".planning/STATE.md").read_text()
    if "RomM PC Library" not in project or "35" not in state:
        raise RuntimeError("planning identity mismatch")


def validate_receipt(receipt):
    cleanup = receipt.get("cleanup", {})
    if (
        cleanup.get("clean") is not True
        or cleanup.get("snapshot_removed") is not True
        or cleanup.get("source_unchanged") is not True
        or any(cleanup.get("remaining", {}).values())
    ):
        raise RuntimeError("incomplete cleanup receipt")
    if (
        receipt.get("passed") is not True
        or receipt.get("observed_worker") is not True
        or receipt.get("source_unchanged") is not True
        or not {"cold", "warm-manual", "warm-scheduled"}.issubset(
            receipt.get("stages", [])
        )
    ):
        raise RuntimeError("incomplete connected receipt")
    if receipt.get("scenario") == "authority":
        expected = {
            phase + "-" + kind
            for phase in ("detection", "completion")
            for kind in (
                "revision",
                "root",
                "root-binding",
                "incarnation",
                "lease",
                "attempt",
                "cancel",
            )
        }
        if set(receipt.get("authority_cases", [])) != expected:
            raise RuntimeError("incomplete authority barrier receipt")
    return receipt


def observations(run):
    path = run.evidence / "observations.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def assert_warm(snapshot, observed):
    if snapshot.get("scan_stats", {}).get("inventory_unchanged", 0) < 1:
        raise RuntimeError("warm scan lacks durable inventory facts")
    forbidden = {"hash", "components", "enrichment", "media_prepare", "provider_http"}
    if any(row["kind"] in forbidden for row in observed):
        raise RuntimeError("warm scan performed expensive work")


def call(run, action, stage="inspect", mode="quick"):
    run.exec(
        ["uv", "run", "python", CLIENT, action, "--stage", stage, "--mode", mode],
        timeout=120,
    )
    path = run.evidence / (stage + ".json")
    return read_json(path) if path.exists() else None


def start(run, *, initialize):
    if initialize:
        run.exec(["uv", "run", "alembic", "upgrade", "head"])
        run.exec(["uv", "run", "python", "startup.py"], timeout=90)
        start_process(run, "provider", ["uv", "run", "python", WORKER, "provider"])
        wait_http(run, "http://127.0.0.1:3346/api/storesearch")
    start_process(
        run,
        "api",
        ["uv", "run", "python", WORKER, "api"],
        extra={"DEV_PORT": "3344", "ENABLE_SCHEDULED_RESCAN": "false"},
    )
    wait_http(run, "http://127.0.0.1:3344/api/heartbeat")
    start_process(run, "worker", ["uv", "run", "python", WORKER, "worker"])


def stop_owned_processes(run):
    script = (
        "import os,signal; from pathlib import Path; "
        "from tools.phase34_target_guard import validate_target; validate_target()\n"
        "for name in ('api','worker'):\n"
        " pid=int(Path('/phase34/evidence/'+name+'.pid').read_text())\n"
        " env=Path('/proc/'+str(pid)+'/environ').read_bytes().split(bytes([0]))\n"
        " assert ('PHASE34_RUN_TOKEN='+os.environ['PHASE34_RUN_TOKEN']).encode() in env\n"
        " os.killpg(pid,signal.SIGTERM)\n"
    )
    run.exec(["uv", "run", "python", "-c", script])


def stage(run, name, action="scan", mode="quick", warm=False):
    preserved = call(run, "inspect", name + "-before") if warm else None
    offset = len(observations(run))
    snapshot = call(run, action, name, mode)
    observed = observations(run)[offset:]
    assert_immutable(run.root / "Games", run.before)
    if snapshot["state"] != "completed":
        raise RuntimeError("actual worker did not complete")
    if warm:
        assert_warm(snapshot, observed)
        assert preserved is not None
        if not preserved["media"]:
            raise RuntimeError("warm owned media proof missing")
        assert_preserved(preserved, snapshot["catalog"])
    expected = {
        row["path"]: {"size": row["size"], "sha256": row["sha256"]}
        for row in manifest(run.root / "fixture/Games/pc/Known.Game")
    }
    assert_game_files(snapshot["catalog"], expected)
    assert_stage_counts(name, snapshot)
    (run.evidence / (name + "-calls.json")).write_text(json.dumps(observed, indent=2))
    print("PASS actual", name, snapshot["scan_stats"], flush=True)
    return snapshot, observed


def execute(driver, scenario):
    preflight()
    phase34.prepare = prepare
    phase34.COMPOSE = (
        phase34.REPO
        / ".planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-uat-compose.yml"
    )
    run = phase34.Run(driver)
    run.env["P33_GAMES"] = str(run.root / "fixture/Games")
    receipt = {"scenario": scenario, "dialect": driver, "passed": False, "stages": []}
    try:
        (run.evidence / "observations.jsonl").touch()
        run.start()
        start(run, initialize=True)
        call(run, "setup", "setup")
        segment_edit(run, "alternate-root")
        cold, observed = stage(run, "cold")
        receipt["stages"].append("cold")
        if not any(row["kind"] == "components" for row in observed):
            raise RuntimeError("cold scan did not reach actual component work")
        call(run, "seed")
        stage(run, "adopt-identified", warm=True)
        stage(run, "promote", action="promote")
        stage(run, "collection-discovery")
        control, control_calls = stage(
            run, "initialize-non-windows", action="scheduled"
        )
        if control["scan_stats"]["new_roms"] != 1 or not any(
            row["kind"] == "enrichment" for row in control_calls
        ):
            raise RuntimeError("non-Windows control did not use its existing scan path")
        before = call(run, "inspect", "catalog-before")
        for name, action in (("warm-manual", "scan"), ("warm-scheduled", "scheduled")):
            stage(run, name, action=action, warm=True)
            receipt["stages"].append(name)
        if scenario == "incremental":
            for action in ("add", "change", "delete", "new-game", "new-child"):
                segment_edit(run, action)
                result, seen = stage(run, action)
                if not any(row["kind"] == "components" for row in seen):
                    raise RuntimeError("fixture change was not processed: " + action)
                if any(
                    row["name"] == "Castlevania" for row in result["catalog"]["roms"]
                ):
                    raise RuntimeError("classified collection parent resurrected")
            call(run, "age")
            for name in ("due-five", "due-rest", "backoff"):
                snapshot, seen = stage(run, name)
                requests = sum(row["kind"] == "provider_http" for row in seen)
                if any(row["kind"] in {"hash", "components"} for row in seen):
                    raise RuntimeError("metadata-only retry hashed component content")
                if requests != snapshot["scan_stats"].get("provider_requests", 0):
                    raise RuntimeError(
                        "provider counter differs from actual HTTP requests"
                    )
                expected = {"due-five": 10, "due-rest": 10, "backoff": 0}[name]
                if requests != expected:
                    raise RuntimeError(
                        "unexpected fixture retry count: " + str(requests)
                    )
            stage(run, "explicit-hashes", mode="hashes")
        else:
            stop_owned_processes(run)
            start(run, initialize=False)
            stage(run, "restart-warm", warm=True)
            after = call(run, "inspect", "catalog-after")
            if (
                before["roms"] != after["roms"]
                or before["baselines"] != after["baselines"]
            ):
                raise RuntimeError("restart changed authoritative catalog")
            assert_preserved(before, after)
            receipt["authority_cases"] = []
            for phase in ("detection", "completion"):
                for revocation in (
                    "revision",
                    "root",
                    "root-binding",
                    "incarnation",
                    "lease",
                    "attempt",
                    "cancel",
                ):
                    name = phase + "-" + revocation
                    if phase == "completion":
                        segment_edit(
                            run, "add" if revocation == "revision" else "change"
                        )
                    result = call(run, "authority", name)
                    assert_immutable(run.root / "Games", run.before)
                    receipt["authority_cases"].append(name)
                    print("PASS actual authority", name, result["state"], flush=True)
                    stage(run, "restore-" + name)
        receipt["observed_worker"] = any(
            row["kind"] == "worker_boot" for row in observations(run)
        )
        receipt["source_unchanged"] = True
        receipt["passed"] = True
    except BaseException as error:
        receipt["error"] = str(error)
        raise
    finally:
        receipt["passed"] = receipt["passed"] and all(
            row["exit"] == 0 for row in run.records
        )
        try:
            run.close()
        finally:
            cleanup = run.evidence / "cleanup.json"
            receipt["cleanup"] = read_json(cleanup) if cleanup.exists() else {}
            (run.evidence / "phase35-result.json").write_text(
                json.dumps(receipt, indent=2)
            )
            print("PHASE35_EVIDENCE", run.evidence, flush=True)
    validate_receipt(receipt)
    return run.evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dialect", choices=("mariadb", "postgresql"), required=True)
    parser.add_argument(
        "--scenario", choices=("incremental", "authority"), required=True
    )
    args = parser.parse_args()
    execute(args.dialect, args.scenario)


if __name__ == "__main__":
    main()
