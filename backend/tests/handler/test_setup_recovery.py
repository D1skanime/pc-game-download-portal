"""Setup recovery assertions against guarded disposable SQL and read-only Games."""

import pytest
from sqlalchemy import event, select

from config import LIBRARY_BASE_PATH
from handler.database import db_storage_handler
from handler.database.base_handler import sync_session
from handler.setup_folder_handler import setup_folder_handler
from models.platform import Platform
from models.scan_operation import ScanOperation
from models.storage import PlatformStorageMapping, StorageMappingAudit, StorageRoot

SLUGS = {
    "GB GameBoy": "gb",
    "GBA GameBoy Advance": "gba",
    "Nintendo 64": "n64",
    "Nintendo Switch": "switch",
    "PC": "win",
    "PSP": "psp",
    "PlayStation 2": "ps2",
    "SNES Super Nintendo": "snes",
}


def recovery():
    from handler.setup_recovery import setup_recovery_handler

    return setup_recovery_handler


@pytest.fixture
def saved_root():
    return db_storage_handler.register_root("Games", LIBRARY_BASE_PATH)


def persist(root, names):
    with sync_session.begin() as session:
        for name in names:
            platform = Platform(name=name, slug=SLUGS[name], fs_slug=SLUGS[name])
            session.add(platform)
            session.flush()
            session.add(
                PlatformStorageMapping(
                    platform_id=platform.id,
                    storage_root_id=root.id,
                    relative_path=name,
                )
            )


def test_unenrolled_snapshot_is_read_only_and_does_not_register_root():
    # The missing module is the RED feature boundary, not a fixture/import failure.
    handler = recovery()
    statements = []
    engine = sync_session.kw["bind"]

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.split()[0].upper())

    event.listen(engine, "before_cursor_execute", record)
    try:
        snapshot = handler.snapshot()
        assert not snapshot.enrolled
        assert not snapshot.setup_complete
        assert snapshot.current_step == "account"
        assert snapshot.next_action == "create_admin"
        assert len(snapshot.missing_assignments) == 8
        with sync_session.begin() as session:
            assert session.scalar(select(StorageRoot.id)) is None
            assert session.scalar(select(ScanOperation.id)) is None
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert not ({"INSERT", "UPDATE", "DELETE"} & set(statements))


def test_account_success_assignment_failure_preserves_admin(admin_user, saved_root):
    snapshot = recovery().snapshot()
    assert snapshot.enrolled and not snapshot.setup_complete
    assert snapshot.current_step == "folders"
    assert snapshot.cause_code == "assignments_missing"
    assert snapshot.next_action == "assign_missing"
    assert len(snapshot.missing_assignments) == 8
    assert snapshot.saved_assignments == []


def test_partial_batch_and_lost_response_are_reconciled(admin_user, saved_root):
    persist(saved_root, ["PC", "PSP"])
    first = recovery().snapshot()
    assert {row.folder_name for row in first.saved_assignments} == {"PC", "PSP"}
    assert len(first.missing_assignments) == 6
    identities = {row.folder_name: row.mapping_id for row in first.saved_assignments}
    persist(saved_root, set(SLUGS) - {"PC", "PSP"})
    after_loss = recovery().snapshot()
    assert after_loss.setup_complete and after_loss.current_step == "complete"
    assert after_loss.next_action == "start_first_scan"
    assert after_loss.missing_assignments == []
    assert all(
        row.mapping_id == identities[row.folder_name]
        for row in after_loss.saved_assignments
        if row.folder_name in identities
    )
    assert recovery().snapshot() == after_loss


def test_unknown_folder_stays_missing_until_explicit_mapping(
    admin_user, saved_root, monkeypatch
):
    from handler.setup_folder_handler import DiscoveredFolder, DiscoveryResult

    monkeypatch.setattr(
        setup_folder_handler,
        "discover",
        lambda root: DiscoveryResult(
            (DiscoveredFolder("Unrecognized", "Unrecognized", "unknown", None),),
            (),
        ),
    )
    snapshot = recovery().snapshot()
    assert not snapshot.setup_complete
    assert snapshot.missing_assignments[0].suggested_platform is None
    assert snapshot.missing_assignments[0].name == "Unrecognized"


@pytest.mark.parametrize(
    "condition,cause",
    [
        ("missing", "root_missing"),
        ("unreadable", "root_unreadable"),
        ("writable", "root_not_read_only"),
        ("inactive", "root_inactive"),
    ],
)
def test_root_failures_keep_saved_rows_and_offer_retry(
    admin_user,
    saved_root,
    monkeypatch,
    condition,
    cause,
):
    from datetime import datetime, timezone

    import handler.setup_recovery as module
    from handler.filesystem.storage_resolver import StorageRootHealthSnapshot

    persist(saved_root, ["PC"])
    if condition == "inactive":
        with sync_session.begin() as session:
            session.get(StorageRoot, saved_root.id).active = False
    else:
        health = StorageRootHealthSnapshot(
            condition != "missing",
            condition not in {"missing", "unreadable"},
            False if condition == "writable" else None,
            datetime.now(timezone.utc),
            "/private/path secret diagnostic",
        )
        monkeypatch.setattr(
            module, "get_storage_root_health_snapshot", lambda root: health
        )
    snapshot = recovery().snapshot()
    assert not snapshot.setup_complete and snapshot.current_step == "folders"
    assert snapshot.cause_code == cause
    assert snapshot.next_action == "retry_check"
    assert snapshot.saved_assignments[0].folder_name == "PC"
    assert "/private" not in snapshot.model_dump_json()


def test_status_never_rewrites_saved_mapping_or_audit(admin_user, saved_root):
    persist(saved_root, SLUGS)
    with sync_session.begin() as session:
        before = [
            (m.id, m.version, m.updated_at)
            for m in session.scalars(select(PlatformStorageMapping)).all()
        ]
        audit_count = session.query(StorageMappingAudit).count()
    assert recovery().snapshot().setup_complete
    assert recovery().snapshot().setup_complete
    with sync_session.begin() as session:
        after = [
            (m.id, m.version, m.updated_at)
            for m in session.scalars(select(PlatformStorageMapping)).all()
        ]
        assert before == after
        assert session.query(StorageMappingAudit).count() == audit_count
        assert session.query(ScanOperation).count() == 0
