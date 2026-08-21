import asyncio
import errno
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from exceptions.storage_exceptions import StorageResolutionError
from handler.filesystem.storage_access import (
    OwnedCreate,
    OwnedRead,
    ReadCapability,
    open_owned_access,
    open_storage_access,
)
from handler.filesystem.storage_composition import (
    StorageCompositionConfig,
    build_storage_composition,
)
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation
from utils.rom_patcher.patcher import PatcherError, apply_patch


@contextmanager
def _patch_capabilities(
    tmp_path: Path, output_name: str = "out.bin"
) -> Iterator[tuple[ReadCapability, OwnedRead, OwnedCreate, Path]]:
    library = tmp_path / "library"
    library.mkdir()
    (library / "game.bin").write_bytes(b"game")
    owned = {kind: tmp_path / kind.value for kind in OwnedStorageKind}
    for path in owned.values():
        path.mkdir()
    (owned[OwnedStorageKind.TEMP] / "fix.ips").write_bytes(b"patch")
    output_path = owned[OwnedStorageKind.TEMP] / output_name
    composition = build_storage_composition(StorageCompositionConfig(library, owned))
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
            output_name,
        ) as output,
    ):
        assert isinstance(rom, ReadCapability)
        assert isinstance(patch, OwnedRead)
        assert isinstance(output, OwnedCreate)
        yield rom, patch, output, output_path


def _process(
    *,
    stdout: bytes = b'{"validated": true}',
    stderr: bytes = b"",
    returncode: int = 0,
) -> MagicMock:
    process = MagicMock()
    process.communicate = AsyncMock(return_value=(stdout, stderr))
    process.wait = AsyncMock(return_value=returncode)
    process.returncode = returncode
    return process


@pytest.mark.asyncio
async def test_apply_patch_uses_only_inherited_capability_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = _process()

    async def create_process(*argv: str, **kwargs: object):
        assert all(str(value).startswith("/proc/self/fd/") for value in argv[2:])
        assert set(kwargs["pass_fds"]) == {
            int(value.rsplit("/", 1)[1]) for value in argv[2:]
        }
        assert not output_path.exists()
        os.write(int(argv[-1].rsplit("/", 1)[1]), b"patched")
        assert not output_path.exists()
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", create_process)
    with _patch_capabilities(tmp_path) as (rom, patch, output, output_path):
        assert await apply_patch(rom, patch, output) is True
        assert output_path.read_bytes() == b"patched"


@pytest.mark.asyncio
async def test_apply_patch_failure_never_publishes_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = _process(stderr=b'{"error": "bad patch"}', returncode=2)

    async def create_process(*argv: str, **_kwargs: object):
        os.write(int(argv[-1].rsplit("/", 1)[1]), b"partial")
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", create_process)
    with _patch_capabilities(tmp_path) as (rom, patch, output, output_path):
        with pytest.raises(PatcherError, match="bad patch"):
            await apply_patch(rom, patch, output)
        assert not output_path.exists()
        assert tuple(output_path.parent.glob(f".{output_path.name}.*.tmp")) == ()


@pytest.mark.asyncio
async def test_apply_patch_timeout_kills_writer_without_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = _process()
    process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)

    async def create_process(*argv: str, **_kwargs: object):
        os.write(int(argv[-1].rsplit("/", 1)[1]), b"partial")
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", create_process)
    with _patch_capabilities(tmp_path) as (rom, patch, output, output_path):
        with pytest.raises(PatcherError, match="timed out"):
            await apply_patch(rom, patch, output)
        process.kill.assert_called_once_with()
        process.wait.assert_awaited_once_with()
        assert not output_path.exists()
        assert tuple(output_path.parent.glob(f".{output_path.name}.*.tmp")) == ()


@pytest.mark.asyncio
async def test_apply_patch_collision_preserves_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = _process()
    called = False

    async def create_process(*argv: str, **_kwargs: object):
        nonlocal called
        called = True
        os.write(int(argv[-1].rsplit("/", 1)[1]), b"replacement")
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", create_process)
    with _patch_capabilities(tmp_path) as (rom, patch, output, output_path):
        output_path.write_bytes(b"existing")
        with pytest.raises(StorageResolutionError):
            await apply_patch(rom, patch, output)
        assert called
        assert output_path.read_bytes() == b"existing"
        assert tuple(output_path.parent.glob(f".{output_path.name}.*.tmp")) == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["close", "fsync"])
async def test_apply_patch_context_finalization_failure_cleans_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    process = _process()
    staged: set[int] = set()
    real_open = os.open
    real_close = os.close
    real_fsync = os.fsync
    failed = False

    def tracking_open(path, flags, *args, **kwargs):
        descriptor = real_open(path, flags, *args, **kwargs)
        if isinstance(path, str) and path.startswith(".out.bin."):
            staged.add(descriptor)
        return descriptor

    def failing_close(descriptor: int) -> None:
        nonlocal failed
        if failure == "close" and descriptor in staged and not failed:
            failed = True
            real_close(descriptor)
            raise OSError(errno.EIO, "simulated close failure")
        real_close(descriptor)

    def failing_fsync(descriptor: int) -> None:
        nonlocal failed
        if failure == "fsync" and descriptor in staged and not failed:
            failed = True
            raise OSError(errno.EIO, "simulated fsync failure")
        real_fsync(descriptor)

    async def create_process(*argv: str, **_kwargs: object):
        os.write(int(argv[-1].rsplit("/", 1)[1]), b"patched")
        return process

    monkeypatch.setattr("handler.filesystem.storage_access.os.open", tracking_open)
    monkeypatch.setattr("handler.filesystem.storage_access.os.close", failing_close)
    monkeypatch.setattr("handler.filesystem.storage_access.os.fsync", failing_fsync)
    monkeypatch.setattr("asyncio.create_subprocess_exec", create_process)
    with _patch_capabilities(tmp_path) as (rom, patch, output, output_path):
        with pytest.raises(StorageResolutionError):
            await apply_patch(rom, patch, output)
        assert failed
        assert not output_path.exists()
        assert tuple(output_path.parent.glob(f".{output_path.name}.*.tmp")) == ()


@pytest.mark.asyncio
async def test_apply_patch_rejects_raw_paths() -> None:
    with pytest.raises(TypeError):
        await apply_patch(
            Path("rom"), Path("patch"), Path("output")  # type: ignore[arg-type]
        )
