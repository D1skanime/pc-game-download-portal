from fastapi import status

from models.rom import RomComponent, RomComponentKind, RomComponentManifestMember


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_editor_can_create_list_and_replace_archive_set(client, access_token, rom):
    component = RomComponent(
        rom_id=rom.id,
        relative_path="base",
        kind=RomComponentKind.BASE,
        manifest_members=[
            RomComponentManifestMember(
                relative_path="base/game.bin", size_bytes=3, sha256="a" * 64
            )
        ],
    )
    from tests.conftest import session

    with session.begin() as db:
        db.add(component)
    created = client.post(
        f"/api/roms/{rom.id}/download-archive-sets",
        headers=_headers(access_token),
        json={
            "name": "whole-game",
            "members": [
                {
                    "component_id": component.id,
                    "manifest_member_id": component.manifest_members[0].id,
                    "required": True,
                }
            ],
        },
    )
    assert created.status_code == status.HTTP_201_CREATED
    archive_set = created.json()
    assert archive_set["members"][0]["position"] == 0
    listed = client.get(
        f"/api/roms/{rom.id}/download-archive-sets", headers=_headers(access_token)
    )
    assert listed.status_code == status.HTTP_200_OK
    assert listed.json()[0]["name"] == "whole-game"
    replaced = client.put(
        f"/api/roms/{rom.id}/download-archive-sets/{archive_set['id']}",
        headers=_headers(access_token),
        json={
            "name": "optional-game",
            "members": [
                {
                    "component_id": component.id,
                    "manifest_member_id": component.manifest_members[0].id,
                    "required": False,
                }
            ],
        },
    )
    assert replaced.status_code == status.HTTP_200_OK
    assert replaced.json()["members"][0]["required"] is False


def test_archive_set_payload_is_bounded_and_rejects_unknown_fields(
    client, access_token, rom
):
    response = client.post(
        f"/api/roms/{rom.id}/download-archive-sets",
        headers=_headers(access_token),
        json={"name": "bad", "members": [], "relative_path": "/nas/private"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "/nas/private" not in response.text
