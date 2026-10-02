from unittest.mock import AsyncMock, MagicMock

import pytest

from handler.metadata.flashpoint_handler import FlashpointHandler
from handler.metadata.hasheous_handler import HasheousHandler
from handler.metadata.hltb_handler import HLTBHandler
from handler.metadata.igdb_handler import IGDBHandler
from handler.metadata.launchbox_handler.handler import LaunchboxHandler
from handler.metadata.libretro_handler import LibretroHandler
from handler.metadata.moby_handler import MobyGamesHandler
from handler.metadata.playmatch_handler import PlaymatchHandler
from handler.metadata.ra_handler import RAHandler
from handler.metadata.sgdb_handler import SGDBBaseHandler
from handler.metadata.ss_handler import SSHandler
from handler.metadata.tgdb_handler import TGDBHandler
from handler.scan_command import ScanScope, ScanTrigger
from handler.scan_handler import MetadataSource, ScanType
from tasks.scheduled.scan_library import (
    PC_AUTOMATION_UAT_SCAN_TASK_FUNC,
    PcAutomationUatIntervalTask,
    ScanLibraryTask,
    scan_library_task,
)
from tasks.tasks import DevelopmentIntervalTask


class TestScanLibraryTask:
    @pytest.fixture
    def task(self):
        return ScanLibraryTask()

    def test_init(self, task):
        assert task.func == "tasks.scheduled.scan_library.scan_library_task.run"
        assert task.description == "Rescans the entire library"

    async def test_run_enabled(self, task, mocker):
        mocker.patch.object(HasheousHandler, "is_enabled", return_value=False)
        mocker.patch.object(IGDBHandler, "is_enabled", return_value=False)
        mocker.patch.object(LaunchboxHandler, "is_enabled", return_value=True)
        mocker.patch.object(MobyGamesHandler, "is_enabled", return_value=False)
        mocker.patch.object(PlaymatchHandler, "is_enabled", return_value=False)
        mocker.patch.object(RAHandler, "is_enabled", return_value=True)
        mocker.patch.object(SGDBBaseHandler, "is_enabled", return_value=False)
        mocker.patch.object(SSHandler, "is_enabled", return_value=False)
        mocker.patch.object(FlashpointHandler, "is_enabled", return_value=False)
        mocker.patch.object(HLTBHandler, "is_enabled", return_value=False)
        mocker.patch.object(TGDBHandler, "is_enabled", return_value=False)
        mocker.patch.object(LibretroHandler, "is_enabled", return_value=False)
        mocker.patch("tasks.scheduled.scan_library.ENABLE_SCHEDULED_RESCAN", True)
        commands = [MagicMock()]
        mock_commands = mocker.patch(
            "tasks.scheduled.scan_library.mapping_scan_commands",
            return_value=commands,
        )
        scan_result = MagicMock()
        scan_result.to_dict.return_value = {}
        mock_execute = mocker.patch(
            "tasks.scheduled.scan_library.execute_mapping_scans",
            new=AsyncMock(return_value=scan_result),
        )
        mock_log = mocker.patch("tasks.scheduled.scan_library.log")

        await task.run()

        mock_log.info.assert_any_call("Scheduled library scan started...")
        mock_commands.assert_called_once_with(
            [],
            trigger=ScanTrigger.SCHEDULED,
            scope=ScanScope.LIBRARY,
            scan_type=ScanType.QUICK,
        )
        mock_execute.assert_awaited_once_with(
            commands,
            metadata_sources=[MetadataSource.RA, MetadataSource.LAUNCHBOX],
        )
        mock_log.info.assert_any_call("Scheduled library scan done")

    async def test_run_disabled(self, task, mocker):
        mocker.patch("tasks.scheduled.scan_library.ENABLE_SCHEDULED_RESCAN", False)
        mock_execute = mocker.patch(
            "tasks.scheduled.scan_library.execute_mapping_scans"
        )
        mock_log = mocker.patch("tasks.scheduled.scan_library.log")
        task.unschedule = MagicMock()

        await task.run()

        mock_log.info.assert_called_once_with(
            "Scheduled library scan not enabled, unscheduling..."
        )
        task.unschedule.assert_called_once()
        mock_execute.assert_not_called()

    async def test_run_skips_execution_when_no_active_mappings_exist(
        self, task, mocker
    ):
        """An unmapped platform must not make a scheduled library scan fail."""
        mocker.patch("tasks.scheduled.scan_library.ENABLE_SCHEDULED_RESCAN", True)
        for handler in (
            "meta_hasheous_handler",
            "meta_igdb_handler",
            "meta_launchbox_handler",
            "meta_moby_handler",
            "meta_playmatch_handler",
            "meta_ra_handler",
            "meta_sgdb_handler",
            "meta_ss_handler",
            "meta_flashpoint_handler",
            "meta_hltb_handler",
            "meta_tgdb_handler",
            "meta_libretro_handler",
            "meta_steam_handler",
        ):
            mocker.patch.object(
                getattr(
                    __import__("tasks.scheduled.scan_library", fromlist=[handler]),
                    handler,
                ),
                "is_enabled",
                return_value=False,
            )
        mocker.patch(
            "tasks.scheduled.scan_library.meta_igdb_handler.is_enabled",
            return_value=True,
        )
        mocker.patch(
            "tasks.scheduled.scan_library.mapping_scan_commands", return_value=[]
        )
        execute = mocker.patch(
            "tasks.scheduled.scan_library.execute_mapping_scans", new=AsyncMock()
        )

        await task.run()

        execute.assert_not_awaited()

    def test_task_instance(self):
        assert isinstance(scan_library_task, ScanLibraryTask)
        assert (
            scan_library_task.func
            == "tasks.scheduled.scan_library.scan_library_task.run"
        )

    def test_scheduled_scan_includes_enabled_steam_source(self, task, mocker):
        mocker.patch(
            "tasks.scheduled.scan_library.meta_steam_handler.is_enabled",
            return_value=True,
        )
        mocker.patch("tasks.scheduled.scan_library.ENABLE_SCHEDULED_RESCAN", True)
        mocker.patch(
            "tasks.scheduled.scan_library.mapping_scan_commands",
            return_value=[MagicMock()],
        )
        execute = mocker.patch(
            "tasks.scheduled.scan_library.execute_mapping_scans",
            new=AsyncMock(return_value=MagicMock(to_dict=MagicMock(return_value={}))),
        )
        for handler in (
            "meta_hasheous_handler",
            "meta_igdb_handler",
            "meta_launchbox_handler",
            "meta_moby_handler",
            "meta_playmatch_handler",
            "meta_ra_handler",
            "meta_sgdb_handler",
            "meta_ss_handler",
            "meta_flashpoint_handler",
            "meta_hltb_handler",
            "meta_tgdb_handler",
            "meta_libretro_handler",
        ):
            mocker.patch.object(
                getattr(
                    __import__("tasks.scheduled.scan_library", fromlist=[handler]),
                    handler,
                ),
                "is_enabled",
                return_value=False,
            )

        import asyncio

        asyncio.run(task.run())

        assert execute.await_args.kwargs["metadata_sources"] == [MetadataSource.STEAM]

    def test_development_interval_uses_exact_rq_interval_schedule(self, mocker):
        scheduler = mocker.patch("tasks.tasks.tasks_scheduler")
        task = DevelopmentIntervalTask(
            title="PC automation UAT scan",
            description="Runs mapped scan in development",
            task_type=ScanLibraryTask().task_type,
            enabled=True,
            func=PC_AUTOMATION_UAT_SCAN_TASK_FUNC,
            interval_seconds=10,
        )
        mocker.patch.object(task, "_get_existing_job", return_value=None)

        task.schedule()

        scheduler.schedule.assert_called_once()
        assert scheduler.schedule.call_args.kwargs["interval"] == 10
        assert scheduler.schedule.call_args.kwargs["repeat"] is None

    def test_uat_interval_task_calls_the_mapped_scan_function(self):
        task = PcAutomationUatIntervalTask()

        assert task.func == PC_AUTOMATION_UAT_SCAN_TASK_FUNC
        assert PC_AUTOMATION_UAT_SCAN_TASK_FUNC == ScanLibraryTask().func
