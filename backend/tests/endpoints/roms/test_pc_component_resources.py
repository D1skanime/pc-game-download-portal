from fastapi import status

from handler.database import db_rom_handler
from models.rom import RomComponent, RomComponentKind


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
