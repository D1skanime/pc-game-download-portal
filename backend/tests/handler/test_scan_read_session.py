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
    original_filter = db_rom_handler.filter_roms
    with bind_scan_write_context(
        ScanWriteContext(attempt.id, attempt.attempt_id, "worker")
    ), sync_session.begin() as session:

        def same_session(*args, **kwargs):
            assert kwargs.get("session") is session
            return original(*args, **kwargs)

        def same_filter_session(*args, **kwargs):
            assert kwargs.get("session") is session
            return original_filter(*args, **kwargs)

        monkeypatch.setattr(db_rom_handler, "get_roms_query", same_session)
        monkeypatch.setattr(db_rom_handler, "filter_roms", same_filter_session)
        assert isinstance(
            db_rom_handler.get_roms_scalar(
                only_fields=[Rom.fs_name, Rom.fs_path], session=session
            ),
            list,
        )


def test_known_paths_projection_avoids_generic_filters(platform, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("filesystem projection must not enter generic filters")

    monkeypatch.setattr(db_rom_handler, "get_roms_scalar", forbidden)
    monkeypatch.setattr(db_rom_handler, "get_roms_query", forbidden)
    monkeypatch.setattr(db_rom_handler, "filter_roms", forbidden)
    assert isinstance(db_rom_handler.get_rom_filesystem_paths(platform.id), list)


def test_scan_reader_requests_domain_before_slot_across_processes(admin_user, command):
    """A cooperating writer holding both locks cannot form a reader cycle."""
    import json
    import subprocess
    import sys
    import tempfile
    import time
    from pathlib import Path

    from tests.integration.test_scan_operation_faults import PREFIX

    from handler.database.scan_write_fence import fence_bound_session
    from handler.filesystem.owned_writer_domain import owned_writer_domain

    attempt = running(DBScanOperationsHandler(), admin_user, command)
    context = ScanWriteContext(attempt.id, attempt.attempt_id, "worker")
    with tempfile.TemporaryDirectory(dir="/phase34/owned") as directory:
        events = Path(directory) / "events"
        source = PREFIX + r"""
import json,sys
from contextlib import contextmanager
from pathlib import Path
import decorators.database as database
from handler.database import db_rom_handler
from handler.database.scan_write_fence import ScanWriteContext,bind_scan_write_context
from handler.filesystem.owned_writer_domain import owned_writer_domain
payload=json.load(sys.stdin)
path=Path(payload["events"])
def event(value):
 with path.open("a") as output:
  output.write(value+"\n")
@contextmanager
def domain():
 event("domain")
 with owned_writer_domain(): yield
original_fence=database.fence_bound_session
@contextmanager
def fence(session):
 event("slot")
 with original_fence(session): yield
database.owned_writer_domain=domain
import handler.filesystem.owned_writer_domain as writer_module
writer_module.owned_writer_domain=domain
database.fence_bound_session=fence
with bind_scan_write_context(ScanWriteContext(payload["id"],payload["attempt"],"worker")):
 db_rom_handler.get_roms_scalar(platform_ids=[])
event("complete")
"""
        process = None
        try:
            with owned_writer_domain(), bind_scan_write_context(context):
                with sync_session.begin() as session, fence_bound_session(session):
                    process = subprocess.Popen(
                        [sys.executable, "-c", source],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        close_fds=True,
                    )
                    assert process.stdin is not None
                    process.stdin.write(
                        json.dumps(
                            {
                                "events": str(events),
                                "id": attempt.id,
                                "attempt": attempt.attempt_id,
                            }
                        )
                    )
                    process.stdin.close()
                    process.stdin = None
                    deadline = time.monotonic() + 10
                    while not events.exists() or not events.read_text().splitlines():
                        assert process.poll() is None, process.communicate()[1]
                        assert time.monotonic() < deadline
                        time.sleep(0.01)
                    assert events.read_text().splitlines()[0] == "domain"
            stdout, stderr = process.communicate(timeout=15)
            assert process.returncode == 0, (stdout + stderr)[-3000:]
            assert events.read_text().splitlines()[-1] == "complete"
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate(timeout=3)


def test_publication_and_database_import_orders():
    import subprocess
    import sys

    prefix = (
        "from tools.phase34_target_guard import validate_target; validate_target(); "
    )
    for modules in (
        "import sys; from decorators.owned_io import serialized_owned_write; "
        "assert 'handler.filesystem' not in sys.modules; "
        "assert 'handler.database' not in sys.modules",
        "import handler.database; import handler.filesystem; import startup; "
        "from decorators.owned_io import serialized_owned_write; "
        "from handler.filesystem.owned_publication import serialized_owned_write as public; "
        "assert public is serialized_owned_write",
    ):
        result = subprocess.run(
            [sys.executable, "-c", prefix + modules],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert result.returncode == 0, result.stderr[-3000:]
