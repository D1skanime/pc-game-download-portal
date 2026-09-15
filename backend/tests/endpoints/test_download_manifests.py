from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from sqlalchemy import select
from tests.conftest import session

from handler.database import db_download_manifest_handler, db_rom_handler
from handler.filesystem.roms_handler import DownloadManifestMemberEvidence
from models.download_manifest import DownloadManifest, DownloadManifestStatus
from models.permission import HiddenEntity, PermEntity
from models.rom import RomComponent, RomComponentKind, RomComponentManifestMember


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


class _ManifestFilesystem:
    def capture_download_manifest_member(self, rom, member):
        return DownloadManifestMemberEvidence(
            destination=f"Game/{member.relative_path}",
            size_bytes=member.size_bytes,
            sha256=member.sha256,
            snapshot=f'"snapshot-{member.id}"',
            mtime_ns=member.id,
            device=None,
            inode=None,
        )

    def light_revalidate_download_manifest_member(self, _rom, _member, _evidence):
        return "UNCHANGED_BY_LIGHT_CHECK"


@pytest.fixture(autouse=True)
def _clear_manifests():
    yield
    with session.begin() as db:
        db.query(DownloadManifest).delete()


@pytest.fixture
def manifest_components(rom):
    components = []
    for index, kind in enumerate(
        (
            RomComponentKind.BASE,
            RomComponentKind.UPDATE,
            RomComponentKind.DLC,
            RomComponentKind.EXTRA,
        ),
        start=1,
    ):
        component = RomComponent(rom_id=rom.id, relative_path=kind.value, kind=kind)
        component.manifest_members = [
            RomComponentManifestMember(
                relative_path=f"{kind.value}/content-{index}.bin",
                size_bytes=5 * 1024**3 + index,
                sha256=(f"{index:x}" * 64)[:64],
            )
        ]
        components.append(component)
    with session.begin() as db:
        db.add_all(components)
    return db_rom_handler.get_rom(rom.id).components


@pytest.fixture(autouse=True)
def _isolated_manifest_filesystem(monkeypatch):
    monkeypatch.setattr(
        db_download_manifest_handler, "_filesystem_handler", _ManifestFilesystem()
    )


def test_create_and_retrieve_a_path_free_whole_game_manifest(
    client, access_token, rom, manifest_components
):
    created = client.post(
        f"/api/roms/{rom.id}/download-manifests",
        headers=_headers(access_token),
        json={"component_ids": None},
    )

    assert created.status_code == status.HTTP_201_CREATED
    body = created.json()
    assert body["schema_version"] == 1
    assert [item["component_id"] for item in body["components"]] == sorted(
        component.id for component in manifest_components
    )
    assert [member["size"] for member in body["members"]] == [
        5 * 1024**3 + index for index in range(1, 5)
    ]
    assert all(member["snapshot"].startswith('"') for member in body["members"])
    assert all(
        member["download"]
        == f"/api/download-manifests/{body['id']}/files/{member['file_id']}"
        for member in body["members"]
    )
    assert all(
        forbidden not in created.text
        for forbidden in ("fs_path", "fs_name", "container_path", "/tmp", "Range")
    )

    fetched = client.get(
        f"/api/download-manifests/{body['id']}", headers=_headers(access_token)
    )
    assert fetched.status_code == status.HTTP_200_OK
    assert fetched.json() == body


def test_create_exact_components_rejects_invalid_or_foreign_selection(
    client, access_token, rom, manifest_components
):
    selected = manifest_components[1:3]
    created = client.post(
        f"/api/roms/{rom.id}/download-manifests",
        headers=_headers(access_token),
        json={"component_ids": [component.id for component in selected]},
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert [item["component_id"] for item in created.json()["components"]] == [
        component.id for component in selected
    ]

    for payload in (
        {"component_ids": []},
        {"component_ids": [selected[0].id, selected[0].id]},
        {"component_ids": [0]},
        {"component_ids": [999999]},
        {"component_ids": None, "source_path": "/nas/private"},
    ):
        response = client.post(
            f"/api/roms/{rom.id}/download-manifests",
            headers=_headers(access_token),
            json=payload,
        )
        assert response.status_code in {
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        }
        assert "/nas/private" not in response.text


def test_manifest_owner_and_hidden_rom_are_masked_on_get(
    client,
    access_token,
    admin_user,
    viewer_access_token,
    viewer_user,
    rom,
    manifest_components,
):
    db_rom_handler.add_rom_user(rom_id=rom.id, user_id=viewer_user.id)
    created = client.post(
        f"/api/roms/{rom.id}/download-manifests",
        headers=_headers(viewer_access_token),
        json={"component_ids": [manifest_components[0].id]},
    ).json()
    manifest_id = created["id"]

    foreign = client.get(
        f"/api/download-manifests/{manifest_id}", headers=_headers(access_token)
    )
    assert foreign.status_code == status.HTTP_404_NOT_FOUND
    assert manifest_id not in foreign.text

    with session.begin() as db:
        db.add(
            HiddenEntity(
                entity=PermEntity.ROMS, entity_id=rom.id, user_id=viewer_user.id
            )
        )
    hidden = client.get(
        f"/api/download-manifests/{manifest_id}", headers=_headers(viewer_access_token)
    )
    assert hidden.status_code == status.HTTP_404_NOT_FOUND
    assert hidden.json() == {"detail": "Download manifest not found"}
    assert all(
        value not in hidden.text
        for value in (manifest_id, str(manifest_components[0].id), "snapshot", "/tmp")
    )


@pytest.mark.parametrize(
    ("manifest_status", "expected_status", "expected_code"),
    [
        (DownloadManifestStatus.EXPIRED, status.HTTP_410_GONE, "manifest_expired"),
        (DownloadManifestStatus.REVOKED, status.HTTP_410_GONE, "manifest_revoked"),
        (
            DownloadManifestStatus.SOURCE_CHANGED,
            status.HTTP_409_CONFLICT,
            "manifest_source_changed",
        ),
    ],
)
def test_closed_manifest_states_are_bounded(
    client,
    access_token,
    admin_user,
    rom,
    manifest_components,
    manifest_status,
    expected_status,
    expected_code,
):
    manifest = db_download_manifest_handler.create_manifest(
        admin_user.id, rom.id, [manifest_components[0].id]
    )
    with session.begin() as db:
        persisted = db.scalar(
            select(DownloadManifest).where(DownloadManifest.id == manifest.id)
        )
        persisted.status = manifest_status
        if manifest_status is DownloadManifestStatus.EXPIRED:
            persisted.expires_at = datetime.now(UTC) - timedelta(seconds=1)

    response = client.get(
        f"/api/download-manifests/{manifest.id}", headers=_headers(access_token)
    )
    assert response.status_code == expected_status
    assert response.json() == {"detail": {"code": expected_code}}
    assert manifest.id not in response.text
