#!/usr/bin/env python3
"""Fail-closed connected description proof using phase34.Run ownership and cleanup."""

import argparse
import json
import platform
import re
import socket
from pathlib import Path

import phase34
from phase34_evidence import read_json
from phase34_faults import start_process, wait_http
from phase35_incremental_scan_fixture import assert_immutable
from phase35_incremental_scan_probe import git_value, observations, stop_owned_processes
from phase36_description_fixture import prepare

BRANCH = "codex/phase-36-localized-provider-descriptions"
ORIGIN = "https://github.com/D1skanime/zockarchive.git"
ROOT = Path("/home/d1sk/pc-game-download-portal")
CLIENT = "tools/phase36_description_client.py"
WORKER = "tools/phase36_description_worker.py"


def assert_identity(actual, expected):
    if actual != expected:
        raise RuntimeError("description execution identity mismatch")


def preflight():
    phase34.host_preflight()
    assert_identity(
        (
            platform.system(),
            socket.gethostname(),
            phase34.REPO,
            git_value("branch", "--show-current"),
            git_value("remote", "get-url", "origin"),
        ),
        ("Linux", "team4slinux", ROOT, BRANCH, ORIGIN),
    )
    if (
        "RomM PC Library" not in (ROOT / ".planning/PROJECT.md").read_text()
        or "Phase36" not in (ROOT / ".planning/STATE.md").read_text()
    ):
        raise RuntimeError("description planning identity mismatch")


def validate_receipt(receipt, expected_source_hashes=None):
    cleanup = receipt.get("cleanup", {})
    if not all(
        cleanup.get(key) is True
        for key in ("clean", "snapshot_removed", "source_unchanged")
    ) or any(cleanup.get("remaining", {}).values()):
        raise RuntimeError("description cleanup incomplete")
    exact = cleanup.get("exact_resources", {})
    if set(exact) != {"container", "volume", "network"} or not all(
        isinstance(value, list) and value for value in exact.values()
    ):
        raise RuntimeError("description cleanup lacks actual owned resource inventory")
    if (
        not receipt.get("description_stages")
        or not receipt.get("source_hashes")
        or not receipt.get("wire_requests")
        or not receipt.get("observed_worker")
        or receipt.get("passed") is not True
    ):
        raise RuntimeError("description connected evidence incomplete")
    if receipt.get("scenario") == "authority":
        from phase35_incremental_barrier import REVOCATIONS

        expected = {
            (provider, phase + "-" + kind)
            for provider in ("steam", "ss")
            for phase in ("detection", "completion")
            for kind in REVOCATIONS
        }
        actual = {
            (row["provider"], row["case"])
            for row in receipt.get("authority_cases", [])
            if row.get("restored") is True
            and row.get("operation")
            and row.get("job_status") in {"finished", "failed", "stopped"}
        }
        if expected != actual or len(receipt.get("authority_cases", [])) != len(
            expected
        ):
            raise RuntimeError("description authority evidence incomplete")
    manifest = receipt["source_hashes"]
    if (
        not isinstance(manifest, dict)
        or not re.fullmatch(r"[a-f0-9]{64}", manifest.get("sha256", ""))
        or not manifest.get("files")
        or not all(
            re.fullmatch(r"[a-f0-9]{64}", value) for value in manifest["files"].values()
        )
    ):
        raise RuntimeError("description source hash receipt invalid")
    if expected_source_hashes is not None and manifest != expected_source_hashes:
        raise RuntimeError("description source hash receipt stale")
    return receipt


def call(run, action, stage, *, mode="quick", locale="de", provider="steam"):
    run.exec(
        [
            "uv",
            "run",
            "python",
            CLIENT,
            action,
            "--stage",
            stage,
            "--mode",
            mode,
            "--locale",
            locale,
            "--provider",
            provider,
        ],
        timeout=420 if action == "authority-suite" else 150,
    )
    return read_json(run.evidence / (stage + ".json"))


def start(run, initialize=False):
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


