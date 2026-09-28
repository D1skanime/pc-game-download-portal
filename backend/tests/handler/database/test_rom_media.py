from tests.conftest import session

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
