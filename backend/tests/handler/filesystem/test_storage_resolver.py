import builtins
import os
import shutil
import stat
import tempfile
import unicodedata
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from exceptions.storage_exceptions import (
    InactiveStorageRootError,
    InvalidRelativePathError,
    MissingStorageRootError,
    MissingStorageTargetError,
    NonDirectoryStorageTargetError,
    StorageEscapeError,
    UnreadableStorageTargetError,
    UnsafeSymlinkError,
    UnsafeWritableRootError,
)
from handler.filesystem.storage_resolver import (
    check_storage_root_health,
    normalize_relative_path,
    resolve_directory,
    resolve_storage_root,
)
from models.storage import EXTERNAL_READ_ONLY_MODE, StorageRoot


@pytest.mark.parametrize(
    ("raw", "case"),
    [
        ("", "empty mapping path"),
        ("/games", "POSIX absolute path"),
        ("games/", "trailing separator"),
        ("games//arcade", "repeated separator"),
        ("games/./arcade", "dot segment"),
        (".", "single dot segment"),
        ("..", "parent traversal"),
        ("games/../arcade", "nested parent traversal"),
        ("../../etc", "repeated parent traversal"),
        ("C:/Games", "Windows drive path with forward separators"),
        (r"C:\Games", "Windows drive path"),
        ("C:Games", "Windows drive-relative path"),
        (r"\\server\share", "UNC path"),
        (r"\\?\C:\Games", "Windows device path"),
        (r"games\arcade", "backslash separator"),
        ("games\x00arcade", "NUL control"),
        ("games\x1farcade", "C0 control"),
        ("games\x7farcade", "DEL control"),
    ],
)
def test_normalize_rejects_unsafe_lexical_forms(raw: str, case: str) -> None:
    with pytest.raises(InvalidRelativePathError):
        normalize_relative_path(raw)


def test_normalize_intenal_root_contract_allows_empty_path() -> None:
    assert normalize_relative_path("", allow_root=True) == ""


@pytest.mark.parametrize(
    "raw",
    [
        "Nintendo Switch",
        "Sony.PlayStation-2",
        "M\u00fcnchen/\u00dcber Spiele",
        "\u65e5\u672c\u8a9e/\u30b2\u30fc\u30e0",
        "nested/archive.with dots/game-set",
        "a" * 255,
    ],
)
def test_valid_names_are_preserved_exactly(raw: str) -> None:
    assert normalize_relative_path(raw) == raw


def test_valid_names_preserve_composed_and_decomposed_unicode() -> None:
    composed = "Caf\u00e9"
    decomposed = unicodedata.normalize("NFD", composed)

    assert composed != decomposed
    assert normalize_relative_path(composed) == composed
    assert normalize_relative_path(decomposed) == decomposed


@given(
    st.text(
        alphabet=st.characters(
            blacklist_categories=("Cc", "Cs"),
            blacklist_characters="/\\",
        ),
        min_size=1,
        max_size=80,
    ).filter(lambda value: value not in {".", ".."})
)
def test_valid_names_are_not_case_folded_or_unicode_normalized(name: str) -> None:
    assert normalize_relative_path(name) == name


def test_safe_error_omits_unrelated_absolute_roots() -> None:
    unrelated_root = "/mnt/private/archive"

    with pytest.raises(InvalidRelativePathError) as exc_info:
        normalize_relative_path("../escape")

    assert unrelated_root not in str(exc_info.value)
    assert len(str(exc_info.value)) <= 200


def _root(path: Path, *, active: bool = True) -> StorageRoot:
    root = StorageRoot(name="Archive", container_path=str(path), mode=EXTERNAL_READ_ONLY_MODE, active=active)
    root.id = 17
    return root


def _manifest(path: Path) -> tuple[tuple[object, ...], ...]:
    entries = []
    for item in sorted(path.rglob("*"), key=lambda value: str(value.relative_to(path))):
        metadata = item.lstat()
        entries.append((str(item.relative_to(path)), stat.S_IFMT(metadata.st_mode), metadata.st_size, stat.S_IMODE(metadata.st_mode), metadata.st_mtime_ns, os.readlink(item) if item.is_symlink() else None))
    return tuple(entries)


def _permission_observer(path: object, mode: int) -> bool:
    return not bool(mode & os.W_OK)


def test_health_records_bounded_metadata_without_mutating_tree(tmp_path: Path) -> None:
    target = tmp_path / "Nintendo Switch"
    target.mkdir()
    (target / "game.txt").write_text("archive", encoding="utf-8")
    root = _root(tmp_path)
    before = _manifest(tmp_path)
    with patch("handler.filesystem.storage_resolver.os.access", _permission_observer):
        health = check_storage_root_health(root)
    assert (health.reachable, health.readable, health.non_writable) == (True, True, True)
    assert health.safe_error is None
    assert health.last_checked_at is not None
    assert _manifest(tmp_path) == before


@pytest.mark.parametrize("operation", ["health", "root", "target"])
def test_storage_observation_has_no_mutation_primitives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str) -> None:
    (tmp_path / "games").mkdir()
    root = _root(tmp_path)
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("storage observation attempted a mutation")
    original_open = builtins.open
    def guarded_open(file: object, mode: str = "r", *args: object, **kwargs: object):
        if any(flag in mode for flag in "wax+"):
            forbidden()
        return original_open(file, mode, *args, **kwargs)
    for owner, name in [(Path, "mkdir"), (Path, "unlink"), (Path, "rename"), (Path, "replace"), (shutil, "copy"), (shutil, "copy2"), (shutil, "copytree"), (shutil, "move"), (tempfile, "NamedTemporaryFile"), (tempfile, "TemporaryFile")]:
        monkeypatch.setattr(owner, name, forbidden)
    monkeypatch.setattr(builtins, "open", guarded_open)
    with patch("handler.filesystem.storage_resolver.os.access", _permission_observer):
        {"health": check_storage_root_health, "root": resolve_storage_root, "target": lambda value: resolve_directory(value, "games")}[operation](root)


