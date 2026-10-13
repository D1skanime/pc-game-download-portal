from fastapi import status
from fastapi.testclient import TestClient

from models.platform import Platform
from models.rom import Rom


def test_platform_rom_list_with_all_sidecars_disabled(
    client: TestClient, access_token: str, rom: Rom, platform: Platform
):
    """Platform galleries must still return a valid page when sidecars are disabled."""
    response = client.get(
        "/api/roms",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "platform_id": platform.id,
            "limit": 72,
            "with_char_index": False,
            "with_filter_values": False,
            "with_rom_id_index": False,
            "with_total": False,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["items"][0]["id"] == rom.id
    assert body["char_index"] == {}
    assert body["rom_id_index"] == []
    assert body["filter_values"]["genres"] == []
