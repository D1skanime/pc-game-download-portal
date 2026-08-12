from __future__ import annotations

import dataclasses
import functools
import hashlib
import shutil
import time
import zipfile
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

import anyio

from config import ZIP_CACHE_PATH
from exceptions.storage_read import MappedReadError
from handler.filesystem.storage_access import DownloadCapability, OwnedReplace
from logger.logger import log

if TYPE_CHECKING:
    from handler.storage.read_context import MappingReadContext

CACHE_KEY_LENGTH = 16
SECONDS_PER_HOUR = 3600
LARGE_ZIP_THRESHOLD_BYTES = 8 * 1024 * 1024 * 1024  # 8 GB
DEFAULT_TTL_HOURS = 48
LARGE_ZIP_TTL_HOURS = 12
BULK_CACHE_MAX_ROMS = 100
BULK_NAMESPACE_PREFIX = "bulk"


@dataclasses.dataclass(frozen=True)
class ZipFileEntry:
    """Thread-safe snapshot of a RomFile's download-relevant data."""

    download_name: str
    mapping_id: int
    expected_mapping_revision: int
    logical_path: str
    file_size_bytes: int
    updated_at_epoch: float

    def __post_init__(self) -> None:
        if self.mapping_id <= 0 or self.expected_mapping_revision <= 0:
            raise ValueError("ZIP entries require positive mapping identity")
        for value in (self.download_name, self.logical_path):
            path = PurePath(value)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("ZIP entries require bounded logical paths")


@dataclasses.dataclass(frozen=True)
class AuthorizedZipSource:
    """One logical ZIP member bound to its authorized open descriptor."""

    entry: ZipFileEntry
    context: MappingReadContext
    access: DownloadCapability


def get_cache_key(
    namespace: str,
    entries: list[ZipFileEntry],
    hidden_folder: bool = False,
) -> str:
    """Deterministic cache key derived from content state."""
    parts = [
        namespace,
        str(hidden_folder),
        str(max((e.updated_at_epoch for e in entries), default=0.0)),
    ]
    for e in sorted(entries, key=lambda x: x.download_name):
        parts.append(
            ":".join(
                (
                    str(e.mapping_id),
                    str(e.expected_mapping_revision),
                    e.logical_path,
                    e.download_name,
                    str(e.file_size_bytes),
                )
            )
        )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:CACHE_KEY_LENGTH]


def get_bulk_namespace(rom_ids: list[int]) -> str:
    """Deterministic namespace for bulk downloads, hashed to avoid ENAMETOOLONG."""
    id_str = "-".join(str(i) for i in sorted(rom_ids))
    id_hash = hashlib.sha256(id_str.encode()).hexdigest()[:CACHE_KEY_LENGTH]
    return f"{BULK_NAMESPACE_PREFIX}-{id_hash}"


def _cache_dir(namespace: str) -> Path:
    return Path(ZIP_CACHE_PATH) / namespace


def _cache_file(namespace: str, cache_key: str) -> Path:
    return _cache_dir(namespace) / f"{cache_key}.zip"


def get_cached_zip(namespace: str, cache_key: str) -> Path | None:
    """Return the cached ZIP path if it exists on disk, else None."""
    path = _cache_file(namespace, cache_key)
    return path if path.exists() else None


def _ensure_zipfile_writable() -> None:
    """Restore ``zipfile._get_compressor`` to a writable signature.

    ``zipfile_inflate64`` (imported in ``handler/filesystem/roms_handler.py``
    to support Enhanced Deflate) replaces ``zipfile._get_compressor`` with a
    wrapper that only accepts ``compress_type``. CPython 3.13 calls it with
    ``(compress_type, compresslevel)``, so ``ZipFile.write()``/``writestr()``
    raise ``TypeError``. Wrap it once with a signature-compatible shim that
    drops the extra arg, matching inflate64's own behavior (it already ignores
    ``compresslevel``). Idempotent and safe to call from any thread.
    """
    current = zipfile._get_compressor  # type: ignore[attr-defined]
    if getattr(current, "_romm_compresslevel_safe", False):
        return

    # Probe with two args: the stdlib accepts them, inflate64's wrapper does not.
    try:
        current(zipfile.ZIP_STORED, None)
        return
    except TypeError:
        pass

    @functools.wraps(current)
    def _get_compressor(compress_type, compresslevel=None):
        return current(compress_type)

    _get_compressor._romm_compresslevel_safe = True  # type: ignore[attr-defined]
    zipfile._get_compressor = _get_compressor  # type: ignore[attr-defined,assignment]


