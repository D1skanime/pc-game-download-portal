"""Real SQL cleanup retains shared or replaced content and resumes exact intents."""

import importlib
import os
from datetime import timedelta
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


def test_shared_reference_removed_after_prepare_is_rechecked(rom, admin_user):
    target, _ = seed(rom, admin_user)
    relative = rom.fs_resources_path + "/cover/original.png"
    with sync_session.begin() as session:
        session.add(
            Collection(name="shared", user_id=admin_user.id, path_cover_l=relative)
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
