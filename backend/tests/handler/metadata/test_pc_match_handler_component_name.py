from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from handler.metadata.pc_match_handler import PcMetadataMatchHandler


@pytest.mark.asyncio
async def test_parent_listed_steam_dlc_uses_existing_component_name():
    steam = Mock(is_enabled=Mock(return_value=True))
    steam.get_rom_by_id = AsyncMock(
        return_value={
            "steam_id": 2138330,
            "name": "Cyberpunk 2077: Phantom Liberty",
            "steam_metadata": {"type": "dlc", "fullgame": {"appid": 1091500}},
        }
    )
    handler = PcMetadataMatchHandler(providers={"steam": steam})
    rom = SimpleNamespace(
        steam_id=1091500, steam_metadata={"dlc_ids": [2138330]}, name="Cyberpunk 2077"
    )
    component = SimpleNamespace(
        relative_path="Expansion",
        component_metadata=SimpleNamespace(name="Cyberpunk 2077: Phantom Liberty"),
        manifest_members=[SimpleNamespace(relative_path="Expansion/setup.exe")],
    )
    match = await handler.fetch_parent_listed_steam_dlc(rom, component)
    assert match is not None
    assert match["steam_id"] == 2138330
