from datetime import timedelta
from unittest.mock import AsyncMock

from fastapi import status

from endpoints.roms.pc_metadata import pc_metadata_match_handler
from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.filesystem import fs_resource_handler, fs_rom_handler
from handler.metadata.pc_match_handler import (
    PcMetadataCandidate,
    PcMetadataProviderResult,
)
from models.permission import HiddenEntity, PermEntity
from models.rom import (
    RomComponent,
    RomComponentKind,
    RomComponentLocalMediaRole,
    RomComponentManifestMember,
)


def _candidate() -> PcMetadataCandidate:
    return PcMetadataCandidate(
        id="candidate-igdb-101",
        provider="igdb",
        title="Selected PC Game",
        provider_ids={"igdb_id": 101},
        description_available=True,
        media=[{"kind": "cover", "url": "https://images.igdb.com/cover.jpg"}],
        fields={
            "igdb_id": 101,
            "name": "Selected PC Game",
            "summary": "Selected only after review",
        },
    )


def _candidate_results() -> dict[str, PcMetadataProviderResult]:
    return {
        "igdb": PcMetadataProviderResult("igdb", True, [_candidate()]),
        "moby": PcMetadataProviderResult("moby", False, [], "disabled"),
    }


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_get_rom_serializes_pc_component_manifest(client, access_token, rom):
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="base",
                kind=RomComponentKind.BASE,
                manifest_members=[
                    RomComponentManifestMember(
                        relative_path="base/setup.exe",
                        size_bytes=4,
                        sha256="a" * 64,
                    )
                ],
            )
        ],
    )

    response = client.get(f"/api/roms/{rom.id}", headers=_headers(access_token))

    assert response.status_code == status.HTTP_200_OK
    component = response.json()["components"][0]
    assert component["id"] > 0
    assert component["relative_path"] == "base"
    assert component["kind"] == "base"
    assert component["component_metadata"] is None
    assert component["local_media"] == []
    assert component["manifest_members"][0] == {
        "id": component["manifest_members"][0]["id"],
        "relative_path": "base/setup.exe",
        "size_bytes": 4,
        "sha256": "a" * 64,
    }


def test_get_roms_serializes_pc_components(client, access_token, rom):
    """Gallery requests must serialize PC components instead of failing lazily."""
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="base",
                kind=RomComponentKind.BASE,
                manifest_members=[
                    RomComponentManifestMember(
                        relative_path="base/setup.exe",
                        size_bytes=4,
                        sha256="a" * 64,
                    )
                ],
            )
        ],
    )

    response = client.get(
        "/api/roms",
        headers=_headers(access_token),
        params={"platform_id": rom.platform_id},
    )

    assert response.status_code == status.HTTP_200_OK
    component = response.json()["items"][0]["components"][0]
    assert component["id"] > 0
    assert component["relative_path"] == "base"
    assert component["kind"] == "base"
    assert component["component_metadata"] is None
    assert component["local_media"] == []
    assert component["manifest_members"][0] == {
        "id": component["manifest_members"][0]["id"],
        "relative_path": "base/setup.exe",
        "size_bytes": 4,
        "sha256": "a" * 64,
    }


