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
from tasks.scheduled.scan_library import ScanLibraryTask, scan_library_task


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

    def test_task_instance(self):
        assert isinstance(scan_library_task, ScanLibraryTask)
        assert (
            scan_library_task.func
            == "tasks.scheduled.scan_library.scan_library_task.run"
        )
