from datetime import UTC, datetime, timedelta

import pytest
from tests.conftest import session

from handler.database.download_transfers_handler import DBDownloadTransfersHandler
from models.download_manifest import (
    DownloadManifest,
    DownloadManifestComponent,
    DownloadManifestMember,
)
from models.download_transfer import (
    DownloadTransferEvent,
    DownloadTransferItemStatus,
    DownloadTransferMode,
    DownloadTransferSession,
    DownloadTransferSessionStatus,
)
from models.rom import RomComponent, RomComponentKind, RomComponentManifestMember


@pytest.fixture
def manifest(rom, admin_user):
    component = RomComponent(
        rom_id=rom.id, relative_path="base", kind=RomComponentKind.BASE
    )
    source = RomComponentManifestMember(
        component=component,
        relative_path="base/game.iso",
        size_bytes=42,
        sha256="a" * 64,
    )
    with session.begin() as db:
        db.add(component)
        db.flush()
        saved = DownloadManifest(
            user_id=admin_user.id,
            rom_id=rom.id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        selected = DownloadManifestComponent(manifest=saved, component=component)
        DownloadManifestMember(
            component=selected,
            manifest_member=source,
            destination="game.iso",
            size_bytes=42,
            sha256="a" * 64,
            snapshot='"snapshot"',
            mtime_ns=1,
        )
        db.add(saved)
        db.flush()
        return saved


def test_owner_scoped_session_creation_copies_manifest_members(
    admin_user, rom, manifest
):
    handler = DBDownloadTransfersHandler()
    transfer = handler.create_session(
        admin_user.id, manifest.id, DownloadTransferMode.STANDARD
    )
    assert transfer.user_id == admin_user.id
    assert len(transfer.items) == len(manifest.members)
    assert all(
        item.status is DownloadTransferItemStatus.QUEUED for item in transfer.items
    )


def test_foreign_owner_is_masked_and_events_are_append_only(
    admin_user, viewer_user, manifest
):
    handler = DBDownloadTransfersHandler()
    transfer = handler.create_session(
        admin_user.id, manifest.id, DownloadTransferMode.STANDARD
    )
    assert handler.get_session(transfer.id, viewer_user.id) is None
    item = transfer.items[0]
    handoff = handler.append_observation(
        transfer.id, admin_user.id, item.id, "handoff", observed_bytes=0
    )
    assert handoff.ordinal == 1
    assert (
        handler.get_session(transfer.id, admin_user.id).items[0].status
        is DownloadTransferItemStatus.HANDED_TO_BROWSER
    )
    with pytest.raises(ValueError, match="served"):
        handler.append_observation(
            transfer.id,
            admin_user.id,
            item.id,
            "served",
            observed_bytes=item.expected_bytes,
        )
    with pytest.raises(ValueError, match="monotonic"):
        handler.append_observation(
            transfer.id, admin_user.id, item.id, "progress", observed_bytes=1
        )


def test_get_sessions_applies_owner_scoped_rom_and_manifest_filters(
    admin_user, manifest, rom
):
    handler = DBDownloadTransfersHandler()
    transfer = handler.create_session(
        admin_user.id, manifest.id, DownloadTransferMode.STANDARD
    )

    assert [item.id for item in handler.get_sessions(admin_user.id)] == [transfer.id]
    assert [item.id for item in handler.get_sessions(admin_user.id, rom_id=rom.id)] == [
        transfer.id
    ]
    assert [
        item.id for item in handler.get_sessions(admin_user.id, manifest_id=manifest.id)
    ] == [transfer.id]
    assert handler.get_sessions(admin_user.id, rom_id=rom.id + 1) == []
    assert handler.get_sessions(admin_user.id, manifest_id="0" * 36) == []


def test_standard_cannot_claim_verified_and_enhanced_can_verify_only_digest_match(
    admin_user, manifest
):
    handler = DBDownloadTransfersHandler()
    standard = handler.create_session(
        admin_user.id, manifest.id, DownloadTransferMode.STANDARD
    )
    item = standard.items[0]
    handler.append_observation(standard.id, admin_user.id, item.id, "handoff")
    with pytest.raises(ValueError, match="standard"):
        handler.append_observation(
            standard.id,
            admin_user.id,
            item.id,
            "verified",
            observed_bytes=item.expected_bytes,
            sha256="a" * 64,
        )

    enhanced = handler.create_session(
        admin_user.id, manifest.id, DownloadTransferMode.ENHANCED
    )
    enhanced_item = enhanced.items[0]
    handler.append_observation(enhanced.id, admin_user.id, enhanced_item.id, "handoff")
    with pytest.raises(ValueError, match="digest"):
        handler.append_observation(
            enhanced.id,
            admin_user.id,
            enhanced_item.id,
            "verified",
            observed_bytes=enhanced_item.expected_bytes,
            sha256="b" * 64,
        )


def test_closed_sessions_reject_new_observations(admin_user, manifest):
    handler = DBDownloadTransfersHandler()
    transfer = handler.create_session(
        admin_user.id, manifest.id, DownloadTransferMode.ENHANCED
    )
    handler.cancel_session(transfer.id, admin_user.id)
    with pytest.raises(ValueError, match="closed"):
        handler.append_observation(
            transfer.id, admin_user.id, transfer.items[0].id, "handoff"
        )


def test_cleanup_marks_active_sessions_with_expired_manifests_stale(
    admin_user, rom, manifest
):
    handler = DBDownloadTransfersHandler()
    transfer = handler.create_session(
        admin_user.id, manifest.id, DownloadTransferMode.ENHANCED
    )
    cutoff_now = datetime(2026, 1, 1, tzinfo=UTC)
    with session.begin() as db:
        manifest.expires_at = cutoff_now - timedelta(seconds=1)
        db.add(manifest)

    result = handler.cleanup_sessions(now=cutoff_now, batch_limit=10)
    assert result["staled"] == 1
    refreshed = handler.get_session(transfer.id, admin_user.id)
    assert refreshed.status is DownloadTransferSessionStatus.STALE
    assert refreshed.items[0].status is DownloadTransferItemStatus.STALE
    assert refreshed.events[-1].event_type == "stale"
    with pytest.raises(ValueError, match="closed"):
        handler.append_observation(
            transfer.id, admin_user.id, transfer.items[0].id, "resume"
        )


def test_cleanup_deletes_terminal_sessions_at_exact_90_day_cutoff(admin_user, manifest):
    handler = DBDownloadTransfersHandler()
    transfer = handler.create_session(
        admin_user.id, manifest.id, DownloadTransferMode.STANDARD
    )
    finished = datetime(2025, 10, 3, tzinfo=UTC)
    now = finished + timedelta(days=90)
    with session.begin() as db:
        row = db.get(DownloadTransferSession, transfer.id)
        row.status = DownloadTransferSessionStatus.CANCELLED
        row.ended_at = finished
        db.add(
            DownloadTransferEvent(
                session_id=transfer.id,
                item_id=transfer.items[0].id,
                ordinal=1,
                event_type="cancel",
                observed_bytes=0,
                occurred_at=finished,
            )
        )

    result = handler.cleanup_sessions(now=now, batch_limit=10)
    assert result["deleted"] == 1
    assert handler.get_session(transfer.id, admin_user.id) is None


def test_cleanup_is_capped_and_repeatable(admin_user, manifest):
    handler = DBDownloadTransfersHandler()
    transfers = [
        handler.create_session(
            admin_user.id, manifest.id, DownloadTransferMode.STANDARD
        )
        for _ in range(3)
    ]
    finished = datetime(2025, 10, 3, tzinfo=UTC)
    now = finished + timedelta(days=90)
    with session.begin() as db:
        for transfer in transfers:
            row = db.get(DownloadTransferSession, transfer.id)
            row.status = DownloadTransferSessionStatus.FAILED
            row.ended_at = finished

    first = handler.cleanup_sessions(now=now, batch_limit=2)
    second = handler.cleanup_sessions(now=now, batch_limit=2)
    third = handler.cleanup_sessions(now=now, batch_limit=2)
    assert [first["deleted"], second["deleted"], third["deleted"]] == [2, 1, 0]
