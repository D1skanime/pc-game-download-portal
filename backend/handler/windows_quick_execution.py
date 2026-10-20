"""Mapped Windows quick advice and per-game refresh context.

Inventory is advisory. Mapping reads, checked writes and media publication retain
their existing authority; completion and retry persistence belong to finalization.
"""

import json
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from config.config_manager import config_manager as cm
from handler.database import db_rom_handler
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
    files: Any = None
    components: Any = None
    after: InventoryEvidence | None = None


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
    config = cm.get_config()
    fingerprint = digest_path(
        json.dumps(
            [
                "windows-quick",
                1,
                1,
                "json-ascii",
                bool(config.SKIP_HASH_CALCULATION),
                sorted(config.EXCLUDED_MULTI_PARTS_FILES),
                sorted(config.EXCLUDED_MULTI_PARTS_EXT),
            ],
            separators=(",", ":"),
        )
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
    if decision == QuickScanDecision.REFRESH:
        from handler.database.scan_inventory_state import save_completed_baseline

        save_completed_baseline(
            binding,
            evidence,
            evidence,
            files_reconciled=False,
            components_reconciled=False,
        )
    context = WindowsQuickContext(binding, evidence, decision)
    if decision == QuickScanDecision.METADATA_ONLY:
        from handler.scan_retry_execution import consider_unknown_retry

        consider_unknown_retry(context, rom)
    return context


async def inspect_discovered_game(
    platform, fs_rom, rom, *, scan_type, rom_ids, metadata_only
):
    command = current_checkpoint_command()
    if (
        command is None
        or platform.slug != "win"
        or scan_type not in {"quick", "complete", "update"}
        or (rom_ids and (rom is None or rom.id not in rom_ids))
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
    if scan_type != "quick" or rom_ids:
        evidence = await handler.get_pc_inventory(candidate)
        binding = inventory_binding(candidate, relative) if candidate.id else None
        return WindowsQuickContext(
            binding,
            evidence,
            (
                QuickScanDecision.REFRESH
                if evidence.complete
                else QuickScanDecision.INCOMPLETE
            ),
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


async def prepare_quick_refresh(context, handler, rom, *, calculate_hashes):
    from handler.filesystem.pc_scan_inventory import InventoryIncomplete
    from handler.scan_inventory_contracts import InventoryAssessment

    if not context.before.complete:
        raise InventoryIncomplete(context.before.reason or "incomplete_evidence")
    try:
        components = await handler.get_pc_components(rom, inventory=context.before)
        files = await handler.get_rom_files(rom, calculate_hashes=calculate_hashes)
        after = await handler.get_pc_inventory(rom)
    except (OSError, ValueError) as error:
        raise InventoryIncomplete("refresh_unreadable") from error
    if InventoryAssessment.compare(after, context.before).state != "unchanged":
        raise InventoryIncomplete(after.reason or "unstable_inventory")
    context.components = components
    context.files = files
    context.after = after


def recheck_quick_inventory(context, handler, rom, session):
    from handler.database.scan_inventory_state import _enlist
    from handler.database.scan_write_fence import checked_scan_write
    from handler.filesystem.pc_scan_inventory import (
        InventoryIncomplete,
        collect_pc_inventory,
    )
    from handler.scan_inventory_contracts import InventoryAssessment

    if context.binding is None:
        raise InventoryIncomplete("refresh_binding_missing")

    def boundary():
        with checked_scan_write(session) as operation:
            _enlist(session, context.binding, operation)

    # Hold the existing mapping fence through commit without a nested session.
    after = collect_pc_inventory(
        handler.open_access, handler._pc_game_path(rom), check=boundary
    )
    if InventoryAssessment.compare(after, context.before).state != "unchanged":
        raise InventoryIncomplete(after.reason or "unstable_inventory")
    context.after = after


def reconcile_quick_files(context, handler, rom, session):
    from handler.filesystem.pc_scan_inventory import InventoryIncomplete

    recheck_quick_inventory(context, handler, rom, session)
    if context.files is None or context.components is None:
        raise InventoryIncomplete("refresh_not_prepared")
    files = db_rom_handler.sync_rom_files(
        rom.id, context.files.rom_files, session=session
    )
    components = db_rom_handler.sync_rom_components(
        rom.id, context.components, session=session
    )
    recheck_quick_inventory(context, handler, rom, session)
    return files, components


def complete_quick_baseline(rom, session):
    """Adopt only reconciled refresh evidence inside the existing completion fence."""
    from handler.database.scan_inventory_state import save_completed_baseline

    context = current_windows_quick()
    if context is None or context.decision != QuickScanDecision.REFRESH:
        return False
    if context.binding is None:
        return False
    if context.files_reconciled and context.components_reconciled:
        recheck_quick_inventory(context, get_fs_rom_handler(), rom, session)
    return save_completed_baseline(
        context.binding,
        context.before,
        context.after,
        files_reconciled=context.files_reconciled,
        components_reconciled=context.components_reconciled,
        session=session,
    )
