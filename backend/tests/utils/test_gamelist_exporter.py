import hashlib
from os.path import isabs
from xml.etree.ElementTree import fromstring

import pytest

from config import FRONTEND_RESOURCES_PATH
from exceptions.storage_exceptions import InvalidRelativePathError, StoragePolicyDenied
from handler.database import db_platform_handler, db_rom_handler
from handler.filesystem import fs_platform_handler, fs_resource_handler
from handler.filesystem.storage_access import open_owned_access
from handler.filesystem.storage_composition import (
    StorageCompositionConfig,
    build_storage_composition,
)
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation
from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger
from models.platform import Platform
from models.rom import Rom
from models.user import User
from utils.gamelist_exporter import GamelistExporter


@pytest.fixture
def platform_with_roms(admin_user: User):
    platform = Platform(name="Super Nintendo", slug="snes", fs_slug="snes")
    platform = db_platform_handler.add_platform(platform)

    rom = Rom(
        platform_id=platform.id,
        name="Super Mario World",
        slug="super-mario-world",
        fs_name="Super Mario World (USA).sfc",
        fs_name_no_tags="Super Mario World",
        fs_name_no_ext="Super Mario World (USA)",
        fs_extension="sfc",
        fs_path="snes/roms",
        summary="A classic platformer game.",
        regions=["USA"],
        languages=["en"],
        gamelist_id="12345",
        gamelist_metadata={"player_count": "2"},
    )
    rom = db_rom_handler.add_rom(rom)
    db_rom_handler.add_rom_user(rom_id=rom.id, user_id=admin_user.id)

    db_rom_handler.update_rom(
        rom.id,
        {
            "igdb_metadata": {
                "genres": ["Platformer", "Adventure"],
                "companies": ["Nintendo", "Nintendo EAD"],
                "first_release_date": 709257600,  # 1992-06-23 UTC in seconds; view *1000
                "total_rating": 92.0,  # view uses this directly as a 0-100 igdb_rating
            },
            "path_cover_l": "snes/covers/super-mario-world.jpg",
            "path_manual": "snes/manuals/super-mario-world.pdf",
            "path_screenshots": ["snes/screenshots/super-mario-world-1.jpg"],
            "gamelist_metadata": {
                "player_count": "2",
                "video_path": "snes/videos/super-mario-world.mp4",  # feeds rom.path_video property
            },
        },
    )

    # Re-fetch to get joined metadata
    rom = db_rom_handler.get_rom(rom.id)

    return platform, [rom]


@pytest.fixture
def platform_with_minimal_rom(admin_user: User):
    platform = Platform(name="Game Boy", slug="gb", fs_slug="gb")
    platform = db_platform_handler.add_platform(platform)

    rom = Rom(
        platform_id=platform.id,
        name=None,
        slug="unknown-rom",
        fs_name="unknown.gb",
        fs_name_no_tags="unknown",
        fs_name_no_ext="unknown",
        fs_extension="gb",
        fs_path="gb/roms",
    )
    rom = db_rom_handler.add_rom(rom)
    db_rom_handler.add_rom_user(rom_id=rom.id, user_id=admin_user.id)

    return platform, [rom]


def test_export_gamelist_xml_basic(platform_with_roms):
    platform, _roms = platform_with_roms
    exporter = GamelistExporter(local_export=True)

    xml_str = exporter.export_platform_to_xml(platform.id, request=None)

    root = fromstring(xml_str)
    assert root.tag == "gameList"

    games = root.findall("game")
    assert len(games) == 1

    game = games[0]
    name = game.find("name")
    path = game.find("path")
    desc = game.find("desc")
    developer = game.find("developer")
    publisher = game.find("publisher")
    genre = game.find("genre")
    lang = game.find("lang")
    region = game.find("region")
    gamelist_id = game.find("id")
    players = game.find("players")

    assert name is not None
    assert path is not None
    assert desc is not None
    assert developer is not None
    assert publisher is not None
    assert genre is not None
    assert lang is not None
    assert region is not None
    assert gamelist_id is not None
    assert players is not None

    assert name.text == "Super Mario World"
    assert path.text == "./Super Mario World (USA).sfc"
    assert desc.text == "A classic platformer game."
    assert developer.text == "Nintendo"
    assert publisher.text == "Nintendo EAD"
    assert genre.text == "Platformer"
    assert lang.text == "en"
    assert region.text == "USA"
    assert gamelist_id.text == "12345"
    assert players.text == "2"


