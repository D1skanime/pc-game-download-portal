"""Observe post-scan PC automation through the existing provider result owner."""


async def observe_pc_automation(automation, platform, scanned, durable, newly_added):
    from handler.database import db_rom_handler
    from handler.scan_metadata_result import record_provider_result
    from handler.scan_provider_execution import execute_provider

    async def run():
        await automation(platform, scanned, durable, newly_added)
        current = db_rom_handler.get_rom(durable.id)
        return {"steam_id": current.steam_id if current else None}

    await execute_provider("steam", run(), durable.fs_name)
    record_provider_result("steam", durable.fs_name, rom=durable, files=durable.files)