def test_health_reports_missing_unreadable_and_writable_roots(tmp_path: Path) -> None:
    missing = _root(tmp_path / "missing")
    check_storage_root_health(missing)
    assert (missing.reachable, missing.readable, missing.non_writable) == (False, False, None)
    assert missing.safe_error == "Storage root was not found"
    unreadable = _root(tmp_path)
    with patch("handler.filesystem.storage_resolver.os.access", return_value=False):
        check_storage_root_health(unreadable)
    assert unreadable.reachable is True
    assert unreadable.readable is False
    assert unreadable.safe_error == "Storage root is not readable"
    writable = _root(tmp_path)
    with patch("handler.filesystem.storage_resolver.os.access", return_value=True):
        check_storage_root_health(writable)
    assert writable.non_writable is False
    assert writable.safe_error == "Storage root 17 is writable"


def test_resolution_requires_existing_active_non_writable_root(tmp_path: Path) -> None:
    with pytest.raises(MissingStorageRootError):
        resolve_storage_root(_root(tmp_path / "missing"))
    with pytest.raises(InactiveStorageRootError):
        resolve_storage_root(_root(tmp_path, active=False))
    with patch("handler.filesystem.storage_resolver.os.access", return_value=True):
        with pytest.raises(UnsafeWritableRootError):
            resolve_storage_root(_root(tmp_path))


def test_internal_root_resolution_is_the_only_empty_path_contract(tmp_path: Path) -> None:
    root = _root(tmp_path)
    with patch("handler.filesystem.storage_resolver.os.access", _permission_observer):
        assert resolve_storage_root(root) == tmp_path.resolve()
        with pytest.raises(InvalidRelativePathError):
            resolve_directory(root, "")


def test_target_must_exist_be_a_readable_directory(tmp_path: Path) -> None:
    (tmp_path / "file").write_text("content", encoding="utf-8")
    (tmp_path / "directory").mkdir()
    root = _root(tmp_path)
    with patch("handler.filesystem.storage_resolver.os.access", _permission_observer):
        with pytest.raises(MissingStorageTargetError):
            resolve_directory(root, "missing")
        with pytest.raises(NonDirectoryStorageTargetError):
            resolve_directory(root, "file")
    def unreadable_target(path: object, mode: int) -> bool:
        return Path(path).name != "directory" if mode & os.R_OK else False
    with patch("handler.filesystem.storage_resolver.os.access", unreadable_target):
        with pytest.raises(UnreadableStorageTargetError):
            resolve_directory(root, "directory")


def test_nested_target_resolves_inside_canonical_root(tmp_path: Path) -> None:
    target = tmp_path / "Sony.PlayStation-2" / "M\u00fcnchen"
    target.mkdir(parents=True)
    with patch("handler.filesystem.storage_resolver.os.access", _permission_observer):
        assert resolve_directory(_root(tmp_path), "Sony.PlayStation-2/M\u00fcnchen") == target.resolve()


@pytest.mark.parametrize(("position", "link_target"), [("root", "absolute-in-root"), ("root", "relative-in-root"), ("first", "absolute-in-root"), ("first", "relative-escape"), ("middle", "relative-in-root"), ("leaf", "absolute-escape"), ("leaf", "broken"), ("leaf", "loop")])
def test_symlink_at_every_component_and_target_form_is_rejected(tmp_path: Path, position: str, link_target: str) -> None:
    real_root = tmp_path / "library"
    real_target = real_root / "first" / "middle" / "leaf"
    real_target.mkdir(parents=True)
    outside = tmp_path / "library-old"
    outside.mkdir()
    root_path = real_root
    relative = "first/middle/leaf"
    if position == "root":
        root_path = tmp_path / "configured"
        root_path.symlink_to(real_root if link_target == "absolute-in-root" else Path("library"), target_is_directory=True)
    else:
        link = {"first": real_root / "first", "middle": real_root / "first" / "middle", "leaf": real_target}[position]
        if link.is_dir():
            shutil.rmtree(link)
        destinations = {"absolute-in-root": real_target, "relative-in-root": Path("../middle/leaf"), "relative-escape": Path("../../library-old"), "absolute-escape": outside, "broken": Path("does-not-exist"), "loop": Path("leaf")}
        link.symlink_to(destinations[link_target], target_is_directory=True)
    with patch("handler.filesystem.storage_resolver.os.access", _permission_observer):
        with pytest.raises(UnsafeSymlinkError):
            resolve_directory(_root(root_path), relative)


def test_canonical_sibling_prefix_is_not_containment(tmp_path: Path) -> None:
    root_path = tmp_path / "library"
    root_path.mkdir()
    sibling = tmp_path / "library-old"
    sibling.mkdir()
    with patch("handler.filesystem.storage_resolver.os.access", _permission_observer), patch("handler.filesystem.storage_resolver._strict_resolve_target", return_value=sibling.resolve()):
        with pytest.raises(StorageEscapeError):
            resolve_directory(_root(root_path), "games")
