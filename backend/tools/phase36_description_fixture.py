"""Synthetic description corpus using the existing token-owned Run snapshot."""

import json
import shutil
from pathlib import Path

from phase34_fixtures import prepare as original_prepare
from phase35_incremental_scan_fixture import owned_root

GAMES = (
    "Known.Game",
    "Complete34",
    "Manual",
    "ManualEnglish",
    "MissingDE",
    "Identical",
    "WrongID",
    "Empty",
    "Rate",
    "Timeout",
)
IDS = dict(zip(GAMES, (1245620, 34, 53, 54, 201, 202, 203, 204, 205, 206), strict=True))
TEXT = {
    "de": "Deutscher Beschreibungstext",
    "fr": "Description francaise",
    "en": "English description",
}


def prepare(root, repo, *, profile="descriptions"):
    owned_root(root)
    games, checkout = original_prepare(root, repo)
    if games.is_symlink() or games.resolve() != root / "Games":
        raise RuntimeError("unexpected synthetic source")
    shutil.rmtree(games)
    if profile not in {"descriptions", "authority"}:
        raise RuntimeError("unknown owned fixture profile")
    names = GAMES if profile == "descriptions" else ("Known.Game", "Complete34")
    (root / "evidence/fixture-profile.json").write_text(
        json.dumps({"profile": profile, "games": list(names)})
    )
    for name in names:
        folder = games / "pc" / name / "Base"
        folder.mkdir(parents=True)
        (folder / "game.bin").write_bytes(("synthetic " + name).encode())
    if profile == "descriptions":
        for index in range(9):
            (
                games / "pc/Known.Game/Base" / ("Expansion" + str(index) + ".bin")
            ).write_bytes(("owned component " + str(index)).encode())
    console = games / "My Games"
    console.mkdir()
    (console / "Control.sfc").write_bytes(b"synthetic console")
    return games, checkout


def slots(provider, identity):
    languages = {"de": "german", "fr": "french", "en": "english"}
    variants = {
        tag: {
            "source_language": languages[tag] if provider == "steam" else tag,
            "summary": text + " " + str(identity),
        }
        for tag, text in TEXT.items()
    }
    return {
        "text_variants": variants,
        **({"app_id": identity, "source": "storefront"} if provider == "steam" else {}),
    }


def seed(mode="initial"):
    from phase33_collection_fixture import authority
    from sqlalchemy import select

    from config import LIBRARY_BASE_PATH, RESOURCES_BASE_PATH
    from handler.database.base_handler import sync_session
    from models.rom import Rom, RomComponent, RomComponentMetadata
    from models.storage import StorageRoot

    authority()
    with sync_session.begin() as session:
        rows = session.scalars(select(Rom)).all()
        profile = json.loads(Path("/phase34/evidence/fixture-profile.json").read_text())
        expected = (
            GAMES
            if profile["profile"] == "descriptions"
            else ("Known.Game", "Complete34")
        )
        if profile["games"] != list(expected) or {row.fs_name for row in rows} != set(
            expected
        ) | {"Control.sfc"}:
            raise RuntimeError("unexpected disposable catalog")
        if mode == "initial":
            session.add(
                StorageRoot(
                    name="phase35-alternate",
                    container_path=str(Path(LIBRARY_BASE_PATH) / "alternate"),
                    mode="external_read_only",
                    active=True,
                )
            )
        if mode == "initial":
            known = next(row for row in rows if row.fs_name == "Known.Game")
            relative = known.fs_resources_path + "/phase35-preserved-cover.bin"
            media = Path(RESOURCES_BASE_PATH) / relative
            if (
                not media.resolve().is_relative_to("/phase34/owned")
                or media.exists()
                or media.is_symlink()
            ):
                raise RuntimeError("fixture media custody mismatch")
            media.parent.mkdir(parents=True, exist_ok=True)
            media.write_bytes(b"owned preserved description control")
            known.path_cover_s = relative
        for row in rows:
            provider = "ss" if row.fs_name == "Control.sfc" else "steam"
            identity = 38 if provider == "ss" else IDS[row.fs_name]
            setattr(row, provider + "_id", identity)
            row.summary = "Untouched legacy scalar " + row.fs_name
            row.manual_metadata = (
                {"descriptions": {"de": "Protected Deutsch", "en": "Protected English"}}
                if row.fs_name == "Manual"
                else {}
            )
            if row.fs_name == "ManualEnglish":
                row.manual_metadata = {
                    "descriptions": {"en": "Protected manual English"}
                }
            setattr(
                row,
                provider + "_metadata",
                (
                    slots(provider, identity)
                    if mode == "complete" or row.fs_name == "Complete34"
                    else {}
                ),
            )
        if profile["profile"] == "descriptions" and mode == "initial":
            known = next(row for row in rows if row.fs_name == "Known.Game")
            for index in range(9):
                relative = "Base/Expansion" + str(index) + ".bin"
                if not (Path(LIBRARY_BASE_PATH) / "pc/Known.Game" / relative).is_file():
                    raise RuntimeError("owned component file missing")
                session.add(
                    RomComponent(rom_id=known.id, relative_path=relative, kind="dlc")
                )
            session.flush()
        for component in session.scalars(
            select(RomComponent).where(RomComponent.kind == "dlc")
        ):
            metadata = session.get(RomComponentMetadata, component.id)
            if metadata is None:
                metadata = RomComponentMetadata(component_id=component.id)
                session.add(metadata)
            metadata.steam_id = 300 + component.id
            metadata.steam_metadata = (
                slots("steam", metadata.steam_id) if mode == "complete" else {}
            )
            metadata.summary = "Untouched component scalar"
            metadata.manual_metadata = {
                "descriptions": {"en": "Protected component English"}
            }

    (Path("/phase34/evidence") / "provider-control.json").write_text(
        json.dumps({"enabled": True})
    )


def reset_one(provider="steam"):
    from phase33_collection_fixture import authority
    from sqlalchemy import select

    from handler.database.base_handler import sync_session
    from models.rom import Rom, RomComponentMetadata

    authority()
    with sync_session.begin() as session:
        rows = session.scalars(select(Rom)).all()
        for row in rows:
            source = "ss" if row.fs_name == "Control.sfc" else "steam"
            identity = getattr(row, source + "_id")
            setattr(row, source + "_metadata", slots(source, identity))
            if row.fs_name == ("Known.Game" if provider == "steam" else "Control.sfc"):
                setattr(row, source + "_metadata", {})
        for metadata in session.scalars(select(RomComponentMetadata)):
            metadata.steam_metadata = slots("steam", metadata.steam_id)


def seed_ss_fault():
    from phase33_collection_fixture import authority
    from sqlalchemy import select

    from handler.database.base_handler import sync_session
    from models.rom import Rom

    authority()
    with sync_session.begin() as session:
        rom = session.scalar(select(Rom).where(Rom.fs_name == "Control.sfc"))
        if rom is None or rom.ss_id != 38:
            raise RuntimeError("foreign SS fault fixture")
        rom.ss_id = 39
        rom.ss_metadata = {}
