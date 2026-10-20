"""Authenticated HTTP acceptance and disposable fixture state inspection."""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase33_collection_fixture import authority  # noqa: E402

EVIDENCE = Path("/phase34/evidence")


def login(create=False):
    import httpx

    from handler.auth.constants import Scope

    client = httpx.Client(base_url="http://127.0.0.1:3344", timeout=20)
    client.get("/api/heartbeat").raise_for_status()
    client.headers["x-csrftoken"] = client.cookies["romm_csrftoken"]
    if create:
        client.post(
            "/api/users",
            json={
                "username": "phase35-admin",
                "email": "phase35@example.test",
                "password": os.environ["PHASE34_RUN_TOKEN"],
                "role": "admin",
            },
        ).raise_for_status()
    response = client.post(
        "/api/token",
        data={
            "grant_type": "password",
            "username": "phase35-admin",
            "password": os.environ["PHASE34_RUN_TOKEN"],
            "scope": " ".join(scope.value for scope in Scope),
        },
    )
    response.raise_for_status()
    client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
    return client


def request(client, method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json()


def wait(client, identity):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        row = request(client, "GET", "/api/scan-operations/" + identity)
        if row["state"] in {"completed", "failed", "cancelled", "interrupted"}:
            if row["state"] != "completed":
                raise RuntimeError("actual worker terminated: " + json.dumps(row))
            return row
        time.sleep(0.1)
    raise RuntimeError("actual worker deadline")


def catalog():
    from sqlalchemy import select

    from config import RESOURCES_BASE_PATH
    from handler.database.base_handler import sync_session
    from models.rom import Rom, RomComponent, RomComponentManifestMember, RomFile
    from models.scan_collection import ScanCollectionFolder
    from models.scan_inventory import ScanInventoryBaseline, ScanMetadataRetry
    from models.storage import PlatformStorageMapping

    media = []
    resources = Path(RESOURCES_BASE_PATH)
    if not resources.resolve().is_relative_to("/phase34/owned"):
        raise RuntimeError("media outside generated owned volume")
    for target in sorted(resources.rglob("phase35-preserved-cover.bin")):
        if target.is_symlink() or not target.is_file():
            raise RuntimeError("invalid owned media identity")
        stat = target.stat()
        media.append(
            {
                "path": target.relative_to(resources).as_posix(),
                "device": stat.st_dev,
                "inode": stat.st_ino,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )
    with sync_session() as session:
        result = {
            "roms": [
                {
                    "id": row.id,
                    "name": row.fs_name,
                    "path": row.fs_path,
                    "steam_id": row.steam_id,
                    "incarnation": row.incarnation_token,
                    "cover": row.path_cover_s,
                }
                for row in session.scalars(select(Rom))
            ],
            "files": [
                {
                    "rom_id": row.rom_id,
                    "name": row.file_name,
                    "path": row.file_path,
                    "size": row.file_size_bytes,
                    "id": row.id,
                    "incarnation": row.incarnation_token,
                    "missing": row.missing_from_fs,
                }
                for row in session.scalars(select(RomFile))
            ],
            "components": [
                {
                    "id": row.id,
                    "rom_id": row.rom_id,
                    "kind": str(row.kind),
                    "name": row.relative_path,
                }
                for row in session.scalars(select(RomComponent))
            ],
            "members": [
                {
                    "id": row.id,
                    "component_id": row.component_id,
                    "path": row.relative_path,
                    "size": row.size_bytes,
                    "sha256": row.sha256,
                    "missing": row.missing_from_fs,
                }
                for row in session.scalars(select(RomComponentManifestMember))
            ],
            "media": media,
            "baselines": [
                {
                    "rom_id": row.rom_id,
                    "reusable": row.reusable,
                    "digest": row.inventory_digest,
                    "identity": row.identity_digest,
                    "incarnation": row.rom_incarnation,
                }
                for row in session.scalars(select(ScanInventoryBaseline))
            ],
            "retries": [
                {
                    "rom_id": row.rom_id,
                    "streak": row.no_match_streak,
                    "requested": row.last_request_at is not None,
                    "due": (
                        row.next_eligible_at.isoformat()
                        if row.next_eligible_at
                        else None
                    ),
                }
                for row in session.scalars(select(ScanMetadataRetry))
            ],
            "collections": [
                row.parent_relative_path
                for row in session.scalars(select(ScanCollectionFolder))
            ],
            "mappings": [
                {"id": row.id, "version": row.version, "platform": row.platform_id}
                for row in session.scalars(select(PlatformStorageMapping))
            ],
        }
        return {
            key: sorted(value, key=lambda row: json.dumps(row, sort_keys=True))
            for key, value in result.items()
        }


def seed_known():
    from sqlalchemy import select

    from config import LIBRARY_BASE_PATH, RESOURCES_BASE_PATH
    from handler.database.base_handler import sync_session
    from models.rom import Rom
    from models.storage import StorageRoot

    with sync_session.begin() as session:
        rom = session.scalar(select(Rom).where(Rom.fs_name == "Known.Game"))
        if rom is None:
            raise RuntimeError("identified fixture row missing")
        alternate_path = Path(LIBRARY_BASE_PATH) / "alternate"
        if not (alternate_path / "pc/Known.Game/Base/game.bin").is_file():
            raise RuntimeError("alternate synthetic root missing")
        session.add(
            StorageRoot(
                name="phase35-alternate",
                container_path=str(alternate_path),
                mode="external_read_only",
                active=True,
            )
        )
        rom.steam_id = 42
        relative = rom.fs_resources_path + "/phase35-preserved-cover.bin"
        target = Path(RESOURCES_BASE_PATH) / relative
        if target.exists():
            raise RuntimeError("fixture media already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"phase35 preserved owned media")
        rom.path_cover_s = relative


def scheduled():
    from handler.metadata import meta_steam_handler
    from tasks.scheduled import scan_library

    for name, handler in vars(scan_library).items():
        if name.startswith("meta_") and hasattr(handler, "is_enabled"):
            handler.is_enabled = lambda: False
    meta_steam_handler.is_enabled = lambda: True
    scan_library.ENABLE_SCHEDULED_RESCAN = True
    result = asyncio.run(scan_library.scan_library_task.run())
    if not result.get("operation_id"):
        raise RuntimeError("actual scheduler did not accept an operation")
    return result["operation_id"]


def authority_case(client, platform, case):
    from phase35_incremental_assertions import assert_authority
    from phase35_incremental_barrier import mutate, restore_mutation
    from rq.job import Job

    from handler.database.scan_operations_handler import DBScanOperationsHandler
    from handler.redis_handler import redis_client

    phase, revocation = case.split("-", 1)
    control = {"case": case, "phase": phase, "revocation": revocation}
    barrier_request = EVIDENCE / "barrier-request.json"
    if barrier_request.exists():
        raise RuntimeError("barrier already armed")
    barrier_request.write_text(json.dumps(control))
    payload = {
        "request_key": str(uuid4()),
        "platforms": [platform["id"]],
        "apis": ["steam"],
        "type": "quick",
    }
    identity = request(client, "POST", "/api/scan-operations", json=payload)["id"]
    reached = EVIDENCE / (case + "-reached.json")
    deadline = time.monotonic() + 30
    while not reached.exists():
        if time.monotonic() > deadline:
            raise RuntimeError("actual worker did not reach barrier")
        time.sleep(0.05)
    barrier = json.loads(reached.read_text())
    if barrier["operation"] != identity:
        raise RuntimeError("foreign operation reached authority barrier")
    repository = DBScanOperationsHandler()
    before_stats = repository.execution(identity)["scan_stats"]
    before = catalog()
    restore = mutate(barrier)
    mutated = catalog()
    (EVIDENCE / (case + "-release.json")).write_text(json.dumps(control))
    state = repository.execution(identity)
    job = Job.fetch(state["rq_job_id"], connection=redis_client)
    deadline = time.monotonic() + 30
    while True:
        job_status = job.get_status(refresh=True).value
        if job_status in {"finished", "failed", "stopped"}:
            break
        if time.monotonic() > deadline:
            raise RuntimeError("revoked worker did not exit")
        time.sleep(0.05)
    state = repository.execution(identity)
    result = {
        "barrier": barrier,
        "before": before,
        "mutated": mutated,
        "after": catalog(),
        "state": state["state"],
        "job_status": job_status,
        "stats_before": before_stats,
        "stats_after": state["scan_stats"],
        "intentional_mutation": restore,
    }
    (EVIDENCE / (case + "-authority.json")).write_text(json.dumps(result, indent=2))
    assert_authority(result)
    if before_stats != state["scan_stats"]:
        raise RuntimeError("revoked worker changed counters after barrier")
    restore_mutation(restore, identity)
    barrier_request.unlink()
    result["fixture_restored"] = True
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "setup",
            "scan",
            "scheduled",
            "inspect",
            "seed",
            "age",
            "promote",
            "authority",
        ),
    )
    parser.add_argument("--stage", default="inspect")
    parser.add_argument("--mode", default="quick")
    args = parser.parse_args()
    authority()
    if args.action == "seed":
        seed_known()
        return
    if args.action == "age":
        from sqlalchemy import update

        from handler.database.base_handler import sync_session
        from models.scan_inventory import ScanInventoryBaseline, ScanMetadataRetry

        with sync_session.begin() as session:
            session.execute(
                update(ScanInventoryBaseline).values(
                    completed_at=datetime.now() - timedelta(days=2)
                )
            )
            session.execute(
                update(ScanMetadataRetry).values(
                    next_eligible_at=datetime.now() - timedelta(days=1)
                )
            )
        return
    if args.action == "inspect":
        result = catalog()
    else:
        with closing(login(create=args.action == "setup")) as client:
            if args.action == "setup":
                result = request(
                    client,
                    "POST",
                    "/api/setup/folders/assign",
                    json={
                        "assignments": [
                            {"folder_name": "pc", "platform_slug": "win"},
                            {"folder_name": "My Games", "platform_slug": "snes"},
                        ]
                    },
                )
            else:
                platforms = request(client, "GET", "/api/platforms")
                win = next(row for row in platforms if row["slug"] == "win")
                if args.action == "authority":
                    result = authority_case(client, win, args.stage)
                    (EVIDENCE / (args.stage + ".json")).write_text(
                        json.dumps(result, indent=2)
                    )
                    return
                if args.action == "scheduled":
                    identity = scheduled()
                else:
                    payload = {
                        "request_key": str(uuid4()),
                        "platforms": [win["id"]],
                        "apis": ["steam"],
                        "type": args.mode,
                    }
                    if args.action == "promote":
                        data = catalog()
                        parent = next(
                            row for row in data["roms"] if row["name"] == "Castlevania"
                        )
                        mapping = next(
                            row
                            for row in data["mappings"]
                            if row["platform"] == win["id"]
                        )
                        payload.update(
                            filesystem_scope_paths={
                                win["fs_slug"]: "Castlevania/Belmonts.Curse"
                            },
                            collection_promotion={
                                "parent_rom_id": parent["id"],
                                "mapping_id": mapping["id"],
                                "expected_revision": mapping["version"],
                                "parent_relative_path": "Castlevania",
                                "selected_child_relative_path": "Castlevania/Belmonts.Curse",
                            },
                        )
                    identity = request(
                        client, "POST", "/api/scan-operations", json=payload
                    )["id"]
                result = wait(client, identity)
                result["catalog"] = catalog()
    (EVIDENCE / (args.stage + ".json")).write_text(json.dumps(result, indent=2))
    print("PHASE35", args.stage, result.get("state", "fixture"))


if __name__ == "__main__":
    main()
