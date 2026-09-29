import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from tests.conftest import session

from endpoints.responses.rom import RomOwnedMediaSchema
from handler.database import db_rom_handler
from models.owned_media_cleanup import OwnedMediaCleanupIntent
from models.rom import (
    Rom,
    RomFile,
    RomFileCategory,
    RomLocalBackgroundAudio,
    RomOwnedBackgroundAudio,
    RomOwnedMedia,
    RomOwnedMediaOrigin,
    RomOwnedMediaPlacement,
    RomOwnedMediaRole,
    RomOwnedMediaState,
    RomOwnedMediaSurface,
    derive_owned_media_display_label,
)


def test_local_background_audio_rejects_foreign_and_non_soundtrack_files(rom, platform):
    soundtrack = db_rom_handler.add_rom_file(
        RomFile(
            rom_id=rom.id,
            file_name="track.mp3",
            file_path=f"{rom.fs_path}/OST",
            category=RomFileCategory.SOUNDTRACK,
        )
    )
    game_file = db_rom_handler.add_rom_file(
        RomFile(
            rom_id=rom.id,
            file_name="game.exe",
            file_path=rom.fs_path,
            category=RomFileCategory.GAME,
        )
    )
    foreign_rom = db_rom_handler.add_rom(
        Rom(
            platform_id=platform.id,
            name="foreign",
            fs_name="foreign.zip",
            fs_path=rom.fs_path,
        )
    )
    foreign_file = db_rom_handler.add_rom_file(
        RomFile(
            rom_id=foreign_rom.id,
            file_name="foreign.mp3",
            file_path=f"{foreign_rom.fs_path}/OST",
            category=RomFileCategory.SOUNDTRACK,
        )
    )

    selected = db_rom_handler.replace_local_background_audio(
        rom.id, rom.updated_at, [soundtrack.id]
    )

    assert selected is not None
    assert [item.rom_file_id for item in selected.local_background_audio] == [
        soundtrack.id
    ]
    assert (
        db_rom_handler.replace_local_background_audio(
            rom.id, selected.updated_at, [foreign_file.id]
        )
        is None
    )
    assert (
        db_rom_handler.replace_local_background_audio(
            rom.id, selected.updated_at, [game_file.id]
        )
        is None
    )


def test_local_background_audio_cascades_when_source_file_is_removed(rom):
    soundtrack = db_rom_handler.add_rom_file(
        RomFile(
            rom_id=rom.id,
            file_name="track.mp3",
            file_path=f"{rom.fs_path}/OST",
            category=RomFileCategory.SOUNDTRACK,
        )
    )
    selected = db_rom_handler.replace_local_background_audio(
        rom.id, rom.updated_at, [soundtrack.id]
    )
    assert selected is not None

    with session.begin() as db:
        db.delete(db.get(RomFile, soundtrack.id))

    with session() as db:
        assert db.query(RomLocalBackgroundAudio).count() == 0


def test_owned_background_audio_rejects_foreign_inactive_and_non_soundtrack_media(
    rom, platform
):
    foreign_rom = db_rom_handler.add_rom(
        Rom(
            platform_id=platform.id,
            name="foreign",
            fs_name="foreign.zip",
            fs_path=rom.fs_path,
        )
    )
    track = RomOwnedMedia(
        rom_id=rom.id,
        origin=RomOwnedMediaOrigin.UPLOAD,
        role=RomOwnedMediaRole.SOUNDTRACK,
        display_label="track.mp3",
        mime_type="audio/mpeg",
        owned_path="roms/1/media/upload/track.mp3",
    )
    foreign_track = RomOwnedMedia(
        rom_id=foreign_rom.id,
        origin=RomOwnedMediaOrigin.UPLOAD,
        role=RomOwnedMediaRole.SOUNDTRACK,
        display_label="foreign.mp3",
        mime_type="audio/mpeg",
        owned_path="roms/2/media/upload/foreign.mp3",
    )
    artwork = RomOwnedMedia(
        rom_id=rom.id,
        origin=RomOwnedMediaOrigin.UPLOAD,
        role=RomOwnedMediaRole.ARTWORK,
        display_label="artwork.webp",
        mime_type="image/webp",
        owned_path="roms/1/media/upload/artwork.webp",
    )
    inactive_track = RomOwnedMedia(
        rom_id=rom.id,
        origin=RomOwnedMediaOrigin.UPLOAD,
        role=RomOwnedMediaRole.SOUNDTRACK,
        state=RomOwnedMediaState.TOMBSTONED,
        display_label="inactive.mp3",
        mime_type="audio/mpeg",
        owned_path=None,
    )
    with session.begin() as db:
        db.add_all((track, foreign_track, artwork, inactive_track))
        db.flush()

    selected = db_rom_handler.replace_owned_background_audio(
        rom.id, rom.updated_at, [track.id]
    )

    assert selected is not None
    assert selected.owned_background_audio_media_ids == [track.id]
    assert (
        db_rom_handler.replace_owned_background_audio(
            rom.id, selected.updated_at, [foreign_track.id]
        )
        is None
    )
    assert (
        db_rom_handler.replace_owned_background_audio(
            rom.id, selected.updated_at, [artwork.id]
        )
        is None
    )
    assert (
        db_rom_handler.replace_owned_background_audio(
            rom.id, selected.updated_at, [inactive_track.id]
        )
        is None
    )


