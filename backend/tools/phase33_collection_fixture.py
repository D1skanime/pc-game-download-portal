#!/usr/bin/env python3
"""Synthetic-only collection UAT data and calls to registered application tasks."""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from phase34_target_guard import validate_target

RECEIPT = Path("/phase34/evidence/phase33-collection-seed.json")
NOTE = "Retain the synthetic parent operator context"


def authority():
    validate_target()
    backend = str(Path(__file__).resolve().parents[1])
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from handler.database.base_handler import sync_engine

    validate_target(resolved_url=sync_engine.url)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_parent(parent_id):
    authority()
    from sqlalchemy import select

    from config import LIBRARY_BASE_PATH, RESOURCES_BASE_PATH
    from handler.database.base_handler import sync_session
    from models.rom import Rom, RomNote, RomUser
    from models.user import User

    if RECEIPT.exists():
        raise RuntimeError("synthetic parent fixture already seeded")
    resource_root = Path(RESOURCES_BASE_PATH).resolve()
    if not resource_root.is_relative_to(Path("/phase34/owned")):
        raise RuntimeError("fixture resources are outside the generated owned volume")
    source = Path(LIBRARY_BASE_PATH) / "pc/Castlevania/Belmonts.Curse/game.part01.rar"
    if not source.is_file():
        raise RuntimeError("expected synthetic Games fixture is missing")
    with sync_session.begin() as session:
        parent = session.get(Rom, parent_id)
        if parent is None or (parent.fs_name, parent.fs_path) != ("Castlevania", "pc"):
            raise RuntimeError("fixture parent must be the synthetic Castlevania row")
        user = session.scalar(select(User).where(User.username == "phase33-admin"))
        sibling = session.scalar(
            select(Rom).where(
                Rom.platform_id == parent.platform_id, Rom.id != parent.id
            )
        )
        if user is None or sibling is None:
            raise RuntimeError(
                "synthetic administrator and shared-reference control required"
            )
        relative = parent.fs_resources_path
        folder = resource_root / relative
        folder.mkdir(parents=True, exist_ok=True)
        names = (
            "uat-exclusive-cover.png",
            "uat-exclusive-manual.pdf",
            "uat-shared-cover.png",
        )
        files = {}
        for name in names:
            target = folder / name
            if target.exists() or target.is_symlink():
                raise RuntimeError("refusing to replace an existing fixture resource")
            target.write_bytes(
                ("synthetic exclusively controlled UAT resource " + name).encode()
            )
            files[name] = {"path": str(target), "sha256": digest(target)}
        parent.name = "Mistaken collection parent metadata"
        parent.path_cover_s = relative + "/" + names[0]
        parent.path_manual = relative + "/" + names[1]
        parent.path_cover_l = relative + "/" + names[2]
        sibling.path_cover_s = relative + "/" + names[2]
        session.add(
            RomNote(
                rom_id=parent.id,
                user_id=user.id,
                title="UAT retained parent context",
                content=NOTE,
                is_public=False,
            )
        )
        flags = session.scalar(
            select(RomUser).where(
                RomUser.rom_id == parent.id, RomUser.user_id == user.id
            )
        )
        if flags is None:
            flags = RomUser(rom_id=parent.id, user_id=user.id)
            session.add(flags)
        flags.backlogged, flags.rating = True, 5
        receipt = {
            "parent_id": parent.id,
            "parent_incarnation": parent.incarnation_token,
            "platform_id": parent.platform_id,
            "user_id": user.id,
            "shared_rom_id": sibling.id,
            "files": files,
            "source": {"path": str(source), "sha256": digest(source)},
        }
    RECEIPT.write_text(json.dumps(receipt, indent=2))
    return {
        "seeded": True,
        "parent_id": parent_id,
        "exclusive_files": 2,
        "shared_control_files": 1,
    }


