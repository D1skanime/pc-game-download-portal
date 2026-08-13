from pathlib import Path
from types import SimpleNamespace

import pytest

from exceptions.storage_exceptions import (
    InactiveStorageRootError,
    InvalidRelativePathError,
    MissingPlatformStorageMappingError,
    MissingStorageRootError,
    MissingStorageTargetError,
    NonDirectoryStorageTargetError,
    SafeStorageFilesystemError,
    StaleStorageMappingVersionError,
    StorageEscapeError,
    StoragePolicyDenied,
    StorageResolutionError,
    UnreadableStorageTargetError,
    UnsafeSymlinkError,
    UnsafeWritableRootError,
)
from exceptions.storage_read import (
    MappedReadDeniedError,
    MissingMappedContentError,
    StaleMappedReadError,
    UnreachableMappedStorageError,
)
from handler.filesystem.storage_policy import StorageOperation
from handler.storage import read_context
from handler.storage.read_context import MappingReadContext


class MappingRepository:
    def __init__(self, mapping):
        self.mapping = mapping

    def get_mapping(self, mapping_id: int):
        assert mapping_id == self.mapping.id
        return self.mapping


def mapping(root: Path, *, active: bool = True, version: int = 7):
    return SimpleNamespace(
        id=41,
        version=version,
        active=active,
        relative_path="console",
        storage_root_id=3,
        storage_root=SimpleNamespace(
            id=3,
            container_path=str(root),
            active=True,
            mode="external_read_only",
        ),
    )


def test_context_rejects_inactive_or_changed_mapping_before_open(tmp_path: Path):
    root = tmp_path / "external"
    (root / "console").mkdir(parents=True)
    for actual in (mapping(root, active=False), mapping(root, version=8)):
        context = MappingReadContext(41, 7, repository=MappingRepository(actual))
        with pytest.raises(StaleMappedReadError) as error:
            context.open(StorageOperation.SCAN)
        assert error.value.mapping_id == 41
        assert error.value.expected_revision == 7
        assert str(root) not in repr(error.value)


def test_context_rejects_symlink_before_issuing_handle(tmp_path: Path):
    root = tmp_path / "external"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "console").symlink_to(outside, target_is_directory=True)
    context = MappingReadContext(41, 7, repository=MappingRepository(mapping(root)))
    with pytest.raises(Exception):
        context.open(StorageOperation.SCAN)


@pytest.mark.parametrize(
    ("failure", "expected_error", "code", "safe_state"),
    (
        (
            InvalidRelativePathError(),
            MissingMappedContentError,
            "missing_storage_content",
            "missing",
        ),
        (
            MissingStorageTargetError(),
            MissingMappedContentError,
            "missing_storage_content",
            "missing",
        ),
        (
            NonDirectoryStorageTargetError(),
            MissingMappedContentError,
            "missing_storage_content",
            "missing",
        ),
        (
            UnsafeSymlinkError(),
            MissingMappedContentError,
            "missing_storage_content",
            "missing",
        ),
        (
            StorageEscapeError(),
            MissingMappedContentError,
            "missing_storage_content",
            "missing",
        ),
        (
            MissingStorageRootError(3),
            UnreachableMappedStorageError,
            "unreachable_storage",
            "unreachable",
        ),
        (
            InactiveStorageRootError(3),
            UnreachableMappedStorageError,
            "unreachable_storage",
            "unreachable",
        ),
        (
            UnreadableStorageTargetError(),
            UnreachableMappedStorageError,
            "unreachable_storage",
            "unreachable",
        ),
        (
            UnsafeWritableRootError(3),
            UnreachableMappedStorageError,
            "unreachable_storage",
            "unreachable",
        ),
        (
            SafeStorageFilesystemError(3),
            UnreachableMappedStorageError,
            "unreachable_storage",
            "unreachable",
        ),
        (
            StorageResolutionError("/secret/source raw os error"),
            UnreachableMappedStorageError,
            "unreachable_storage",
            "unreachable",
        ),
        (
            StoragePolicyDenied("stream", "external", "/secret/source"),
            MappedReadDeniedError,
            "mapped_storage_access_denied",
            "denied",
        ),
    ),
)
def test_context_translates_expected_resolution_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: StorageResolutionError,
    expected_error: type[StorageResolutionError],
    code: str,
    safe_state: str,
) -> None:
    root = tmp_path / "external"
    (root / "console").mkdir(parents=True)
    context = MappingReadContext(41, 7, repository=MappingRepository(mapping(root)))

    monkeypatch.setattr(
        read_context,
        "get_storage_root_health_snapshot",
        lambda _root: SimpleNamespace(reachable=True, readable=True, non_writable=True),
    )

    def fail_resolution(*_args):
        raise failure

    if isinstance(failure, StoragePolicyDenied):
        monkeypatch.setattr(
            read_context, "resolve_directory", lambda *_args: root / "console"
        )
        monkeypatch.setattr(
            read_context,
            "_create_external_descriptor",
            lambda *_args, **_kwargs: object(),
        )
        monkeypatch.setattr(read_context, "open_storage_access", fail_resolution)
    else:
        monkeypatch.setattr(read_context, "resolve_directory", fail_resolution)
    with pytest.raises(expected_error) as error:
        context.open(StorageOperation.STREAM, "game.bin")

    assert error.value.code == code
    assert error.value.safe_state == safe_state
    assert str(root) not in str(error.value)
    assert "/secret" not in str(error.value)


@pytest.mark.parametrize(
    "failure",
    (MissingPlatformStorageMappingError(41), StaleStorageMappingVersionError(41, 8)),
)
def test_context_translates_mapping_identity_failures(
    failure: StorageResolutionError,
) -> None:
    class FailingRepository:
        def get_mapping(self, mapping_id: int):
            raise failure

    with pytest.raises(StaleMappedReadError):
        MappingReadContext(41, 7, repository=FailingRepository()).open(
            StorageOperation.SCAN
        )


def test_first_use_mark_precedes_bounded_resolution_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "external"
    (root / "console").mkdir(parents=True)
    context = MappingReadContext(41, 7, repository=MappingRepository(mapping(root)))
    marks: list[str] = []
    monkeypatch.setattr(
        read_context,
        "get_storage_root_health_snapshot",
        lambda _root: SimpleNamespace(reachable=True, readable=True, non_writable=True),
    )
    monkeypatch.setattr(
        MappingReadContext,
        "_mark_first_use",
        lambda _self, operation: marks.append(operation),
    )

    def fail_after_mark(*_args):
        raise InvalidRelativePathError()

    monkeypatch.setattr(read_context, "resolve_directory", fail_after_mark)
    with pytest.raises(MissingMappedContentError) as error:
        context.open(StorageOperation.STREAM, "game.bin")

    assert marks == ["stream"]
    assert error.value.code == "missing_storage_content"
    assert error.value.safe_state == "missing"