def test_pc_local_media_review_only_lists_direct_dlc_images(
    client, access_token, rom, monkeypatch
):
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="dlc/phantom-liberty",
                kind=RomComponentKind.DLC,
                manifest_members=[
                    RomComponentManifestMember(
                        relative_path="dlc/phantom-liberty/poster.png",
                        size_bytes=4,
                        sha256="a" * 64,
                    ),
                    RomComponentManifestMember(
                        relative_path="dlc/phantom-liberty/guide.pdf",
                        size_bytes=4,
                        sha256="b" * 64,
                    ),
                    RomComponentManifestMember(
                        relative_path="dlc/phantom-liberty/archive.zip",
                        size_bytes=4,
                        sha256="c" * 64,
                    ),
                    RomComponentManifestMember(
                        relative_path="dlc/phantom-liberty/not-an-image.png",
                        size_bytes=4,
                        sha256="d" * 64,
                    ),
                ],
            )
        ],
    )

    def read_image(_rom, member):
        if member.relative_path.endswith("poster.png"):
            return b"valid-image", "png"
        raise ValueError("PC local media is not a decodable image")

    monkeypatch.setattr(fs_rom_handler, "read_pc_component_image", read_image)

    response = client.get(
        f"/api/roms/{rom.id}/pc-local-media-candidates",
        headers=_headers(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    candidates = response.json()["candidates"]
    assert len(candidates) == 1
    assert candidates[0]["relative_path"] == "dlc/phantom-liberty/poster.png"
    assert candidates[0]["image_type"] == "png"
    assert candidates[0]["preview_url"] == (
        f"/api/roms/{rom.id}/pc-local-media-preview/"
        f"{candidates[0]['component_id']}/{candidates[0]['member_id']}"
    )


def test_pc_local_media_selection_copies_verified_image_to_owned_storage(
    client, access_token, rom, monkeypatch
):
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="extra/artwork",
                kind=RomComponentKind.EXTRA,
                manifest_members=[
                    RomComponentManifestMember(
                        relative_path="extra/artwork/wallpaper.webp",
                        size_bytes=4,
                        sha256="d" * 64,
                    )
                ],
            )
        ],
    )
    persisted = db_rom_handler.get_rom(rom.id)
    assert persisted is not None
    component = persisted.components[0]
    member = component.manifest_members[0]

    def read(*_args):
        return (b"verified-image", "webp")

    store = AsyncMock(
        return_value=(
            "roms/1/1/pc-media/1-1-background.webp",
            None,
            None,
        )
    )
    monkeypatch.setattr(fs_rom_handler, "read_pc_component_image", read)
    monkeypatch.setattr(fs_resource_handler, "store_pc_component_image", store)

    response = client.post(
        f"/api/roms/{rom.id}/pc-local-media-selection",
        headers=_headers(access_token),
        json={
            "component_id": component.id,
            "member_id": member.id,
            "role": RomComponentLocalMediaRole.BACKGROUND.value,
            "expected_version": persisted.updated_at.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["media"]["owned_path"].endswith("background.webp")
    store.assert_awaited_once()
    saved = db_rom_handler.get_rom(rom.id)
    assert saved is not None
    assert saved.components[0].local_media[0].source_sha256 == "d" * 64


def test_pc_local_media_selection_rejects_changed_manifest_bytes(
    client, access_token, rom, monkeypatch
):
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="dlc/phantom-liberty",
                kind=RomComponentKind.DLC,
                manifest_members=[
                    RomComponentManifestMember(
                        relative_path="dlc/phantom-liberty/poster.png",
                        size_bytes=4,
                        sha256="e" * 64,
                    )
                ],
            )
        ],
    )
    persisted = db_rom_handler.get_rom(rom.id)
    assert persisted is not None
    component = persisted.components[0]
    member = component.manifest_members[0]
    store = AsyncMock()

    def changed(*_args):
        raise ValueError("PC local media source changed since the last scan")

    monkeypatch.setattr(fs_rom_handler, "read_pc_component_image", changed)
    monkeypatch.setattr(fs_resource_handler, "store_pc_component_image", store)

    response = client.post(
        f"/api/roms/{rom.id}/pc-local-media-selection",
        headers=_headers(access_token),
        json={
            "component_id": component.id,
            "member_id": member.id,
            "role": RomComponentLocalMediaRole.GALLERY.value,
            "expected_version": persisted.updated_at.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    store.assert_not_awaited()


def test_dlc_metadata_selection_only_updates_the_component(
    client, access_token, rom, monkeypatch
):
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="dlc/phantom-liberty",
                kind=RomComponentKind.DLC,
                manifest_members=[],
            )
        ],
    )
    persisted = db_rom_handler.get_rom(rom.id)
    assert persisted is not None
    component = persisted.components[0]
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "collect_component_candidates",
        AsyncMock(return_value=_candidate_results()),
    )

    review = client.get(
        f"/api/roms/{rom.id}/pc-components/{component.id}/metadata-candidates",
        headers=_headers(access_token),
    )
    assert review.status_code == status.HTTP_200_OK

    response = client.post(
        f"/api/roms/{rom.id}/pc-components/{component.id}/metadata-selection",
        headers=_headers(access_token),
        json={
            "candidate_id": _candidate().id,
            "expected_version": review.json()["expected_version"],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    saved = db_rom_handler.get_rom(rom.id)
    assert saved is not None
    assert saved.igdb_id is None
    assert saved.components[0].component_metadata is not None
    assert saved.components[0].component_metadata.igdb_id == 101
    assert saved.components[0].component_metadata.name == "Selected PC Game"


def test_get_pc_metadata_candidates_is_read_only(
    client, access_token, rom, monkeypatch
):
    collect = AsyncMock(return_value=_candidate_results())
    monkeypatch.setattr(pc_metadata_match_handler, "collect_candidates", collect)

    response = client.get(
        f"/api/roms/{rom.id}/pc-metadata-candidates", headers=_headers(access_token)
    )

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()["providers"]["igdb"]["candidates"][0]["id"] == _candidate().id
    )
    persisted = db_rom_handler.get_rom(rom.id)
    assert persisted is not None
    assert persisted.igdb_id is None
    assert persisted.name == "test_rom"
    collect.assert_awaited_once()


def test_select_pc_metadata_candidate_requires_candidate_id(client, access_token, rom):
    response = client.post(
        f"/api/roms/{rom.id}/pc-metadata-selection",
        headers=_headers(access_token),
        json={"expected_version": rom.updated_at.isoformat()},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_select_pc_metadata_candidate_updates_once(
    client, access_token, rom, monkeypatch
):
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "collect_candidates",
        AsyncMock(return_value=_candidate_results()),
    )

    review = client.get(
        f"/api/roms/{rom.id}/pc-metadata-candidates", headers=_headers(access_token)
    )
    assert review.status_code == status.HTTP_200_OK

    response = client.post(
        f"/api/roms/{rom.id}/pc-metadata-selection",
        headers=_headers(access_token),
        json={
            "candidate_id": _candidate().id,
            "expected_version": review.json()["expected_version"],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    persisted = db_rom_handler.get_rom(rom.id)
    assert persisted is not None
    assert persisted.igdb_id == 101
    assert persisted.name == "Selected PC Game"
    assert persisted.summary == "Selected only after review"


def test_select_pc_metadata_candidate_rejects_stale_version(
    client, access_token, rom, monkeypatch
):
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "collect_candidates",
        AsyncMock(return_value=_candidate_results()),
    )
    stale_version = (rom.updated_at - timedelta(days=1)).isoformat()

    response = client.post(
        f"/api/roms/{rom.id}/pc-metadata-selection",
        headers=_headers(access_token),
        json={"candidate_id": _candidate().id, "expected_version": stale_version},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_hidden_rom_pc_metadata_selection_returns_404(
    client, viewer_access_token, viewer_user, rom, monkeypatch
):
    with sync_session.begin() as session:
        session.add(
            HiddenEntity(
                entity=PermEntity.ROMS, entity_id=rom.id, user_id=viewer_user.id
            )
        )
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "collect_candidates",
        AsyncMock(return_value=_candidate_results()),
    )

    response = client.get(
        f"/api/roms/{rom.id}/pc-metadata-candidates",
        headers=_headers(viewer_access_token),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_unavailable_provider_does_not_update_existing_metadata(
    client, access_token, rom, monkeypatch
):
    db_rom_handler.update_rom(rom.id, {"summary": "Existing metadata"})
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "collect_candidates",
        AsyncMock(
            return_value={
                "igdb": PcMetadataProviderResult("igdb", False, [], "unavailable")
            }
        ),
    )

    response = client.post(
        f"/api/roms/{rom.id}/pc-metadata-selection",
        headers=_headers(access_token),
        json={
            "candidate_id": "missing",
            "expected_version": rom.updated_at.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    persisted = db_rom_handler.get_rom(rom.id)
    assert persisted is not None
    assert persisted.summary == "Existing metadata"