def test_owned_background_audio_keeps_inactive_selection_and_cascades_on_delete(rom):
    track = RomOwnedMedia(
        rom_id=rom.id,
        origin=RomOwnedMediaOrigin.UPLOAD,
        role=RomOwnedMediaRole.SOUNDTRACK,
        display_label="track.mp3",
        mime_type="audio/mpeg",
        owned_path="roms/1/media/upload/track.mp3",
    )
    with session.begin() as db:
        db.add(track)
        db.flush()

    selected = db_rom_handler.replace_owned_background_audio(
        rom.id, rom.updated_at, [track.id]
    )
    assert selected is not None

    with session.begin() as db:
        db.get(RomOwnedMedia, track.id).state = RomOwnedMediaState.TOMBSTONED

    with session() as db:
        assert db.query(RomOwnedBackgroundAudio).count() == 1

    with session.begin() as db:
        db.delete(db.get(RomOwnedMedia, track.id))

    with session() as db:
        assert db.query(RomOwnedBackgroundAudio).count() == 0


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


def test_detailed_rom_contract_loads_owned_catalog_before_any_legacy_refresh():
    handler_source = (
        Path(__file__).parents[3] / "handler/database/roms_handler.py"
    ).read_text()
    response_source = (
        Path(__file__).parents[3] / "endpoints/responses/rom.py"
    ).read_text()

    assert (
        "selectinload(Rom.owned_media).selectinload(RomOwnedMedia.placements)"
        in handler_source
    )
    assert "owned_media: list[RomOwnedMediaSchema]" in response_source
    assert (
        "owned_media_placements: list[RomOwnedMediaPlacementSchema]" in response_source
    )


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
        role=RomOwnedMediaRole.SCREENSHOT,
        display_label="image-1.webp",
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
        role=RomOwnedMediaRole.SCREENSHOT,
        display_label="image-1.webp",
        mime_type="image/webp",
        owned_path="roms/1/media/provider/image-1.webp",
    )
    assert refreshed is not None
    assert refreshed.media.id == created.media.id
    assert refreshed.media.placements == []


