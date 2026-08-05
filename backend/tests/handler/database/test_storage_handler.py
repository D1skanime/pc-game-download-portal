import os
import shutil
import stat
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from exceptions.storage_exceptions import (
    DuplicateStorageMappingError,
    InvalidRelativePathError,
    MissingStoragePlatformError,
    MissingStorageRootError,
    StorageMappingOverlapError,
    StoragePersistenceError,
    UnsafeWritableRootError,
)
from handler.database import db_storage_handler
from handler.database.base_handler import sync_engine, sync_session
from models.platform import Platform
from models.storage import PlatformStorageMapping, StorageRoot


def access(_path, mode):
    return mode != os.W_OK


def add_objects(session, base: Path, roots):
    platforms = []
    stored_roots = []
    for name, path in roots:
        root = StorageRoot(name=name, container_path=str(path))
        session.add(root)
        stored_roots.append(root)
    for name in ("one", "two", "three"):
        platform = Platform(name=name, slug=name, fs_slug=name)
        session.add(platform)
        platforms.append(platform)
    session.flush()
    return stored_roots, platforms


def manifest(path: Path):
    entries = []
    for item in sorted(path.rglob("*"), key=lambda value: str(value.relative_to(path))):
        metadata = item.lstat()
        entries.append(
            (
                str(item.relative_to(path)),
                stat.S_IFMT(metadata.st_mode),
                metadata.st_size,
                stat.S_IMODE(metadata.st_mode),
                metadata.st_mtime_ns,
                os.readlink(item) if item.is_symlink() else None,
            )
        )
    return tuple(entries)


