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