def stage(run, name, action="scan", **kwargs):
    before = call(run, "inspect", name + "-before")
    offset = len(observations(run))
    result = call(run, action, name, **kwargs)
    seen = observations(run)[offset:]
    assert_immutable(run.root / "Games", run.before)
    wire = [row for row in seen if row["kind"] == "provider_http"]
    (run.evidence / (name + "-wire.json")).write_text(json.dumps(wire, indent=2))
    if action in {"scan", "scheduled", "adopt"} and result["state"] != "completed":
        raise RuntimeError("actual description worker incomplete")
    print(
        "PASS stage", name, "wire", len(wire), result.get("scan_stats", {}), flush=True
    )
    return result, seen, before


def descriptions(run, receipt):
    call(run, "seed", "seed")
    stage(run, "adopt", action="adopt")
    call(run, "language", "language-de")
    result, seen, before = stage(run, "repair-de")
    from phase36_description_assertions import assert_repair

    assert_repair(before, result, seen)
    receipt["description_stages"].append("repair-de")
    for name in ("repair-rest-de", "cooldown-de"):
        result, seen, before = stage(run, name)
        assert_repair(before, result, seen)
        receipt["description_stages"].append(name)
    for locale in ("fr", "en"):
        result, seen, before = stage(run, "repair-" + locale, locale=locale)
        if locale == "fr":
            stage(run, "repair-rest-fr", locale=locale)
        receipt["description_stages"].append("repair-" + locale)
    stage(run, "repair-rest-en", locale="en")
    stop_owned_processes(run)
    start(run)
    result, seen, before = stage(run, "restart-cooldown", locale="en")
    if any(row["kind"] == "provider_http" for row in seen):
        raise RuntimeError("restart lost durable description cooldown")
    receipt["description_stages"].append("restart-cooldown")
    result, seen, before = stage(run, "cooldown-en", locale="en")
    if any(row["kind"] == "provider_http" for row in seen):
        raise RuntimeError("durable cooldown repeated provider HTTP")
    call(run, "ss-fault", "seed-ss-fault")
    result, seen, before = stage(
        run, "ss-disabled-selection", action="adopt", locale="en"
    )
    if any(row["kind"] == "provider_http" for row in seen):
        raise RuntimeError("disabled provider selection issued HTTP")
    result, seen, before = stage(run, "ss-fault", locale="en")
    assert_repair(before, result, seen)
    requests = [row for row in seen if row["kind"] == "provider_http"]
    if len(requests) != 2 or any(
        row["provider"] != "ss" or row["status"] != 429 for row in requests
    ):
        raise RuntimeError(
            "SS fault did not produce the actual bounded pair of429 responses"
        )
    retries = [
        row
        for row in result["catalog"]["description_retries"]
        if row["query"] == "descriptions:v1:39:parent"
    ]
    if len(retries) != 1 or not retries[0]["requested"] or not retries[0]["next"]:
        raise RuntimeError("SS fault lacks durable actual request/cooldown facts")
    stop_owned_processes(run)
    start(run)
    result, seen, before = stage(run, "ss-restart-backoff", locale="en")
    if any(row["kind"] == "provider_http" for row in seen) or result["scan_stats"].get(
        "provider_requests", 0
    ):
        raise RuntimeError("restart lost SS durable backoff")
    receipt["description_stages"] += [
        "ss-disabled-selection",
        "ss-fault",
        "ss-restart-backoff",
    ]
    call(run, "complete", "complete-controls")
    for name, action in (("warm-manual", "scan"), ("warm-scheduled", "scheduled")):
        result, seen, before = stage(run, name, action=action)
        if any(
            row["kind"] == "provider_http"
            and row["endpoint"].endswith(("appdetails", "jeuInfos.php"))
            for row in seen
        ):
            raise RuntimeError("complete warm description issued HTTP")
        receipt["description_stages"].append(name)
    for provider in ("steam", "ss"):
        for locale in ("de", "fr", "en"):
            call(run, "reset", "reset-" + provider + locale, provider=provider)
            result, seen, before = stage(
                run,
                "interactive-" + provider + locale,
                action="interactive",
                provider=provider,
                locale=locale,
            )
            receipt["description_stages"].append("interactive-" + provider + locale)
    for provider in ("steam", "ss"):
        result, seen, before = stage(
            run,
            "game-refresh-" + provider,
            action="refresh",
            provider=provider,
            mode="complete",
            locale="fr",
        )
        receipt["description_stages"].append("game-refresh-" + provider)
    for mode in ("update", "unmatched", "complete", "hashes", "new_platforms"):
        stage(run, "manual-mode-" + mode, mode=mode, locale="fr")
        receipt["description_stages"].append("manual-mode-" + mode)
    discovery_tail(run, receipt)


