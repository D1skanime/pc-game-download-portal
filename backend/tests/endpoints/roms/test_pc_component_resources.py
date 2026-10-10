import time

from fastapi import status

from endpoints.roms import pc_component_resources
from handler.database import db_rom_handler
from models.rom import RomComponent, RomComponentKind, RomComponentManifestMember


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _dlc(rom):
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="dlc/example",
                kind=RomComponentKind.DLC,
                manifest_members=[],
            )
        ],
    )
    return db_rom_handler.get_rom(rom.id).components[0]


def test_component_notes_are_scoped_to_the_resolved_dlc(client, access_token, rom):
    component = _dlc(rom)

    response = client.post(
        f"/api/roms/{rom.id}/pc-components/{component.id}/notes",
        headers=_headers(access_token),
        json={
            "title": "DLC note",
            "content": "Only this DLC",
            "expected_version": component.updated_at.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == "DLC note"
    assert (
        client.get(f"/api/roms/{rom.id}/notes", headers=_headers(access_token)).json()
        == []
    )


def test_non_dlc_component_resource_routes_are_masked(client, access_token, rom):
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="base", kind=RomComponentKind.BASE, manifest_members=[]
            )
        ],
    )
    component = db_rom_handler.get_rom(rom.id).components[0]

    response = client.get(
        f"/api/roms/{rom.id}/pc-components/{component.id}/notes",
        headers=_headers(access_token),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_manifest_download_requires_an_exact_member_of_the_dlc(
    client, access_token, rom, monkeypatch
):
    db_rom_handler.sync_rom_components(
        rom.id,
        [
            RomComponent(
                relative_path="dlc/example",
                kind=RomComponentKind.DLC,
                manifest_members=[
                    RomComponentManifestMember(
                        relative_path="dlc/example/setup.bin",
                        size_bytes=4,
                        sha256="a" * 64,
                    )
                ],
            )
        ],
    )
    component = db_rom_handler.get_rom(rom.id).components[0]
    member = component.manifest_members[0]
    monkeypatch.setattr(
        pc_component_resources,
        "preflight_mapped_download",
        lambda *_args: (object(), object(), 4),
    )
    monkeypatch.setattr(
        pc_component_resources, "_mapped_chunks", lambda *_args: iter([b"data"])
    )

    response = client.get(
        f"/api/roms/{rom.id}/pc-components/{component.id}/manifest-members/{member.id}/content",
        headers=_headers(access_token),
    )
    wrong = client.get(
        f"/api/roms/{rom.id}/pc-components/{component.id}/manifest-members/{member.id + 999}/content",
        headers=_headers(access_token),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.content == b"data"
    assert wrong.status_code == status.HTTP_404_NOT_FOUND


def test_component_media_placement_routes_are_scoped_and_version_checked(
    client, access_token, rom, admin_user
):
    component = _dlc(rom)
    media = db_rom_handler.create_pc_component_owned_media(
        rom.id,
        component.id,
        admin_user.id,
        component.updated_at,
        "screenshot",
        "image/jpeg",
        "roms/1/components/shot.jpg",
        "upload",
    )
    assert media is not None
    refreshed = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    response = client.post(
        f"/api/roms/{rom.id}/pc-components/{component.id}/media/{media.media.id}/placement",
        headers=_headers(access_token),
        json={"expected_version": refreshed.updated_at.isoformat()},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["placements"][0]["position"] == 0
    refreshed = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    removed = client.delete(
        f"/api/roms/{rom.id}/pc-components/{component.id}/media/{media.media.id}/placement",
        headers=_headers(access_token),
        params={"expected_version": refreshed.updated_at.isoformat()},
    )
    assert removed.status_code == status.HTTP_200_OK
    assert removed.json()["placements"] == []
    assert db_rom_handler.get_pc_component_owned_media(
        rom.id, component.id, admin_user.id
    )


def test_deleting_component_media_with_missing_owned_file_updates_state(
    client, access_token, rom, admin_user, monkeypatch
):
    component = _dlc(rom)
    media = db_rom_handler.create_pc_component_owned_media(
        rom.id,
        component.id,
        admin_user.id,
        component.updated_at,
        "screenshot",
        "image/jpeg",
        "roms/1/components/missing.jpg",
        "upload",
    )
    assert media is not None
    before = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    assert before is not None

    async def missing_file(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr(
        pc_component_resources.fs_resource_handler, "remove_file", missing_file
    )
    time.sleep(1.1)
    response = client.delete(
        f"/api/roms/{rom.id}/pc-components/{component.id}/media/{media.media.id}",
        headers=_headers(access_token),
        params={"expected_version": before.updated_at.isoformat()},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Media deleted successfully"}
    after = db_rom_handler.get_pc_component_by_id(rom.id, component.id)
    assert after is not None
    assert after.updated_at > before.updated_at
    assert (
        db_rom_handler.get_pc_component_owned_media(rom.id, component.id, admin_user.id)
        == []
    )
