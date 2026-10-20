"""One mapping-backed inventory for manually confirmed collection folders."""

import stat
from dataclasses import replace

from sqlalchemy import select

from decorators.database import begin_session
from exceptions.storage_read import MissingMappedContentError
from handler.filesystem import use_fs_rom_handler
from handler.filesystem.roms_handler import FSRomsHandler
from handler.filesystem.storage_policy import StorageOperation
from handler.scan_collection_policy import digest_path, mapping_binding
from handler.scan_operation_checkpoint import (
    bind_checkpoint_command,
    current_checkpoint_command,
)
from handler.storage.read_context import MappingReadContext
from models.scan_collection import ScanCollectionFolder


@begin_session
def get_collection_folders(mapping, *, session=None):
    rows = list(
        session.scalars(
            select(ScanCollectionFolder)
            .where(
                ScanCollectionFolder.mapping_id == mapping.id,
                ScanCollectionFolder.binding_digest == mapping_binding(mapping),
            )
            .order_by(ScanCollectionFolder.id)
            .limit(257)
        )
    )
    if len(rows) > 256:
        raise ValueError("collection_inventory_limit")
    for row in rows:
        if (
            row.storage_root_id != mapping.storage_root_id
            or row.mapping_relative_path != mapping.relative_path
            or row.path_digest != digest_path(row.parent_relative_path)
        ):
            raise ValueError("collection_binding_collision")
    return rows


def collection_inventory(platform, entries, filesystem_scope_path=None):
    command = current_checkpoint_command()
    if command is None or filesystem_scope_path is not None:
        return entries, False
    context = MappingReadContext(command.mapping_id, command.expected_revision)
    mapping = context.validate()
    rows = get_collection_folders(mapping)
    if not rows:
        return entries, False
    parents = {row.parent_relative_path for row in rows}
    inventory = [entry for entry in entries if entry["fs_name"] not in parents]
    for row in rows:
        template = next(
            (
                entry
                for entry in entries
                if entry["fs_name"] == row.parent_relative_path.split("/")[0]
            ),
            None,
        )
        if template is None:
            continue
        try:
            with context.open(
                StorageOperation.SCAN, row.parent_relative_path
            ) as directory:
                children = directory.scan()
            if len(children) > 4096:
                raise ValueError("collection_child_inventory_limit")
            for name in sorted(children):
                child = row.parent_relative_path + "/" + name
                if child in parents:
                    continue
                with context.open(StorageOperation.STAT, child) as source:
                    if not stat.S_ISDIR(source.stat().st_mode):
                        continue
                inventory.append(
                    {
                        **template,
                        "fs_name": name,
                        "flat": False,
                        "nested": True,
                        "scan_relative_path": child,
                        "logical_fs_path": "/".join(
                            p
                            for p in (mapping.relative_path, row.parent_relative_path)
                            if p
                        ),
                    }
                )
        except MissingMappedContentError:
            continue
    return inventory, True


def filesystem_identity(handler, platform, entry):
    return (
        entry.get(
            "logical_fs_path", handler.get_logical_roms_fs_structure(platform.fs_slug)
        ),
        entry["fs_name"],
    )


async def identify_collection_game(fs_rom, identify, **kwargs):
    scope = fs_rom.get("scan_relative_path")
    if scope is None:
        return await identify(fs_rom=fs_rom, **kwargs)
    command = current_checkpoint_command()
    context = MappingReadContext(command.mapping_id, command.expected_revision)
    mapping = context.validate()
    child_command = replace(command, options=(("relative_path", scope),))
    with use_fs_rom_handler(
        FSRomsHandler.for_mapping(mapping, scope)
    ), bind_checkpoint_command(child_command):
        return await identify(fs_rom=fs_rom, **kwargs)


async def count_scan_inventory(platform, filesystem_scope_path=None):
    from handler.filesystem import get_fs_rom_handler

    handler = get_fs_rom_handler()
    if current_checkpoint_command() is None:
        return await handler.count_roms(platform)
    entries = await handler.get_roms(platform)
    inventory, _ = collection_inventory(platform, entries, filesystem_scope_path)
    return len(inventory)