def discovery_tail(run, receipt):
    """Remaining discovery/restart proof, independently receipted after fixture-only fixes."""
    assert_immutable(run.root / "Games", run.before)
    from phase34_fixtures import source_manifest

    folder = run.root / "Games/pc/New.Game (igdb-3070)/Base"
    folder.mkdir(parents=True)
    (folder / "new.bin").write_bytes(b"owned new discovery")
    run.before = source_manifest(run.root / "Games")
    (run.evidence / "new-discovery-source.json").write_text(
        json.dumps(run.before, indent=2)
    )
    run.exec(
        [
            "python",
            "-c",
            "from pathlib import Path; import json; "
            "Path('/phase34/evidence/provider-control.json').write_text("
            "json.dumps({'enabled': True, 'igdb': True}))",
        ]
    )
    result, seen, before = stage(run, "new-igdb", locale="fr")
    new = next(
        row
        for row in result["catalog"]["descriptions"]
        if row["name"] == "New.Game (igdb-3070)"
    )
    if new["steam_id"] != 777 or not new["steam"].get("text_variants", {}).get(
        "fr", {}
    ).get("summary"):
        raise RuntimeError("new actual IGDB identity did not reach shared text repair")
    receipt["description_stages"].append("new-igdb")
    stop_owned_processes(run)
    start(run)
    stage(run, "restart", action="scheduled")


def execute(driver, scenario):
    preflight()
    phase34.prepare = lambda root, repo: prepare(
        root, repo, profile="authority" if scenario == "authority" else "descriptions"
    )
    phase34.COMPOSE = (
        ROOT
        / ".planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-uat-compose.yml"
    )
    run = phase34.Run(driver)
    run.env["P33_GAMES"] = str(run.root / "Games")
    run.env["PLAYMATCH_API_URL"] = "http://127.0.0.1:3346"
    receipt = {
        "scenario": scenario,
        "dialect": driver,
        "passed": False,
        "description_stages": [],
        "source_hashes": {},
        "wire_requests": [],
    }
    try:
        (run.evidence / "observations.jsonl").touch()
        if scenario == "authority":
            (run.evidence / "enable-authority").touch()
        run.start()
        start(run, initialize=True)
        call(run, "setup", "setup")
        from phase34_fixtures import source_manifest

        alternate = run.root / "Games/alternate/pc/Known.Game/Base"
        alternate.mkdir(parents=True)
        (alternate / "game.bin").write_bytes(b"different owned source")
        run.before = source_manifest(run.root / "Games")
        (run.evidence / "source-before.json").write_text(
            json.dumps(run.before, indent=2)
        )
        stage(run, "cold")
        if scenario == "descriptions":
            descriptions(run, receipt)
        elif scenario == "discovery-tail":
            call(run, "seed", "seed")
            stage(run, "adopt", action="adopt")
            call(run, "complete", "complete-controls")
            discovery_tail(run, receipt)
        else:
            from phase36_description_authority import run_cases

            run_cases(run, receipt)
        receipt["wire_requests"] = [
            row for row in observations(run) if row["kind"] == "provider_http"
        ]
        receipt["observed_worker"] = any(
            row["kind"] == "description_worker_boot" for row in observations(run)
        )
        receipt["source_hashes"] = read_json(run.evidence / "code-before.json")
        receipt["passed"] = True
    except BaseException as error:
        receipt["error"] = str(error)
        raise
    finally:
        try:
            run.close()
        finally:
            path = run.evidence / "cleanup.json"
            receipt["cleanup"] = read_json(path) if path.exists() else {}
            (run.evidence / "phase36-result.json").write_text(
                json.dumps(receipt, indent=2)
            )
            print("PHASE36_EVIDENCE", run.evidence, flush=True)
    validate_receipt(receipt)
    return run.evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dialect", choices=("mariadb", "postgresql"), required=True)
    parser.add_argument(
        "--scenario",
        choices=("descriptions", "authority", "discovery-tail"),
        required=True,
    )
    args = parser.parse_args()
    execute(args.dialect, args.scenario)


if __name__ == "__main__":
    main()
