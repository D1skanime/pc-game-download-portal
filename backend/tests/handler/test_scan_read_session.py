"""Fenced scan reads cannot open a second transaction behind their own slot."""

from tests.handler.test_scan_operations import command as command_fixture
from tests.handler.test_scan_operations import running

from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.database.scan_operations_handler import DBScanOperationsHandler
from handler.database.scan_write_fence import ScanWriteContext, bind_scan_write_context
from models.rom import Rom

command = command_fixture


def test_scan_rom_query_reuses_its_fenced_session(admin_user, command, monkeypatch):
    attempt = running(DBScanOperationsHandler(), admin_user, command)
    original = db_rom_handler.get_roms_query
    with bind_scan_write_context(
        ScanWriteContext(attempt.id, attempt.attempt_id, "worker")
    ), sync_session.begin() as session:

        def same_session(*args, **kwargs):
            assert kwargs.get("session") is session
            return original(*args, **kwargs)

        monkeypatch.setattr(db_rom_handler, "get_roms_query", same_session)
        assert isinstance(
            db_rom_handler.get_roms_scalar(
                only_fields=[Rom.fs_name, Rom.fs_path], session=session
            ),
            list,
        )
