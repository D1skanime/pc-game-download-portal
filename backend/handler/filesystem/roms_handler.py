import asyncio
import binascii
import fnmatch
import hashlib
import os
import re
import stat
import zipfile
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, TypedDict

from anyio import Path as AnyioPath
from PIL import Image, UnidentifiedImageError

from config import DOWNLOAD_MANIFEST_TRANSFER_MAX_CONCURRENCY
from config.config_manager import (
    DEFAULT_EXCLUDED_EXTENSIONS,
    DEFAULT_EXCLUDED_FILES,
)
from config.config_manager import config_manager as cm
from exceptions.fs_exceptions import (
    RomAlreadyExistsException,
    RomsNotFoundException,
)
from handler.metadata.base_handler import UniversalPlatformSlug as UPS
from logger.logger import log
from models.download_manifest import DownloadManifestMember
from models.platform import Platform
from models.rom import (
    Rom,
    RomComponent,
    RomComponentKind,
    RomComponentManifestMember,
    RomFile,
    RomFileCategory,
    TrackMeta,
)
from utils.archives import (
    ArchiveReadError,
    detect_mime_type,
    extract_chd_hash,
    is_chd_file,
    process_7z_file,
    read_7z_archive_files,
    read_basic_file,
    read_bz2_file,
    read_gz_file,
    read_rar_archive_files,
    read_tar_archive_files,
    read_tar_file,
    read_zip_archive_files,
    read_zip_file,
)
from utils.filesystem import iter_files
from utils.hashing import crc32_to_hex
from utils.rate_limiter import ConcurrencyLimiter

from .base_handler import (
    LANGUAGES_BY_SHORTCODE,
    LANGUAGES_NAME_KEYS,
    REGIONS_BY_SHORTCODE,
    REGIONS_NAME_KEYS,
    ExternalFSHandler,
)
from .storage_policy import ExternalStorageDescriptor, StorageOperation

if TYPE_CHECKING:
    from handler.storage.read_context import MappingReadContext


# PICO-8 cartridges are often stored as PNG files
PICO8_CARTRIDGE_EXTENSION = ".p8.png"
PC_LOCAL_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp"})
PC_LOCAL_IMAGE_FORMATS = {
    "PNG": "png",
    "JPEG": "jpg",
    "WEBP": "webp",
}


NON_HASHABLE_PLATFORMS = frozenset(
    (
        UPS.AMAZON_ALEXA,
        UPS.AMAZON_FIRE_TV,
        UPS.ANDROID,
        UPS.GEAR_VR,
        UPS.IOS,
        UPS.IPAD,
        UPS.LINUX,
        UPS.MAC,
        UPS.META_QUEST_2,
        UPS.META_QUEST_3,
        UPS.OCULUS_GO,
        UPS.OCULUS_QUEST,
        UPS.OCULUS_RIFT,
        UPS.PS3,
        UPS.PS4,
        UPS.PS5,
        UPS.PSVR,
        UPS.PSVR2,
        UPS.SERIES_X_S,
        UPS.SWITCH,
        UPS.SWITCH_2,
        UPS.WIIU,
        UPS.WIN,
        UPS.XBOX360,
        UPS.XBOXONE,
        UPS.SERIES_X_S,
    )
)


class FSRom(TypedDict):
    fs_name: str
    flat: bool
    nested: bool
    files: list[RomFile]
    crc_hash: str
    md5_hash: str
    sha1_hash: str
    ra_hash: str


class FileHash(TypedDict):
    crc_hash: str
    md5_hash: str
    sha1_hash: str
    chd_sha1_hash: str


def category_matches(category: str, path_parts: list[str]):
    return category in path_parts or f"{category}s" in path_parts


DEFAULT_CRC_C = 0
DEFAULT_MD5_H_DIGEST = hashlib.md5(usedforsecurity=False).digest()
DEFAULT_SHA1_H_DIGEST = hashlib.sha1(usedforsecurity=False).digest()

ARCHIVE_READERS = {
    ".zip": read_zip_archive_files,
    ".tar": read_tar_archive_files,
    ".tar.gz": read_tar_archive_files,
    ".tgz": read_tar_archive_files,
    ".tar.bz2": read_tar_archive_files,
    ".tbz2": read_tar_archive_files,
    ".tar.xz": read_tar_archive_files,
    ".txz": read_tar_archive_files,
    ".7z": read_7z_archive_files,
    ".rar": read_rar_archive_files,
}

PC_COMPONENT_LAYOUTS = {
    "base": RomComponentKind.BASE,
    "update": RomComponentKind.UPDATE,
    "dlc": RomComponentKind.DLC,
    "hotfix": RomComponentKind.HOTFIX,
    "language-pack": RomComponentKind.LANGUAGE_PACK,
    "extra": RomComponentKind.EXTRA,
}


def parse_pc_component_layout(relative_path: str) -> RomComponentKind:
    """Classify only exact, configured PC component directory names.

    Layout inference is intentionally constrained to the top-level component
    directory. Unknown and nested paths remain unresolved instead of granting
    meaning to weak directory names.
    """
    path = PurePosixPath(relative_path)
    if path.is_absolute() or ".." in path.parts or not relative_path:
        raise ValueError("PC component path must be a non-empty relative path")
    if len(path.parts) != 1 or path.parts[0] in {".", ""}:
        return RomComponentKind.UNRESOLVED
    return PC_COMPONENT_LAYOUTS.get(path.parts[0].lower(), RomComponentKind.UNRESOLVED)


