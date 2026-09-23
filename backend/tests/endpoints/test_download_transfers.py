from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from tests.conftest import session

from models.download_manifest import (
    DownloadManifest,
    DownloadManifestComponent,
    DownloadManifestMember,
)
from models.rom import RomComponent, RomComponentKind, RomComponentManifestMember


@pytest.fixture
def manifest(rom, admin_user):
    component = RomComponent(
        rom_id=rom.id, relative_path="base", kind=RomComponentKind.BASE
    )
    source = RomComponentManifestMember(
        component=component,
        relative_path="base/game.iso",
        size_bytes=42,
        sha256="a" * 64,
    )
    with session.begin() as db:
        db.add(component)
        db.flush()
        saved = DownloadManifest(
            user_id=admin_user.id,
            rom_id=rom.id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        selected = DownloadManifestComponent(manifest=saved, component=component)
        DownloadManifestMember(
            component=selected,
            manifest_member=source,
            destination="game.iso",
            size_bytes=42,
            sha256="a" * 64,
            snapshot='"snapshot"',
            mtime_ns=1,
        )
        db.add(saved)
        db.flush()
        return saved


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_transfer_history_requires_authentication(client, manifest):
    response = client.get(f"/api/download-transfer-sessions/{manifest.id}")
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
    )


def test_transfer_history_masks_foreign_owner(
    client, access_token, viewer_access_token, manifest
):
    created = client.post(
        "/api/download-transfer-sessions",
        headers=_headers(access_token),
        json={"manifest_id": manifest.id, "mode": "standard"},
    )
    assert created.status_code == status.HTTP_201_CREATED

    response = client.get(
        f"/api/download-transfer-sessions/{created.json()['id']}",
        headers=_headers(viewer_access_token),
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Download transfer session not found"}


def test_transfer_payload_rejects_unknown_fields(client, access_token, manifest):
    response = client.post(
        "/api/download-transfer-sessions",
        headers=_headers(access_token),
        json={
            "manifest_id": manifest.id,
            "mode": "standard",
            "path": "/tmp/x",
            "zip": True,
            "desktop": True,
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_standard_transfer_response_does_not_claim_local_storage(
    client, access_token, manifest
):
    created = client.post(
        "/api/download-transfer-sessions",
        headers=_headers(access_token),
        json={"manifest_id": manifest.id, "mode": "standard"},
    )
    assert created.status_code == status.HTTP_201_CREATED
    body = created.json()
    assert body["mode"] == "standard"
    assert all(item["status"] == "queued" for item in body["items"])
    assert all(
        forbidden not in created.text
        for forbidden in ("source_path", "fs_path", "file://", "token", "credential")
    )


def test_cancelling_an_active_transfer_returns_the_cancelled_session(
    client, access_token, manifest
):
    headers = _headers(access_token)
    created = client.post(
        "/api/download-transfer-sessions",
        headers=headers,
        json={"manifest_id": manifest.id, "mode": "standard"},
    )
    assert created.status_code == status.HTTP_201_CREATED

    cancelled = client.post(
        f"/api/download-transfer-sessions/{created.json()['id']}/cancel",
        headers=headers,
    )

    assert cancelled.status_code == status.HTTP_200_OK
    assert cancelled.json()["status"] == "cancelled"


def test_transfer_history_supports_owner_scoped_rom_and_manifest_filters(
    client, access_token, manifest, rom
):
    created = client.post(
        "/api/download-transfer-sessions",
        headers=_headers(access_token),
        json={"manifest_id": manifest.id, "mode": "standard"},
    )
    assert created.status_code == status.HTTP_201_CREATED

    headers = _headers(access_token)
    unfiltered = client.get("/api/download-transfer-sessions", headers=headers)
    by_rom = client.get(
        f"/api/download-transfer-sessions?rom_id={rom.id}", headers=headers
    )
    by_manifest = client.get(
        f"/api/download-transfer-sessions?manifest_id={manifest.id}", headers=headers
    )
    unmatched = client.get(
        "/api/download-transfer-sessions?rom_id=999999", headers=headers
    )

    assert unfiltered.status_code == status.HTTP_200_OK
    assert by_rom.status_code == status.HTTP_200_OK
    assert by_manifest.status_code == status.HTTP_200_OK
    assert unmatched.status_code == status.HTTP_200_OK
    assert len(unfiltered.json()) == len(by_rom.json()) == len(by_manifest.json()) == 1
    assert unmatched.json() == []


@pytest.mark.parametrize(
    "query",
    ["rom_id=0", "manifest_id=not-a-uuid"],
)
def test_transfer_history_filters_are_validated(client, access_token, query):
    response = client.get(
        f"/api/download-transfer-sessions?{query}",
        headers=_headers(access_token),
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
