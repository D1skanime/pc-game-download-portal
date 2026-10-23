"""Actual description dispatch/write barriers and disposable authority mutations."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from phase35_incremental_barrier import (
    REVOCATIONS,
    replace_fixture_incarnation,
    restore_mutation,
)

EVIDENCE = Path("/phase34/evidence")


def pause(phase, provider, rom_id):
    from phase33_collection_fixture import authority

    from handler.database.scan_write_fence import require_scan_write_context

    path = EVIDENCE / "description-barrier.json"
    if not path.exists():
        return
    control = json.loads(path.read_text())
    if control["phase"] != phase or control["provider"] != provider:
        return
    authority()
    context = require_scan_write_context()
    reached = {
        **control,
        "operation": context.operation_id,
        "attempt": context.attempt_id,
        "lease_owner": context.lease_owner,
        "rom_id": rom_id,
    }
    (EVIDENCE / (control["case"] + "-reached.json")).write_text(json.dumps(reached))
    release = EVIDENCE / (control["case"] + "-release.json")
    deadline = time.monotonic() + 45
    while not release.exists():
        if time.monotonic() > deadline:
            raise RuntimeError("actual description barrier release deadline")
        time.sleep(0.05)
    if json.loads(release.read_text()) != control:
        raise RuntimeError("description barrier release mismatch")
    authority()


def install():
    from handler import scan_description_retry
    from handler.database import db_rom_handler

    original_dispatch = scan_description_retry.dispatch_description
    original_write = db_rom_handler.apply_description_patch

    async def detection(coordinator, work, identity):
        pause("detection", identity.provider, work.rom_id)
        return await original_dispatch(coordinator, work, identity)

    def completion(**kwargs):
        pause("completion", kwargs["provider"], kwargs["binding"].rom_id)
        return original_write(**kwargs)

    scan_description_retry.dispatch_description = detection
    db_rom_handler.apply_description_patch = completion


def mutate(barrier):
    from phase33_collection_fixture import authority
    from sqlalchemy import select

    from config import LIBRARY_BASE_PATH
    from handler.database.base_handler import sync_session
    from models.rom import Rom
    from models.scan_operation import ScanOperation
    from models.storage import PlatformStorageMapping, StorageRoot

    authority()
    kind = barrier["revocation"]
    if kind not in REVOCATIONS:
        raise RuntimeError("unknown fixture revocation")
    with sync_session.begin() as session:
        operation = session.get(ScanOperation, barrier["operation"])
        if (operation.state, operation.attempt_id, operation.lease_owner) != (
            "running",
            barrier["attempt"],
            barrier["lease_owner"],
        ):
            raise RuntimeError("actual barrier lost operation custody")
        rom = session.get(Rom, barrier["rom_id"])
        expected = "Known.Game" if barrier["provider"] == "steam" else "Control.sfc"
        if rom.fs_name != expected:
            raise RuntimeError("foreign fixture ROM")
        mapping = session.scalar(
            select(PlatformStorageMapping).where(
                PlatformStorageMapping.platform_id == rom.platform_id,
                PlatformStorageMapping.active.is_(True),
            )
        )
        root = session.get(StorageRoot, mapping.storage_root_id)
        if root.container_path != LIBRARY_BASE_PATH:
            raise RuntimeError("foreign fixture source")
        if kind == "revision":
            target, field, value = mapping, "version", mapping.version + 1
        elif kind == "root":
            target, field, value = root, "active", False
        elif kind == "root-binding":
            alternate = session.scalar(
                select(StorageRoot).where(StorageRoot.name == "phase35-alternate")
            )
            if alternate.container_path != str(Path(LIBRARY_BASE_PATH) / "alternate"):
                raise RuntimeError("foreign alternate root")
            target, field, value = mapping, "storage_root_id", alternate.id
        elif kind == "incarnation":
            target, field, value = rom, "incarnation_token", uuid4().hex
        elif kind == "lease":
            target, field, value = (
                operation,
                "lease_expires_at",
                datetime.now() - timedelta(seconds=1),
            )
        elif kind == "attempt":
            target, field, value = operation, "attempt_id", str(uuid4())
        else:
            target, field, value = operation, "intentional_cancel", True
        original_updated_at = rom.updated_at.isoformat()
        old = getattr(target, field)
        if kind == "incarnation":
            replace_fixture_incarnation(session, target.id, old, value)
        else:
            setattr(target, field, value)
        model, identity = type(target), target.id
        restoration = {
            "kind": kind,
            "field": field,
            "id": identity,
            "old": old.isoformat() if isinstance(old, datetime) else old,
            "new": value.isoformat() if isinstance(value, datetime) else value,
        }
    with sync_session() as session:
        if getattr(session.get(model, identity), field) != value:
            raise RuntimeError("fixture revocation was not persisted")
    if kind == "incarnation":
        restoration["rom_updated_at"] = original_updated_at
    restoration["verified"] = True
    return restoration


def execute_case(client, provider, case):
    from phase33_collection_fixture import authority
    from phase36_description_assertions import assert_authority
    from phase36_description_client import accept, catalog
    from rq.job import Job

    from handler.database.scan_operations_handler import DBScanOperationsHandler
    from handler.redis_handler import redis_client

    authority()
    phase, revocation = case.split("-", 1)
    name = provider + "-" + case
    control = {
        "case": name,
        "phase": phase,
        "revocation": revocation,
        "provider": provider,
    }
    request = EVIDENCE / "description-barrier.json"
    if request.exists():
        raise RuntimeError("description barrier already armed")
    request.write_text(json.dumps(control))
    operation_id = accept(client, provider=provider)
    reached = EVIDENCE / (name + "-reached.json")
    deadline = time.monotonic() + 45
    while not reached.exists():
        if time.monotonic() > deadline:
            raise RuntimeError("actual description worker did not reach " + name)
        time.sleep(0.05)
    barrier = json.loads(reached.read_text())
    if barrier["operation"] != operation_id:
        raise RuntimeError("foreign operation at description barrier")
    repository = DBScanOperationsHandler()
    state = repository.execution(operation_id)
    before_stats = state["scan_stats"]
    before = catalog()
    restoration = mutate(barrier)
    mutated = catalog()
    (EVIDENCE / (name + "-release.json")).write_text(json.dumps(control))
    job = Job.fetch(state["rq_job_id"], connection=redis_client)
    deadline = time.monotonic() + 45
    while job.get_status(refresh=True).value not in {"finished", "failed", "stopped"}:
        if time.monotonic() > deadline:
            raise RuntimeError("revoked actual worker did not exit")
        time.sleep(0.05)
    state = repository.execution(operation_id)
    result = {
        "barrier": barrier,
        "before": before,
        "mutated": mutated,
        "after": catalog(),
        "stats_before": before_stats,
        "stats_after": state["scan_stats"],
        "state": state["state"],
        "job_status": job.get_status(refresh=True).value,
        "intentional_mutation": restoration,
    }
    (EVIDENCE / (name + "-authority.json")).write_text(json.dumps(result, indent=2))
    try:
        assert_authority(result)
    finally:
        restore_mutation(restoration, operation_id)
        if restoration["kind"] == "incarnation":
            from sqlalchemy import text

            from handler.database.base_handler import sync_session

            authority()
            with sync_session.begin() as session:
                changed = session.execute(
                    text(
                        "UPDATE roms SET updated_at=:stamp WHERE id=:identity AND incarnation_token=:token"
                    ),
                    {
                        "stamp": datetime.fromisoformat(restoration["rom_updated_at"]),
                        "identity": restoration["id"],
                        "token": restoration["old"],
                    },
                )
                if changed.rowcount != 1:
                    raise RuntimeError("incarnation timestamp restoration lost custody")
        request.unlink()
    restored = catalog()
    (EVIDENCE / (name + "-restored.json")).write_text(json.dumps(restored, indent=2))
    result["fixture_restored"] = restored == before
    if not result["fixture_restored"]:
        raise RuntimeError("fixture authority not exactly restored")
    return result


def run_cases(run, receipt):
    from phase36_description_probe import call, stage

    call(run, "seed", "seed")
    stage(run, "adopt", action="adopt")
    result = call(run, "authority-suite", "authority-suite")
    receipt.update(result)
    receipt["description_stages"].append("authority")


def suite(client):
    from phase36_description_fixture import reset_one

    result: dict[str, Any] = {"authority_cases": []}
    for provider in ("steam", "ss"):
        for phase in ("detection", "completion"):
            for revocation in REVOCATIONS:
                name = phase + "-" + revocation
                reset_one(provider)
                observed = execute_case(client, provider, name)
                result["authority_cases"].append(
                    {
                        "provider": provider,
                        "case": name,
                        "operation": observed["barrier"]["operation"],
                        "restored": observed["fixture_restored"],
                        "job_status": observed["job_status"],
                    }
                )
                print(
                    "PASS actual authority",
                    provider,
                    name,
                    observed["state"],
                    flush=True,
                )
    result["auth_cases"] = auth_cases(client)
    result["concurrent_cases"] = []
    for provider in ("steam", "ss"):
        reset_one(provider)
        observed = concurrent_case(client, provider)
        (EVIDENCE / ("manual-" + provider + ".json")).write_text(
            json.dumps(observed, indent=2)
        )
        result["concurrent_cases"].append(
            {
                "provider": provider,
                "operation": observed["barrier"]["operation"],
                "stale_status": observed["stale_status"],
                "job_status": observed["job_status"],
            }
        )
    return result


def auth_cases(client):
    import os

    import httpx
    from phase33_collection_fixture import authority
    from phase36_description_client import catalog, request

    from config.config_manager import config_manager

    authority()
    rom = next(row for row in catalog()["descriptions"] if row["name"] == "Known.Game")
    before = request(client, "GET", "/api/config")["SCAN_LANGUAGE_PRIORITY"]
    with httpx.Client(base_url="http://127.0.0.1:3344", timeout=20) as limited:
        limited.get("/api/heartbeat").raise_for_status()
        limited.headers["x-csrftoken"] = limited.cookies["romm_csrftoken"]
        token = request(
            limited,
            "POST",
            "/api/token",
            data={
                "grant_type": "password",
                "username": "phase35-admin",
                "password": os.environ["PHASE34_RUN_TOKEN"],
                "scope": "me.read me.write roms.read",
            },
        )
        limited.headers["Authorization"] = "Bearer " + token["access_token"]
        config_response = limited.put(
            "/api/config/scan/language",
            json={"language_priority": ["fr"], "expected_language_priority": before},
        )
        description_response = limited.put(
            "/api/roms/" + str(rom["id"]) + "/description",
            json={
                "locale": "de",
                "description": "Unauthorized",
                "expected_version": rom["updated_at"],
            },
        )
    if config_response.status_code != 403 or description_response.status_code != 403:
        raise RuntimeError(
            "scope-limited caller changed global language or description"
        )
    conflict = client.put(
        "/api/config/scan/language",
        json={
            "language_priority": ["fr"],
            "expected_language_priority": ["invalid-stale"],
        },
    )
    if conflict.status_code != 409:
        raise RuntimeError("config compare-and-swap did not conflict")
    config_path = Path(config_manager.config_file)
    if (
        not config_path.resolve().is_relative_to("/phase34/owned")
        or config_path.is_symlink()
    ):
        raise RuntimeError("read-only check refused foreign configuration")
    original_mode = config_path.stat().st_mode & 0o777
    try:
        config_path.chmod(0o400)
        readonly = client.put(
            "/api/config/scan/language",
            json={"language_priority": ["fr"], "expected_language_priority": before},
        )
        if readonly.status_code != 500:
            raise RuntimeError("read-only configuration reported false success")
    finally:
        config_path.chmod(original_mode)
    if request(client, "GET", "/api/config")["SCAN_LANGUAGE_PRIORITY"] != before:
        raise RuntimeError("failed config mutation changed authority")
    return {
        "me_write_global_status": config_response.status_code,
        "readonly_description_status": description_response.status_code,
        "cas_status": conflict.status_code,
        "readonly_config_status": readonly.status_code,
        "preserved_priority": before,
    }


def concurrent_case(client, provider):
    from phase33_collection_fixture import authority
    from phase36_description_client import accept, catalog, language, request
    from rq.job import Job

    from handler.database.base_handler import sync_session
    from handler.database.scan_operations_handler import DBScanOperationsHandler
    from handler.redis_handler import redis_client
    from models.scan_operation import ScanOperation

    authority()
    name = "concurrent-" + provider
    control = {
        "case": name,
        "phase": "completion",
        "revocation": "manual",
        "provider": provider,
    }
    barrier_path = EVIDENCE / "description-barrier.json"
    barrier_path.write_text(json.dumps(control))
    identity = accept(client, locale="de", provider=provider)
    reached = EVIDENCE / (name + "-reached.json")
    deadline = time.monotonic() + 45
    while not reached.exists():
        if time.monotonic() > deadline:
            raise RuntimeError("manual concurrency did not reach actual completion")
        time.sleep(0.05)
    barrier = json.loads(reached.read_text())
    if barrier["operation"] != identity:
        raise RuntimeError("foreign manual concurrency operation")
    rom = next(
        row for row in catalog()["descriptions"] if row["id"] == barrier["rom_id"]
    )
    payload = {
        "locale": "de",
        "description": "Concurrent protected Deutsch " + provider,
        "expected_version": rom["updated_at"],
    }
    saved = request(
        client, "PUT", "/api/roms/" + str(rom["id"]) + "/description", json=payload
    )
    stale = client.put(
        "/api/roms/" + str(rom["id"]) + "/description",
        json={**payload, "description": "Stale replacement"},
    )
    if stale.status_code != 409:
        raise RuntimeError("stale manual description did not return409")
    with sync_session() as session:
        captured_before = session.get(ScanOperation, identity).command
    language(client, "fr")
    (EVIDENCE / (name + "-release.json")).write_text(json.dumps(control))
    repository = DBScanOperationsHandler()
    state = repository.execution(identity)
    job = Job.fetch(state["rq_job_id"], connection=redis_client)
    deadline = time.monotonic() + 45
    while job.get_status(refresh=True).value not in {"finished", "failed", "stopped"}:
        if time.monotonic() > deadline:
            raise RuntimeError("concurrent actual worker did not exit")
        time.sleep(0.05)
    with sync_session() as session:
        captured_after = session.get(ScanOperation, identity).command
    if (
        captured_before != captured_after
        or captured_after["request"]["metadata_locale"] != "de"
    ):
        raise RuntimeError("accepted immutable language changed")
    current = request(client, "GET", "/api/roms/" + str(rom["id"]))
    if current["manual_metadata"]["descriptions"]["de"] != payload["description"]:
        raise RuntimeError("provider overwrote concurrent manual edit")
    durable = next(row for row in catalog()["descriptions"] if row["id"] == rom["id"])
    if durable[provider] != rom[provider]:
        raise RuntimeError("stale provider patch committed during manual edit")
    barrier_path.unlink()
    return {
        "barrier": barrier,
        "saved": saved,
        "stale_status": stale.status_code,
        "captured_before": captured_before,
        "captured_after": captured_after,
        "reloaded": current,
        "job_status": job.get_status(refresh=True).value,
    }
