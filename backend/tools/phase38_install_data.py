"""Seed and verify synthetic compatibility state inside an owned production app."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from tools.phase33_collection_fixture import authority


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


def client():
    import httpx

    from handler.auth.constants import Scope

    caller = httpx.Client(base_url="http://127.0.0.1:5000", timeout=30)
    caller.get("/api/heartbeat").raise_for_status()
    caller.headers["x-csrftoken"] = caller.cookies["romm_csrftoken"]
    return caller, Scope


def authenticate(caller, scopes):
    token = caller.post(
        "/api/token",
        data={
            "grant_type": "password",
            "username": "phase38-admin",
            "password": os.environ["PHASE34_RUN_TOKEN"],
            "scope": " ".join(scope.value for scope in scopes),
        },
    )
    token.raise_for_status()
    caller.headers["Authorization"] = "Bearer " + token.json()["access_token"]


def seed():
    authority()
    from sqlalchemy import select

    from config import LIBRARY_BASE_PATH, RESOURCES_BASE_PATH
    from handler.database.base_handler import sync_session
    from handler.redis_handler import redis_client
    from models.platform import Platform
    from models.rom import Rom, RomFile, RomFileCategory, RomUser
    from models.storage import PlatformStorageMapping, StorageRoot
    from models.user import User

    caller, scopes = client()
    response = caller.post(
        "/api/users",
        json={
            "username": "phase38-admin",
            "email": "phase38@example.test",
            "password": os.environ["PHASE34_RUN_TOKEN"],
            "role": "admin",
        },
    )
    response.raise_for_status()
    authenticate(caller, scopes)
    with sync_session.begin() as session:
        user = session.scalar(select(User).where(User.username == "phase38-admin"))
        user.ui_settings = {"uiVersion": "v2", "phase38": "preserved"}
        platform = Platform(name="Owned Windows fixture", slug="win", fs_slug="PC")
        session.add(platform)
        session.flush()
        root = StorageRoot(
            name="phase38-owned",
            container_path=LIBRARY_BASE_PATH,
            mode="external_read_only",
            active=True,
        )
        session.add(root)
        session.flush()
        session.add(
            PlatformStorageMapping(
                platform_id=platform.id,
                storage_root_id=root.id,
                relative_path="PC",
                active=True,
                version=1,
            )
        )
        rom = Rom(
            platform_id=platform.id,
            name="Owned preserved game",
            slug="owned-preserved",
            fs_name="Phase34-Synthetic.bin",
            fs_name_no_tags="Phase34-Synthetic",
            fs_name_no_ext="Phase34-Synthetic",
            fs_extension="bin",
            fs_path="PC",
        )
        session.add(rom)
        session.flush()
        session.add(
            RomFile(
                rom_id=rom.id,
                file_name="Phase34-Synthetic.bin",
                file_path="PC",
                file_size_bytes=26,
                category=RomFileCategory.GAME,
            )
        )
        session.add(RomUser(rom_id=rom.id, user_id=user.id, backlogged=True, rating=3))
        console = Platform(name="Owned Game Boy", slug="gb", fs_slug="GB GameBoy")
        session.add(console)
        session.flush()
        session.add(
            PlatformStorageMapping(
                platform_id=console.id,
                storage_root_id=root.id,
                relative_path="GB GameBoy",
                active=True,
                version=1,
            )
        )
        cartridge = Rom(
            platform_id=console.id,
            name="Owned synthetic cartridge",
            slug="owned-cartridge",
            fs_name="owned.gb",
            fs_name_no_tags="owned",
            fs_name_no_ext="owned",
            fs_extension="gb",
            fs_path="GB GameBoy",
        )
        session.add(cartridge)
        session.flush()
        session.add(
            RomFile(
                rom_id=cartridge.id,
                file_name="owned.gb",
                file_path="GB GameBoy",
                file_size_bytes=32768,
                category=RomFileCategory.GAME,
            )
        )
    resource = Path(RESOURCES_BASE_PATH) / "phase38-sentinel.bin"
    if not resource.resolve().is_relative_to("/phase34/owned"):
        raise RuntimeError("unowned resource sentinel")
    resource.write_bytes(b"phase38 owned resource sentinel")
    redis_client.set("phase38:compatibility", "preserved")
    caller.close()


def snapshot():
    authority()
    from sqlalchemy import select, text

    from config import LIBRARY_BASE_PATH, RESOURCES_BASE_PATH
    from handler.database.base_handler import sync_session
    from handler.redis_handler import redis_client
    from models.platform import Platform
    from models.rom import Rom, RomFile, RomUser
    from models.storage import PlatformStorageMapping, StorageRoot
    from models.user import User

    with sync_session() as session:
        user = session.scalar(select(User).where(User.username == "phase38-admin"))
        values = {
            "user": [
                user.id,
                user.username,
                user.hashed_password,
                user.role,
                user.enabled,
                user.permission_group_id,
                user.ui_settings,
            ],
            "platforms": [
                (p.id, p.name, p.slug, p.fs_slug)
                for p in session.scalars(select(Platform))
            ],
            "games": [
                (p.id, p.name, p.platform_id, p.fs_path, p.fs_name, p.incarnation_token)
                for p in session.scalars(select(Rom))
            ],
            "files": [
                (p.id, p.rom_id, p.file_name, p.file_path, p.incarnation_token)
                for p in session.scalars(select(RomFile))
            ],
            "roots": [
                (p.id, p.name, p.container_path, p.mode, p.active)
                for p in session.scalars(select(StorageRoot))
            ],
            "mappings": [
                (
                    p.id,
                    p.platform_id,
                    p.storage_root_id,
                    p.relative_path,
                    p.version,
                    p.active,
                )
                for p in session.scalars(select(PlatformStorageMapping))
            ],
            "user_game_state": [
                (p.id, p.rom_id, p.user_id, p.backlogged, p.rating)
                for p in session.scalars(select(RomUser))
            ],
            "schema": session.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one(),
        }
    result = {key: digest(value) for key, value in values.items()}
    for key, path in (
        ("source", Path(LIBRARY_BASE_PATH) / "PC/Phase34-Synthetic.bin"),
        ("resource", Path(RESOURCES_BASE_PATH) / "phase38-sentinel.bin"),
    ):
        result[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    result["redis"] = digest(redis_client.get("phase38:compatibility"))
    return result


def verify_http():
    authority()
    caller, scopes = client()
    authenticate(caller, scopes)
    caller.get("/api/heartbeat").raise_for_status()
    rows = caller.get("/api/roms?limit=100")
    rows.raise_for_status()
    rom = next(
        row for row in rows.json()["items"] if row["name"] == "Owned preserved game"
    )
    detail = caller.get("/api/roms/" + str(rom["id"]))
    detail.raise_for_status()
    file = detail.json()["files"][0]
    path = "/api/roms/" + str(file["id"]) + "/files/content/Phase34-Synthetic.bin"
    response = caller.get(path)
    response.raise_for_status()
    if response.content != b"phase34 synthetic fixture\n":
        raise RuntimeError("preserved mapped download bytes mismatch")
    authenticate(caller, [scopes.ME_READ])
    if caller.get(path).status_code != 403:
        raise RuntimeError("scope-limited download was not denied")
    caller.close()
    return {
        "login": True,
        "heartbeat": True,
        "library": True,
        "download": True,
        "denied": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seed", "verify"))
    args = parser.parse_args()
    if args.action == "seed":
        seed()
    result = {"digests": snapshot(), "http": verify_http()}
    destination = Path("/phase34/evidence/upgrade-" + args.action + ".json")
    destination.write_text(json.dumps(result, indent=2))
    print("PASS owned populated state " + args.action)


if __name__ == "__main__":
    main()
