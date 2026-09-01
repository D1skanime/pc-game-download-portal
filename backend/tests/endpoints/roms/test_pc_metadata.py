from datetime import timedelta
from unittest.mock import AsyncMock

from fastapi import status

from endpoints.roms.pc_metadata import pc_metadata_match_handler
from handler.database import db_rom_handler
from handler.database.base_handler import sync_session
from handler.metadata.pc_match_handler import (
    PcMetadataCandidate,
    PcMetadataProviderResult,
)
from models.permission import HiddenEntity, PermEntity


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

    response = client.post(
        f"/api/roms/{rom.id}/pc-metadata-selection",
        headers=_headers(access_token),
        json={
            "candidate_id": _candidate().id,
            "expected_version": rom.updated_at.isoformat(),
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