def _make_file_hash(
    crc_c: int, md5_h: Any, sha1_h: Any, chd_sha1_hash: str = ""
) -> FileHash:
    """Build a FileHash, blanking each field whose hasher state is still the default."""
    return FileHash(
        crc_hash=crc32_to_hex(crc_c) if crc_c != DEFAULT_CRC_C else "",
        md5_hash=md5_h.hexdigest() if md5_h.digest() != DEFAULT_MD5_H_DIGEST else "",
        sha1_hash=(
            sha1_h.hexdigest() if sha1_h.digest() != DEFAULT_SHA1_H_DIGEST else ""
        ),
        chd_sha1_hash=chd_sha1_hash,
    )


GENERIC_TAG_REGEX = re.compile(r"\(([^)]+)\)|\[([^]]+)\]")
VERSION_TAG_REGEX = re.compile(r"^(?:version|ver|v)(?:[\s._-](.*)|([.\d].*))", re.I)
REGION_TAG_REGEX = re.compile(r"^reg[\s|-](.*)$", re.I)
REVISION_TAG_REGEX = re.compile(r"^rev[\s|-](.*)$", re.I)


@dataclass(frozen=True)
class ParsedTags:
    version: str
    revision: str
    regions: list[str]
    languages: list[str]
    other_tags: list[str]


@dataclass(frozen=True)
class ParsedRomFiles:
    rom_files: list[RomFile]
    crc_hash: str
    md5_hash: str
    sha1_hash: str
    ra_hash: str


@dataclass(frozen=True)
class DownloadManifestMemberEvidence:
    """Captured, path-free evidence for one immutable download member."""

    destination: str
    size_bytes: int
    sha256: str
    snapshot: str
    mtime_ns: int
    device: int | None
    inode: int | None


class DownloadManifestTransferState(StrEnum):
    READY = "ready"
    SOURCE_CHANGED = "source_changed"


