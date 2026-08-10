from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from handler.filesystem.storage_access import open_owned_access, open_storage_access
from handler.filesystem.storage_composition import (
    StorageCompositionConfig,
    build_storage_composition,
)
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation
from utils.rom_patcher.patcher import apply_patch


@pytest.mark.asyncio
async def test_apply_patch_uses_only_inherited_capability_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = tmp_path / "library"
    library.mkdir()
    (library / "game.bin").write_bytes(b"game")
    owned = {kind: tmp_path / kind.value for kind in OwnedStorageKind}
    for path in owned.values():
        path.mkdir()
    (owned[OwnedStorageKind.TEMP] / "fix.ips").write_bytes(b"patch")
    composition = build_storage_composition(StorageCompositionConfig(library, owned))
    process = AsyncMock()
    process.communicate.return_value = (b'{"validated": true}', b"")
    process.returncode = 0

    async def create_process(*argv: str, **kwargs: object):
        assert all(str(value).startswith("/proc/self/fd/") for value in argv[2:])
        assert set(kwargs["pass_fds"]) == {
            int(value.rsplit("/", 1)[1]) for value in argv[2:]
        }
        Path(argv[-1]).write_bytes(b"patched")
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", create_process)
    with (
        open_storage_access(
            composition.legacy_external, StorageOperation.READ, "game.bin"
        ) as rom,
        open_owned_access(
            composition.owned[OwnedStorageKind.TEMP],
            StorageOperation.READ,
            "fix.ips",
        ) as patch,
        open_owned_access(
            composition.owned[OwnedStorageKind.TEMP],
            StorageOperation.CREATE,
            "out.bin",
        ) as output,
    ):
        assert await apply_patch(rom, patch, output) is True


@pytest.mark.asyncio
async def test_apply_patch_rejects_raw_paths() -> None:
    with pytest.raises(TypeError):
        await apply_patch(
            Path("rom"), Path("patch"), Path("output")  # type: ignore[arg-type]
        )
