from datetime import datetime

import pytest
from sqlalchemy import delete, inspect
from sqlalchemy.exc import IntegrityError

from models.platform import Platform
from models.storage import PlatformStorageMapping, StorageRoot
from tests.conftest import session


@pytest.fixture
def storage_root() -> StorageRoot:
    with session.begin() as db:
        root = StorageRoot(name="Archive", container_path="/romm/library", mode="external_read_only")
        db.add(root)
        db.flush()
        root_id = root.id
    with session() as db:
        return db.get(StorageRoot, root_id)


def _platform(slug: str) -> Platform:
    with session.begin() as db:
        platform = Platform(name=slug, slug=slug, fs_slug=slug)
        db.add(platform)
        db.flush()
        platform_id = platform.id
    with session() as db:
        return db.get(Platform, platform_id)


def test_storage_root_contract(storage_root: StorageRoot):
    assert storage_root.mode == "external_read_only"
    assert storage_root.active is True
    assert storage_root.reachable is None
    assert storage_root.readable is None
    assert storage_root.non_writable is None
    assert storage_root.last_checked_at is None
    assert storage_root.safe_error is None
    assert isinstance(storage_root.created_at, datetime)
    assert isinstance(storage_root.updated_at, datetime)
    assert inspect(StorageRoot).columns.safe_error.type.length == 1000


def test_storage_root_rejects_other_mode():
    with pytest.raises(IntegrityError):
        with session.begin() as db:
            db.add(StorageRoot(name="Unsafe", container_path="/unsafe", mode="writable"))


def test_storage_root_container_path_is_unique(storage_root: StorageRoot):
    with pytest.raises(IntegrityError):
        with session.begin() as db:
            db.add(StorageRoot(name="Duplicate", container_path=storage_root.container_path, mode="external_read_only"))


def test_mapping_stores_only_identities_and_relative_path(storage_root: StorageRoot):
    platform = _platform("snes")
    with session.begin() as db:
        db.add(PlatformStorageMapping(platform_id=platform.id, storage_root_id=storage_root.id, relative_path="SNES Super Nintendo"))
    columns = set(inspect(PlatformStorageMapping).columns.keys())
    assert columns == {"id", "platform_id", "storage_root_id", "relative_path", "created_at", "updated_at"}
    assert platform.fs_slug == "snes"


def test_mapping_platform_is_unique(storage_root: StorageRoot):
    platform = _platform("ps2")
    with pytest.raises(IntegrityError):
        with session.begin() as db:
            db.add_all([PlatformStorageMapping(platform_id=platform.id, storage_root_id=storage_root.id, relative_path="PlayStation 2"), PlatformStorageMapping(platform_id=platform.id, storage_root_id=storage_root.id, relative_path="PS2 Duplicate")])


def test_mapping_root_relative_path_is_unique(storage_root: StorageRoot):
    first = _platform("gb")
    second = _platform("gbc")
    with pytest.raises(IntegrityError):
        with session.begin() as db:
            db.add_all([PlatformStorageMapping(platform_id=first.id, storage_root_id=storage_root.id, relative_path="GB GameBoy"), PlatformStorageMapping(platform_id=second.id, storage_root_id=storage_root.id, relative_path="GB GameBoy")])


def test_storage_root_delete_is_restricted(storage_root: StorageRoot):
    platform = _platform("switch")
    with session.begin() as db:
        db.add(PlatformStorageMapping(platform_id=platform.id, storage_root_id=storage_root.id, relative_path="Nintendo Switch"))
    with pytest.raises(IntegrityError):
        with session.begin() as db:
            db.execute(delete(StorageRoot).where(StorageRoot.id == storage_root.id))


def test_platform_mapping_relationship_is_scalar(storage_root: StorageRoot):
    platform = _platform("pc")
    with session.begin() as db:
        db.add(PlatformStorageMapping(platform_id=platform.id, storage_root_id=storage_root.id, relative_path="PC"))
    with session() as db:
        loaded = db.get(Platform, platform.id)
        assert isinstance(loaded.storage_mapping, PlatformStorageMapping)
