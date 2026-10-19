"""Mapping-bound collection decisions and checked scan promotion policy."""

import hashlib
import json
from pathlib import PurePosixPath

from sqlalchemy import select

from decorators.database import begin_session
from handler.storage.read_context import MappingReadContext
from models.rom import Rom
from models.scan_collection import ScanCollectionFolder


def digest_path(value):
    return hashlib.sha256(value.encode()).hexdigest()


def mapping_binding(mapping):
    return digest_path(
        json.dumps(
            [mapping.storage_root_id, mapping.relative_path], separators=(",", ":")
        )
    )


def find_classification(session, mapping, parent_path):
    row = session.scalar(
        select(ScanCollectionFolder).where(
            ScanCollectionFolder.mapping_id == mapping.id,
            ScanCollectionFolder.binding_digest == mapping_binding(mapping),
            ScanCollectionFolder.path_digest == digest_path(parent_path),
        )
    )
    if row is not None and (
        row.storage_root_id != mapping.storage_root_id
        or row.mapping_relative_path != mapping.relative_path
        or row.parent_relative_path != parent_path
    ):
        raise ValueError("collection_binding_collision")
    return row


@begin_session
def get_validated_promotion(body, commands, *, session=None):
    intent = body.collection_promotion
    if intent is None:
        return None
    if (
        body.metadata_only
        or body.media_only
        or body.type in {"hashes", "new_platforms"}
        or body.roms_ids
    ):
        raise ValueError("collection_requires_filesystem_scan")
    if len(commands) != 1:
        raise ValueError("collection_requires_one_mapping")
    command = commands[0]
    if (command.mapping_id, command.expected_revision) != (
        intent.mapping_id,
        intent.expected_revision,
    ):
        raise ValueError("collection_mapping_mismatch")
    mapping = MappingReadContext(intent.mapping_id, intent.expected_revision).validate()
    if (
        dict(command.options).get("relative_path")
        != intent.selected_child_relative_path
    ):
        raise ValueError("collection_scope_mismatch")
    parent_path = PurePosixPath(intent.parent_relative_path)
    child_path = PurePosixPath(intent.selected_child_relative_path)
    if child_path.parent != parent_path:
        raise ValueError("collection_child_outside_parent")
    parent = session.get(Rom, intent.parent_rom_id)
    if parent is None:
        classification = find_classification(
            session, mapping, intent.parent_relative_path
        )
        if classification is None or (
            classification.parent_rom_id != intent.parent_rom_id
            or classification.selected_child_relative_path
            != intent.selected_child_relative_path
        ):
            raise ValueError("collection_parent_missing")
        incarnation = classification.parent_incarnation
    else:
        try:
            actual = (
                (PurePosixPath(parent.fs_path) / parent.fs_name)
                .relative_to(PurePosixPath(mapping.relative_path))
                .as_posix()
            )
        except ValueError:
            raise ValueError("collection_parent_outside_mapping") from None
        if (
            parent.platform_id != mapping.platform_id
            or actual != intent.parent_relative_path
        ):
            raise ValueError("collection_parent_mismatch")
        incarnation = parent.incarnation_token
    return {
        **intent.model_dump(),
        "parent_incarnation": incarnation,
        "storage_root_id": mapping.storage_root_id,
        "mapping_relative_path": mapping.relative_path,
        "binding_digest": mapping_binding(mapping),
    }