def inspect_parent(parent_id):
    authority()
    from sqlalchemy import select

    from handler.database.base_handler import sync_session
    from models.catalog_lifecycle import OwnedCleanupIntent, RetainedCatalogIdentity
    from models.rom import Rom, RomNote, RomUser
    from models.scan_collection import ScanCollectionFolder

    receipt = json.loads(RECEIPT.read_text())
    if receipt["parent_id"] != parent_id:
        raise RuntimeError("fixture identity mismatch")
    with sync_session() as session:
        parent = session.get(Rom, parent_id)
        row = session.scalar(
            select(ScanCollectionFolder).where(
                ScanCollectionFolder.parent_rom_id == parent_id,
                ScanCollectionFolder.parent_incarnation
                == receipt["parent_incarnation"],
            )
        )
        retained = session.scalar(
            select(RetainedCatalogIdentity).where(
                RetainedCatalogIdentity.detached_rom_id == parent_id,
                RetainedCatalogIdentity.file_name == "Castlevania",
            )
        )
        audit = row.audit if row else {}
        notes = audit.get("notes", [])
        flags = audit.get("rom_users", [])
        retained_ok = bool(retained and retained.retained_audit == audit)
        child = session.scalar(
            select(Rom).where(
                Rom.platform_id == receipt["platform_id"],
                Rom.fs_name == "Belmonts.Curse",
            )
        )
        child_notes = (
            list(session.scalars(select(RomNote).where(RomNote.rom_id == child.id)))
            if child
            else []
        )
        child_flags = (
            list(session.scalars(select(RomUser).where(RomUser.rom_id == child.id)))
            if child
            else []
        )
        intents = (
            list(
                session.scalars(
                    select(OwnedCleanupIntent).where(
                        OwnedCleanupIntent.retained_catalog_id == retained.id
                    )
                )
            )
            if retained
            else []
        )
        states = [str(intent.state) for intent in intents]
    files = receipt["files"]
    exclusive = [files["uat-exclusive-cover.png"], files["uat-exclusive-manual.pdf"]]
    shared = files["uat-shared-cover.png"]
    source = receipt["source"]
    return {
        "classified": row is not None,
        "parent_absent": parent is None,
        "user_state_retained": retained_ok
        and any(note.get("content") == NOTE for note in notes)
        and any(
            flag.get("backlogged") is True and flag.get("rating") == 5 for flag in flags
        ),
        "user_state_not_attached_to_child": not any(
            note.content == NOTE for note in child_notes
        )
        and not any(flag.backlogged or flag.rating == 5 for flag in child_flags),
        "owned_media_removed": all(
            not Path(item["path"]).exists() for item in exclusive
        ),
        "shared_media_preserved": Path(shared["path"]).is_file()
        and digest(Path(shared["path"])) == shared["sha256"],
        "source_media_preserved": Path(source["path"]).is_file()
        and digest(Path(source["path"])) == source["sha256"],
        "cleanup_states": states,
    }


def run_cleanup():
    authority()
    from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task

    asyncio.run(owned_media_cleanup_task.run())
    return {"scheduled_cleanup_invoked": True}


def run_scheduled(platform_id):
    authority()
    os.environ["ENABLE_SCHEDULED_RESCAN"] = "true"
    from handler.database.base_handler import sync_session
    from models.platform import Platform
    from models.scan_operation import ScanOperation
    from tasks.scheduled import scan_library

    with sync_session() as session:
        platform = session.get(Platform, platform_id)
        if platform is None or platform.slug != "win":
            raise RuntimeError(
                "scheduled fixture requires the mapped synthetic Windows platform"
            )
    # External metadata is irrelevant to source discovery in this isolated fixture.
    for name, handler in vars(scan_library).items():
        if name.startswith("meta_") and hasattr(handler, "is_enabled"):
            handler.is_enabled = lambda: False
    scan_library.ENABLE_SCHEDULED_RESCAN = True
    outcome = asyncio.run(scan_library.scan_library_task.run())
    operation_id = outcome.get("operation_id")
    if not operation_id:
        raise RuntimeError("registered scheduled task did not accept an operation")
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        with sync_session() as session:
            operation = session.get(ScanOperation, operation_id)
            state = str(operation.state) if operation else "missing"
        if state == "completed":
            return {
                "completed": True,
                "operation_id": operation_id,
                "metadata_providers": [],
                "entrypoint": "scan_library_task.run",
                "scan_stats": operation.scan_stats,
            }
        if state in {"failed", "cancelled", "interrupted"}:
            raise RuntimeError(
                "scheduled operation terminated without completion: " + state
            )
        time.sleep(0.2)
    raise RuntimeError("scheduled operation completion deadline")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("seed-parent", "inspect-parent", "run-cleanup", "run-scheduled"),
    )
    parser.add_argument("identity", type=int, nargs="?")
    args = parser.parse_args()
    if args.action != "run-cleanup" and (args.identity is None or args.identity < 1):
        parser.error("a positive synthetic identity is required")
    if args.action == "seed-parent":
        result = seed_parent(args.identity)
    elif args.action == "inspect-parent":
        result = inspect_parent(args.identity)
    elif args.action == "run-scheduled":
        result = run_scheduled(args.identity)
    else:
        result = run_cleanup()
    print("PGDP33_FIXTURE_JSON:" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