def build_cached_zip(
    sources: list[AuthorizedZipSource],
    m3u_content: bytes | None,
    m3u_filename: str | None,
    destination: OwnedReplace,
) -> None:
    """Build a ZIP from authorized descriptors into an owned replacement."""
    if not isinstance(destination, OwnedReplace) or not all(
        isinstance(source.access, DownloadCapability) for source in sources
    ):
        raise TypeError("ZIP building requires download inputs and owned output")
    with destination.binary_file() as output:
        _ensure_zipfile_writable()
        with zipfile.ZipFile(output, "w") as zf:
            for source in sources:
                source.context.boundary()
                with source.access.binary_file() as input_file, zf.open(
                    source.entry.download_name, "w"
                ) as member:
                    shutil.copyfileobj(input_file, member)
                source.context.boundary()
            if m3u_content is not None and m3u_filename is not None:
                zf.writestr(m3u_filename, m3u_content)


def get_zip_redirect_path(namespace: str, cache_key: str) -> Path:
    """Return the nginx-internal URL path for the cached ZIP."""
    return Path(f"/cache/zips/{namespace}/{cache_key}.zip")


async def resolve_cached_zip(
    namespace: str,
    sources: list[AuthorizedZipSource],
    destination: OwnedReplace,
    *,
    hidden_folder: bool = False,
    m3u_content: bytes | None = None,
    m3u_filename: str | None = None,
    log_label: str,
) -> Path | None:
    """Return the nginx redirect path for a cached ZIP, building it on demand.

    Returns ``None`` when there is nothing to cache or generation fails.
    Mapping invalidation is never converted into a generation fallback.
    """
    if not sources:
        return None

    entries = [source.entry for source in sources]
    cache_key = get_cache_key(namespace, entries, hidden_folder)

    try:
        await anyio.to_thread.run_sync(
            functools.partial(
                build_cached_zip,
                sources=sources,
                m3u_content=m3u_content,
                m3u_filename=m3u_filename,
                destination=destination,
            )
        )
    except MappedReadError:
        raise
    except Exception as e:
        log.warning(f"Failed to build cached ZIP for {log_label}: {e}")
        return None

    return get_zip_redirect_path(namespace, cache_key)


def get_ttl_hours(size_bytes: int) -> int:
    """Return the appropriate TTL based on ZIP size."""
    if size_bytes > LARGE_ZIP_THRESHOLD_BYTES:
        return LARGE_ZIP_TTL_HOURS
    return DEFAULT_TTL_HOURS


def cleanup_stale_zips() -> int:
    """Remove cached ZIPs that have exceeded their TTL.

    Files larger than LARGE_ZIP_THRESHOLD_BYTES use LARGE_ZIP_TTL_HOURS,
    all others use DEFAULT_TTL_HOURS.
    """
    cache_root = Path(ZIP_CACHE_PATH)
    if not cache_root.exists():
        return 0

    now = time.time()
    deleted = 0

    for ns_dir in cache_root.iterdir():
        if not ns_dir.is_dir():
            continue
        for zip_file in ns_dir.glob("*.zip"):
            stat = zip_file.stat()
            cutoff = now - (get_ttl_hours(stat.st_size) * SECONDS_PER_HOUR)
            if stat.st_mtime < cutoff:
                zip_file.unlink()
                deleted += 1
        if ns_dir.exists() and not any(ns_dir.iterdir()):
            ns_dir.rmdir()

    return deleted
