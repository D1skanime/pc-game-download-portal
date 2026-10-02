import pytest
from sqlalchemy import BigInteger, inspect
from tests.conftest import session

from models.base import BaseModel
from models.download_manifest import (
    DownloadManifest,
    DownloadManifestComponent,
    DownloadManifestMember,
)
from models.download_transfer import (
    DownloadTransferEvent,
    DownloadTransferItem,
    DownloadTransferItemStatus,
    DownloadTransferMode,
    DownloadTransferSession,
    DownloadTransferSessionStatus,
)
from models.rom import RomComponent, RomComponentKind, RomComponentManifestMember


@pytest.fixture(scope="module", autouse=True)
def transfer_tables():
    tables = [
        DownloadTransferSession.__table__,
        DownloadTransferItem.__table__,
        DownloadTransferEvent.__table__,
    ]
    engine = session.kw["bind"]
    created = not inspect(engine).has_table(DownloadTransferSession.__tablename__)
    if created:
        BaseModel.metadata.create_all(bind=engine, tables=tables)
    yield
    if created:
        BaseModel.metadata.drop_all(bind=engine, tables=tables)


@pytest.fixture(autouse=True)
def clear_transfer_rows():
    yield
    with session.begin() as db:
        db.query(DownloadTransferEvent).delete()
        db.query(DownloadTransferItem).delete()
        db.query(DownloadTransferSession).delete()


def test_transfer_snapshot_is_path_free_and_owner_cascades(admin_user, rom):
    component = RomComponent(
        rom_id=rom.id, relative_path="base", kind=RomComponentKind.BASE
    )
    source_member = RomComponentManifestMember(
        component=component,
        relative_path="base/game.iso",
        size_bytes=2**32 + 3,
        sha256="a" * 64,
    )
    manifest = DownloadManifest(user_id=admin_user.id, rom_id=rom.id)
    selected_component = DownloadManifestComponent(
        manifest=manifest, component=component
    )
    manifest_member = DownloadManifestMember(
        component=selected_component,
        manifest_member=source_member,
        destination="game.iso",
        size_bytes=2**32 + 3,
        sha256="a" * 64,
        snapshot='"snapshot"',
        mtime_ns=1,
    )
    with session.begin() as db:
        db.add(manifest)
        db.flush()
        manifest_member_id = manifest_member.id
        manifest_member_public_id = manifest_member.public_id
    transfer = DownloadTransferSession(
        user_id=admin_user.id,
        rom_id=rom.id,
        manifest=manifest,
        mode=DownloadTransferMode.STANDARD,
        selected_items=1,
        selected_bytes=2**32 + 3,
        status=DownloadTransferSessionStatus.ACTIVE,
    )
    item = DownloadTransferItem(
        session=transfer,
        manifest_member_id=manifest_member_id,
        manifest_member_public_id=manifest_member_public_id,
        expected_bytes=2**32 + 3,
        status=DownloadTransferItemStatus.QUEUED,
    )
    event = DownloadTransferEvent(
        session=transfer,
        item=item,
        ordinal=1,
        event_type="handoff",
        observed_bytes=0,
    )
    with session.begin() as db:
        db.add(event)
        db.flush()
        transfer_id = transfer.id

    with session() as db:
        saved = db.get(DownloadTransferSession, transfer_id)
        assert saved is not None
        assert saved.user_id == admin_user.id
        assert saved.items[0].expected_bytes == 2**32 + 3
        assert saved.events[0].ordinal == 1

    columns = {
        column.name
        for table in (
            DownloadTransferSession.__table__,
            DownloadTransferItem.__table__,
            DownloadTransferEvent.__table__,
        )
        for column in table.columns
    }
    assert columns.isdisjoint(
        {"path", "source_path", "url", "token", "credential", "local_handle", "range"}
    )

    with session.begin() as db:
        db.delete(db.get(DownloadTransferSession, transfer_id))
    with session() as db:
        assert db.get(DownloadTransferItem, item.id) is None
        assert db.get(DownloadTransferEvent, event.id) is None


def test_transfer_statuses_distinguish_server_facts_from_browser_observations():
    assert DownloadTransferItemStatus.HANDED_TO_BROWSER.value == "handed_to_browser"
    assert DownloadTransferItemStatus.SERVED.value == "served"
    assert DownloadTransferItemStatus.VERIFIED.value == "verified"
    assert DownloadTransferSessionStatus.STALE.value == "stale"
    assert DownloadTransferMode.STANDARD.value == "standard"
    assert DownloadTransferMode.ENHANCED.value == "enhanced"


def test_event_bounds_and_timestamps_are_explicit():
    assert DownloadTransferEvent.__table__.c.error_code.type.length <= 64
    assert isinstance(DownloadTransferEvent.__table__.c.observed_bytes.type, BigInteger)
    assert DownloadTransferSession.__table__.c.started_at.nullable is False