@dataclass
class DownloadManifestTransferLease:
    """Own a verified source descriptor and its transfer slot until streaming ends."""

    size_bytes: int
    snapshot: str
    _source: Any
    _limiter: ConcurrencyLimiter
    _closed: bool = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._source.close()
        finally:
            self._limiter.release()

    def iter_chunks(self, start: int, length: int) -> Iterator[bytes]:
        if type(start) is not int or type(length) is not int:
            raise ValueError("Download range bounds must be integers")
        if start < 0 or length < 0 or start > self.size_bytes:
            raise ValueError("Download range bounds are invalid")
        if length > self.size_bytes - start:
            raise ValueError("Download range exceeds verified source size")

        remaining = length
        os.lseek(self._source.fileno(), start, os.SEEK_SET)
        try:
            while remaining:
                chunk = os.read(self._source.fileno(), min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        finally:
            self.close()


@dataclass(frozen=True)
class DownloadManifestTransferResult:
    state: DownloadManifestTransferState
    lease: DownloadManifestTransferLease | None = None


_download_manifest_transfer_limiter = ConcurrencyLimiter(
    DOWNLOAD_MANIFEST_TRANSFER_MAX_CONCURRENCY
)


def _download_manifest_destination(rom: Rom, member: RomComponentManifestMember) -> str:
    """Create a client-safe destination from trusted persisted identities."""
    relative_path = PurePosixPath(member.relative_path)
    parts = relative_path.parts
    if (
        relative_path.is_absolute()
        or not parts
        or any(part in {"", ".", ".."} for part in parts)
        or "\\" in member.relative_path
        or any(ord(character) < 32 for character in member.relative_path)
        or not rom.fs_name
        or "/" in rom.fs_name
        or "\\" in rom.fs_name
        or any(ord(character) < 32 for character in rom.fs_name)
    ):
        raise ValueError("PC component manifest path is invalid")
    return f"{rom.fs_name}/{relative_path.as_posix()}"


def _download_manifest_snapshot(
    public_id: str, destination: str, size_bytes: int, sha256: str
) -> str:
    """Build the versioned strong validator from immutable captured evidence."""
    canonical = b"\0".join(
        (
            b"romm-manifest-v1",
            public_id.encode(),
            destination.encode(),
            str(size_bytes).encode(),
            sha256.encode(),
        )
    )
    return f'"{hashlib.sha256(canonical).hexdigest()}"'


class FSRomsHandler(ExternalFSHandler):
    def __init__(self, storage: ExternalStorageDescriptor | None = None) -> None:
        if storage is None:
            from handler.filesystem import legacy_external_storage

            storage = legacy_external_storage
        super().__init__(base_path=Path(storage._root_path), storage=storage)

    def open_rom_read(self, relative_path: str):
        return self.open_access(StorageOperation.READ, relative_path)

    def open_rom_hash(self, relative_path: str):
        return self.open_access(StorageOperation.HASH, relative_path)

    @staticmethod
    def is_pc_component_image(member: RomComponentManifestMember) -> bool:
        return (
            PurePosixPath(member.relative_path).suffix.lower()
            in PC_LOCAL_IMAGE_EXTENSIONS
        )

    def read_pc_component_image(
        self, rom: Rom, member: RomComponentManifestMember
    ) -> tuple[bytes, str]:
        """Read and validate one direct manifest image without modifying its source."""
        if not self.is_pc_component_image(member):
            raise ValueError("PC local media must be a direct PNG, JPEG, or WebP file")
        relative_path = PurePosixPath(member.relative_path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("PC local media path is invalid")

        source_path = f"{rom.fs_path}/{rom.fs_name}/{relative_path.as_posix()}"
        with self.open_rom_read(source_path) as source:
            content = source.read()
        if hashlib.sha256(content).hexdigest() != member.sha256:
            raise ValueError("PC local media source changed since the last scan")

        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
                image_type = PC_LOCAL_IMAGE_FORMATS.get(image.format or "")
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError("PC local media is not a decodable image") from exc
        if image_type is None:
            raise ValueError("PC local media is not a PNG, JPEG, or WebP image")
        return content, image_type

    @staticmethod
    def pc_component_member_path(rom: Rom, member: RomComponentManifestMember) -> str:
        """Return a manifest-bound source path without accepting browser paths."""
        relative_path = PurePosixPath(member.relative_path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("PC component manifest path is invalid")
        return f"{rom.fs_path}/{rom.fs_name}/{relative_path.as_posix()}"

    def capture_download_manifest_member(
        self, rom: Rom, member: RomComponentManifestMember, public_id: str
    ) -> DownloadManifestMemberEvidence:
        """Fully verify one persisted source member through a HASH capability."""
        destination = _download_manifest_destination(rom, member)
        try:
            source_path = self.pc_component_member_path(rom, member)
            with self.open_rom_hash(source_path) as source:
                before = os.fstat(source.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise ValueError("PC component manifest source is unavailable")
                sha256 = source.hash("sha256").lower()
                after = os.fstat(source.fileno())
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("PC component manifest source is unavailable") from exc

        indicators = (before.st_size, before.st_mtime_ns, before.st_dev, before.st_ino)
        if indicators != (after.st_size, after.st_mtime_ns, after.st_dev, after.st_ino):
            raise ValueError("PC component manifest source changed")
        if before.st_size != member.size_bytes or sha256 != member.sha256.lower():
            raise ValueError("PC component manifest source changed")
        return DownloadManifestMemberEvidence(
            destination=destination,
            size_bytes=before.st_size,
            sha256=sha256,
            snapshot=_download_manifest_snapshot(
                public_id, destination, before.st_size, sha256
            ),
            mtime_ns=before.st_mtime_ns,
            device=before.st_dev if hasattr(before, "st_dev") else None,
            inode=before.st_ino if hasattr(before, "st_ino") else None,
        )

    async def open_verified_download_manifest_member(
        self, rom: Rom, persisted_member: DownloadManifestMember
    ) -> DownloadManifestTransferResult:
        """Rehash one persisted member before allowing its verified descriptor to stream."""
        await _download_manifest_transfer_limiter.acquire()
        source = None
        lease_transferred = False
        try:
            member = persisted_member.manifest_member
            destination = _download_manifest_destination(rom, member)
            source_path = self.pc_component_member_path(rom, member)
            source = self.open_rom_hash(source_path)
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("PC component manifest source is unavailable")
            sha256 = source.hash("sha256").lower()
            after = os.fstat(source.fileno())

            before_indicators = (
                before.st_size,
                before.st_mtime_ns,
                before.st_dev,
                before.st_ino,
            )
            after_indicators = (
                after.st_size,
                after.st_mtime_ns,
                after.st_dev,
                after.st_ino,
            )
            snapshot = _download_manifest_snapshot(
                persisted_member.public_id, destination, before.st_size, sha256
            )
            if (
                before_indicators != after_indicators
                or destination != persisted_member.destination
                or before.st_size != persisted_member.size_bytes
                or sha256 != persisted_member.sha256.lower()
                or snapshot != persisted_member.snapshot
                or before.st_mtime_ns != persisted_member.mtime_ns
                or (
                    persisted_member.device is not None
                    and before.st_dev != persisted_member.device
                )
                or (
                    persisted_member.inode is not None
                    and before.st_ino != persisted_member.inode
                )
            ):
                raise ValueError("PC component manifest source changed")

            lease = DownloadManifestTransferLease(
                size_bytes=before.st_size,
                snapshot=snapshot,
                _source=source,
                _limiter=_download_manifest_transfer_limiter,
            )
            lease_transferred = True
            return DownloadManifestTransferResult(
                state=DownloadManifestTransferState.READY,
                lease=lease,
            )
        except Exception:
            return DownloadManifestTransferResult(
                state=DownloadManifestTransferState.SOURCE_CHANGED
            )
        finally:
            if not lease_transferred:
                try:
                    if source is not None:
                        source.close()
                finally:
                    _download_manifest_transfer_limiter.release()

    def light_revalidate_download_manifest_member(
        self,
        rom: Rom,
        member: RomComponentManifestMember,
        evidence: DownloadManifestMemberEvidence | Any,
    ) -> str:
        """Compare current cheap indicators only, without rehashing content."""
        try:
            source_path = self.pc_component_member_path(rom, member)
            with self.open_access(StorageOperation.STAT, source_path) as source:
                current = source.stat()
        except Exception:
            return "SOURCE_CHANGED"
        if (
            current.st_size != evidence.size_bytes
            or current.st_mtime_ns != evidence.mtime_ns
        ):
            return "SOURCE_CHANGED"
        if evidence.device is not None and current.st_dev != evidence.device:
            return "SOURCE_CHANGED"
        if evidence.inode is not None and current.st_ino != evidence.inode:
            return "SOURCE_CHANGED"
        return "UNCHANGED_BY_LIGHT_CHECK"

    async def get_pc_components(self, rom: Rom) -> list[RomComponent]:
        """Build immutable component manifests for one directory-backed PC ROM.

        All filesystem work goes through the external read capabilities. This
        method neither creates nor mutates source-library entries.
        """
        rom_path = f"{rom.fs_path}/{rom.fs_name}"
        components: list[RomComponent] = []

        async def build_component(
            component_path: str,
            relative_path: str,
            kind: RomComponentKind,
            *,
            recursive: bool,
        ) -> RomComponent:
            manifest_members: list[RomComponentManifestMember] = []
            pending_directories = [component_path] if recursive else []

            while pending_directories:
                directory = pending_directories.pop()
                for directory_name in reversed(
                    sorted(await self.list_directories(directory))
                ):
                    pending_directories.append(f"{directory}/{directory_name}")
                for file_name in sorted(await self.list_files(directory)):
                    file_path = f"{directory}/{file_name}"
                    manifest_path = file_path.removeprefix(f"{rom_path}/")
                    with self.open_rom_hash(file_path) as source:
                        sha256 = source.hash("sha256")
                    manifest_members.append(
                        RomComponentManifestMember(
                            relative_path=manifest_path,
                            size_bytes=await self.get_file_size(file_path),
                            sha256=sha256,
                        )
                    )

            if not recursive:
                for file_name in sorted(await self.list_files(component_path)):
                    file_path = f"{component_path}/{file_name}"
                    manifest_path = file_path.removeprefix(f"{rom_path}/")
                    with self.open_rom_hash(file_path) as source:
                        sha256 = source.hash("sha256")
                    manifest_members.append(
                        RomComponentManifestMember(
                            relative_path=manifest_path,
                            size_bytes=await self.get_file_size(file_path),
                            sha256=sha256,
                        )
                    )

            return RomComponent(
                relative_path=relative_path,
                kind=kind,
                manifest_members=manifest_members,
            )

        for component_name in sorted(await self.list_directories(rom_path)):
            kind = parse_pc_component_layout(component_name)
            component_path = f"{rom_path}/{component_name}"
            nested_directories = sorted(await self.list_directories(component_path))
            if kind == RomComponentKind.DLC and nested_directories:
                if await self.list_files(component_path):
                    components.append(
                        await build_component(
                            component_path,
                            component_name,
                            kind,
                            recursive=False,
                        )
                    )
                for nested_name in nested_directories:
                    components.append(
                        await build_component(
                            f"{component_path}/{nested_name}",
                            f"{component_name}/{nested_name}",
                            kind,
                            recursive=True,
                        )
                    )
                continue
            components.append(
                await build_component(
                    component_path, component_name, kind, recursive=True
                )
            )

        return components

    @staticmethod
    def open_mapped_scan(context: "MappingReadContext", relative_path: str = ""):
        return context.open(StorageOperation.SCAN, relative_path)

    @staticmethod
    def open_mapped_read(context: "MappingReadContext", relative_path: str):
        return context.open(StorageOperation.READ, relative_path)

    @staticmethod
    def open_mapped_hash(context: "MappingReadContext", relative_path: str):
        return context.open(StorageOperation.HASH, relative_path)

    @staticmethod
    def calculate_mapped_hashes(
        context: "MappingReadContext", relative_path: str
    ) -> FileHash:
        """Hash one mapping revision through a single operation-bound handle."""
        crc_c = 0
        md5_h = hashlib.md5(usedforsecurity=False)
        sha1_h = hashlib.sha1(usedforsecurity=False)

        def update(chunk: bytes) -> None:
            nonlocal crc_c
            context.boundary()
            crc_c = binascii.crc32(chunk, crc_c)
            md5_h.update(chunk)
            sha1_h.update(chunk)

        with context.open(StorageOperation.HASH, relative_path) as capability:
            descriptor = os.dup(capability.fileno())
            try:
                with os.fdopen(descriptor, "rb", closefd=True) as source:
                    if relative_path.lower().endswith(".zip"):
                        try:
                            with zipfile.ZipFile(source) as archive:
                                members = [
                                    m for m in archive.infolist() if not m.is_dir()
                                ]
                                if not members:
                                    raise ArchiveReadError("archive has no files")
                                largest = max(members, key=lambda m: m.file_size)
                                with archive.open(largest) as member:
                                    while chunk := member.read(1024 * 1024):
                                        update(chunk)
                        except (OSError, RuntimeError, zipfile.BadZipFile) as error:
                            raise ArchiveReadError(
                                "archive could not be read"
                            ) from error
                    else:
                        while chunk := source.read(1024 * 1024):
                            update(chunk)
            finally:
                context.boundary()
        return _make_file_hash(crc_c, md5_h, sha1_h)

    def get_roms_fs_structure(self, fs_slug: str) -> str:
        cnfg = cm.get_config()
        return (
            f"{fs_slug}/{cnfg.ROMS_FOLDER_NAME}"
            if cnfg.has_structure_path_b
            else f"{cnfg.ROMS_FOLDER_NAME}/{fs_slug}"
        )

    def parse_tags(self, fs_name: str) -> ParsedTags:
        tags = [
            chunk.strip()
            for tag in (m[0] or m[1] for m in GENERIC_TAG_REGEX.findall(fs_name))
            for chunk in tag.split(",")
        ]

        regions, languages, other_tags = [], [], []
        version = revision = ""

        for raw_tag in tags:
            lower_tag = raw_tag.lower()

            # Region by code
            if raw_tag in REGIONS_BY_SHORTCODE.keys():
                regions.append(REGIONS_BY_SHORTCODE[raw_tag])
                continue
            if lower_tag in REGIONS_NAME_KEYS:
                regions.append(raw_tag)
                continue

            # Language by code
            if raw_tag in LANGUAGES_BY_SHORTCODE.keys():
                languages.append(LANGUAGES_BY_SHORTCODE[raw_tag])
                continue
            if lower_tag in LANGUAGES_NAME_KEYS:
                languages.append(raw_tag)
                continue

            # Version
            version_match = VERSION_TAG_REGEX.match(raw_tag)
            if version_match:
                version = (version_match[1] or version_match[2] or "").strip()
                continue

            # Region prefix
            region_match = REGION_TAG_REGEX.match(raw_tag)
            if region_match:
                region = region_match[1]
                regions.append(REGIONS_BY_SHORTCODE.get(region, region))
                continue

            # Revision prefix
            revision_match = REVISION_TAG_REGEX.match(raw_tag)
            if revision_match:
                revision = revision_match[1]
                continue

            # Anything else
            other_tags.append(raw_tag)

        return ParsedTags(
            version=version,
            regions=regions,
            languages=languages,
            revision=revision,
            other_tags=other_tags,
        )

    def exclude_multi_roms(self, roms: list[str]) -> list[str]:
        excluded_names = cm.get_config().EXCLUDED_MULTI_FILES
        normalized_patterns = [
            excluded_name.lower().strip() for excluded_name in excluded_names
        ]

        kept_roms: list[str] = []
        for rom in roms:
            normalized_rom_name = rom.strip().lower()
            if normalized_rom_name in normalized_patterns:
                continue

            if any(
                fnmatch.fnmatch(normalized_rom_name, pattern)
                for pattern in normalized_patterns
            ):
                continue

            kept_roms.append(rom)

        return kept_roms

    def _build_rom_file(
        self,
        rom: Rom,
        rom_path: Path,
        file_name: str,
        file_hash: FileHash,
        file_size_bytes: int | None = None,
        last_modified: float | None = None,
        archive_members: list[dict[str, Any]] | None = None,
    ) -> RomFile:
        abs_file_path = Path(self.base_path, rom_path, file_name)

        path_parts_lower = list(map(str.lower, rom_path.parts))
        matching_category = next(
            (
                category
                for category in RomFileCategory
                if category_matches(category.value, path_parts_lower)
            ),
            None,
        )

        track_meta = None
        if matching_category == RomFileCategory.SOUNDTRACK:
            from utils.audio_tags import (
                extract_audio_meta,
                is_allowed_audio_file,
                track_meta_columns,
            )

            if is_allowed_audio_file(file_name):
                meta = extract_audio_meta(str(abs_file_path))
                if meta:
                    track_meta = TrackMeta(rom_id=rom.id, **track_meta_columns(meta))

        return RomFile(
            rom=rom,
            rom_id=rom.id,
            file_name=file_name,
            file_path=str(rom_path),
            file_size_bytes=(
                file_size_bytes
                if file_size_bytes is not None
                else os.stat(abs_file_path).st_size
            ),
            last_modified=(
                last_modified
                if last_modified is not None
                else os.path.getmtime(abs_file_path)
            ),
            category=matching_category,
            track_meta=track_meta,
            crc_hash=file_hash["crc_hash"],
            md5_hash=file_hash["md5_hash"],
            sha1_hash=file_hash["sha1_hash"],
            chd_sha1_hash=file_hash["chd_sha1_hash"],
            archive_members=archive_members,
        )

    async def get_rom_files(
        self, rom: Rom, calculate_hashes: bool = True
    ) -> ParsedRomFiles:
        from adapters.services.rahasher import RAHasherService
        from handler.metadata import meta_ra_handler

        rel_roms_path = self.get_roms_fs_structure(
            rom.platform.fs_slug
        )  # Relative path to roms
        abs_fs_path = self.validate_path(rel_roms_path)  # Absolute path to roms
        rom_files: list[RomFile] = []

        # Skip hashing games for platforms that don't have a hash database or when hashes are disabled
        hashable_platform = (
            rom.platform_slug not in NON_HASHABLE_PLATFORMS and calculate_hashes
        )

        cnfg = cm.get_config()
        excluded_file_names = cnfg.EXCLUDED_MULTI_PARTS_FILES
        excluded_file_exts = cnfg.EXCLUDED_MULTI_PARTS_EXT

        rom_crc_c = 0
        rom_md5_h = hashlib.md5(usedforsecurity=False) if calculate_hashes else None
        rom_sha1_h = hashlib.sha1(usedforsecurity=False) if calculate_hashes else None
        rom_ra_h = ""

        rom_dir = Path(abs_fs_path, rom.fs_name)
        rom_ext = f".{rom.fs_extension.lower()}" if rom.fs_extension else ""

        # Check if rom is a multi-part rom
        if await AnyioPath(f"{abs_fs_path}/{rom.fs_name}").is_dir():
            # Calculate the RA hash if the platform has a slug that matches a known RA slug
            if calculate_hashes:
                ra_platform = meta_ra_handler.get_platform(rom.platform_slug)
                if ra_platform and ra_platform["ra_id"]:
                    # RAHasher can't process CHD files via the /* wildcard and instead expects
                    # track files (bin/cue/etc.). For CHD-only folders, find the largest
                    # CHD and pass it directly, matching single-file CHD behaviour.

                    def _largest_chd_file() -> Path | None:
                        chds = [f for f in rom_dir.iterdir() if is_chd_file(f)]
                        sorted_chds = sorted(
                            chds, key=lambda f: f.stat().st_size, reverse=True
                        )
                        return sorted_chds[0] if sorted_chds else None

                    chd_file = await asyncio.to_thread(_largest_chd_file)
                    ra_path = (
                        str(chd_file)
                        if chd_file and chd_file.is_file()
                        else f"{abs_fs_path}/{rom.fs_name}/*"
                    )
                    rom_ra_h = await RAHasherService().calculate_hash(
                        ra_platform,
                        ra_path,
                    )

            for f_path, file_name in iter_files(
                f"{abs_fs_path}/{rom.fs_name}", recursive=True
            ):
                # Check if file is excluded by extension.
                f_rom_dir = Path(f_path, rom.fs_name)
                file_name_lower = file_name.lower()
                if any(
                    file_name_lower.endswith("." + ext) for ext in excluded_file_exts
                ):
                    continue

                # Check if the file name matches a pattern in the excluded list.
                if any(
                    file_name == exc_name or fnmatch.fnmatch(file_name, exc_name)
                    for exc_name in excluded_file_names
                ):
                    continue

                # Check if this is a top-level file (not in a subdirectory)
                is_top_level = f_path.samefile(Path(abs_fs_path, rom.fs_name))

                if hashable_platform:
                    try:
                        if is_top_level:
                            # Include this file in the main ROM hash calculation
                            (
                                crc_c,
                                rom_crc_c,
                                md5_h,
                                rom_md5_h,
                                sha1_h,
                                rom_sha1_h,
                            ) = await asyncio.to_thread(
                                self._calculate_rom_hashes,
                                Path(f_path, file_name),
                                rom_crc_c,
                                rom_md5_h,
                                rom_sha1_h,
                            )
                        else:
                            # Calculate individual file hash only
                            crc_c, _, md5_h, _, sha1_h, _ = await asyncio.to_thread(
                                self._calculate_rom_hashes,
                                Path(f_path, file_name),
                            )
                    except zlib.error:
                        crc_c = 0
                        md5_h = hashlib.md5(usedforsecurity=False)
                        sha1_h = hashlib.sha1(usedforsecurity=False)

                    file_hash = _make_file_hash(
                        crc_c,
                        md5_h,
                        sha1_h,
                        chd_sha1_hash=(
                            extract_chd_hash(f_rom_dir)
                            if is_chd_file(f_rom_dir)
                            else ""
                        ),
                    )
                else:
                    file_hash = FileHash(
                        crc_hash="",
                        md5_hash="",
                        sha1_hash="",
                        chd_sha1_hash="",
                    )

                rom_files.append(
                    self._build_rom_file(
                        rom=rom,
                        rom_path=f_path.relative_to(self.base_path),
                        file_name=file_name,
                        file_hash=file_hash,
                    )
                )
        elif hashable_platform and rom_ext in ARCHIVE_READERS:
            # Multi-file archive: compute a composite hash across all
            # internal entries (in ASCII path order) for hash-database
            # matching, while still emitting a single RomFile for the
            # archive file itself. Per-member hashes are stored on that
            # RomFile in `archive_members` so consumers can identify each
            # internal file without us inventing RomFile rows whose
            # full_path would point inside the archive and break downloads.
            assert rom_md5_h is not None and rom_sha1_h is not None

            def _hash_archive_entries(
                crc: int, md5_h: Any, sha1_h: Any
            ) -> tuple[list[dict[str, Any]], int, Any, Any]:
                # Accumulate into copies so an archive we can't read in full
                # leaves the caller's hashers untouched for the raw fallback.
                original_crc, md5_h, sha1_h = crc, md5_h.copy(), sha1_h.copy()
                members: list[dict[str, Any]] = []
                try:
                    for name, size, chunks in ARCHIVE_READERS[rom_ext](
                        rom_dir,
                        DEFAULT_EXCLUDED_FILES,
                        DEFAULT_EXCLUDED_EXTENSIONS,
                    ):
                        member_crc = 0
                        member_md5 = hashlib.md5(usedforsecurity=False)
                        member_sha1 = hashlib.sha1(usedforsecurity=False)
                        for chunk in chunks:
                            crc = binascii.crc32(chunk, crc)
                            md5_h.update(chunk)
                            sha1_h.update(chunk)
                            member_crc = binascii.crc32(chunk, member_crc)
                            member_md5.update(chunk)
                            member_sha1.update(chunk)
                        members.append(
                            {
                                "name": name,
                                "size": size,
                                "crc_hash": crc32_to_hex(member_crc),
                                "md5_hash": member_md5.hexdigest(),
                                "sha1_hash": member_sha1.hexdigest(),
                            }
                        )
                except ArchiveReadError as e:
                    log.error(f"Incomplete read of archive {rom_dir}: {e}")
                    return [], original_crc, None, None
                return members, crc, md5_h, sha1_h

            members, rom_crc_c, archive_md5_h, archive_sha1_h = await asyncio.to_thread(
                _hash_archive_entries, rom_crc_c, rom_md5_h, rom_sha1_h
            )

            if members:
                rom_md5_h, rom_sha1_h = archive_md5_h, archive_sha1_h
                if calculate_hashes:
                    ra_platform = meta_ra_handler.get_platform(rom.platform_slug)
                    if ra_platform and ra_platform["ra_id"]:
                        rom_ra_h = await RAHasherService().calculate_hash(
                            ra_platform,
                            f"{abs_fs_path}/{rom.fs_name}",
                        )

                rom_files.append(
                    self._build_rom_file(
                        rom=rom,
                        rom_path=Path(rel_roms_path),
                        file_name=rom.fs_name,
                        file_hash=_make_file_hash(rom_crc_c, rom_md5_h, rom_sha1_h),
                        archive_members=members,
                    )
                )
            else:
                # Empty, malformed, unreadable, or all-excluded archive: hash the archive
                # file's raw bytes. We avoid `_calculate_rom_hashes` here because
                # it would decompress based on extension and end up hashing the
                # largest internal member, not the archive itself — and would
                # crash on an empty zip. `archive_members` stays None.
                def _hash_raw_archive(crc: int) -> int:
                    for chunk in read_basic_file(rom_dir):
                        crc = binascii.crc32(chunk, crc)
                        if rom_md5_h:
                            rom_md5_h.update(chunk)
                        if rom_sha1_h:
                            rom_sha1_h.update(chunk)
                    return crc

                rom_crc_c = await asyncio.to_thread(_hash_raw_archive, rom_crc_c)
                rom_files.append(
                    self._build_rom_file(
                        rom=rom,
                        rom_path=Path(rel_roms_path),
                        file_name=rom.fs_name,
                        file_hash=_make_file_hash(rom_crc_c, rom_md5_h, rom_sha1_h),
                    )
                )
        elif hashable_platform:
            try:
                crc_c, _, md5_h, _, sha1_h, _ = await asyncio.to_thread(
                    self._calculate_rom_hashes,
                    Path(abs_fs_path, rom.fs_name),
                )
            except zlib.error:
                crc_c = 0
                md5_h = hashlib.md5(usedforsecurity=False)
                sha1_h = hashlib.sha1(usedforsecurity=False)

            # A single-file ROM spans exactly one file, so its ROM-level hashes
            # are that file's hashes.
            rom_crc_c, rom_md5_h, rom_sha1_h = crc_c, md5_h, sha1_h

            # Calculate the RA hash if the platform has a slug that matches a known RA slug
            if calculate_hashes:
                ra_platform = meta_ra_handler.get_platform(rom.platform_slug)
                if ra_platform and ra_platform["ra_id"]:
                    rom_ra_h = await RAHasherService().calculate_hash(
                        ra_platform,
                        f"{abs_fs_path}/{rom.fs_name}",
                    )

            file_hash = _make_file_hash(
                crc_c,
                md5_h,
                sha1_h,
                chd_sha1_hash=(
                    extract_chd_hash(rom_dir) if is_chd_file(rom_dir) else ""
                ),
            )
            rom_files.append(
                self._build_rom_file(
                    rom=rom,
                    rom_path=Path(rel_roms_path),
                    file_name=rom.fs_name,
                    file_hash=file_hash,
                )
            )
        else:
            file_hash = FileHash(
                crc_hash="",
                md5_hash="",
                sha1_hash="",
                chd_sha1_hash="",
            )
            rom_files.append(
                self._build_rom_file(
                    rom=rom,
                    rom_path=Path(rel_roms_path),
                    file_name=rom.fs_name,
                    file_hash=file_hash,
                )
            )

        return ParsedRomFiles(
            rom_files=rom_files,
            crc_hash=crc32_to_hex(rom_crc_c) if rom_crc_c != DEFAULT_CRC_C else "",
            md5_hash=(
                rom_md5_h.hexdigest()
                if rom_md5_h and rom_md5_h.digest() != DEFAULT_MD5_H_DIGEST
                else ""
            ),
            sha1_hash=(
                rom_sha1_h.hexdigest()
                if rom_sha1_h and rom_sha1_h.digest() != DEFAULT_SHA1_H_DIGEST
                else ""
            ),
            ra_hash=rom_ra_h,
        )

    def _calculate_rom_hashes(
        self,
        file_path: Path,
        rom_crc_c: int = 0,
        rom_md5_h: Any = None,
        rom_sha1_h: Any = None,
    ) -> tuple[int, int, Any, Any, Any, Any]:
        """Hash one file, optionally folding its bytes into ROM-level accumulators.

        A ROM-level hash spans every top-level file of a multi-file ROM, so it
        can only be built by feeding each file through a second set of hashers.
        Callers that don't need one pass no accumulators, because a second pass
        over a chunk costs as much as the first.
        """
        extension = Path(file_path).suffix.lower()
        try:
            file_type = detect_mime_type(file_path)

            crc_c = 0
            md5_h = hashlib.md5(usedforsecurity=False)
            sha1_h = hashlib.sha1(usedforsecurity=False)
            accumulate = rom_md5_h is not None and rom_sha1_h is not None

            def update_hashes(chunk: bytes | bytearray):
                nonlocal crc_c, rom_crc_c

                md5_h.update(chunk)
                sha1_h.update(chunk)
                crc_c = binascii.crc32(chunk, crc_c)

                if accumulate:
                    rom_md5_h.update(chunk)
                    rom_sha1_h.update(chunk)
                    rom_crc_c = binascii.crc32(chunk, rom_crc_c)

            if extension == ".zip" or file_type == "application/zip":
                relative_path = str(file_path.relative_to(self.base_path))
                with self.open_rom_read(relative_path) as source:
                    for chunk in read_zip_file(source):
                        update_hashes(chunk)

            elif extension == ".tar" or file_type == "application/x-tar":
                for chunk in read_tar_file(file_path):
                    update_hashes(chunk)

            elif extension == ".gz" or file_type == "application/x-gzip":
                for chunk in read_gz_file(file_path):
                    update_hashes(chunk)

            elif extension == ".7z" or file_type == "application/x-7z-compressed":
                process_7z_file(
                    file_path=file_path,
                    fn_hash_update=update_hashes,
                )

            elif extension == ".bz2" or file_type == "application/x-bzip2":
                for chunk in read_bz2_file(file_path):
                    update_hashes(chunk)

            else:
                for chunk in read_basic_file(file_path):
                    update_hashes(chunk)

            return crc_c, rom_crc_c, md5_h, rom_md5_h, sha1_h, rom_sha1_h
        except (FileNotFoundError, PermissionError):
            return (
                0,
                rom_crc_c,
                hashlib.md5(usedforsecurity=False),
                rom_md5_h,
                hashlib.sha1(usedforsecurity=False),
                rom_sha1_h,
            )

    async def count_roms(self, platform: Platform) -> int:
        """Return the number of filesystem roms for a platform without
        materializing FSRom objects.
        """
        try:
            rel_roms_path = self.get_roms_fs_structure(platform.fs_slug)
            fs_single_roms = await self.list_files(path=rel_roms_path)
            fs_multi_roms = await self.list_directories(path=rel_roms_path)
        except FileNotFoundError as e:
            raise RomsNotFoundException(platform=platform.fs_slug) from e

        return len(self.exclude_single_files(fs_single_roms)) + len(
            self.exclude_multi_roms(fs_multi_roms)
        )

    async def get_roms(self, platform: Platform) -> list[FSRom]:
        """Gets all filesystem roms for a platform

        Args:
            platform: platform where roms belong
        Returns:
            list with all the filesystem roms for a platform
        """
        try:
            rel_roms_path = self.get_roms_fs_structure(
                platform.fs_slug
            )  # Relative path to roms

            fs_single_roms = await self.list_files(path=rel_roms_path)
            fs_multi_roms = await self.list_directories(path=rel_roms_path)
        except FileNotFoundError as e:
            raise RomsNotFoundException(platform=platform.fs_slug) from e

        fs_roms: list[dict] = [
            {"fs_name": rom, "flat": True, "nested": False}
            for rom in self.exclude_single_files(fs_single_roms)
        ] + [
            {"fs_name": rom, "flat": False, "nested": True}
            for rom in self.exclude_multi_roms(fs_multi_roms)
        ]

        return sorted(
            [
                FSRom(
                    fs_name=rom["fs_name"],
                    flat=rom["flat"],
                    nested=rom["nested"],
                    files=[],
                    crc_hash="",
                    md5_hash="",
                    sha1_hash="",
                    ra_hash="",
                )
                for rom in fs_roms
            ],
            key=lambda rom: rom["fs_name"],
        )

    async def rename_fs_rom(self, old_name: str, new_name: str, fs_path: str) -> None:
        if new_name != old_name:
            file_path = f"{fs_path}/{new_name}"
            if await self.file_exists(file_path=file_path):
                raise RomAlreadyExistsException(new_name)

            await self.move_file_or_folder(
                f"{fs_path}/{old_name}", f"{fs_path}/{new_name}"
            )

    def get_pico8_cover_url(
        self, platform_slug: str, fs_name: str, fs_path: str
    ) -> str | None:
        """Return a ``file://`` URL for a PICO-8 cartridge label, or ``None``.

        PICO-8 ``.p8.png`` files are valid PNG images whose visual content *is*
        the cartridge label/cover art.  When such a ROM is found we can use the
        file itself as the cover instead of fetching one from an external source.
        """
        if platform_slug == UPS.PICO and fs_name.lower().endswith(
            PICO8_CARTRIDGE_EXTENSION
        ):
            self.validate_path(f"{fs_path}/{fs_name}")
            return f"file://{fs_path}/{fs_name}"
        return None
