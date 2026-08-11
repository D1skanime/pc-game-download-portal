from pathlib import Path
from types import SimpleNamespace

import pytest

from exceptions.storage_read import StaleMappedReadError
from handler.filesystem.storage_policy import StorageOperation
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
