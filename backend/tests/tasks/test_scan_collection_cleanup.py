"""Real SQL cleanup retains shared or replaced content and resumes exact intents."""

import asyncio
import importlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest.mock import patch

import pytest
from sqlalchemy import select

from handler.database.base_handler import sync_session
from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler
from handler.filesystem import fs_resource_handler
from models.base import utc_now
from models.catalog_lifecycle import OwnedCleanupIntent, OwnedCleanupState
from models.collection import Collection


def cleanup():
    return importlib.import_module("handler.filesystem.catalog_collection_cleanup")


def seed(rom, admin_user):
    target = fs_resource_handler.validate_path(
        rom.fs_resources_path + "/cover/original.png"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"proven parent cover")
    manifest = cleanup().prepare_collection_cleanup(rom)
    lifecycle = CatalogLifecycleHandler()
    lifecycle.remove_from_catalog(rom.id, actor_user_id=admin_user.id)
    with sync_session.begin() as session:
        row = session.scalar(
            select(OwnedCleanupIntent).where(
                OwnedCleanupIntent.relative_path == rom.fs_resources_path,
            )
        )
        row.exact_manifest = manifest
        row.exact_progress = {"cursor": 0, "retained": []}
    return target, lifecycle


def test_exact_cleanup_completes_and_replay_is_noop(rom, admin_user):
    target, lifecycle = seed(rom, admin_user)
    claimed = lifecycle.claim_cleanup_intents(limit=8, collection_only=True)
    assert len(claimed) == 1
    assert cleanup().process_collection_cleanup_intent(
        claimed[0].id, claimed[0].version
    )
    assert not target.exists()
    assert (
        cleanup().process_collection_cleanup_intent(claimed[0].id, claimed[0].version)
        is False
    )
    with sync_session.begin() as session:
        row = session.get(OwnedCleanupIntent, claimed[0].id)
        assert row.state == OwnedCleanupState.COMPLETED
        assert row.exact_progress["cursor"] == len(row.exact_manifest["outputs"])


@pytest.mark.parametrize("replacement", ["different_bytes", "same_bytes_new_inode"])
def test_reused_path_is_retained(rom, admin_user, replacement):
    target, _ = seed(rom, admin_user)
    original = target.read_bytes()
    target.unlink()
    target.write_bytes(
        original if replacement == "same_bytes_new_inode" else b"replacement"
    )
    expected = target.read_bytes()
    result = cleanup().process_pending_collection_cleanup()
    assert result["completed"] == 1
    assert target.read_bytes() == expected
    with sync_session.begin() as session:
        row = session.scalar(
            select(OwnedCleanupIntent).where(
                OwnedCleanupIntent.exact_manifest.is_not(None)
            )
        )
        assert row.exact_progress["retained"]


def test_other_collection_cover_reference_preserves_file(rom, admin_user):
    target, _ = seed(rom, admin_user)
    relative = target.relative_to(
        fs_resource_handler.validate_path(rom.fs_resources_path).parents[2]
    ).as_posix()
    with sync_session.begin() as session:
        session.add(
            Collection(name="shared", user_id=admin_user.id, path_cover_l=relative)
        )
    assert cleanup().process_pending_collection_cleanup()["completed"] == 1
    assert target.read_bytes() == b"proven parent cover"


@pytest.mark.parametrize(
    "surface",
    [
        "rom",
        "owned",
        "component_owned",
        "component_local",
        "component_metadata",
        "track",
        "screenshot",
    ],
)
def test_live_reference_surfaces_are_rechecked(
    rom, admin_user, multi_file_rom, surface
):
    from models.assets import Screenshot
    from models.rom import (
        Rom,
        RomComponent,
        RomComponentKind,
        RomComponentLocalMedia,
        RomComponentLocalMediaRole,
        RomComponentMetadata,
        RomComponentOwnedMedia,
        RomComponentOwnedMediaOrigin,
        RomComponentOwnedMediaRole,
        RomOwnedMedia,
        RomOwnedMediaOrigin,
        TrackMeta,
    )

    target, _ = seed(rom, admin_user)
    relative = rom.fs_resources_path + "/cover/original.png"
    other = multi_file_rom
    with sync_session.begin() as session:
        if surface == "rom":
            session.get(Rom, other.id).path_cover_l = relative
        elif surface == "owned":
            session.add(
                RomOwnedMedia(
                    rom_id=other.id,
                    origin=RomOwnedMediaOrigin.UPLOAD,
                    mime_type="image/png",
                    owned_path=relative,
                )
            )
        elif surface.startswith("component"):
            component = RomComponent(
                rom_id=other.id, relative_path="base", kind=RomComponentKind.BASE
            )
            session.add(component)
            session.flush()
            if surface == "component_owned":
                session.add(
                    RomComponentOwnedMedia(
                        component_id=component.id,
                        role=RomComponentOwnedMediaRole.COVER,
                        origin=RomComponentOwnedMediaOrigin.UPLOAD,
                        mime_type="image/png",
                        owned_path=relative,
                    )
                )
            elif surface == "component_local":
                session.add(
                    RomComponentLocalMedia(
                        component_id=component.id,
                        source_relative_path="cover.png",
                        source_sha256="a" * 64,
                        owned_path=relative,
                        image_type="image/png",
                        role=RomComponentLocalMediaRole.COVER,
                    )
                )
            else:
                session.add(
                    RomComponentMetadata(
                        component_id=component.id,
                        steam_metadata={"cover_path": relative},
                    )
                )
        elif surface == "track":
            session.add(
                TrackMeta(
                    rom_id=other.id, rom_file_id=other.files[0].id, cover_path=relative
                )
            )
        else:
            session.add(
                Screenshot(
                    rom_id=other.id,
                    user_id=admin_user.id,
                    file_name="original.png",
                    file_path=rom.fs_resources_path + "/cover",
                    file_size_bytes=18,
                )
            )
    assert cleanup().process_pending_collection_cleanup()["completed"] == 1
    assert target.exists()