def install_mutation_tripwires(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("storage persistence attempted a source mutation")

    for owner, name in (
        (Path, "mkdir"),
        (Path, "unlink"),
        (Path, "rename"),
        (Path, "replace"),
        (shutil, "copy"),
        (shutil, "copy2"),
        (shutil, "copytree"),
        (shutil, "move"),
        (tempfile, "NamedTemporaryFile"),
        (tempfile, "TemporaryFile"),
    ):
        monkeypatch.setattr(owner, name, forbidden)


def test_register_existing_root_without_mutation(tmp_path: Path):
    root_path = tmp_path / "library"
    root_path.mkdir()
    before = list(tmp_path.rglob("*"))
    with patch("handler.filesystem.storage_resolver.os.access", side_effect=access):
        root = db_storage_handler.register_root(
            "Archive", str(root_path), mode="writable"
        )
    assert root.mode == "external_read_only"
    assert root.reachable and root.readable and root.non_writable
    assert list(tmp_path.rglob("*")) == before


def test_register_rejects_relative_missing_and_writable(tmp_path: Path):
    with pytest.raises(InvalidRelativePathError):
        db_storage_handler.register_root("Bad", "relative")
    with pytest.raises(MissingStorageRootError):
        db_storage_handler.register_root("Missing", str(tmp_path / "missing"))
    with (
        patch(
            "handler.filesystem.storage_resolver.os.access",
            return_value=True,
        ),
        pytest.raises(UnsafeWritableRootError),
    ):
        db_storage_handler.register_root("Writable", str(tmp_path))


def test_registration_and_mapping_preserve_source_manifest_and_avoid_mutation_primitives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root_path = tmp_path / "library"
    target = root_path / "Nintendo Switch" / "nested"
    target.mkdir(parents=True)
    source = target / "game.nsp"
    source.write_bytes(b"immutable archive")
    before = manifest(root_path)

    install_mutation_tripwires(monkeypatch)
    with patch("handler.filesystem.storage_resolver.os.access", side_effect=access):
        root = db_storage_handler.register_root("Archive", str(root_path))
        with sync_session.begin() as session:
            platform = Platform(name="switch", slug="switch", fs_slug="switch")
            session.add(platform)
            session.flush()
            platform_id = platform.id
        db_storage_handler.save_mapping(platform_id, root.id, "Nintendo Switch/nested")

    assert manifest(root_path) == before
    assert source.read_bytes() == b"immutable archive"


@pytest.mark.parametrize("candidate", ["games", "games/child", "games/child/deeper"])
def test_overlap_equal_ancestor_descendant_and_rollback(tmp_path: Path, candidate: str):
    (tmp_path / "games" / "child" / "deeper").mkdir(parents=True)
    with sync_session.begin() as session:
        roots, platforms = add_objects(session, tmp_path, [("root", tmp_path)])
    with patch("handler.filesystem.storage_resolver.os.access", side_effect=access):
        db_storage_handler.save_mapping(platforms[0].id, roots[0].id, "games/child")
        with pytest.raises(StorageMappingOverlapError):
            db_storage_handler.save_mapping(platforms[1].id, roots[0].id, candidate)
    with sync_session() as session:
        assert (
            session.scalar(
                select(PlatformStorageMapping).where(
                    PlatformStorageMapping.platform_id == platforms[1].id
                )
            )
            is None
        )


def test_cross_root_canonical_overlap_and_text_prefix_non_overlap(tmp_path: Path):
    shared = tmp_path / "shared"
    nested = shared / "nested"
    (nested / "target").mkdir(parents=True)
    (shared / "target-old").mkdir()
    with sync_session.begin() as session:
        roots, platforms = add_objects(
            session, tmp_path, [("outer", shared), ("inner", nested)]
        )
    with patch("handler.filesystem.storage_resolver.os.access", side_effect=access):
        db_storage_handler.save_mapping(platforms[0].id, roots[0].id, "nested/target")
        with pytest.raises(StorageMappingOverlapError):
            db_storage_handler.save_mapping(platforms[1].id, roots[1].id, "target")
        db_storage_handler.save_mapping(platforms[2].id, roots[0].id, "target-old")


def test_platform_unique_constraint_is_backstop(tmp_path: Path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    with sync_session.begin() as session:
        roots, platforms = add_objects(session, tmp_path, [("root", tmp_path)])
    with patch("handler.filesystem.storage_resolver.os.access", side_effect=access):
        db_storage_handler.save_mapping(platforms[0].id, roots[0].id, "a")
        with pytest.raises(DuplicateStorageMappingError):
            db_storage_handler.save_mapping(platforms[0].id, roots[0].id, "b")


def test_missing_platform_is_bounded_and_not_duplicate(tmp_path: Path):
    (tmp_path / "a").mkdir()
    with sync_session.begin() as session:
        roots, _ = add_objects(session, tmp_path, [("root", tmp_path)])
    with (
        patch("handler.filesystem.storage_resolver.os.access", side_effect=access),
        pytest.raises(MissingStoragePlatformError) as error,
    ):
        db_storage_handler.save_mapping(999999, roots[0].id, "a")
    assert "999999" in str(error.value)
    assert "SELECT" not in str(error.value)


def test_unrelated_integrity_error_is_bounded_and_not_duplicate(tmp_path: Path):
    (tmp_path / "a").mkdir()
    with sync_session.begin() as session:
        roots, platforms = add_objects(session, tmp_path, [("root", tmp_path)])
        real_flush = session.flush

        def fail_mapping_flush(*args, **kwargs):
            if any(isinstance(item, PlatformStorageMapping) for item in session.new):
                raise IntegrityError("SQL", {}, Exception("detail"))
            return real_flush(*args, **kwargs)

        with (
            patch("handler.filesystem.storage_resolver.os.access", side_effect=access),
            patch.object(session, "flush", side_effect=fail_mapping_flush),
            pytest.raises(StoragePersistenceError) as error,
        ):
            db_storage_handler.save_mapping(
                platforms[0].id, roots[0].id, "a", session=session
            )
    assert str(error.value) == "Storage mapping could not be persisted"


MAPPING_UNIQUE_KEYS = (
    "uq_platform_storage_mappings_platform_id",
    "uq_platform_storage_mappings_root_relative_path",
)


def dbapi_original(message: str, *, constraint_name=None, errno=None):
    attributes = {}
    if constraint_name is not None:
        attributes["diag"] = type(
            "Diagnostic", (), {"constraint_name": constraint_name}
        )()
    if errno is not None:
        attributes["errno"] = errno
    return type("Original", (), attributes | {"__str__": lambda self: message})()


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        *[
            (dbapi_original("hidden", constraint_name=key), True)
            for key in MAPPING_UNIQUE_KEYS
        ],
        (
            dbapi_original(
                "hidden", constraint_name="fk_platform_storage_mappings_platform_id"
            ),
            False,
        ),
        *[
            (dbapi_original(f"Duplicate entry for key '{key}'", errno=1062), True)
            for key in MAPPING_UNIQUE_KEYS
        ],
        *[
            (dbapi_original(f"Failure mentioning {key}", errno=1452), False)
            for key in MAPPING_UNIQUE_KEYS
        ],
        *[
            (dbapi_original(f"Unknown failure mentioning {key}"), False)
            for key in MAPPING_UNIQUE_KEYS
        ],
    ],
)
def test_mapping_unique_vendor_diagnostic_matrix(original, expected):
    error = IntegrityError("hidden SQL", {"secret": "parameter"}, original)
    assert db_storage_handler._is_mapping_unique_violation(error) is expected