def test_export_gamelist_xml_rating(platform_with_roms):
    platform, _ = platform_with_roms
    exporter = GamelistExporter(local_export=True)

    xml_str = exporter.export_platform_to_xml(platform.id, request=None)
    root = fromstring(xml_str)
    game = root.findall("game")[0]

    # Rating should be on 0-1 scale (9.2 / 10 = 0.92)
    rating = game.find("rating")
    assert rating is not None
    assert rating.text == "0.92"


def test_export_gamelist_xml_release_date(platform_with_roms):
    platform, _ = platform_with_roms
    exporter = GamelistExporter(local_export=True)

    xml_str = exporter.export_platform_to_xml(platform.id, request=None)
    root = fromstring(xml_str)
    game = root.findall("game")[0]

    release_date = game.find("releasedate")
    assert release_date is not None
    assert release_date.text == "19920623T000000"


def test_export_gamelist_xml_minimal_rom(platform_with_minimal_rom):
    platform, _ = platform_with_minimal_rom
    exporter = GamelistExporter(local_export=True)

    xml_str = exporter.export_platform_to_xml(platform.id, request=None)
    root = fromstring(xml_str)

    games = root.findall("game")
    assert len(games) == 1

    game = games[0]
    # Falls back to fs_name when name is None
    name = game.find("name")
    path = game.find("path")
    assert name is not None
    assert path is not None
    assert name.text == "unknown.gb"
    assert path.text == "./unknown.gb"
    # Optional fields should not be present
    assert game.find("desc") is None
    assert game.find("developer") is None
    assert game.find("genre") is None


def test_export_gamelist_xml_skips_missing_roms(admin_user: User):
    platform = Platform(name="NES", slug="nes", fs_slug="nes")
    platform = db_platform_handler.add_platform(platform)

    rom = Rom(
        platform_id=platform.id,
        name="Missing ROM",
        slug="missing-rom",
        fs_name="missing.nes",
        fs_name_no_tags="missing",
        fs_name_no_ext="missing",
        fs_extension="nes",
        fs_path="nes/roms",
        missing_from_fs=True,
    )
    db_rom_handler.add_rom(rom)

    exporter = GamelistExporter(local_export=True)
    xml_str = exporter.export_platform_to_xml(platform.id, request=None)
    root = fromstring(xml_str)

    assert len(root.findall("game")) == 0


def test_export_gamelist_xml_invalid_platform():
    exporter = GamelistExporter(local_export=True)

    with pytest.raises(ValueError, match="not found"):
        exporter.export_platform_to_xml(99999, request=None)


def test_export_gamelist_xml_scrap_element(platform_with_roms):
    platform, _ = platform_with_roms
    exporter = GamelistExporter(local_export=True)

    xml_str = exporter.export_platform_to_xml(platform.id, request=None)
    root = fromstring(xml_str)
    game = root.findall("game")[0]

    scrap = game.find("scrap")
    assert scrap is not None
    assert scrap.get("name") == "RomM"


@pytest.mark.parametrize("tag", ["thumbnail", "image", "video", "screenshot", "manual"])
def test_export_gamelist_xml_local_media_relative_path(platform_with_roms, tag):
    platform, _ = platform_with_roms
    exporter = GamelistExporter(local_export=True)
    xml_str = exporter.export_platform_to_xml(platform.id, request=None)
    root = fromstring(xml_str)
    game = root.findall("game")[0]

    elem = game.find(tag)
    assert elem is not None
    assert elem.text is not None
    assert not isabs(elem.text)


def test_export_gamelist_xml_local_ss_metadata_media_relative(platform_with_roms):
    platform, roms = platform_with_roms

    db_rom_handler.update_rom(
        roms[0].id,
        {
            "ss_metadata": {
                "box3d_path": "snes-ss/box3d/test.png",
                "box2d_back_path": "snes-ss/boxback/test.png",
                "fanart_path": "snes-ss/fanart/test.png",
                "logo_path": "snes-ss/logo/test.png",
                "miximage_path": "snes-ss/miximage/test.png",
                "physical_path": "snes-ss/physical/test.png",
                "title_screen_path": "snes-ss/titlescreen/test.png",
                "bezel_path": "snes-ss/bezel/test.png",
            }
        },
    )

    exporter = GamelistExporter(local_export=True)
    xml_str = exporter.export_platform_to_xml(platform.id, request=None)
    root = fromstring(xml_str)
    game = root.findall("game")[0]

    media_tags = [
        "box3d",
        "boxback",
        "fanart",
        "marquee",
        "miximage",
        "physicalmedia",
        "title_screen",
        "bezel",
    ]
    for tag in media_tags:
        elem = game.find(tag)
        assert elem is not None and elem.text is not None

        assert not isabs(elem.text)


