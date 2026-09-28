from tests.conftest import session

from handler.database import db_rom_handler
from models.owned_media_cleanup import OwnedMediaCleanupIntent
from models.rom import (
    RomOwnedMedia,
    RomOwnedMediaOrigin,
    RomOwnedMediaPlacement,
    RomOwnedMediaSurface,
)


def test_model_keeps_candidate_and_placements_independent(rom):
    candidate = RomOwnedMedia(
        rom_id=rom.id,
        origin=RomOwnedMediaOrigin.PROVIDER,
        provider="igdb",
        provider_media_id="screenshot-1",
        mime_type="image/webp",
        owned_path="roms/1/media/provider/screenshot-1.webp",
    )
    overview = RomOwnedMediaPlacement(
        media=candidate,
        surface=RomOwnedMediaSurface.OVERVIEW,
        position=0,
    )
    background = RomOwnedMediaPlacement(
        media=candidate,
        surface=RomOwnedMediaSurface.BACKGROUND,
        position=0,
    )

    with session.begin() as db:
        db.add_all((candidate, overview, background))
        db.flush()

    assert candidate.id is not None
    assert {placement.surface for placement in candidate.placements} == {
        RomOwnedMediaSurface.OVERVIEW,
        RomOwnedMediaSurface.BACKGROUND,
    }
    assert candidate.rom_id == rom.id


def test_cleanup_intent_only_accepts_generated_owned_resource_path(rom):
    intent = OwnedMediaCleanupIntent(
        rom_id=rom.id,
        media_id=42,
        owned_path="roms/1/media/upload/cover.webp",
    )

    with session.begin() as db:
        db.add(intent)
        db.flush()

    assert intent.owned_path == "roms/1/media/upload/cover.webp"


def test_provider_refresh_reactivates_tombstone_without_placing_it(rom):
    created = db_rom_handler.reconcile_provider_owned_media(
        rom_id=rom.id,
        expected_updated_at=rom.updated_at,
        provider="igdb",
        provider_media_id="image-1",
        mime_type="image/webp",
        owned_path="roms/1/media/provider/image-1.webp",
    )
    assert created is not None

    deleted = db_rom_handler.delete_owned_media(
        rom_id=rom.id,
        media_id=created.media.id,
        expected_updated_at=created.rom.updated_at,
    )
    assert deleted is not None
    assert deleted.owned_paths == ["roms/1/media/provider/image-1.webp"]

    refreshed = db_rom_handler.reconcile_provider_owned_media(
        rom_id=rom.id,
        expected_updated_at=deleted.rom.updated_at,
        provider="igdb",
        provider_media_id="image-1",
        mime_type="image/webp",
        owned_path="roms/1/media/provider/image-1.webp",
    )
    assert refreshed is not None
    assert refreshed.media.id == created.media.id
    assert refreshed.media.placements == []


def test_complete_reorder_rejects_incomplete_membership(rom):
    first = db_rom_handler.create_owned_upload_media(
        rom.id, rom.updated_at, "image/webp", "roms/1/media/upload/first.webp"
    )
    assert first is not None
    second = db_rom_handler.create_owned_upload_media(
        rom.id,
        first.rom.updated_at,
        "image/webp",
        "roms/1/media/upload/second.webp",
    )
    assert second is not None
    placed = db_rom_handler.replace_owned_media_placements(
        rom.id,
        second.rom.updated_at,
        RomOwnedMediaSurface.BACKGROUND,
        [first.media.id, second.media.id],
    )
    assert placed is not None
    assert (
        db_rom_handler.replace_owned_media_placements(
            rom.id,
            placed.updated_at,
            RomOwnedMediaSurface.BACKGROUND,
            [first.media.id],
        )
        is None
    )
