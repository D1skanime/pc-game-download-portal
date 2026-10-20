"""Successful game publication, checkpoint and parent retirement share one fence."""

import enum
import json
from datetime import datetime
from pathlib import PurePosixPath

from sqlalchemy import func, select

from handler.database import db_rom_handler
from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler
from handler.database.scan_operations_handler import DBScanOperationsHandler
from handler.database.scan_write_fence import (
    checked_scan_write,
    current_scan_write_context,
)
from handler.filesystem import fs_resource_handler
from handler.filesystem.scan_media_publication import ScanMediaBatch
from handler.scan_collection_policy import (
    digest_path,
    find_classification,
    mapping_binding,
)
from handler.storage.read_context import MappingReadContext
from logger.logger import log
from models.assets import Screenshot
from models.collection import CollectionRom
from models.rom import Rom, RomFile, RomNote, RomUser
from models.scan_collection import ScanCollectionFolder
from models.storage import PlatformStorageMapping

AUDIT_LIMIT = 128 * 1024


def _json_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    return value


def _audit(session, parent):
    result = {
        "parent_rom_id": parent.id,
        "parent_incarnation": parent.incarnation_token,
    }
    for key, model in (
        ("notes", RomNote),
        ("rom_users", RomUser),
        ("collections", CollectionRom),
        ("screenshots", Screenshot),
    ):
        rows = (
            session.execute(
                select(model.__table__).where(model.rom_id == parent.id).limit(1001)
            )
            .mappings()
            .all()
        )
        if len(rows) > 1000:
            raise ValueError("collection_audit_limit")
        result[key] = [
            {name: _json_value(value) for name, value in row.items()} for row in rows
        ]
    if len(json.dumps(result).encode()) > AUDIT_LIMIT:
        raise ValueError("collection_audit_limit")
    return result


def _promote(session, row, child, intent, cleanup):
    mapping = session.scalar(
        select(PlatformStorageMapping)
        .where(PlatformStorageMapping.id == intent["mapping_id"])
        .with_for_update(of=PlatformStorageMapping)
    )
    if mapping is None or (
        not mapping.active
        or not mapping.storage_root.active
        or mapping.version != intent["expected_revision"]
        or mapping.storage_root_id != intent["storage_root_id"]
        or mapping.relative_path != intent["mapping_relative_path"]
        or mapping_binding(mapping) != intent["binding_digest"]
    ):
        raise ValueError("collection_mapping_changed")
    child_relative = (
        (PurePosixPath(child.fs_path) / child.fs_name)
        .relative_to(PurePosixPath(mapping.relative_path))
        .as_posix()
    )
    if (
        child.platform_id != mapping.platform_id
        or child_relative != intent["selected_child_relative_path"]
    ):
        raise ValueError("collection_child_mismatch")
    if not session.scalar(
        select(func.count())
        .select_from(RomFile)
        .where(RomFile.rom_id == child.id, RomFile.missing_from_fs.is_(False))
    ):
        raise ValueError("collection_child_empty")
    prior = find_classification(session, mapping, intent["parent_relative_path"])
    parent = session.scalar(
        select(Rom).where(Rom.id == intent["parent_rom_id"]).with_for_update(of=Rom)
    )
    if prior is not None:
        if (
            prior.parent_incarnation != intent["parent_incarnation"]
            or parent is not None
        ):
            raise ValueError("collection_replay_incarnation_changed")
        return
    if parent is None or parent.incarnation_token != intent["parent_incarnation"]:
        raise ValueError("collection_parent_changed")
    parent_relative = (
        (PurePosixPath(parent.fs_path) / parent.fs_name)
        .relative_to(PurePosixPath(mapping.relative_path))
        .as_posix()
    )
    if (
        parent.platform_id != mapping.platform_id
        or parent_relative != intent["parent_relative_path"]
    ):
        raise ValueError("collection_parent_changed")
    if cleanup is None or cleanup["parent_incarnation"] != parent.incarnation_token:
        raise ValueError("collection_cleanup_evidence_missing")
    audit = _audit(session, parent)
    session.add(
        ScanCollectionFolder(
            mapping_id=mapping.id,
            storage_root_id=mapping.storage_root_id,
            mapping_relative_path=mapping.relative_path,
            binding_digest=intent["binding_digest"],
            parent_relative_path=intent["parent_relative_path"],
            path_digest=digest_path(intent["parent_relative_path"]),
            parent_rom_id=parent.id,
            parent_incarnation=parent.incarnation_token,
            selected_child_relative_path=intent["selected_child_relative_path"],
            actor_id=row.actor_id,
            operation_id=row.id,
            audit=audit,
        )
    )
    CatalogLifecycleHandler().remove_from_catalog(
        parent.id,
        actor_user_id=row.actor_id,
        exact_cleanup_manifest=cleanup,
        retained_audit=audit,
        session=session,
    )


def _complete(session, rom, command, intent, cleanup):
    with checked_scan_write(session) as row:
        child = session.scalar(
            select(Rom).where(Rom.id == rom.id).with_for_update(of=Rom)
        )
        if child is None or child.incarnation_token != rom.incarnation_token:
            raise ValueError("collection_child_changed")
        if intent is not None:
            _promote(session, row, child, intent, cleanup)
        db_rom_handler.update_rom(child.id, {"missing_from_fs": False}, session=session)
        checkpoint = dict(row.checkpoint)
        checkpoint.update(
            schema=1,
            mapping_id=command.mapping_id,
            revision=command.expected_revision,
            committed_rom_id=child.id,
            cursor=child.fs_name,
            resumable=False,
        )
        DBScanOperationsHandler().worker_update(
            current_scan_write_context(), checkpoint=checkpoint, session=session
        )
        from handler.windows_quick_execution import complete_quick_baseline

        complete_quick_baseline(child, session)
        session.flush()
        return child


def finalize_completed_game(rom, command):
    context = current_scan_write_context()
    if context is None:
        return
    execution = DBScanOperationsHandler().execution(context.operation_id)
    intent = execution["command"].get("collection_promotion")
    cleanup = None
    if intent is not None:
        from handler.filesystem.catalog_collection_cleanup import (
            prepare_collection_cleanup,
        )

        mapping_context = MappingReadContext(
            intent["mapping_id"], intent["expected_revision"]
        )
        mapping_context.validate()
        from handler.filesystem.storage_policy import StorageOperation

        with mapping_context.open(
            StorageOperation.SCAN, intent["selected_child_relative_path"]
        ) as source:
            if next(iter(source.scan()), None) is None:
                raise ValueError("collection_child_empty")
        parent = db_rom_handler.get_rom(intent["parent_rom_id"])
        if parent is not None:
            cleanup = prepare_collection_cleanup(parent)
    with ScanMediaBatch(rom.id, rom.platform_id, fs_resource_handler.storage) as unit:
        unit.publish_and_associate(
            lambda session: _complete(session, rom, command, intent, cleanup)
        )
    if intent is not None:
        from handler.filesystem.catalog_collection_cleanup import (
            process_pending_collection_cleanup,
        )

        try:
            process_pending_collection_cleanup(limit=8)
        except Exception as error:
            log.warning("Collection cleanup remains pending (%s)", type(error).__name__)