def test_complete_reorder_rejects_incomplete_membership(rom):
    first = db_rom_handler.create_owned_upload_media(
        rom.id,
        rom.updated_at,
        RomOwnedMediaRole.ARTWORK,
        "first.webp",
        "image/webp",
        "roms/1/media/upload/first.webp",
    )
    assert first is not None
    second = db_rom_handler.create_owned_upload_media(
        rom.id,
        first.rom.updated_at,
        RomOwnedMediaRole.ARTWORK,
        "second.webp",
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


@pytest.mark.parametrize(
    "role",
    [
        RomOwnedMediaRole.SCREENSHOT,
        RomOwnedMediaRole.ARTWORK,
        RomOwnedMediaRole.SOUNDTRACK,
    ],
)
def test_owned_media_persists_each_supported_role(rom, role):
    candidate = RomOwnedMedia(
        rom_id=rom.id,
        origin=RomOwnedMediaOrigin.UPLOAD,
        role=role,
        display_label="operator-upload.webp",
        mime_type="image/webp",
        owned_path="roms/1/media/upload/operator-upload.webp",
    )

    with session.begin() as db:
        db.add(candidate)
        db.flush()

    assert candidate.role == role


def test_owned_media_database_rejects_invalid_role(rom):
    candidate = RomOwnedMedia(
        rom_id=rom.id,
        origin=RomOwnedMediaOrigin.UPLOAD,
        role="cover",
        display_label="operator-upload.webp",
        mime_type="image/webp",
        owned_path="roms/1/media/upload/operator-upload.webp",
    )

    with pytest.raises(IntegrityError):
        with session.begin() as db:
            db.add(candidate)
            db.flush()


def test_owned_media_role_is_immutable_after_persistence(rom):
    candidate = RomOwnedMedia(
        rom_id=rom.id,
        origin=RomOwnedMediaOrigin.UPLOAD,
        role=RomOwnedMediaRole.ARTWORK,
        display_label="operator-upload.webp",
        mime_type="image/webp",
        owned_path="roms/1/media/upload/operator-upload.webp",
    )
    with session.begin() as db:
        db.add(candidate)
        db.flush()

    with pytest.raises(ValueError, match="immutable"):
        candidate.role = RomOwnedMediaRole.SOUNDTRACK


def test_display_label_is_a_bounded_sanitized_basename():
    label = derive_owned_media_display_label("nested\\operator:mix?01.flac" + "x" * 400)

    assert label.startswith("operator-mix01.flac")
    assert len(label) <= 255
    assert "/" not in label
    assert "\\" not in label
    assert not any(char.isspace() and ord(char) < 32 for char in label)


@pytest.mark.parametrize(
    "label",
    [
        "/absolute.webp",
        "relative/path.webp",
        "relative\\path.webp",
        "label\n.webp",
        "https://provider.example/image.webp",
    ],
)
def test_display_label_rejects_path_control_and_provider_url_values(label):
    with pytest.raises(ValueError):
        derive_owned_media_display_label(label, reject_unsafe_input=True)


def test_owned_media_role_migration_is_additive_and_reversible():
    migration_path = (
        Path(__file__).parents[3]
        / "alembic/versions/0123_owned_media_role_and_display_label.py"
    )
    spec = importlib.util.spec_from_file_location(
        "owned_media_role_migration", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.down_revision == "0127_parent_rom_owned_media"
    assert migration.revision == "0128_owned_media_role_and_display_label"


def test_provider_reconciliation_requires_safe_server_owned_role_and_label(rom):
    created = db_rom_handler.reconcile_provider_owned_media(
        rom_id=rom.id,
        expected_updated_at=rom.updated_at,
        provider="igdb",
        provider_media_id="artwork-1",
        role=RomOwnedMediaRole.ARTWORK,
        display_label="artwork-1.webp",
        mime_type="image/webp",
        owned_path="roms/1/media/provider/artwork-1.webp",
    )

    assert created is not None
    assert created.media.role == RomOwnedMediaRole.ARTWORK
    assert created.media.display_label == "artwork-1.webp"

    assert (
        db_rom_handler.reconcile_provider_owned_media(
            rom_id=rom.id,
            expected_updated_at=created.rom.updated_at,
            provider="igdb",
            provider_media_id="artwork-1",
            role=RomOwnedMediaRole.SCREENSHOT,
            display_label="artwork-1.webp",
            mime_type="image/webp",
            owned_path="roms/1/media/provider/artwork-1.webp",
        )
        is None
    )


def test_upload_creation_accepts_only_artwork_or_soundtrack_with_safe_label(rom):
    artwork = db_rom_handler.create_owned_upload_media(
        rom.id,
        rom.updated_at,
        RomOwnedMediaRole.ARTWORK,
        "operator-artwork.webp",
        "image/webp",
        "roms/1/media/upload/operator-artwork.webp",
    )
    assert artwork is not None
    assert artwork.media.display_label == "operator-artwork.webp"

    assert (
        db_rom_handler.create_owned_upload_media(
            rom.id,
            artwork.rom.updated_at,
            RomOwnedMediaRole.SCREENSHOT,
            "operator-screenshot.webp",
            "image/webp",
            "roms/1/media/upload/operator-screenshot.webp",
        )
        is None
    )
    assert (
        db_rom_handler.create_owned_upload_media(
            rom.id,
            artwork.rom.updated_at,
            RomOwnedMediaRole.SOUNDTRACK,
            "https://provider.example/track.flac",
            "audio/flac",
            "roms/1/media/upload/track.flac",
        )
        is None
    )


@pytest.mark.parametrize(
    ("role", "surface"),
    [
        (RomOwnedMediaRole.SOUNDTRACK, RomOwnedMediaSurface.OVERVIEW),
        (RomOwnedMediaRole.SOUNDTRACK, RomOwnedMediaSurface.BACKGROUND),
        (RomOwnedMediaRole.ARTWORK, RomOwnedMediaSurface.SOUNDTRACK),
    ],
)
def test_placement_rejects_incompatible_owned_media_role(rom, role, surface):
    media = db_rom_handler.create_owned_upload_media(
        rom.id,
        rom.updated_at,
        role,
        "operator-media.flac" if role == RomOwnedMediaRole.SOUNDTRACK else "art.webp",
        "audio/flac" if role == RomOwnedMediaRole.SOUNDTRACK else "image/webp",
        "roms/1/media/upload/operator-media",
    )
    assert media is not None

    assert (
        db_rom_handler.set_owned_media_placement(
            rom.id,
            media.media.id,
            media.rom.updated_at,
            surface,
            selected=True,
        )
        is None
    )


def test_owned_media_schema_serializes_role_and_safe_display_label(rom):
    media = db_rom_handler.create_owned_upload_media(
        rom.id,
        rom.updated_at,
        RomOwnedMediaRole.SOUNDTRACK,
        "operator-track.flac",
        "audio/flac",
        "roms/1/media/upload/operator-track.flac",
    )
    assert media is not None

    schema = RomOwnedMediaSchema.model_validate(media.media)

    assert schema.role == RomOwnedMediaRole.SOUNDTRACK
    assert schema.display_label == "operator-track.flac"
