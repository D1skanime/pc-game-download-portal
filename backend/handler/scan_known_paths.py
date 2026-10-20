"""Check persisted nested game paths without discovering collection children."""

import stat
from pathlib import PurePosixPath

from exceptions.storage_exceptions import StorageResolutionError
from handler.filesystem.storage_policy import StorageOperation
from handler.filesystem.storage_resolver import normalize_relative_path


def present_known_nested_roms(handler, platform_slug, known_roms):
    present = []
    for rom in known_roms:
        try:
            root = PurePosixPath(handler.get_logical_roms_fs_structure(platform_slug))
            relative_parent = PurePosixPath(rom.fs_path).relative_to(root).as_posix()
            if relative_parent == ".":
                continue
            path = normalize_relative_path(relative_parent + "/" + rom.fs_name)
            with handler.open_access(StorageOperation.STAT, path) as source:
                mode = source.stat().st_mode
            if stat.S_ISDIR(mode) or stat.S_ISREG(mode):
                present.append(rom)
        except (StorageResolutionError, ValueError):
            continue
    return present


def present_known_nested_names(handler, platform_slug, known_roms):
    return [
        rom.fs_name
        for rom in present_known_nested_roms(handler, platform_slug, known_roms)
    ]
