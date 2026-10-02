from config import (
    ENABLE_SCHEDULED_RESCAN,
    PC_AUTOMATION_UAT_INTERVAL_SECONDS,
    SCHEDULED_RESCAN_CRON,
)
from endpoints.sockets.scan import (
    ScanStats,
    execute_mapping_scans,
    mapping_scan_commands,
)
from handler.metadata import (
    meta_flashpoint_handler,
    meta_hasheous_handler,
    meta_hltb_handler,
    meta_igdb_handler,
    meta_launchbox_handler,
    meta_libretro_handler,
    meta_moby_handler,
    meta_playmatch_handler,
    meta_ra_handler,
    meta_sgdb_handler,
    meta_ss_handler,
    meta_steam_handler,
    meta_tgdb_handler,
)
from handler.scan_command import ScanScope, ScanTrigger
from handler.scan_handler import MetadataSource, ScanType
from logger.logger import log
from tasks.tasks import (
    SCAN_LIBRARY_TASK_FUNC,
    DevelopmentIntervalTask,
    PeriodicTask,
    TaskType,
)

PC_AUTOMATION_UAT_SCAN_TASK_FUNC = SCAN_LIBRARY_TASK_FUNC


class ScanLibraryTask(PeriodicTask):
    def __init__(self):
        super().__init__(
            title="Scheduled rescan",
            description="Rescans the entire library",
            task_type=TaskType.SCAN,
            enabled=ENABLE_SCHEDULED_RESCAN,
            manual_run=False,
            cron_string=SCHEDULED_RESCAN_CRON,
            func=SCAN_LIBRARY_TASK_FUNC,
        )

    async def run(self) -> dict[str, str]:
        scan_stats = ScanStats()

        if not ENABLE_SCHEDULED_RESCAN:
            log.info("Scheduled library scan not enabled, unscheduling...")
            self.unschedule()
            return scan_stats.to_dict()

        source_mapping: dict[str, bool] = {
            MetadataSource.IGDB: meta_igdb_handler.is_enabled(),
            MetadataSource.SS: meta_ss_handler.is_enabled(),
            MetadataSource.MOBY: meta_moby_handler.is_enabled(),
            MetadataSource.RA: meta_ra_handler.is_enabled(),
            MetadataSource.LAUNCHBOX: meta_launchbox_handler.is_enabled(),
            MetadataSource.HASHEOUS: meta_hasheous_handler.is_enabled(),
            MetadataSource.PLAYMATCH: meta_playmatch_handler.is_enabled(),
            MetadataSource.SGDB: meta_sgdb_handler.is_enabled(),
            MetadataSource.FLASHPOINT: meta_flashpoint_handler.is_enabled(),
            MetadataSource.HLTB: meta_hltb_handler.is_enabled(),
            MetadataSource.TGDB: meta_tgdb_handler.is_enabled(),
            MetadataSource.LIBRETRO: meta_libretro_handler.is_enabled(),
            MetadataSource.STEAM: meta_steam_handler.is_enabled(),
        }

        metadata_sources = [source for source, flag in source_mapping.items() if flag]
        if not metadata_sources:
            log.warning("No metadata sources enabled, unscheduling library scan")
            return scan_stats.to_dict()

        log.info("Scheduled library scan started...")
        commands = mapping_scan_commands(
            [],
            trigger=ScanTrigger.SCHEDULED,
            scope=ScanScope.LIBRARY,
            scan_type=ScanType.QUICK,
        )
        if not commands:
            log.info("Scheduled library scan skipped, no active storage mappings")
            return scan_stats.to_dict()
        scan_stats = await execute_mapping_scans(
            commands,
            metadata_sources=metadata_sources,
        )
        log.info("Scheduled library scan done")

        return scan_stats.to_dict()


scan_library_task = ScanLibraryTask()


class PcAutomationUatIntervalTask(DevelopmentIntervalTask):
    """Development-only ten-second runner for the authorized mapped scan."""

    def __init__(self):
        super().__init__(
            title="PC automation UAT scan",
            description="Runs mapped library scans every 10 seconds in development",
            task_type=TaskType.SCAN,
            enabled=PC_AUTOMATION_UAT_INTERVAL_SECONDS == 10,
            manual_run=False,
            func=PC_AUTOMATION_UAT_SCAN_TASK_FUNC,
            interval_seconds=10,
        )

    async def run(self) -> dict[str, str]:
        return await scan_library_task.run()


pc_automation_uat_interval_task = PcAutomationUatIntervalTask()
