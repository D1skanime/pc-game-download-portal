"""Token-bound browser fixture identity and owned-media seeding."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase33_collection_fixture import authority  # noqa: E402


def seed():
    authority()
    from sqlalchemy import select

    from config import RESOURCES_BASE_PATH
    from handler.database.base_handler import sync_session
    from models.rom import Rom

    base = Path(RESOURCES_BASE_PATH)
    if not base.resolve().is_relative_to("/phase34/owned"):
        raise RuntimeError("unowned browser media fixture")
    with sync_session.begin() as session:
        rom = session.scalar(select(Rom).where(Rom.fs_name == "Known.Game"))
        if rom is None:
            raise RuntimeError("missing synthetic known game")
        relative = rom.fs_resources_path + "/phase35-preserved-cover.bin"
        target = base / relative
        if target.exists() or target.is_symlink():
            raise RuntimeError("media fixture already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"phase35 preserved owned media")
        rom.steam_id = 42
        rom.path_cover_s = relative


if __name__ == "__main__":
    seed()
