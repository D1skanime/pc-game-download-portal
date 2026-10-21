"""Observe post-scan PC automation through the existing provider result owner."""


async def observe_pc_automation(
    automation, platform, scanned, durable, newly_added, *, selected=True
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
    current = db_rom_handler.get_rom(durable.id)
    if selected and current is not None:
        record_provider_result(
            "steam", current.fs_name, rom=current, files=current.files
        )
