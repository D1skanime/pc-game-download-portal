"""Mapped Windows quick advice and per-game refresh context.

Inventory is advisory. Mapping reads, checked writes and media publication retain
their existing authority; completion and retry persistence belong to finalization.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import PurePosixPath

from config.config_manager import config_manager as cm
from handler.database.scan_inventory_state import InventoryBinding, load_baseline
from handler.filesystem import get_fs_rom_handler
from handler.filesystem.roms_handler import FSRomsHandler
from handler.scan_collection_policy import digest_path
from handler.scan_inventory_contracts import InventoryEvidence, QuickScanDecision
from handler.scan_operation_checkpoint import current_checkpoint_command
from handler.storage.read_context import MappingReadContext
from handler.windows_quick_policy import decide_windows_quick, is_identified_windows
from models.rom import Rom

_CURRENT = ContextVar("windows_quick_refresh", default=None)


@dataclass
class WindowsQuickContext:
    binding: InventoryBinding | None
    before: InventoryEvidence
    decision: QuickScanDecision
    files_reconciled: bool = False
    components_reconciled: bool = False


def current_windows_quick():
    return _CURRENT.get()


@contextmanager
def bind_windows_quick(context):
    token = _CURRENT.set(context)
    try:
        yield context
    finally:
        _CURRENT.reset(token)


def inventory_binding(rom, relative_path):
    command = current_checkpoint_command()
    if command is None:
        return None
    mapping = MappingReadContext(
        command.mapping_id, command.expected_revision
    ).validate()
    fingerprint = digest_path(
        "windows-quick:inventory=1:classifier=1:encoding=json-ascii:"
        + str(bool(cm.get_config().SKIP_HASH_CALCULATION))
    )
    return InventoryBinding.from_mapping(mapping, rom, relative_path, fingerprint)


async def inspect_windows_quick(
    handler,
    rom,
    *,
    scan_type,
    platform_slug,
    rom_ids,
    relative_path,
    collection_expanded,
    metadata_only=False,
):
    if (
        scan_type != "quick"
        or platform_slug != "win"
        or rom_ids
        or not collection_expanded
        or metadata_only
    ):
        return None
    evidence = await handler.get_pc_inventory(rom)
    binding = inventory_binding(rom, relative_path) if rom.id else None
    if not evidence.complete:
        return WindowsQuickContext(binding, evidence, QuickScanDecision.INCOMPLETE)
    if binding is None:
        return WindowsQuickContext(None, evidence, QuickScanDecision.REFRESH)
    baseline = load_baseline(binding, evidence)
    decision = decide_windows_quick(
        scan_type=scan_type,
        platform_slug=platform_slug,
        current_binding=binding,
        baseline_binding=binding,
        current=evidence,
        baseline=baseline,
        identified=is_identified_windows(rom),
        collection_expanded=collection_expanded,
    )
    assert decision is not None
    return WindowsQuickContext(binding, evidence, decision)


async def inspect_discovered_game(
    platform, fs_rom, rom, *, scan_type, rom_ids, metadata_only
):
    command = current_checkpoint_command()
    if (
        command is None
        or platform.slug != "win"
        or scan_type != "quick"
        or rom_ids
        or metadata_only
        or not fs_rom["nested"]
    ):
        return None
    mapping = MappingReadContext(
        command.mapping_id, command.expected_revision
    ).validate()
    logical_path = fs_rom.get(
        "logical_fs_path",
        get_fs_rom_handler().get_logical_roms_fs_structure(platform.fs_slug),
    )
    relative = (
        (PurePosixPath(logical_path) / fs_rom["fs_name"])
        .relative_to(PurePosixPath(mapping.relative_path))
        .as_posix()
    )
    handler = FSRomsHandler.for_mapping(mapping, fs_rom.get("scan_relative_path"))
    candidate = (
        rom
        if rom is not None
        else Rom(
            fs_name=fs_rom["fs_name"],
            fs_path=logical_path,
            platform_id=platform.id,
        )
    )
    return await inspect_windows_quick(
        handler,
        candidate,
        scan_type=scan_type,
        platform_slug=platform.slug,
        rom_ids=rom_ids,
        relative_path=relative,
        collection_expanded=True,
    )
