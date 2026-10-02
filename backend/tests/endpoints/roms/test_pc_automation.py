from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import status

import endpoints.roms.pc_automation as pc_automation_endpoint
from handler.database.pc_automation_handler import PcAutomationQueueResult
from models.pc_automation import (
    PcAutomationOutcome,
    PcAutomationQueueState,
    PcAutomationTargetKind,
)
from models.rom import RomComponentKind


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _item(rom_id: int, *, queue_id: int = 7):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=queue_id,
        rom_id=rom_id,
        component_id=None,
        target_kind=PcAutomationTargetKind.PARENT,
        normalized_query="Cyberpunk 2077",
        candidate_fingerprint="steam:1091500:stale_target",
        candidate_title="Cyberpunk 2077",
        candidate_cover_url="https://cdn.example/cover.jpg",
        provider="steam",
        reason="stale_target",
        state=PcAutomationQueueState.PENDING,
        target_updated_at=now,
        updated_at=now,
    )


def _action_body(item) -> dict[str, str]:
    return {
        "expected_queue_version": item.updated_at.isoformat(),
        "expected_target_version": item.target_updated_at.isoformat(),
        "candidate_fingerprint": item.candidate_fingerprint,
    }


def test_queue_list_returns_bounded_evidence_and_count(
    client, access_token, rom, monkeypatch
):
    item = _item(rom.id)
    list_pending = AsyncMock(return_value=([item], 1))
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler, "list_pending", list_pending
    )

    response = client.get(
        "/api/roms/pc-automation/review-queue?limit=1&offset=0",
        headers=_headers(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "items": [
            {
                "id": 7,
                "rom_id": rom.id,
                "component_id": None,
                "component_kind": None,
                "target_kind": "parent",
                "normalized_query": "Cyberpunk 2077",
                "target_title": "test_rom",
                "candidate_fingerprint": "steam:1091500:stale_target",
                "candidate_title": "Cyberpunk 2077",
                "candidate_cover_url": "https://cdn.example/cover.jpg",
                "provider": "steam",
                "reason": "stale_target",
                "state": "pending",
                "expected_queue_version": item.updated_at.isoformat(),
                "expected_target_version": item.target_updated_at.isoformat(),
            }
        ],
        "total": 1,
        "limit": 1,
        "offset": 0,
    }
    list_pending.assert_awaited_once_with(limit=1, offset=0)


def test_queue_list_exposes_the_actual_eligible_component_kind(
    mocker,
):
    item = _item(7)
    item.component_id = 23
    item.target_kind = PcAutomationTargetKind.COMPONENT
    component = SimpleNamespace(
        id=23,
        kind=RomComponentKind.DLC,
        relative_path="dlc/Phantom Liberty",
        component_metadata=None,
    )
    mocker.patch.object(
        pc_automation_endpoint.db_rom_handler,
        "get_rom",
        return_value=SimpleNamespace(name="Cyberpunk 2077", components=[component]),
    )

    assert pc_automation_endpoint._schema(item).component_kind == RomComponentKind.DLC


def test_queue_schema_prefers_component_metadata_name_then_relative_path(mocker):
    item = _item(7)
    item.component_id = 23
    item.target_kind = PcAutomationTargetKind.COMPONENT
    component = SimpleNamespace(
        id=23,
        kind=RomComponentKind.DLC,
        relative_path="dlc/Phantom Liberty",
        component_metadata=SimpleNamespace(name="Cyberpunk 2077: Phantom Liberty"),
    )
    mocker.patch.object(
        pc_automation_endpoint.db_rom_handler,
        "get_rom",
        return_value=SimpleNamespace(name="Cyberpunk 2077", components=[component]),
    )
    schema = pc_automation_endpoint._schema(item)

    assert schema.target_title == "Cyberpunk 2077: Phantom Liberty"
    component.component_metadata.name = None
    assert pc_automation_endpoint._schema(item).target_title == "dlc/Phantom Liberty"


def test_queue_list_exposes_the_normalized_query_for_unmatched_titles(
    client, access_token, rom, monkeypatch
):
    item = _item(rom.id)
    item.normalized_query = "Civilization VI"
    item.candidate_title = None
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler,
        "list_pending",
        AsyncMock(return_value=([item], 1)),
    )

    response = client.get(
        "/api/roms/pc-automation/review-queue", headers=_headers(access_token)
    )

    assert response.json()["items"][0]["normalized_query"] == "Civilization VI"


