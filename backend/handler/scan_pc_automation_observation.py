"""Observe post-scan PC automation through the existing provider result owner."""


async def observe_pc_automation(
    automation,
    platform,
    scanned,
    durable,
    newly_added,
    *,
    selected=True,
    completed=None
):
    from handler.database import db_rom_handler
    from handler.scan_metadata_result import record_provider_result
    from handler.scan_provider_execution import bind_provider_results, execute_provider
    from handler.windows_quick_execution import current_windows_quick

    async def run():
        await automation(platform, scanned, durable, newly_added)
        current = db_rom_handler.get_rom(durable.id)
        return {"steam_id": current.steam_id if current else None}

    with bind_provider_results() as observations:
        await execute_provider("steam", run(), durable.fs_name, selected=selected)
    quick = current_windows_quick()
    if not selected and quick is not None and quick.binding is not None:
        observation = observations[-1]
        quick.automation_observation = {
            "requests": observation.requests,
            "invoked": observation.invoked,
            "cached": observation.cached,
            "outcome": observation.outcome,
        }
    if completed is not None:
        completed(durable)
    current = db_rom_handler.get_rom(durable.id)
    if current is not None:
        consider_scan_descriptions(current)
    if selected and current is not None:
        record_provider_result(
            "steam", current.fs_name, rom=current, files=current.files
        )


def consider_scan_descriptions(rom):
    """Offer current persisted IDs without creating inventory or provider work."""
    from pathlib import PurePosixPath
    from types import SimpleNamespace

    from handler.scan_operation_checkpoint import current_checkpoint_command
    from handler.scan_retry_execution import current_retry_coordinator
    from handler.storage.read_context import MappingReadContext
    from handler.windows_quick_execution import current_windows_quick, inventory_binding

    coordinator = current_retry_coordinator()
    command = current_checkpoint_command()
    if coordinator is None or command is None:
        return
    quick = current_windows_quick()
    if quick is None:
        mapping = MappingReadContext(
            command.mapping_id, command.expected_revision
        ).validate()
        relative = (
            (PurePosixPath(rom.fs_path) / rom.fs_name)
            .relative_to(PurePosixPath(mapping.relative_path))
            .as_posix()
        )
        quick = SimpleNamespace(
            binding=inventory_binding(rom, relative),
            before=None,
            automation_observation=None,
        )
    coordinator.consider_descriptions(quick, rom, command)
