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
                "candidate_fingerprint": "steam:1091500:stale_target",
                "candidate_title": "Cyberpunk 2077",
                "candidate_cover_url": "https://cdn.example/cover.jpg",
                "provider": "steam",
                "reason": "stale_target",
                "state": "pending",
                "expected_queue_version": item.updated_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "expected_target_version": item.target_updated_at.isoformat().replace(
                    "+00:00", "Z"
                ),
            }
        ],
        "total": 1,
        "limit": 1,
        "offset": 0,
    }
    list_pending.assert_awaited_once_with(limit=1, offset=0)


def test_queue_list_exposes_the_actual_eligible_component_kind(
    client, access_token, rom, monkeypatch
):
    item = _item(rom.id)
    item.component_id = 23
    item.target_kind = PcAutomationTargetKind.COMPONENT
    monkeypatch.setattr(
        pc_automation_endpoint.pc_automation_handler,
        "list_pending",
        AsyncMock(return_value=([item], 1)),
    )
    monkeypatch.setattr(
        pc_automation_endpoint.db_rom_handler,
        "get_pc_component_by_id",
        lambda _rom_id, _component_id: SimpleNamespace(kind=RomComponentKind.DLC),
    )

    response = client.get(
        "/api/roms/pc-automation/review-queue", headers=_headers(access_token)
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"][0]["component_kind"] == "dlc"


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
