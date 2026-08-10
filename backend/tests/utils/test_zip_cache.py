from contextlib import ExitStack
from pathlib import Path
from zipfile import ZipFile

import pytest

from handler.filesystem.storage_access import open_owned_access, open_storage_access
from handler.filesystem.storage_composition import (
    StorageCompositionConfig,
    build_storage_composition,
)
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation
from utils.zip_cache import ZipFileEntry, build_cached_zip, get_cache_key


def _composition(tmp_path: Path):
    library = tmp_path / "library"
    library.mkdir()
    owned = {kind: tmp_path / kind.value for kind in OwnedStorageKind}
    for path in owned.values():
        path.mkdir()
    return build_storage_composition(StorageCompositionConfig(library, owned))


def test_cache_key_is_order_independent() -> None:
    first = ZipFileEntry("a.bin", "a.bin", 1, 1.0)
    second = ZipFileEntry("b.bin", "b.bin", 2, 1.0)
    assert get_cache_key("rom", [first, second]) == get_cache_key(
        "rom", [second, first]
    )


def test_build_cached_zip_copies_download_capabilities_to_owned_output(
    tmp_path: Path,
) -> None:
    composition = _composition(tmp_path)
    library = Path(str(composition.legacy_external._root_path))
    (library / "a.bin").write_bytes(b"a")
    (library / "b.bin").write_bytes(b"bb")
    entries = [
        ZipFileEntry("one.bin", "a.bin", 1, 1.0),
        ZipFileEntry("two.bin", "b.bin", 2, 1.0),
    ]
    with ExitStack() as stack:
        sources = [
            stack.enter_context(
                open_storage_access(
                    composition.legacy_external,
                    StorageOperation.DOWNLOAD,
                    entry.full_path,
                )
            )
            for entry in entries
        ]
        output = stack.enter_context(
            open_owned_access(
                composition.owned[OwnedStorageKind.CACHE],
                StorageOperation.OVERWRITE,
                "archive.zip",
            )
        )
        build_cached_zip(entries, sources, b"one.bin\n", "list.m3u", output)

    with ZipFile(tmp_path / OwnedStorageKind.CACHE.value / "archive.zip") as archive:
        assert archive.read("one.bin") == b"a"
        assert archive.read("two.bin") == b"bb"
        assert archive.read("list.m3u") == b"one.bin\n"


def test_build_cached_zip_rejects_raw_paths(tmp_path: Path) -> None:
    entry = ZipFileEntry("one.bin", "a.bin", 1, 1.0)
    with pytest.raises(TypeError):
        build_cached_zip([entry], [tmp_path / "a.bin"], None, None, tmp_path / "x.zip")  # type: ignore[list-item,arg-type]
