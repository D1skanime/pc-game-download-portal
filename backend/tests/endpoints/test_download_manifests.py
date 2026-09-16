from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from fastapi import status
from sqlalchemy import select
from tests.conftest import session

from endpoints import download_manifests as download_manifests_endpoint
from handler.database import db_download_manifest_handler, db_rom_handler
from handler.filesystem.roms_handler import (
    DownloadManifestMemberEvidence,
    DownloadManifestTransferLease,
    DownloadManifestTransferResult,
    DownloadManifestTransferState,
)
from models.download_manifest import DownloadManifest, DownloadManifestStatus
from models.permission import HiddenEntity, PermEntity
from models.rom import RomComponent, RomComponentKind, RomComponentManifestMember


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


class _TransferLease:
    def __init__(self, content: bytes, snapshot: str):
        self.size_bytes = len(content)
        self.snapshot = snapshot
        self._content = content
        self.closed = False
        self.iterated = False

    def close(self) -> None:
        self.closed = True

    def iter_chunks(self, start: int, length: int):
        self.iterated = True
        try:
            yield self._content[start : start + length]
        finally:
            self.close()


def _manifest_member_url(manifest: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    member = manifest["members"][0]
    assert isinstance(member, dict)
    download = member["download"]
    assert isinstance(download, str)
    return download, member


def _install_ready_transfer(monkeypatch, content: bytes):
    leases: list[_TransferLease] = []

    async def open_verified(_rom, persisted_member):
        lease = _TransferLease(content, persisted_member.snapshot)
        leases.append(lease)
        return DownloadManifestTransferResult(
            state=DownloadManifestTransferState.READY,
            lease=cast(DownloadManifestTransferLease, lease),
        )

    monkeypatch.setattr(
        download_manifests_endpoint.fs_rom_handler,
        "open_verified_download_manifest_member",
        open_verified,
    )
    return leases


def _set_component_member_size(component_id: int, size_bytes: int) -> None:
    with session.begin() as db:
        member = db.scalar(
            select(RomComponentManifestMember).where(
                RomComponentManifestMember.component_id == component_id
            )
        )
        assert member is not None
        member.size_bytes = size_bytes


class _ManifestFilesystem:
    def capture_download_manifest_member(self, rom, member, public_id):
        return DownloadManifestMemberEvidence(
            destination=f"Game/{member.relative_path}",
            size_bytes=member.size_bytes,
            sha256=member.sha256,
            snapshot=f'"snapshot-{public_id}"',
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
        len(member["file_id"]) == 36 and member["file_id"] != str(component.id)
        for component in manifest_components
        for member in body["members"]
    )
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

    invalid_payloads: tuple[dict[str, object], ...] = (
        {"component_ids": []},
        {"component_ids": [selected[0].id, selected[0].id]},
        {"component_ids": [0]},
        {"component_ids": [999999]},
        {"component_ids": None, "source_path": "/nas/private"},
    )
    for payload in invalid_payloads:
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


def test_manifest_member_delivers_original_bytes_with_exact_full_and_range_headers(
    client, access_token, rom, manifest_components, monkeypatch
):
    content = b"original-member-bytes"
    _set_component_member_size(manifest_components[0].id, len(content))
    created = client.post(
        f"/api/roms/{rom.id}/download-manifests",
        headers=_headers(access_token),
        json={"component_ids": [manifest_components[0].id]},
    ).json()
    url, member = _manifest_member_url(created)
    leases = _install_ready_transfer(monkeypatch, content)

    full = client.get(url, headers=_headers(access_token))
    assert full.status_code == status.HTTP_200_OK
    assert full.content == content
    assert full.headers["accept-ranges"] == "bytes"
    assert full.headers["content-length"] == str(len(content))
    assert full.headers["content-disposition"].startswith("attachment;")
    assert "zip" not in full.headers["content-type"]
    assert leases[0].closed

    partial = client.get(
        url,
        headers={
            **_headers(access_token),
            "Range": "bytes=3-8",
            "If-Match": member["snapshot"],
        },
    )
    assert partial.status_code == status.HTTP_206_PARTIAL_CONTENT
    assert partial.content == content[3:9]
    assert partial.headers["content-length"] == "6"
    assert partial.headers["content-range"] == f"bytes 3-8/{len(content)}"
    assert leases[1].closed


@pytest.mark.parametrize(
    "range_header",
    [
        "bytes=",
        "bytes=0-1,2-3",
        "items=0-1",
        "bytes=-0",
        "bytes=999-",
        "bytes=8-3",
        "bytes=18446744073709551616-",
    ],
)
def test_manifest_member_rejects_invalid_ranges_before_opening_transfer(
    client, access_token, rom, manifest_components, monkeypatch, range_header
):
    created = client.post(
        f"/api/roms/{rom.id}/download-manifests",
        headers=_headers(access_token),
        json={"component_ids": [manifest_components[0].id]},
    ).json()
    url, member = _manifest_member_url(created)
    if range_header == "bytes=999-":
        range_header = f"bytes={member['size']}-"
    opened = False

    async def open_verified(_rom, _persisted_member):
        nonlocal opened
        opened = True
        raise AssertionError("invalid Range must not open a transfer")

    monkeypatch.setattr(
        download_manifests_endpoint.fs_rom_handler,
        "open_verified_download_manifest_member",
        open_verified,
    )
    response = client.get(
        url,
        headers={
            **_headers(access_token),
            "Range": range_header,
            "If-Match": member["snapshot"],
        },
    )

    assert response.status_code == status.HTTP_416_RANGE_NOT_SATISFIABLE
    assert response.headers["content-range"] == f"bytes */{member['size']}"
    assert not opened


@pytest.mark.parametrize(
    "if_match",
    [None, 'W/"strong"', "*", '"first", "second"', '"stale"'],
)
def test_manifest_member_rejects_non_exact_resume_validators_before_opening_transfer(
    client, access_token, rom, manifest_components, monkeypatch, if_match
):
    created = client.post(
        f"/api/roms/{rom.id}/download-manifests",
        headers=_headers(access_token),
        json={"component_ids": [manifest_components[0].id]},
    ).json()
    url, _member = _manifest_member_url(created)
    opened = False

    async def open_verified(_rom, _persisted_member):
        nonlocal opened
        opened = True
        raise AssertionError("invalid If-Match must not open a transfer")

    monkeypatch.setattr(
        download_manifests_endpoint.fs_rom_handler,
        "open_verified_download_manifest_member",
        open_verified,
    )
    headers = {**_headers(access_token), "Range": "bytes=0-"}
    if if_match is not None:
        headers["If-Match"] = if_match
    response = client.get(url, headers=headers)

    assert response.status_code == status.HTTP_412_PRECONDITION_FAILED
    assert response.json() == {"detail": {"code": "snapshot_mismatch"}}
    assert not opened


def test_manifest_member_source_change_has_no_lease_or_source_bytes(
    client, access_token, rom, manifest_components, monkeypatch
):
    created = client.post(
        f"/api/roms/{rom.id}/download-manifests",
        headers=_headers(access_token),
        json={"component_ids": [manifest_components[0].id]},
    ).json()
    url, member = _manifest_member_url(created)
    source_bytes = b"private-source-bytes"
    opened = 0

    async def changed_source(_rom, _persisted_member):
        nonlocal opened
        opened += 1
        return DownloadManifestTransferResult(
            state=DownloadManifestTransferState.SOURCE_CHANGED
        )

    monkeypatch.setattr(
        download_manifests_endpoint.fs_rom_handler,
        "open_verified_download_manifest_member",
        changed_source,
    )
    response = client.get(
        url,
        headers={
            **_headers(access_token),
            "Range": "bytes=0-",
            "If-Match": member["snapshot"],
        },
    )

    assert response.status_code == status.HTTP_412_PRECONDITION_FAILED
    assert response.json() == {"detail": {"code": "source_changed"}}
    assert opened == 1
    assert source_bytes not in response.content


def test_manifest_member_rejects_mismatched_validator_for_full_transfer(
    client, access_token, rom, manifest_components, monkeypatch
):
    created = client.post(
        f"/api/roms/{rom.id}/download-manifests",
        headers=_headers(access_token),
        json={"component_ids": [manifest_components[0].id]},
    ).json()
    url, _member = _manifest_member_url(created)

    async def open_verified(_rom, _persisted_member):
        raise AssertionError("mismatched validator must not open a transfer")

    monkeypatch.setattr(
        download_manifests_endpoint.fs_rom_handler,
        "open_verified_download_manifest_member",
        open_verified,
    )
    response = client.get(
        url,
        headers={**_headers(access_token), "If-Match": 'W/"stale"'},
    )

    assert response.status_code == status.HTTP_412_PRECONDITION_FAILED
    assert response.json() == {"detail": {"code": "snapshot_mismatch"}}


def test_manifest_member_masks_foreign_and_hidden_rom_before_source_access(
    client,
    access_token,
    viewer_access_token,
    viewer_user,
    rom,
    manifest_components,
    monkeypatch,
):
    db_rom_handler.add_rom_user(rom_id=rom.id, user_id=viewer_user.id)
    created = client.post(
        f"/api/roms/{rom.id}/download-manifests",
        headers=_headers(viewer_access_token),
        json={"component_ids": [manifest_components[0].id]},
    ).json()
    url, _member = _manifest_member_url(created)

    async def open_verified(_rom, _persisted_member):
        raise AssertionError("masked requests must not access a source")

    monkeypatch.setattr(
        download_manifests_endpoint.fs_rom_handler,
        "open_verified_download_manifest_member",
        open_verified,
    )
    foreign = client.get(url, headers=_headers(access_token))
    assert foreign.status_code == status.HTTP_404_NOT_FOUND
    assert foreign.json() == {"detail": "Download manifest not found"}

    with session.begin() as db:
        db.add(
            HiddenEntity(
                entity=PermEntity.ROMS, entity_id=rom.id, user_id=viewer_user.id
            )
        )
    hidden = client.get(url, headers=_headers(viewer_access_token))
    assert hidden.status_code == status.HTTP_404_NOT_FOUND
    assert hidden.json() == {"detail": "Download manifest not found"}


@pytest.mark.parametrize(
    "size,start,end",
    [
        (5 * 1024**3, 4 * 1024**3, 5 * 1024**3 - 1),
        (80 * 1024**3, 79 * 1024**3, 80 * 1024**3 - 1),
        (120 * 1024**3, 119 * 1024**3, 120 * 1024**3 - 1),
    ],
)
def test_manifest_range_bounds_preserve_large_u64_values(size, start, end):
    assert download_manifests_endpoint._transfer_range_bounds(
        f"bytes={start}-{end}", size
    ) == (start, end)
