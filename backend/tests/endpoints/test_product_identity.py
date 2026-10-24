"""Feed display identity is separate from established wire identifiers."""

import csv
import io

from endpoints import feeds
from handler.database import db_platform_handler
from models.platform import Platform
from models.rom import Rom
from utils.gamelist_exporter import GamelistExporter
from utils.pegasus_exporter import PegasusExporter


def test_webrcade_display_and_upstream_assets(client, access_token):
    response = client.get(
        "/api/feeds/webrcade", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "ZockArchive Feed"
    assert body["longTitle"] == "Custom ZockArchive Feed"
    assert body["description"] == "Custom feed from your ZockArchive library"
    assert set(body) == {
        "title",
        "longTitle",
        "description",
        "thumbnail",
        "background",
        "categories",
    }
    assert (
        body["thumbnail"]
        == "https://raw.githubusercontent.com/rommapp/romm/release/.github/resources/isotipo.svg"
    )
    assert (
        body["background"]
        == "https://raw.githubusercontent.com/rommapp/romm/release/.github/resources/screenshots/gallery.png"
    )
    assert client.get("/api/feeds/webrcade").status_code == 401


def test_kekatsu_author_keeps_nine_wire_fields(
    client, access_token, platform: Platform, rom: Rom
):
    response = client.get(
        f"/api/feeds/kekatsu/{platform.slug}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text), delimiter="\t"))
    item = rows[2]
    assert len(item) == 9
    assert item[0] == (rom.name or rom.fs_name_no_tags)
    assert item[4] == "ZockArchive"
    assert f"/roms/{rom.id}/content/" in item[5]
    assert item[6] == rom.fs_name


def test_exporter_display_keeps_pegasus_identifier(rom: Rom):
    game = GamelistExporter(local_export=True)._create_game_element(
        rom, None, {}, "screenshot", "box2d"
    )
    scrap = game.find("scrap")
    assert scrap is not None
    assert scrap.attrib["name"] == "ZockArchive"
    assert set(scrap.attrib) == {"name", "date"}
    assert game.findtext("path") == f"./{rom.fs_name}"
    entry = PegasusExporter(local_export=True)._create_game_entry(rom, None)
    assert f"x-romm-id: {rom.id}" in entry.splitlines()
    assert "x-za-id:" not in entry


def test_synthetic_title_ids_and_real_title_ids_remain_stable(rom: Rom):
    rom.fs_name = "Example.pkg"
    assert feeds.fpkgi_title_id(rom, []) == f"ROMM{str(rom.id)[-5:].zfill(5)}"
    rom.fs_name = "Game CUSA12345.pkg"
    assert feeds.fpkgi_title_id(rom, []) == "CUSA12345"


def test_tinfoil_configured_welcome_is_authoritative(
    client, platform: Platform, monkeypatch
):
    db_platform_handler.update_platform(platform.id, {"slug": "switch"})
    monkeypatch.setattr(
        feeds, "TINFOIL_WELCOME_MESSAGE", "RomM custom operator welcome"
    )
    response = client.get("/api/feeds/tinfoil?slug=switch")
    assert response.status_code == 200
    assert response.json()["success"] == "RomM custom operator welcome"