@pytest.mark.parametrize(
    "original",
    [
        *[
            dbapi_original(f"Failure mentioning {key}", errno=1452)
            for key in MAPPING_UNIQUE_KEYS
        ],
        *[
            dbapi_original(f"Unknown failure mentioning {key}")
            for key in MAPPING_UNIQUE_KEYS
        ],
    ],
)
def test_vendor_diagnostic_negatives_are_bounded_persistence_errors(
    tmp_path: Path, original
):
    (tmp_path / "private-path").mkdir()
    with sync_session.begin() as session:
        roots, platforms = add_objects(session, tmp_path, [("root", tmp_path)])
        real_flush = session.flush

        def fail_mapping_flush(*args, **kwargs):
            if any(isinstance(item, PlatformStorageMapping) for item in session.new):
                raise IntegrityError(
                    "SELECT secret FROM mappings",
                    {"token": "private-parameter"},
                    original,
                )
            return real_flush(*args, **kwargs)

        with (
            patch("handler.filesystem.storage_resolver.os.access", side_effect=access),
            patch.object(session, "flush", side_effect=fail_mapping_flush),
            pytest.raises(StoragePersistenceError) as error,
        ):
            db_storage_handler.save_mapping(
                platforms[0].id, roots[0].id, "private-path", session=session
            )
    assert error.type is StoragePersistenceError
    assert str(error.value) == "Storage mapping could not be persisted"


def test_active_root_lock_is_ordered_before_mapping_load(tmp_path: Path):
    (tmp_path / "a").mkdir()
    with sync_session.begin() as session:
        roots, platforms = add_objects(session, tmp_path, [("root", tmp_path)])
    statements = []

    def listener(_c, _cu, statement, _p, _ctx, _many):
        statements.append(statement)

    event.listen(sync_engine, "before_cursor_execute", listener)
    try:
        with patch("handler.filesystem.storage_resolver.os.access", side_effect=access):
            db_storage_handler.save_mapping(platforms[0].id, roots[0].id, "a")
    finally:
        event.remove(sync_engine, "before_cursor_execute", listener)
    lock = next(
        sql
        for sql in statements
        if "FOR UPDATE" in sql.upper() and "FROM storage_roots" in sql
    )
    assert "ORDER BY storage_roots.id" in lock and "storage_roots.active" in lock
    mapping_lock = next(
        sql
        for sql in statements
        if "FOR UPDATE" in sql.upper() and "FROM platform_storage_mappings" in sql
    )
    assert "JOIN storage_roots" not in mapping_lock
    if sync_engine.dialect.name == "postgresql":
        assert "FOR UPDATE OF platform_storage_mappings" in mapping_lock


def test_concurrent_initial_cross_root_overlap_one_commit(tmp_path: Path):
    shared = tmp_path / "shared"
    nested = shared / "nested"
    (nested / "target").mkdir(parents=True)
    with sync_session.begin() as session:
        roots, platforms = add_objects(
            session, tmp_path, [("outer", shared), ("inner", nested)]
        )
    barrier = threading.Barrier(2)
    outcomes = []

    def attempt(platform_id, root_id, path):
        try:
            with sync_session.begin() as session:
                assert session.scalar(select(PlatformStorageMapping)) is None
                barrier.wait(timeout=5)
                db_storage_handler.save_mapping(
                    platform_id, root_id, path, session=session
                )
            outcomes.append("commit")
        except StorageMappingOverlapError:
            outcomes.append("overlap")

    threads = [
        threading.Thread(
            target=attempt, args=(platforms[0].id, roots[0].id, "nested/target")
        ),
        threading.Thread(target=attempt, args=(platforms[1].id, roots[1].id, "target")),
    ]
    access_patch = patch(
        "handler.filesystem.storage_resolver.os.access", side_effect=access
    )
    access_patch.start()
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
    finally:
        access_patch.stop()

    assert sorted(outcomes) == ["commit", "overlap"]
    with sync_session() as session:
        assert len(session.scalars(select(PlatformStorageMapping)).all()) == 1