def test_export_gamelist_xml_local_no_absolute_paths_anywhere(platform_with_roms):
    """Catch-all: when local_export=True, no element text should contain
    the FRONTEND_RESOURCES_PATH absolute prefix."""
    platform, _ = platform_with_roms

    exporter = GamelistExporter(local_export=True)
    xml_str = exporter.export_platform_to_xml(platform.id, request=None)
    root = fromstring(xml_str)

    for elem in root.iter():
        if elem.text and FRONTEND_RESOURCES_PATH in elem.text:
            pytest.fail(
                f"<{elem.tag}> contains absolute FRONTEND_RESOURCES_PATH: {elem.text}"
            )


def test_export_gamelist_xml_rejects_path_traversal(platform_with_roms):
    """Paths with traversal segments must not escape the resources directory."""
    platform, roms = platform_with_roms

    db_rom_handler.update_rom(roms[0].id, {"path_cover_l": "../../etc/passwd"})

    exporter = GamelistExporter(local_export=True)
    with pytest.raises(InvalidRelativePathError, match="safe relative path"):
        exporter.export_platform_to_xml(platform.id, request=None)


async def test_export_platform_to_file_requires_owned_destination(
    platform_with_roms, tmp_path
):
    platform, _ = platform_with_roms
    library = tmp_path / "library"
    library.mkdir()
    owned = {kind: tmp_path / kind.value for kind in OwnedStorageKind}
    for path in owned.values():
        path.mkdir()
    composition = build_storage_composition(StorageCompositionConfig(library, owned))
    with open_owned_access(
        composition.owned[OwnedStorageKind.RESOURCES],
        StorageOperation.OVERWRITE,
        "gamelist.xml",
    ) as destination:
        assert (
            await GamelistExporter(local_export=True).export_platform_to_file(
                platform.id, request=None, destination=destination
            )
            is True
        )
    content = (owned[OwnedStorageKind.RESOURCES] / "gamelist.xml").read_text()
    assert "<gameList>" in content


def _source_manifest(root):
    entries = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().encode()):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            entries.append((relative, "directory", 0, ""))
        else:
            content = path.read_bytes()
            entries.append(
                (relative, "file", len(content), hashlib.sha256(content).hexdigest())
            )
    return tuple(entries)


@pytest.mark.asyncio
async def test_gamelist_export_rejects_external_destination_before_io(
    platform_with_roms, tmp_path, monkeypatch
):
    platform, _ = platform_with_roms
    library = tmp_path / "library"
    library.mkdir()
    owned = {kind: tmp_path / kind.value for kind in OwnedStorageKind}
    for path in owned.values():
        path.mkdir()
    composition = build_storage_composition(StorageCompositionConfig(library, owned))

    def forbidden(*_args, **_kwargs):
        raise AssertionError("filesystem access before destination denial")

    monkeypatch.setattr(GamelistExporter, "_build_gamelist_xml", forbidden)
    with pytest.raises(StoragePolicyDenied) as error:
        await GamelistExporter(local_export=True).export_platform_to_file(
            platform.id,
            request=None,
            destination=composition.legacy_external, # type: ignore[arg-type]
        )
    assert error.value.code == "external_storage_operation_denied"
    assert error.value.operation == "overwrite"
    assert not tuple(library.iterdir())


@pytest.mark.asyncio
@pytest.mark.parametrize("trigger", list(ScanTrigger))
async def test_gamelist_export_scan_triggers_preserve_mapped_source(
    platform_with_roms, tmp_path, trigger
):
    platform, _ = platform_with_roms
    library = tmp_path / "library"
    (library / "Mapped" / "Nested").mkdir(parents=True)
    (library / "Mapped" / "Game.iso").write_bytes(b"immutable game")
    (library / "Mapped" / "Nested" / "Disc 2.bin").write_bytes(b"disc two")
    before = _source_manifest(library)
    owned = {kind: tmp_path / kind.value for kind in OwnedStorageKind}
    for path in owned.values():
        path.mkdir()
    composition = build_storage_composition(StorageCompositionConfig(library, owned))
    command = MappedScanCommand(
        mapping_id=platform.id,
        expected_revision=1,
        trigger=trigger,
        scope=ScanScope.PLATFORM,
        scan_type="quick",
        options=(("export_gamelist", "true"),),
    )
    assert command.trigger is trigger

    with open_owned_access(
        composition.owned[OwnedStorageKind.RESOURCES],
        StorageOperation.OVERWRITE,
        f"{trigger.value}-gamelist.xml",
    ) as destination:
        assert await GamelistExporter(local_export=True).export_platform_to_file(
            platform.id, request=None, destination=destination
        )

    assert _source_manifest(library) == before