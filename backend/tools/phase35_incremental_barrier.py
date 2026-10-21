"""Test-worker pause points and token-bound disposable authority mutations."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

EVIDENCE = Path("/phase34/evidence")
REVOCATIONS = (
    "revision",
    "root",
    "root-binding",
    "incarnation",
    "lease",
    "attempt",
    "cancel",
)


def pause(phase, rom_name):
    from phase33_collection_fixture import authority

    from handler.database.scan_write_fence import require_scan_write_context

    request = EVIDENCE / "barrier-request.json"
    if rom_name != "Known.Game" or not request.exists():
        return
    control = json.loads(request.read_text())
    if control["phase"] != phase:
        return
    authority()
    context = require_scan_write_context()
    reached = EVIDENCE / (control["case"] + "-reached.json")
    reached.write_text(
        json.dumps(
            dict(
                control,
                operation=context.operation_id,
                attempt=context.attempt_id,
                lease_owner=context.lease_owner,
            )
        )
    )
    deadline = time.monotonic() + 30
    release = EVIDENCE / (control["case"] + "-release.json")
    while not release.exists():
        if time.monotonic() > deadline:
            raise RuntimeError("authority barrier release deadline")
        time.sleep(0.05)
    if json.loads(release.read_text()) != control:
        raise RuntimeError("authority barrier release identity mismatch")
    authority()


def install():
    from handler import windows_quick_execution as quick

    original_detection = quick.inspect_discovered_game
    original_completion = quick.prepare_quick_refresh

    async def detection(platform, fs_rom, rom, **kwargs):
        result = await original_detection(platform, fs_rom, rom, **kwargs)
        if result is not None:
            pause("detection", fs_rom["fs_name"])
        return result

    async def completion(context, handler, rom, **kwargs):
        result = await original_completion(context, handler, rom, **kwargs)
        pause("completion", rom.fs_name)
        return result

    quick.inspect_discovered_game = detection
    quick.prepare_quick_refresh = completion


def replace_fixture_incarnation(session, rom_id, expected, replacement):
    """Simulate external identity replacement only on a token-verified test database."""
    from phase33_collection_fixture import authority
    from sqlalchemy import text

    authority()
    changed = session.execute(
        text(
            "UPDATE roms SET incarnation_token=:replacement WHERE id=:rom_id AND incarnation_token=:expected"
        ),
        {"replacement": replacement, "rom_id": rom_id, "expected": expected},
    )
    if changed.rowcount != 1:
        raise RuntimeError("synthetic external identity no longer matches")


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
        raise RuntimeError("unknown authority mutation")
    with sync_session.begin() as session:
        operation = session.get(ScanOperation, barrier["operation"])
        if (operation.state, operation.attempt_id, operation.lease_owner) != (
            "running",
            barrier["attempt"],
            barrier["lease_owner"],
        ):
            raise RuntimeError("barrier no longer owns operation")
        rom = session.scalar(select(Rom).where(Rom.fs_name == "Known.Game"))
        mapping = session.scalar(
            select(PlatformStorageMapping).where(
                PlatformStorageMapping.platform_id == rom.platform_id,
                PlatformStorageMapping.active.is_(True),
            )
        )
        if rom is None or mapping is None:
            raise RuntimeError("synthetic authority identity missing")
        root = session.get(StorageRoot, mapping.storage_root_id)
        if root.container_path != LIBRARY_BASE_PATH:
            raise RuntimeError("unexpected synthetic source root")
        if kind == "revision":
            target, field, value = mapping, "version", mapping.version + 1
        elif kind == "root":
            target, field, value = root, "active", False
        elif kind == "root-binding":
            alternate = session.scalar(
                select(StorageRoot).where(StorageRoot.name == "phase35-alternate")
            )
            if alternate is None or alternate.container_path != str(
                Path(LIBRARY_BASE_PATH) / "alternate"
            ):
                raise RuntimeError("alternate synthetic root identity mismatch")
            original_bytes = (
                Path(root.container_path) / "pc/Known.Game/Base/game.bin"
            ).read_bytes()
            alternate_bytes = (
                Path(alternate.container_path) / "pc/Known.Game/Base/game.bin"
            ).read_bytes()
            if original_bytes == alternate_bytes:
                raise RuntimeError("alternate root must represent different content")
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
        old = getattr(target, field)
        if kind == "incarnation":
            replace_fixture_incarnation(session, target.id, old, value)
        else:
            setattr(target, field, value)
        restore = {
            "kind": kind,
            "field": field,
            "id": target.id,
            "old": old.isoformat() if isinstance(old, datetime) else old,
            "new": value.isoformat() if isinstance(value, datetime) else value,
        }
    with sync_session() as session:
        observed = getattr(session.get(type(target), target.id), field)
        if observed != value:
            raise RuntimeError("authority mutation was not persisted")
    restore["verified"] = True
    return restore


def restore_mutation(restore, operation_id):
    from phase33_collection_fixture import authority

    from handler.database.base_handler import sync_session
    from handler.database.scan_operations_handler import DBScanOperationsHandler
    from models.rom import Rom
    from models.scan_operation import ScanOperation
    from models.storage import PlatformStorageMapping, StorageRoot

    authority()
    model = {
        "revision": PlatformStorageMapping,
        "root-binding": PlatformStorageMapping,
        "root": StorageRoot,
        "incarnation": Rom,
    }.get(restore["kind"], ScanOperation)
    old = restore["old"]
    if restore["field"] == "lease_expires_at":
        old = datetime.fromisoformat(old)
    with sync_session.begin() as session:
        if restore["kind"] == "incarnation":
            replace_fixture_incarnation(session, restore["id"], restore["new"], old)
        else:
            setattr(session.get(model, restore["id"]), restore["field"], old)
    repository = DBScanOperationsHandler()
    state = repository.execution(operation_id)
    if state["state"] in {"running", "interrupted", "blocked"}:
        repository.transition(
            operation_id,
            state["version"],
            state["attempt_id"],
            "failed",
            cause_code="worker_failed",
            next_action="verify_source",
        )
