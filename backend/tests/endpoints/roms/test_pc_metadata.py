from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import status

from endpoints.roms.pc_metadata import _candidate_media_id, pc_metadata_match_handler
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
    RomComponentMetadata,
)


def _candidate() -> PcMetadataCandidate:
    return PcMetadataCandidate(
        id="candidate-igdb-101",
        provider="igdb",
        title="Selected PC Game",
        provider_ids={"igdb_id": 101},
        description_available=True,
        media=[
            {"kind": "cover", "url": "https://images.igdb.com/cover.jpg"},
            {
                "kind": "screenshot",
                "url": "https://images.igdb.com/screenshot.jpg",
            },
        ],
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


@pytest.mark.parametrize(
    "kind",
    [
        RomComponentKind.BASE,
        RomComponentKind.UPDATE,
        RomComponentKind.DLC,
        RomComponentKind.HOTFIX,
        RomComponentKind.LANGUAGE_PACK,
        RomComponentKind.EXTRA,
    ],
)
def test_classified_pc_component_metadata_candidates_use_explicit_query(
    client, access_token, rom, monkeypatch, kind
):
    db_rom_handler.sync_rom_components(
        rom.id, [RomComponent(relative_path=kind.value, kind=kind, manifest_members=[])]
    )
    component = db_rom_handler.get_rom(rom.id).components[0]
    collect = AsyncMock(return_value=_candidate_results())
    monkeypatch.setattr(
        pc_metadata_match_handler, "collect_component_candidates", collect
    )

    response = client.get(
        f"/api/roms/{rom.id}/pc-components/{component.id}/metadata-candidates",
        headers=_headers(access_token),
        params={"query": "Selected PC Game"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert collect.await_args is not None
    assert collect.await_args.args[2] == "Selected PC Game"


def test_unresolved_pc_component_metadata_routes_return_404(client, access_token, rom):
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="unknown",
                kind=RomComponentKind.UNRESOLVED,
                manifest_members=[],
            )
        ],
    )
    component = db_rom_handler.get_rom(rom.id).components[0]

    for route, method, body in (
        ("metadata-candidates", client.get, {"params": {"query": "Anything"}}),
        (
            "metadata-selection",
            client.post,
            {
                "json": {
                    "candidate_id": _candidate().id,
                    "query": "Anything",
                    "expected_version": component.updated_at.isoformat(),
                }
            },
        ),
    ):
        response = method(
            f"/api/roms/{rom.id}/pc-components/{component.id}/{route}",
            headers=_headers(access_token),
            **body,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_pc_component_metadata_selection_recomputes_submitted_query(
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
    component = db_rom_handler.get_rom(rom.id).components[0]
    collect = AsyncMock(return_value=_candidate_results())
    monkeypatch.setattr(
        pc_metadata_match_handler, "collect_component_candidates", collect
    )

    response = client.post(
        f"/api/roms/{rom.id}/pc-components/{component.id}/metadata-selection",
        headers=_headers(access_token),
        json={
            "candidate_id": _candidate().id,
            "query": "Phantom Liberty",
            "expected_version": component.updated_at.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert collect.await_args is not None
    assert collect.await_args.args[2] == "Phantom Liberty"


def test_dlc_metadata_selection_imports_only_selected_candidate_media(
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
    component = db_rom_handler.get_rom(rom.id).components[0]
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "collect_component_candidates",
        AsyncMock(return_value=_candidate_results()),
    )
    store = AsyncMock(
        return_value=("roms/1/1/pc-media/provider-cover.webp", "image/webp")
    )
    monkeypatch.setattr(fs_resource_handler, "store_pc_component_provider_image", store)

    response = client.post(
        f"/api/roms/{rom.id}/pc-components/{component.id}/metadata-selection",
        headers=_headers(access_token),
        json={
            "candidate_id": _candidate().id,
            "query": "Phantom Liberty",
            "selected_media_ids": [
                _candidate_media_id(_candidate(), _candidate().media[0])
            ],
            "expected_version": component.updated_at.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    store.assert_awaited_once()
    saved = db_rom_handler.get_rom(rom.id)
    assert saved.components[0].owned_media[0].provider == "igdb"


def test_dlc_metadata_selection_accepts_response_media_ids(
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
    component = db_rom_handler.get_rom(rom.id).components[0]
    candidate = _candidate()
    candidate.media[1]["id"] = "igdb-screenshot-101"
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "collect_component_candidates",
        AsyncMock(
            return_value={"igdb": PcMetadataProviderResult("igdb", True, [candidate])}
        ),
    )
    store = AsyncMock(
        return_value=("roms/1/1/pc-media/provider-image.webp", "image/webp")
    )
    monkeypatch.setattr(fs_resource_handler, "store_pc_component_provider_image", store)

    review = client.get(
        f"/api/roms/{rom.id}/pc-components/{component.id}/metadata-candidates",
        headers=_headers(access_token),
        params={"query": "Phantom Liberty"},
    )
    response = client.post(
        f"/api/roms/{rom.id}/pc-components/{component.id}/metadata-selection",
        headers=_headers(access_token),
        json={
            "candidate_id": candidate.id,
            "query": "Phantom Liberty",
            "selected_media_ids": [
                media["id"]
                for media in review.json()["providers"]["igdb"]["candidates"][0][
                    "media"
                ]
            ],
            "expected_version": review.json()["expected_version"],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert store.await_count == 2


def test_pc_parent_metadata_selection_imports_confirmed_cover_and_screenshots(
    client, access_token, rom, monkeypatch
):
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "collect_candidates",
        AsyncMock(return_value=_candidate_results()),
    )
    cover = AsyncMock(return_value=("roms/1/cover/s.jpg", "roms/1/cover/l.jpg"))
    screenshots = AsyncMock(return_value=["roms/1/screenshots/0.jpg"])
    monkeypatch.setattr(fs_resource_handler, "get_cover", cover)
    monkeypatch.setattr(fs_resource_handler, "get_rom_screenshots", screenshots)

    review = client.get(
        f"/api/roms/{rom.id}/pc-metadata-candidates", headers=_headers(access_token)
    )
    assert review.status_code == status.HTTP_200_OK

    response = client.post(
        f"/api/roms/{rom.id}/pc-metadata-selection",
        headers=_headers(access_token),
        json={
            "candidate_id": _candidate().id,
            "query": "Selected PC Game",
            "selected_media_ids": [
                _candidate_media_id(_candidate(), _candidate().media[0]),
                _candidate_media_id(_candidate(), _candidate().media[1]),
            ],
            "expected_version": review.json()["expected_version"],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    cover.assert_awaited_once()
    cover_call = cover.await_args
    assert cover_call is not None
    assert cover_call.kwargs == {
        "overwrite": True,
        "url_cover": _candidate().media[0]["url"],
    }
    screenshots.assert_awaited_once()
    screenshot_call = screenshots.await_args
    assert screenshot_call is not None
    assert screenshot_call.kwargs["overwrite"] is True
    assert screenshot_call.kwargs["url_screenshots"] == [_candidate().media[1]["url"]]
    saved = db_rom_handler.get_rom(rom.id)
    assert saved.path_cover_s == "roms/1/cover/s.jpg"
    assert saved.path_cover_l == "roms/1/cover/l.jpg"
    assert saved.path_screenshots == ["roms/1/screenshots/0.jpg"]


def test_non_dlc_component_rejects_provider_media_selection(
    client, access_token, rom, monkeypatch
):
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="base",
                kind=RomComponentKind.BASE,
                manifest_members=[],
            )
        ],
    )
    component = db_rom_handler.get_rom(rom.id).components[0]
    monkeypatch.setattr(
        pc_metadata_match_handler,
        "collect_component_candidates",
        AsyncMock(return_value=_candidate_results()),
    )

    response = client.post(
        f"/api/roms/{rom.id}/pc-components/{component.id}/metadata-selection",
        headers=_headers(access_token),
        json={
            "candidate_id": _candidate().id,
            "query": "Selected PC Game",
            "selected_media_ids": ["unknown"],
            "expected_version": component.updated_at.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


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


def test_get_roms_serializes_component_metadata_with_missing_list_fields(
    client, access_token, rom
):
    """A partially enriched component must not block its parent in the gallery."""
    components = db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="dlc/incomplete",
                kind=RomComponentKind.DLC,
                manifest_members=[],
            )
        ],
    )
    with sync_session.begin() as session:
        component = session.get(RomComponent, components[0].id)
        assert component is not None
        component.component_metadata = RomComponentMetadata(
            name="Incomplete DLC",
            publishers=None,
            themes=None,
        )

    response = client.get(
        "/api/roms",
        headers=_headers(access_token),
        params={"platform_id": rom.platform_id},
    )

    assert response.status_code == status.HTTP_200_OK
    metadata = response.json()["items"][0]["components"][0]["component_metadata"]
    assert metadata["publishers"] == []
    assert metadata["themes"] == []


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


@pytest.mark.parametrize(
    "role",
    [
        RomComponentLocalMediaRole.BACKGROUND,
        RomComponentLocalMediaRole.GALLERY,
    ],
)
def test_pc_local_media_selection_replaces_an_existing_role_without_duplicates(
    rom, role
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
    first = db_rom_handler.apply_pc_local_media(
        rom.id,
        persisted.updated_at,
        component.id,
        member.id,
        role,
        "roms/1/1/pc-media/background.webp",
        "webp",
        member.sha256,
    )
    assert first is not None
    updated = db_rom_handler.get_rom(rom.id)
    assert updated is not None

    second = db_rom_handler.apply_pc_local_media(
        rom.id,
        updated.updated_at,
        component.id,
        member.id,
        role,
        "roms/1/1/pc-media/background.webp",
        "webp",
        member.sha256,
    )

    assert second is not None
    assert second.replaced_owned_paths == []
    saved = db_rom_handler.get_rom(rom.id)
    assert saved is not None
    assert len(saved.components[0].local_media) == 1


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
        params={"query": "Phantom Liberty"},
    )
    assert review.status_code == status.HTTP_200_OK

    response = client.post(
        f"/api/roms/{rom.id}/pc-components/{component.id}/metadata-selection",
        headers=_headers(access_token),
        json={
            "candidate_id": _candidate().id,
            "query": "Phantom Liberty",
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
            "query": "Selected PC Game",
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
        json={
            "candidate_id": _candidate().id,
            "query": "Selected PC Game",
            "expected_version": stale_version,
        },
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
            "query": "Selected PC Game",
            "expected_version": rom.updated_at.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    persisted = db_rom_handler.get_rom(rom.id)
    assert persisted is not None
    assert persisted.summary == "Existing metadata"