def test_queue_actions_require_authentication(client):
    response = client.get("/api/roms/pc-automation/review-queue")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_queue_rejects_malformed_pagination_and_client_candidate_data(
    client, access_token, rom
):
    assert (
        client.get(
            "/api/roms/pc-automation/review-queue?limit=101",
            headers=_headers(access_token),
        ).status_code
        == status.HTTP_422_UNPROCESSABLE_ENTITY
    )

    item = _item(rom.id)
    body = {**_action_body(item), "candidate_title": "forged"}
    response = client.post(
        f"/api/roms/pc-automation/review-queue/{item.id}/accept",
        headers=_headers(access_token),
        json=body,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_accept_delegates_only_server_revalidated_identifiers(
    client, access_token, rom, monkeypatch
):
    item = _item(rom.id)
    apply = AsyncMock(
        return_value=PcAutomationQueueResult(PcAutomationOutcome.CLAIMED, item)
    )
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler,
        "get_review_item",
        lambda _id: item,
    )
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler, "apply_review_item", apply
    )

    response = client.post(
        f"/api/roms/pc-automation/review-queue/{item.id}/accept",
        headers=_headers(access_token),
        json=_action_body(item),
    )

    assert response.status_code == status.HTTP_200_OK
    apply.assert_awaited_once_with(
        queue_id=item.id,
        expected_queue_updated_at=item.updated_at,
        expected_target_updated_at=item.target_updated_at,
        candidate_fingerprint=item.candidate_fingerprint,
    )


def test_individual_actions_return_conflict_for_stale_versions(
    client, access_token, rom, monkeypatch
):
    item = _item(rom.id)
    stale = AsyncMock(
        return_value=PcAutomationQueueResult(PcAutomationOutcome.STALE_TARGET, None)
    )
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler,
        "get_review_item",
        lambda _id: item,
    )
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler, "apply_review_item", stale
    )

    response = client.post(
        f"/api/roms/pc-automation/review-queue/{item.id}/accept",
        headers=_headers(access_token),
        json=_action_body(item),
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_skip_accepts_utc_versions_returned_for_naive_mariadb_timestamps(
    client, access_token, rom, monkeypatch
):
    item = _item(rom.id)
    item.updated_at = datetime(2026, 10, 2, 17, 12, 31)
    item.target_updated_at = datetime(2026, 10, 2, 17, 12, 31)
    skipped = PcAutomationQueueResult(PcAutomationOutcome.SKIPPED, item)
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler,
        "get_review_item",
        lambda _id: item,
    )
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler.queue_handler,
        "mark_skipped",
        lambda queue_id, expected_queue_version: (
            skipped
            if queue_id == item.id
            and expected_queue_version == datetime(2026, 10, 2, 17, 12, 31)
            else PcAutomationQueueResult(PcAutomationOutcome.CONFLICT, None)
        ),
    )

    response = client.post(
        f"/api/roms/pc-automation/review-queue/{item.id}/skip",
        headers=_headers(access_token),
        json={
            "expected_queue_version": "2026-10-02T17:12:31Z",
            "expected_target_version": "2026-10-02T17:12:31Z",
            "candidate_fingerprint": item.candidate_fingerprint,
        },
    )

    assert response.status_code == status.HTTP_200_OK


def test_batch_delegates_one_fingerprint_and_kind_for_all_items(
    client, access_token, rom, monkeypatch
):
    item = _item(rom.id)
    apply = AsyncMock(
        return_value=[PcAutomationQueueResult(PcAutomationOutcome.CLAIMED, item)]
    )
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler,
        "get_review_item",
        lambda _id: item,
    )
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler, "apply_review_batch", apply
    )
    body = {
        "target_kind": "parent",
        "candidate_fingerprint": item.candidate_fingerprint,
        "items": [
            {
                "queue_id": item.id,
                "expected_queue_version": item.updated_at.isoformat(),
                "expected_target_version": item.target_updated_at.isoformat(),
            }
        ],
    }

    response = client.post(
        "/api/roms/pc-automation/review-queue/batch-accept",
        headers=_headers(access_token),
        json=body,
    )

    assert response.status_code == status.HTTP_200_OK
    apply.assert_awaited_once()


def test_batch_rejects_mixed_or_unsafe_client_data(client, access_token):
    body = {
        "target_kind": "parent",
        "candidate_fingerprint": "steam:1091500:stale_target",
        "items": [
            {
                "queue_id": 7,
                "expected_queue_version": "2026-01-01T00:00:00Z",
                "expected_target_version": "2026-01-01T00:00:00Z",
            },
            {
                "queue_id": 7,
                "expected_queue_version": "2026-01-01T00:00:00Z",
                "expected_target_version": "2026-01-01T00:00:00Z",
            },
        ],
    }
    response = client.post(
        "/api/roms/pc-automation/review-queue/batch-accept",
        headers=_headers(access_token),
        json=body,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