def test_crash_after_unlink_replays_missing_target_and_completes(rom, admin_user):
    target, lifecycle = seed(rom, admin_user)
    claimed = lifecycle.claim_cleanup_intents(limit=8, collection_only=True)[0]
    original = cleanup()._delete_output

    def interrupted(*args, **kwargs):
        original(*args, **kwargs)
        raise SystemExit("simulated process death")

    with patch.object(cleanup(), "_delete_output", interrupted):
        with pytest.raises(SystemExit):
            cleanup().process_collection_cleanup_intent(claimed.id, claimed.version)
    assert not target.exists()
    with sync_session.begin() as session:
        row = session.get(OwnedCleanupIntent, claimed.id)
        row.next_attempt_at = utc_now() - timedelta(seconds=1)
    assert cleanup().process_pending_collection_cleanup()["completed"] == 1


def test_cancelled_or_reclaimed_cleanup_version_cannot_delete(rom, admin_user):
    target, lifecycle = seed(rom, admin_user)
    claimed = lifecycle.claim_cleanup_intents(limit=8, collection_only=True)[0]
    with sync_session.begin() as session:
        session.get(OwnedCleanupIntent, claimed.id).version += 1
    assert (
        cleanup().process_collection_cleanup_intent(claimed.id, claimed.version)
        is False
    )
    assert target.exists()


def test_collection_filter_never_claims_legacy_recursive_intent(rom, admin_user):
    lifecycle = CatalogLifecycleHandler()
    lifecycle.remove_from_catalog(rom.id, actor_user_id=admin_user.id)
    assert lifecycle.claim_cleanup_intents(limit=8, collection_only=True) == []


def test_manifest_does_not_follow_source_symlink(rom, tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"source must survive")
    parent = fs_resource_handler.validate_path(rom.fs_resources_path)
    parent.mkdir(parents=True, exist_ok=True)
    (parent / "escaped.png").symlink_to(source)
    manifest = cleanup().prepare_collection_cleanup(rom)
    assert manifest["outputs"] == []
    assert manifest["retained"]
    assert source.read_bytes() == b"source must survive"


@pytest.mark.parametrize("entrypoint", ["manual", "scheduled"])
def test_registered_tasks_use_exact_processor(rom, admin_user, entrypoint):
    target, _ = seed(rom, admin_user)
    if entrypoint == "manual":
        from tasks.manual.cleanup_catalog_assets import cleanup_catalog_assets_task

        asyncio.run(cleanup_catalog_assets_task.run())
    else:
        from tasks.scheduled.owned_media_cleanup import owned_media_cleanup_task

        asyncio.run(owned_media_cleanup_task.run())
    assert not target.exists()


def test_writer_cannot_replace_between_proof_and_unlink(rom, admin_user):
    from handler.filesystem.owned_writer_domain import owned_writer_domain
    from handler.filesystem.storage_access import OwnedDelete

    target, lifecycle = seed(rom, admin_user)
    claimed = lifecycle.claim_cleanup_intents(limit=8, collection_only=True)[0]
    started, acquired = Event(), Event()
    original = OwnedDelete.delete
    futures = []

    def replacement():
        started.set()
        with owned_writer_domain():
            acquired.set()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"replacement after cleanup commit")

    with ThreadPoolExecutor(max_workers=1) as pool:

        def paused_delete(access):
            if access._name == target.name:
                futures.append(pool.submit(replacement))
                assert started.wait(5)
                assert not acquired.wait(0.05), "writer domain released before unlink"
            original(access)

        with patch.object(OwnedDelete, "delete", paused_delete):
            assert cleanup().process_collection_cleanup_intent(
                claimed.id, claimed.version
            )
        futures[0].result(timeout=5)
    assert target.read_bytes() == b"replacement after cleanup commit"
