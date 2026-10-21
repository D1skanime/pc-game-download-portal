from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from itertools import batched, chain
from typing import Any, Final, cast

import socketio  # type: ignore
from httpx import DecodingError, TransportError
from rq import Worker, get_current_job
from rq.job import Job, JobStatus
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from config import REDIS_URL, SCAN_WORKERS
from config.config_manager import config_manager as cm
from endpoints.responses.platform import PlatformSchema
from endpoints.responses.rom import SimpleRomSchema
from endpoints.sockets.activity import get_authenticated_user
from exceptions.fs_exceptions import (
    FOLDER_STRUCT_MSG,
    FirmwareNotFoundException,
    FolderStructureNotMatchException,
    RomsNotFoundException,
)
from exceptions.socket_exceptions import ScanStoppedException
from exceptions.storage_exceptions import (
    MissingPlatformStorageMappingError,
    StorageResolutionError,
)
from handler.auth.constants import Scope
from handler.database import (
    db_collection_handler,
    db_firmware_handler,
    db_platform_handler,
    db_rom_handler,
    db_storage_handler,
)
from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler
from handler.database.scan_write_fence import (
    ScanWriteRejected,
    require_scan_write_context,
)
from handler.filesystem import (
    fs_firmware_handler,
    fs_platform_handler,
    fs_resource_handler,
    fs_rom_handler,
    get_fs_rom_handler,
    legacy_external_storage,
    open_storage_access,
    use_fs_rom_handler,
)
from handler.filesystem.roms_handler import FSRom
from handler.filesystem.scan_media_inventory import ScanMediaInventory
from handler.filesystem.scan_media_publication import (
    ScanMediaBatch,
    merge_scan_rom,
    publish_rom_resources,
)
from handler.filesystem.storage_access import (
    IndeterminateOwnedPublicationError,
    ScanCapability,
)
from handler.filesystem.storage_policy import StorageOperation
from handler.filesystem.storage_resolver import get_storage_root_health_snapshot
from handler.metadata import (
    meta_gamelist_handler,
    meta_hltb_handler,
    meta_igdb_handler,
    meta_steam_handler,
)
from handler.metadata.base_handler import UniversalPlatformSlug as UPS
from handler.metadata.pc_match_handler import pc_metadata_match_handler
from handler.metadata.rom_media import refresh_provider_owned_media
from handler.metadata.ss_handler import add_ss_auth_to_url
from handler.metadata.ss_handler import begin_scan as begin_ss_scan
from handler.metadata.ss_handler import get_preferred_media_types
from handler.metadata.ss_handler import log_quota as log_ss_quota
from handler.metadata.ss_handler import log_scan_summary as log_ss_scan_summary
from handler.metadata.steam_handler import STEAM_PLATFORMS
from handler.metadata.steam_merge import normalize_steam
from handler.redis_handler import (
    get_job_func_name,
    high_prio_queue,
    low_prio_queue,
    redis_client,
)
from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger
from handler.scan_handler import MappedScanCommand as HandlerMappedScanCommand
from handler.scan_handler import (
    MetadataSource,
    ScanType,
    execute_mapped_scan,
    persist_soundtrack_cover,
    process_pc_automation_after_scan,
    scan_firmware,
    scan_platform,
    scan_rom,
)
from handler.socket_handler import socket_handler
from logger.formatter import BLUE, LIGHTYELLOW
from logger.formatter import highlight as hl
from logger.logger import log
from models.firmware import Firmware
from models.platform import Platform
from models.rom import (
    Rom,
    RomComponent,
    RomComponentKind,
    RomComponentOwnedMediaRole,
    derive_pc_component_provider_media_id,
)
from tasks.tasks import SCAN_LIBRARY_TASK_FUNC, tasks_scheduler, update_job_meta
from utils import emoji
from utils.context import initialize_context
from utils.platform_slugs import canonicalize_filesystem_slug

STOP_SCAN_FLAG: Final = "scan:stop"
catalog_lifecycle_handler = CatalogLifecycleHandler()

_PC_IGDB_MEDIA_ROLES = {
    "cover": RomComponentOwnedMediaRole.COVER,
    "screenshot": RomComponentOwnedMediaRole.SCREENSHOT,
    "artwork": RomComponentOwnedMediaRole.ARTWORK,
}


async def _hydrate_media_urls(
    rom: Rom,
    metadata_sources: list[str],
    metadata_locale: str | None,
) -> tuple[Rom, str | None]:
    """Recover provider media URLs when a media-only scan has no cached URLs."""
    if rom.url_cover or rom.url_screenshots:
        return rom, metadata_sources[0] if metadata_sources else "provider"

    candidates: list[tuple[str, object]] = []
    if MetadataSource.IGDB in metadata_sources and rom.igdb_id:
        candidates.append(
            (
                MetadataSource.IGDB,
                meta_igdb_handler.get_rom_by_id(rom, rom.igdb_id),
            )
        )
    if MetadataSource.STEAM in metadata_sources and rom.steam_id:
        candidates.append(
            (
                MetadataSource.STEAM,
                meta_steam_handler.get_rom_by_id(
                    rom.steam_id,
                    platform_slug=rom.platform_slug,
                    metadata_locale=metadata_locale,
                ),
            )
        )

    for provider, request in candidates:
        fetched = await request
        if isinstance(fetched, dict):
            url_cover = fetched.get("url_cover")
            url_screenshots = fetched.get("url_screenshots") or []
        else:
            url_cover = getattr(fetched, "url_cover", None)
            url_screenshots = getattr(fetched, "url_screenshots", None) or []
        if not url_cover and not url_screenshots:
            continue
        rom = db_rom_handler.update_rom(
            rom.id,
            {
                "url_cover": url_cover,
                "url_screenshots": url_screenshots,
            },
        )
        return rom, provider

    return rom, None


def _refresh_rom_for_scan_emit(rom: Rom) -> Rom:
    """Load the fields required by the scan event before its session closes."""
    if not isinstance(rom, Rom):
        return rom
    return db_rom_handler.get_rom_simple(rom.id) or rom


async def _emit_scanning_rom(socket_manager: Any, rom: Rom) -> None:
    """Emit scan progress without allowing presentation errors to abort scanning."""
    try:
        emitted_rom = _refresh_rom_for_scan_emit(rom)
        await socket_manager.emit(
            "scan:scanning_rom",
            SimpleRomSchema.from_orm_with_factory(emitted_rom).model_dump(
                exclude={
                    "created_at",
                    "updated_at",
                    "rom_user",
                    "last_modified",
                    "files",
                    "sibling_roms",
                }
            ),
        )
    except (ScanWriteRejected, IndeterminateOwnedPublicationError, SQLAlchemyError):
        raise
    except Exception as exc:
        log.warning(
            "Unable to emit scan progress for ROM %s; continuing scan: %s",
            getattr(rom, "id", "unknown"),
            exc,
        )


async def _enrich_pc_dlc_from_igdb(rom: Rom, component: RomComponent) -> None:
    """Import an already-unambiguous DLC candidate into RomM-owned storage."""
    if component.kind != RomComponentKind.DLC:
        return
    candidate = await pc_metadata_match_handler.fetch_unique_related_igdb_candidate(
        rom, component
    )
    if candidate is None:
        return

    saved_component = db_rom_handler.apply_pc_component_metadata_candidate(
        rom.id,
        component.id,
        component.updated_at,
        candidate.provider,
        candidate.fields,
    )
    if saved_component is None:
        return

    steam_candidate = await pc_metadata_match_handler.fetch_validated_steam_dlc(
        rom, candidate
    )
    if steam_candidate is not None:
        current_metadata = saved_component.component_metadata
        current = {
            "name": getattr(current_metadata, "name", None),
            "summary": getattr(current_metadata, "summary", None),
            "steam_metadata": getattr(current_metadata, "steam_metadata", None),
            "metadata": {
                "main_developer": getattr(current_metadata, "main_developer", None),
                "publishers": getattr(current_metadata, "publishers", None),
                "pc_release_date": getattr(current_metadata, "pc_release_date", None),
            },
        }
        steam_data = normalize_steam(steam_candidate, current)
        if steam_data:
            steam_saved_component = (
                db_rom_handler.apply_pc_component_metadata_candidate(
                    rom.id,
                    saved_component.id,
                    saved_component.updated_at,
                    "steam",
                    steam_data,
                )
            )
            if steam_saved_component is not None:
                saved_component = steam_saved_component

    saved_component = db_rom_handler.get_pc_component_by_id(rom.id, saved_component.id)
    if saved_component is None:
        return
    existing_media = db_rom_handler.get_pc_component_provider_media_for_reconciliation(
        rom.id, saved_component.id
    )
    content_hashes: dict[int, str] = {}
    for existing in existing_media:
        try:
            content = await fs_resource_handler.read_file(existing.owned_path)
        except (FileNotFoundError, OSError, ValueError):
            continue
        if content:
            content_hashes[existing.id] = hashlib.sha256(content).hexdigest()
    with ScanMediaBatch(rom.id, rom.platform_id, fs_resource_handler.storage) as unit:
        reconciled = unit.publish_and_associate(
            lambda session: db_rom_handler.reconcile_pc_component_provider_media(
                rom.id,
                saved_component.id,
                saved_component.updated_at,
                content_hashes,
                session=session,
            )
        )
    if reconciled is None:
        return
    saved_component = db_rom_handler.get_pc_component_by_id(
        rom.id, reconciled.component.id
    )
    if saved_component is None:
        return

    for media in candidate.media:
        role = _PC_IGDB_MEDIA_ROLES.get(media.get("kind", ""))
        url = media.get("url")
        if role is None or not isinstance(url, str):
            continue
        try:
            with ScanMediaBatch(
                rom.id, rom.platform_id, fs_resource_handler.storage
            ) as unit:
                owned_path, mime_type, content_sha256 = (
                    await fs_resource_handler.store_pc_component_provider_image(
                        rom, saved_component.id, candidate.provider, role, url
                    )
                )
                provider_media_id = derive_pc_component_provider_media_id(
                    candidate.provider, role, content_sha256
                )

                def associate_dlc(
                    session,
                    saved_component=saved_component,
                    role=role,
                    mime_type=mime_type,
                    owned_path=owned_path,
                    provider_media_id=provider_media_id,
                    content_sha256=content_sha256,
                ):
                    imported = db_rom_handler.import_pc_component_provider_media(
                        rom.id,
                        saved_component.id,
                        saved_component.updated_at,
                        role,
                        mime_type,
                        owned_path,
                        candidate.provider,
                        provider_media_id,
                        content_sha256,
                        session=session,
                    )
                    if imported is None:
                        raise ValueError("DLC media catalog changed")
                    return imported

                unit.publish_and_associate(associate_dlc)
        except (ScanWriteRejected, IndeterminateOwnedPublicationError, SQLAlchemyError):
            raise
        except (ValueError, OSError, TransportError, DecodingError):
            log.warning(
                "Optional DLC media retained prior reference for component %s",
                saved_component.id,
            )
            continue
        saved_component = db_rom_handler.get_pc_component_by_id(
            rom.id, saved_component.id
        )
        if saved_component is None:
            return


def _scan_platforms_func_name() -> str:
    """Fully qualified name RQ records for a directly enqueued scan.

    Derived from the function itself so it cannot drift out of sync with the
    name RQ stores when the job is enqueued.
    """
    return f"{scan_platforms.__module__}.{scan_platforms.__name__}"


def _scan_job_func_names() -> frozenset[str]:
    """Every job function name that ends up running a scan.

    Socket and watcher scans enqueue scan_platforms itself, while the scheduled
    rescan enqueues its own task and calls scan_platforms in process. Both have
    to be recognised or an in-flight scan goes unseen.
    """
    return frozenset(
        (
            _scan_platforms_func_name(),
            SCAN_LIBRARY_TASK_FUNC,
            "endpoints.sockets.scan.execute_mapping_scan",
            "endpoints.sockets.scan.execute_mapping_scans",
            "endpoints.sockets.scan.execute_mixed_scans",
            "handler.scan_operation_worker.run_scan_operation",
        )
    )


def _get_running_scan_job() -> Job | None:
    """The scan currently executing on a worker, if any.

    A started job is no longer in the queue, so it can only be found by asking
    the workers what they are holding.
    """
    func_names = _scan_job_func_names()
    for worker in Worker.all(connection=redis_client):
        job = worker.get_current_job()
        if job is not None and get_job_func_name(job) in func_names:
            return job

    return None


def _get_queued_scan_jobs() -> list[Job]:
    """Scans waiting to run, not yet picked up by a worker.

    Socket scans sit in the high priority queue, while watcher scans are delayed
    through the scheduler before landing in the low priority queue.
    """
    func_names = _scan_job_func_names()
    jobs: dict[str, Job] = {}

    for job in chain(high_prio_queue.get_jobs(), low_prio_queue.get_jobs()):
        if isinstance(job, Job) and get_job_func_name(job) in func_names:
            jobs[job.id] = job

    # The scheduler registry also holds the standing cron entry for the
    # scheduled rescan, which is a schedule rather than a pending scan, so only
    # delayed scan_platforms jobs count as queued here.
    for job in tasks_scheduler.get_jobs():
        if (
            isinstance(job, Job)
            and get_job_func_name(job) in (func_names - {SCAN_LIBRARY_TASK_FUNC})
            and job.get_status() in (JobStatus.SCHEDULED, JobStatus.QUEUED)
        ):
            jobs[job.id] = job

    return list(jobs.values())


@dataclass
class ScanStats:
    total_platforms: int = 0
    total_roms: int = 0
    scanned_platforms: int = 0
    new_platforms: int = 0
    identified_platforms: int = 0
    scanned_roms: int = 0
    new_roms: int = 0
    identified_roms: int = 0
    scanned_firmware: int = 0
    new_firmware: int = 0

    def __post_init__(self):
        # Lock for thread-safe updates
        self._lock = asyncio.Lock()

    async def update(self, socket_manager: socketio.AsyncRedisManager, **kwargs):
        async with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)

            from handler.scan_operation_worker import persist_scan_stats

            payload = persist_scan_stats(self.to_dict())
            update_job_meta({"scan_stats": payload})
            await socket_manager.emit("scan:update_stats", payload)

    async def increment(self, socket_manager: socketio.AsyncRedisManager, **kwargs):
        async with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    current_value = getattr(self, key)
                    setattr(self, key, current_value + value)

            from handler.scan_operation_worker import persist_scan_stats

            payload = persist_scan_stats(self.to_dict())
            update_job_meta({"scan_stats": payload})
            await socket_manager.emit("scan:update_stats", payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_platforms": self.total_platforms,
            "total_roms": self.total_roms,
            "scanned_platforms": self.scanned_platforms,
            "new_platforms": self.new_platforms,
            "identified_platforms": self.identified_platforms,
            "scanned_roms": self.scanned_roms,
            "new_roms": self.new_roms,
            "identified_roms": self.identified_roms,
            "scanned_firmware": self.scanned_firmware,
            "new_firmware": self.new_firmware,
        }


def _get_socket_manager() -> socketio.AsyncRedisManager:
    """Connect to external socketio server"""
    from handler.scan_operation_worker import AttemptSocketManager, active_scan_worker

    manager = socketio.AsyncRedisManager(REDIS_URL, write_only=True)
    return AttemptSocketManager(manager) if active_scan_worker() else manager


async def _identify_firmware(
    platform: Platform,
    fs_fw: str,
) -> int:
    require_scan_write_context()
    from handler.scan_operation_worker import check_worker_boundary

    check_worker_boundary()
    # Break early if the flag is set
    if redis_client.get(STOP_SCAN_FLAG):
        return 0

    firmware = db_firmware_handler.get_firmware_by_filename(platform.id, fs_fw)

    scanned_firmware = await scan_firmware(
        platform=platform,
        file_name=fs_fw,
        firmware=firmware,
    )

    is_verified = Firmware.verify_file_hashes(
        platform_slug=platform.slug,
        file_name=fs_fw,
        file_size_bytes=scanned_firmware.file_size_bytes,
        md5_hash=scanned_firmware.md5_hash,
        sha1_hash=scanned_firmware.sha1_hash,
        crc_hash=scanned_firmware.crc_hash,
    )

    scanned_firmware.missing_from_fs = False
    scanned_firmware.is_verified = is_verified
    db_firmware_handler.add_firmware(scanned_firmware)

    return 1 if not firmware else 0


def should_scan_rom(
    scan_type: ScanType,
    rom: Rom | None,
    roms_ids: list[int],
    metadata_sources: list[str],
    fs_rom: FSRom | None = None,
) -> bool:
    """Decide if a rom should be scanned or not

    Args:
        scan_type (ScanType): Type of scan to be performed.
        rom (Rom | None): The rom to be scanned.
        roms_ids (list[int]): List of selected roms to be scanned.
        metadata_sources (list[str]): List of metadata sources to be used.
        fs_rom (FSRom | None): Current filesystem scan-entry shape.
    """

    # When roms_ids is provided, the scan is scoped to those roms only
    if roms_ids:
        return bool(rom and rom.id in roms_ids)

    # This logic is tricky so only touch it if you know what you're doing"""
    should_scan = bool(
        # Any new roms should be scanned
        (scan_type in {ScanType.NEW_PLATFORMS, ScanType.QUICK} and not rom)
        # Complete rescan should scan all roms
        or (scan_type == ScanType.COMPLETE)
        # Hashes rescan should scan all roms to update the hashes
        or (scan_type == ScanType.HASHES)
        or (
            rom
            and (
                # Existing directory-backed Windows games refresh their PC
                # component manifests during unscoped quick scans.
                (
                    scan_type == ScanType.QUICK
                    and rom.platform_slug == UPS.WIN
                    and fs_rom is not None
                    and fs_rom["nested"] is True
                )
                # Update scan should scan ROMs identified by the selected metadata sources
                or (
                    scan_type == ScanType.UPDATE
                    and rom.is_identified
                    and any(
                        getattr(rom, f"{source}_id", None)
                        for source in metadata_sources
                    )
                )
                or (
                    scan_type == ScanType.UPDATE
                    and rom.platform_slug == UPS.WIN
                    and rom.steam_id is not None
                    and rom.steam_id > 0
                    and not rom.igdb_id
                    and MetadataSource.IGDB in metadata_sources
                )
                or (
                    # D-03/T-21-10: Steam-only UPDATE parity is limited to
                    # supported PC platforms with a persisted Steam identity.
                    scan_type == ScanType.UPDATE
                    and rom.platform_slug in STEAM_PLATFORMS
                    and isinstance(rom.steam_id, int)
                    and not isinstance(rom.steam_id, bool)
                    and rom.steam_id > 0
                    and MetadataSource.STEAM in metadata_sources
                )
                # Unmatched scan is reserved for ROMs with no metadata
                # identity at all. Provider-specific refreshes belong to UPDATE.
                or (scan_type == ScanType.UNMATCHED and rom.is_unidentified)
            )
        )
    )

    return should_scan


def _should_get_rom_files(
    scan_type: ScanType,
    rom: Rom,
    newly_added: bool,
    roms_ids: list[int],
) -> bool:
    """Decide if the files of a rom should be rebuilt or not

    Args:
        scan_type (ScanType): Type of scan to be performed.
        rom (Rom): The rom to be rebuilt.
        newly_added (bool): Whether the rom is newly added.
        roms_ids (list[int]): List of selected roms to be scanned.
    """

    return bool(
        newly_added
        or (scan_type == ScanType.COMPLETE)
        or (scan_type == ScanType.HASHES)
        or (rom and rom.id in roms_ids)
    )


# There's an order of operations here that is important:
# 1. Read the list of roms from the filesystem
# 2. Check if ROM should be scanned based on the scan type
# 3. Create a new ROM entry if it doesn't exist
# 4. Build the ROM files and calculate the hashes
# 4. Scan the ROM and update its metadata
async def _identify_rom(
    platform: Platform,
    fs_rom: FSRom,
    rom: Rom | None,
    scan_type: ScanType,
    roms_ids: list[int],
    metadata_sources: list[str],
    launchbox_remote_enabled: bool,
    playmatch_enabled: bool,
    socket_manager: socketio.AsyncRedisManager,
    scan_stats: ScanStats,
    metadata_locale: str | None = None,
    metadata_only: bool = False,
) -> None:
    require_scan_write_context()
    from handler.scan_operation_worker import check_worker_boundary

    check_worker_boundary()
    # Break early if the flag is set
    if redis_client.get(STOP_SCAN_FLAG):
        return

    # Update properties that don't require metadata
    parsed_tags = get_fs_rom_handler().parse_tags(fs_rom["fs_name"])
    roms_path = get_fs_rom_handler().get_logical_roms_fs_structure(platform.fs_slug)

    rom_attrs = {
        "fs_name": fs_rom["fs_name"],
        "fs_path": roms_path,
        "regions": parsed_tags.regions,
        "revision": parsed_tags.revision,
        "version": parsed_tags.version,
        "languages": parsed_tags.languages,
        "tags": parsed_tags.other_tags,
        "platform_id": platform.id,
        "name": get_fs_rom_handler().get_file_name_with_no_tags(fs_rom["fs_name"]),
        "url_cover": "",
        "url_manual": "",
        "url_screenshots": [],
    }

    calculate_hashes = not cm.get_config().SKIP_HASH_CALCULATION

    from handler.windows_quick_execution import (
        current_windows_quick,
        inventory_binding,
        prepare_quick_refresh,
        reconcile_quick_files,
    )

    quick = current_windows_quick()
    if quick is not None:
        candidate = rom if rom is not None else Rom(**rom_attrs, platform=platform)
        await prepare_quick_refresh(
            quick, get_fs_rom_handler(), candidate, calculate_hashes=calculate_hashes
        )

    newly_added: bool = rom is None
    reassociated: bool = False
    files_built: bool = False

    if rom is None:
        # No entry matches this filename. Before treating it as new, hash
        # the files and check whether they belong to an existing entry that went
        # missing (a renamed or moved ROM), so its collections, notes, and
        # uploaded assets carry over instead of being orphaned on a duplicate.
        parsed_rom_files = (
            quick.files
            if quick is not None
            else await get_fs_rom_handler().get_rom_files(
                Rom(**rom_attrs, platform=platform),
                calculate_hashes=calculate_hashes,
            )
        )
        fs_rom.update(
            {
                "files": parsed_rom_files.rom_files,
                "crc_hash": parsed_rom_files.crc_hash,
                "md5_hash": parsed_rom_files.md5_hash,
                "sha1_hash": parsed_rom_files.sha1_hash,
                "ra_hash": parsed_rom_files.ra_hash,
            }
        )
        files_built = True

        missing_match = db_rom_handler.get_matching_missing_rom(
            platform_id=platform.id,
            logical_path=f"{roms_path}/{fs_rom['fs_name']}",
            crc_hash=parsed_rom_files.crc_hash,
            md5_hash=parsed_rom_files.md5_hash,
            sha1_hash=parsed_rom_files.sha1_hash,
        )
        if missing_match is not None:
            # Move the existing entry onto the new file, clearing its missing state.
            rom = db_rom_handler.update_rom(
                missing_match.id,
                {
                    "fs_name": fs_rom["fs_name"],
                    "fs_path": roms_path,
                    "regions": parsed_tags.regions,
                    "revision": parsed_tags.revision,
                    "version": parsed_tags.version,
                    "languages": parsed_tags.languages,
                    "tags": parsed_tags.other_tags,
                    "missing_from_fs": False,
                },
            )
            reassociated = True
            newly_added = False
            log.info(
                f"Reassociated {hl(fs_rom['fs_name'])} with existing entry "
                f"{hl(rom.name or rom.fs_name, color=BLUE)} by file hash"
            )
        else:
            try:
                rom = db_rom_handler.add_rom(Rom(**rom_attrs))
            except IntegrityError:
                # A concurrent scan already created this ROM, so skip it here.
                log.debug(
                    f"Skipping {hl(fs_rom['fs_name'])}: already created by a concurrent scan"
                )
                return

    # Build rom files object before scanning. A reassociated ROM always rebuilds
    # its files so the stale paths from the old filename are replaced.
    should_update_files = not metadata_only and (
        quick is not None
        or reassociated
        or _should_get_rom_files(
            scan_type=scan_type,
            rom=rom,
            newly_added=newly_added,
            roms_ids=roms_ids,
        )
    )
    if should_update_files and not files_built:
        # Get hash calculation setting from config
        if calculate_hashes:
            log.debug(f"Calculating file hashes for {rom.fs_name}...")

        parsed_rom_files = (
            quick.files
            if quick is not None
            else await get_fs_rom_handler().get_rom_files(
                rom, calculate_hashes=calculate_hashes
            )
        )
        fs_rom.update(
            {
                "files": parsed_rom_files.rom_files,
                "crc_hash": parsed_rom_files.crc_hash,
                "md5_hash": parsed_rom_files.md5_hash,
                "sha1_hash": parsed_rom_files.sha1_hash,
                "ra_hash": parsed_rom_files.ra_hash,
            }
        )

    log.debug(f"Scanning {rom.fs_name}...")
    scanned_rom = await scan_rom(
        scan_type=scan_type,
        platform=platform,
        rom=rom,
        fs_rom=fs_rom,
        metadata_sources=metadata_sources,
        newly_added=newly_added,
        launchbox_remote_enabled=launchbox_remote_enabled,
        playmatch_enabled=playmatch_enabled,
        metadata_locale=metadata_locale,
        metadata_only=metadata_only,
        socket_manager=socket_manager,
    )

    await scan_stats.increment(
        socket_manager=socket_manager,
        scanned_roms=1,
        new_roms=1 if newly_added else 0,
        identified_roms=1 if scanned_rom.is_identified else 0,
    )

    _added_rom = merge_scan_rom(scanned_rom)

    catalog_lifecycle_handler.reconnect_retained_identity(
        rom_id=_added_rom.id,
        platform_id=platform.id,
        logical_path=f"{roms_path}/{fs_rom['fs_name']}",
        crc_hash=fs_rom["crc_hash"],
        md5_hash=fs_rom["md5_hash"],
        sha1_hash=fs_rom["sha1_hash"],
    )

    if _added_rom.is_identified:
        await _emit_scanning_rom(socket_manager, _added_rom)

    if quick is not None and quick.binding is None:
        quick.binding = inventory_binding(
            _added_rom, fs_rom.get("scan_relative_path", _added_rom.fs_name)
        )

    if should_update_files:
        # Reconcile against the existing rows instead of replacing them, so file
        # ids survive a rescan and anything keyed on them (track metadata,
        # persisted soundtrack covers) stays valid.
        with ScanMediaBatch(
            _added_rom.id, _added_rom.platform_id, fs_resource_handler.storage
        ) as unit:
            if quick is not None:
                synced, synced_components = unit.publish_and_associate(
                    lambda session: reconcile_quick_files(
                        quick, get_fs_rom_handler(), _added_rom, session
                    )
                )
                quick.files_reconciled = True
                quick.components_reconciled = True
                from handler.scan_handler import auto_link_pc_dlc_components

                auto_link_pc_dlc_components(rom, synced_components)
            else:
                synced = unit.publish_and_associate(
                    lambda session: db_rom_handler.sync_rom_files(
                        _added_rom.id, fs_rom["files"], session=session
                    )
                )
        for saved in synced.files:
            persist_soundtrack_cover(saved, _added_rom)

    if (
        not metadata_only
        and platform.slug == UPS.WIN
        and isinstance(_added_rom.igdb_metadata, dict)
    ):
        enriched_parent = db_rom_handler.apply_pc_igdb_enrichment(
            _added_rom.id,
            _added_rom.updated_at,
            {
                "igdb_id": _added_rom.igdb_id,
                "name": _added_rom.name,
                "summary": _added_rom.summary,
                "igdb_metadata": _added_rom.igdb_metadata,
            },
        )
        if enriched_parent is not None:
            _added_rom = enriched_parent
            refreshed_rom = db_rom_handler.get_rom(_added_rom.id)
            if refreshed_rom is not None:
                _added_rom = refreshed_rom
        scan_target = db_rom_handler.get_rom(_added_rom.id)
        if scan_target is not None:
            for component in scan_target.components:
                await _enrich_pc_dlc_from_igdb(scan_target, component)

    # Short circuit if the scan type is hashes
    if scan_type == ScanType.HASHES or metadata_only:
        from handler.scan_operation_checkpoint import record_completed_game

        record_completed_game(_added_rom)
        return

    try:
        await publish_rom_resources(
            fs_resource_handler,
            _added_rom,
            rom,
            complete=scan_type == ScanType.COMPLETE,
        )
    except (ValueError, OSError, TransportError, DecodingError) as error:
        log.warning(
            "Scan resource replacement retained prior references (%s)",
            type(error).__name__,
        )
    _added_rom = db_rom_handler.get_rom(_added_rom.id)
    if _added_rom is None:
        raise ValueError("Scan catalog target disappeared")
    media_expected_version = _added_rom.updated_at
    # Keep the legacy resource paths for compatibility, but also reconcile
    # provider images into the canonical owned-media catalog used by the v2
    # media surfaces. Without this bridge a normal scan downloads screenshots
    # successfully while the new UI sees an empty owned_media collection.
    if _added_rom.url_cover or _added_rom.url_screenshots:
        try:
            refreshed_rom, media_failures = await refresh_provider_owned_media(
                _added_rom,
                media_expected_version,
                metadata_sources[0] if metadata_sources else "provider",
            )
            _added_rom = refreshed_rom
            for failure in media_failures:
                log.warning(
                    "Provider media item failed for ROM %s (%s/%s): %s",
                    _added_rom.id,
                    failure.role.value,
                    failure.provider_media_id,
                    failure.reason,
                )
        except (ValueError, OSError, TransportError, DecodingError) as exc:
            log.warning(
                "Provider media catalog refresh failed for ROM %s: %s",
                _added_rom.id,
                exc,
            )

    pending = getattr(scanned_rom, "_pending_scan_media", {})
    for source, field in (
        (MetadataSource.SS, "ss_metadata"),
        (MetadataSource.GAMELIST, "gamelist_metadata"),
        (MetadataSource.LAUNCHBOX, "launchbox_metadata"),
    ):
        if source not in metadata_sources:
            continue
        desired = pending.get(field, {})
        for media_type in get_preferred_media_types():
            key = f"{media_type.value}_path"
            path, url = desired.get(key), desired.get(f"{media_type.value}_url")
            if not path or not url:
                continue
            try:
                with ScanMediaBatch(
                    _added_rom.id, platform.id, fs_resource_handler.storage
                ) as unit:
                    generated = await fs_resource_handler.store_media_file(
                        add_ss_auth_to_url(url), path
                    )

                    def associate_special(
                        session, field=field, key=key, generated=generated
                    ):
                        current = db_rom_handler.get_rom(_added_rom.id, session=session)
                        metadata = dict(getattr(current, field) or {})
                        metadata[key] = generated
                        return db_rom_handler.update_rom(
                            current.id, {field: metadata}, session=session
                        )

                    unit.publish_and_associate(associate_special)
            except (ValueError, OSError, TransportError, DecodingError) as error:
                log.warning(
                    "Scan special media retained prior reference (%s)",
                    type(error).__name__,
                )

    if MetadataSource.RA in metadata_sources and "achievements" in pending.get(
        "ra_metadata", {}
    ):
        from copy import deepcopy

        try:
            achievements = deepcopy(pending["ra_metadata"]["achievements"])
            output_limit = sum(
                bool(item.get("badge_url" + suffix) and item.get("badge_path" + suffix))
                for item in achievements
                for suffix in ("", "_lock")
            )
            with ScanMediaInventory(
                _added_rom.id,
                platform.id,
                fs_resource_handler.storage,
                output_limit=output_limit,
            ) as unit:
                for achievement in achievements:
                    for suffix in ("", "_lock"):
                        url, path = achievement.get(
                            "badge_url" + suffix
                        ), achievement.get("badge_path" + suffix)
                        if url and path:
                            achievement["badge_path" + suffix] = (
                                await fs_resource_handler.store_ra_badge(url, path)
                            )

                def associate_badges(session):
                    current = db_rom_handler.get_rom(_added_rom.id, session=session)
                    metadata = deepcopy(current.ra_metadata or {})
                    metadata["achievements"] = achievements
                    return db_rom_handler.update_rom(
                        current.id, {"ra_metadata": metadata}, session=session
                    )

                unit.publish_and_associate(associate_badges)
        except (ValueError, OSError, TransportError, DecodingError) as error:
            log.warning(
                "Scan badges retained prior references (%s)", type(error).__name__
            )
    await _emit_scanning_rom(socket_manager, _added_rom)

    from handler.scan_pc_automation_observation import observe_pc_automation

    await observe_pc_automation(
        process_pc_automation_after_scan,
        platform,
        scanned_rom,
        _added_rom,
        newly_added,
        selected=MetadataSource.STEAM in metadata_sources,
    )
    from handler.scan_operation_checkpoint import record_completed_game

    record_completed_game(_added_rom)


async def _identify_platform(
    platform_slug: str,
    scan_type: ScanType,
    fs_platforms: list[str],
    roms_ids: list[int],
    metadata_sources: list[str],
    launchbox_remote_enabled: bool,
    playmatch_enabled: bool,
    socket_manager: socketio.AsyncRedisManager,
    scan_stats: ScanStats,
    metadata_locale: str | None = None,
    metadata_only: bool = False,
    filesystem_scope_path: str | None = None,
) -> ScanStats:
    # Stop the scan if the flag is set
    if redis_client.get(STOP_SCAN_FLAG):
        raise ScanStoppedException()

    platform = db_platform_handler.get_platform_by_fs_slug(platform_slug)
    if platform and scan_type == ScanType.NEW_PLATFORMS:
        return scan_stats

    scanned_platform = await scan_platform(platform_slug, fs_platforms)
    if platform:
        scanned_platform.id = platform.id

    await scan_stats.increment(
        socket_manager=socket_manager,
        scanned_platforms=1,
        new_platforms=1 if not platform else 0,
        identified_platforms=1 if scanned_platform.is_identified else 0,
    )

    platform = db_platform_handler.add_platform(scanned_platform)

    # Preparse the platform's gamelist.xml file and cache it
    if MetadataSource.GAMELIST in metadata_sources:
        await meta_gamelist_handler.populate_cache(platform)

    # Scanning firmware
    try:
        fs_firmware = await fs_firmware_handler.get_firmware(platform.fs_slug)
    except FirmwareNotFoundException:
        fs_firmware = []

    if len(fs_firmware) == 0:
        log.warning(
            f"{hl(emoji.EMOJI_WARNING, color=LIGHTYELLOW)} No firmware found for {hl(platform.custom_name or platform.name, color=BLUE)}[{hl(platform.fs_slug)}]"
        )
    else:
        log.info(f"{hl(str(len(fs_firmware)))} firmware files found")

    new_firmware = 0
    for fs_fw in fs_firmware:
        new_firmware += await _identify_firmware(
            platform=platform,
            fs_fw=fs_fw,
        )

    # `new_firmware_count` is scoped to this scan: the client reports what the
    # scan discovered, not the platform's total firmware library.
    await socket_manager.emit(
        "scan:scanning_platform",
        {
            **PlatformSchema.model_validate(platform).model_dump(
                include={
                    "id",
                    "name",
                    "display_name",
                    "slug",
                    "fs_slug",
                    "is_identified",
                }
            ),
            "new_firmware_count": new_firmware,
        },
    )

    # This reduces the number of socket emissions
    await scan_stats.increment(
        socket_manager=socket_manager,
        scanned_firmware=len(fs_firmware),
        new_firmware=new_firmware,
    )

    try:
        fs_roms = await get_fs_rom_handler().get_roms(platform)
    except RomsNotFoundException as e:
        log.error(e)
        return scan_stats

    from handler.scan_collection_discovery import (
        collection_inventory,
        filesystem_identity,
        identify_collection_game,
    )

    fs_roms, classified_inventory = collection_inventory(
        platform, fs_roms, filesystem_scope_path
    )

    if len(fs_roms) == 0:
        log.warning(
            f"{hl(emoji.EMOJI_WARNING, color=LIGHTYELLOW)} No roms found, verify that the folder structure is correct"
        )
    else:
        log.info(f"{hl(str(len(fs_roms)))} roms found in the file system")

    # Snapshot the missing entries before the sync below clears the flag for any
    # whose file is back, so the skip path can still tell the client about them.
    previously_missing_rom_ids = db_rom_handler.get_missing_rom_ids(platform.id)

    # Flag entries whose file is gone before identifying files, so a renamed or
    # moved ROM (a new file with no fs_name match) can be reassociated by hash
    # with its now-missing entry instead of spawning a duplicate. The end-of-scan
    # call below re-syncs and logs, unmarking any entry that got reassociated.
    fs_rom_names = [rom["fs_name"] for rom in fs_roms]
    if filesystem_scope_path is None:
        from handler.scan_known_paths import present_known_nested_roms

        known_nested = present_known_nested_roms(
            get_fs_rom_handler(),
            platform.fs_slug,
            db_rom_handler.get_rom_filesystem_paths(platform.id),
        )
        fs_rom_names.extend(rom.fs_name for rom in known_nested)
        identities = {
            filesystem_identity(get_fs_rom_handler(), platform, entry)
            for entry in fs_roms
        }
        identities.update((rom.fs_path, rom.fs_name) for rom in known_nested)
        missing_options = (
            {"filesystem_identities": identities} if classified_inventory else {}
        )
        db_rom_handler.mark_missing_roms(platform.id, fs_rom_names, **missing_options)

    from handler.scan_inventory_contracts import QuickScanDecision
    from handler.scan_inventory_status import emit_inventory_status
    from handler.windows_quick_execution import (
        WindowsQuickContext,
        bind_windows_quick,
        inspect_discovered_game,
    )

    quick_contexts: dict[int, WindowsQuickContext] = {}
    # Create semaphore to limit concurrent ROM scanning
    scan_semaphore = asyncio.Semaphore(SCAN_WORKERS)

    async def scan_rom_with_semaphore(fs_rom: FSRom, rom: Rom | None) -> None:
        """Scan a single ROM with semaphore limiting"""
        async with scan_semaphore:
            with bind_windows_quick(quick_contexts.get(id(fs_rom))):
                await identify_collection_game(
                    fs_rom,
                    _identify_rom,
                    platform=platform,
                    rom=rom,
                    scan_type=scan_type,
                    roms_ids=roms_ids,
                    metadata_sources=metadata_sources,
                    launchbox_remote_enabled=launchbox_remote_enabled,
                    playmatch_enabled=playmatch_enabled,
                    metadata_locale=metadata_locale,
                    metadata_only=metadata_only,
                    socket_manager=socket_manager,
                    scan_stats=scan_stats,
                )
                quick = quick_contexts.get(id(fs_rom))
                if quick is not None and quick.binding is not None:
                    completed = db_rom_handler.get_rom(quick.binding.rom_id)
                    if completed is not None:
                        await emit_inventory_status(
                            socket_manager,
                            quick,
                            completed,
                            existing_game=rom is not None,
                        )

    for fs_roms_batch in batched(fs_roms, 200, strict=False):
        roms_by_fs_name = db_rom_handler.get_roms_by_fs_name(
            platform_id=platform.id,
            fs_names={fs_rom["fs_name"] for fs_rom in fs_roms_batch},
        )

        collection_roms = (
            db_rom_handler.get_roms_by_filesystem_identity(
                platform.id,
                {
                    filesystem_identity(get_fs_rom_handler(), platform, entry)
                    for entry in fs_roms_batch
                },
            )
            if classified_inventory
            else {}
        )

        # Separate skipped ROMs from those that need scanning
        skipped_rom_ids: list[int] = []
        restored_roms: list[Rom] = []
        roms_to_scan: list[tuple[FSRom, Rom | None]] = []

        for fs_rom in fs_roms_batch:
            rom = (
                collection_roms.get(
                    filesystem_identity(get_fs_rom_handler(), platform, fs_rom)
                )
                if classified_inventory
                else roms_by_fs_name.get(fs_rom["fs_name"])
            )
            quick = await inspect_discovered_game(
                platform,
                fs_rom,
                rom,
                scan_type=scan_type.value,
                rom_ids=roms_ids,
                metadata_only=metadata_only,
            )
            if quick is not None:
                quick_contexts[id(fs_rom)] = quick
                if rom is not None:
                    await emit_inventory_status(
                        socket_manager, quick, rom, existing_game=True
                    )
                if quick.decision == QuickScanDecision.INCOMPLETE:
                    from handler.filesystem.pc_scan_inventory import InventoryIncomplete

                    raise InventoryIncomplete(
                        quick.before.reason or "incomplete_evidence"
                    )
                if quick.decision in {
                    QuickScanDecision.REUSE,
                    QuickScanDecision.METADATA_ONLY,
                }:
                    assert rom is not None
                    skipped_rom_ids.append(rom.id)
                    continue
            if quick is not None or should_scan_rom(
                scan_type=scan_type,
                rom=rom,
                roms_ids=roms_ids,
                metadata_sources=metadata_sources,
                fs_rom=fs_rom,
            ):
                roms_to_scan.append((fs_rom, rom))
            elif rom:
                skipped_rom_ids.append(rom.id)
                if rom.id in previously_missing_rom_ids:
                    restored_roms.append(rom)

        # Bulk update all skipped ROMs in one query instead of per-ROM updates
        if skipped_rom_ids:
            db_rom_handler.bulk_mark_present(platform.id, skipped_rom_ids)
            await scan_stats.increment(
                socket_manager=socket_manager,
                scanned_roms=len(skipped_rom_ids),
            )

        # Skipped ROMs emit nothing, so a ROM whose file came back would keep its
        # stale "missing" badge in an open gallery until a refetch. Reload with
        # details since the scan-loop lookup only eager-loads the platform.
        for restored_rom in restored_roms:
            log.info(
                f"{hl(restored_rom.fs_name)} is back in the filesystem, "
                f"no longer {hl('missing', color=LIGHTYELLOW)}"
            )
            hydrated_rom = db_rom_handler.get_rom(restored_rom.id)
            if hydrated_rom is None:
                continue

            await _emit_scanning_rom(socket_manager, hydrated_rom)

        # Process only ROMs that actually need scanning
        scan_tasks = [
            scan_rom_with_semaphore(fs_rom=fs_rom, rom=rom)
            for fs_rom, rom in roms_to_scan
        ]

        if scan_tasks:
            batched_results = await asyncio.gather(*scan_tasks, return_exceptions=True)
            for result, (_fs_rom, _) in zip(
                batched_results, roms_to_scan, strict=False
            ):
                if isinstance(result, BaseException):
                    raise result
        quick_contexts.clear()

    missing_roms = (
        db_rom_handler.mark_missing_roms(platform.id, fs_rom_names, **missing_options)
        if filesystem_scope_path is None
        else []
    )
    if len(missing_roms) > 0:
        log.warning(f"{hl('Missing')} roms from filesystem:")
        for r in missing_roms:
            log.warning(f" - {r.fs_name}")

    missing_firmware = db_firmware_handler.mark_missing_firmware(
        platform.id, [fw for fw in fs_firmware]
    )
    if len(missing_firmware) > 0:
        log.warning(f"{hl('Missing')} firmware from filesystem:")
        for f in missing_firmware:
            log.warning(f" - {f}")

    if MetadataSource.SS in metadata_sources:
        log_ss_quota()

    return scan_stats


@initialize_context()
async def scan_platforms(
    platform_ids: list[int],
    metadata_sources: list[str],
    scan_type: ScanType = ScanType.QUICK,
    roms_ids: list[int] | None = None,
    launchbox_remote_enabled: bool = True,
    playmatch_enabled: bool = True,
    platform_fs_slugs: list[str] | None = None,
    filesystem_platform_scope: list[str] | None = None,
    metadata_locale: str | None = None,
    metadata_only: bool = False,
    media_only: bool = False,
    filesystem_scope_path: str | None = None,
) -> ScanStats:
    """Scan all the listed platforms and fetch metadata from different sources

    Args:
        platform_ids (list[int]): List of platform ids to be scanned
        metadata_sources (list[str]): List of metadata sources to be used
        scan_type (ScanType): Type of scan to be performed.
        roms_ids (list[int], optional): List of selected roms to be scanned.
        platform_fs_slugs (list[str], optional): Folders to scan with no database row.
    """
    require_scan_write_context()
    from handler.scan_operation_worker import check_worker_boundary

    check_worker_boundary()
    with cast(
        ScanCapability,
        open_storage_access(legacy_external_storage, StorageOperation.SCAN, ""),
    ) as access:
        access.scan()

    # The flag is cleared by the scan that observes it, so one set against a
    # scan that ended first would otherwise stop this one before it began. A
    # scan still on a worker owns the flag though, and clearing it there would
    # let a stopped scan carry on.
    running_job = _get_running_scan_job()
    current_job = get_current_job()
    if running_job is None or (
        current_job is not None and running_job.id == current_job.id
    ):
        redis_client.delete(STOP_SCAN_FLAG)

    if not roms_ids:
        roms_ids = []

    if not platform_fs_slugs:
        platform_fs_slugs = []

    socket_manager = _get_socket_manager()
    scan_stats = ScanStats()

    if media_only:
        if metadata_only:
            raise ValueError("media_only and metadata_only cannot be combined")
        existing_roms = list(
            db_rom_handler.get_roms_scalar(
                platform_ids=platform_ids or None,
            )
        )
        requested_ids = set(roms_ids or [])
        if requested_ids:
            existing_roms = [rom for rom in existing_roms if rom.id in requested_ids]
        await scan_stats.update(
            socket_manager=socket_manager,
            total_platforms=0,
            total_roms=len(existing_roms),
        )
        semaphore = asyncio.Semaphore(SCAN_WORKERS)

        async def refresh_existing_rom(rom: Rom) -> None:
            async with semaphore:
                try:
                    rom, hydrated_provider = await _hydrate_media_urls(
                        rom, metadata_sources, metadata_locale
                    )
                    refreshed, media_failures = await refresh_provider_owned_media(
                        rom,
                        rom.updated_at,
                        hydrated_provider
                        or (metadata_sources[0] if metadata_sources else "provider"),
                    )
                except (ValueError, OSError) as exc:
                    log.warning("Media-only refresh failed for %s: %s", rom.id, exc)
                    return
                for failure in media_failures:
                    log.warning(
                        "Provider media item failed for ROM %s (%s/%s): %s",
                        rom.id,
                        failure.role.value,
                        failure.provider_media_id,
                        failure.reason,
                    )
                await scan_stats.increment(
                    socket_manager=socket_manager,
                    scanned_roms=1,
                    identified_roms=1 if refreshed.is_identified else 0,
                )
                await _emit_scanning_rom(socket_manager, refreshed)

        await asyncio.gather(*(refresh_existing_rom(rom) for rom in existing_roms))
        await socket_manager.emit("scan:done", scan_stats.to_dict())
        return scan_stats

    # ScreenScraper's scan state is process-global, so a scan that never touches
    # it must leave it alone: under DEV_MODE scans run in-process and can
    # overlap, and resetting would drop the other scan's limits and skips.
    if MetadataSource.SS in metadata_sources:
        await begin_ss_scan()

    if filesystem_platform_scope is not None:
        fs_platforms = filesystem_platform_scope
    else:
        try:
            fs_platforms = await fs_platform_handler.get_platforms()
        except FolderStructureNotMatchException as e:
            log.error(e)
            await socket_manager.emit("scan:done_ko", e.message)
            return scan_stats

    # Clear the gamelist cache to ensure we're using fresh gamelist.xml data
    meta_gamelist_handler.clear_cache()

    # Initialize HLTB handler (fetches current search endpoint and security token)
    if MetadataSource.HLTB in metadata_sources:
        meta_hltb_handler.initialize()

    # Resolve the platforms that will actually be scanned. When no platform ids
    # are provided, every filesystem platform is scanned.
    db_platforms = db_platform_handler.get_platforms()
    db_platforms_by_slug = {
        canonicalize_filesystem_slug(p.fs_slug): p for p in db_platforms
    }

    # Selected platforms arrive as database ids and/or filesystem slugs.
    selected_slugs = [
        canonicalize_filesystem_slug(p.fs_slug)
        for p in db_platforms
        if p.id in platform_ids
    ]
    filesystem_slugs = {
        canonicalize_filesystem_slug(fs_slug) for fs_slug in fs_platforms
    }
    for fs_slug in platform_fs_slugs:
        fs_slug = canonicalize_filesystem_slug(fs_slug)
        if fs_slug in selected_slugs:
            continue
        if fs_slug in db_platforms_by_slug or fs_slug in filesystem_slugs:
            selected_slugs.append(fs_slug)

    has_selection = bool(platform_ids or platform_fs_slugs)
    platform_list = sorted(
        set(selected_slugs)
        if has_selection
        else {canonicalize_filesystem_slug(fs_slug) for fs_slug in fs_platforms}
    )

    # A "new platforms" scan skips platforms that already exist in the database,
    # so they must be excluded from the totals to keep the tracker accurate. This
    # mirrors the existence check done per-platform in _identify_platform, reusing
    # the platforms already fetched above instead of querying again per platform.
    platforms_to_scan = platform_list
    if scan_type == ScanType.NEW_PLATFORMS:
        platforms_to_scan = [
            platform_slug
            for platform_slug in platform_list
            if db_platforms_by_slug.get(platform_slug) is None
        ]

    total_roms = 0
    for platform_slug in platforms_to_scan:
        try:
            from handler.scan_collection_discovery import count_scan_inventory

            total_roms += await count_scan_inventory(
                Platform(fs_slug=platform_slug), filesystem_scope_path
            )
        except RomsNotFoundException as e:
            log.error(e)

    await scan_stats.update(
        socket_manager=socket_manager,
        total_platforms=len(platforms_to_scan),
        total_roms=total_roms,
    )

    async def stop_scan():
        log.info(f"{emoji.EMOJI_STOP_SIGN} Scan stopped manually")
        await socket_manager.emit("scan:done", scan_stats.to_dict())
        redis_client.delete(STOP_SCAN_FLAG)

    try:
        if len(platform_list) == 0:
            log.warning(
                f"{hl(emoji.EMOJI_WARNING, color=LIGHTYELLOW)} No platforms found, verify that the folder structure is right and the volume is mounted correctly."
                f"{FOLDER_STRUCT_MSG}"
            )
        else:
            log.info(
                f"Found {hl(str(len(platform_list)))} platforms in the file system"
            )

        for platform_slug in platform_list:
            scan_stats = await _identify_platform(
                platform_slug=platform_slug,
                scan_type=scan_type,
                fs_platforms=fs_platforms,
                roms_ids=roms_ids,
                metadata_sources=metadata_sources,
                launchbox_remote_enabled=launchbox_remote_enabled,
                playmatch_enabled=playmatch_enabled,
                metadata_locale=metadata_locale,
                metadata_only=metadata_only,
                socket_manager=socket_manager,
                scan_stats=scan_stats,
                filesystem_scope_path=filesystem_scope_path,
            )

        missed_platforms = db_platform_handler.mark_missing_platforms(
            fs_platforms,
            platform_ids=(
                platform_ids if filesystem_platform_scope is not None else None
            ),
        )
        if len(missed_platforms) > 0:
            log.warning(f"{hl('Missing')} platforms from filesystem:")
            for p in missed_platforms:
                log.warning(f" - {p.slug} ({p.fs_slug})")

        if MetadataSource.SS in metadata_sources:
            log_ss_scan_summary()

        log.info(f"{emoji.EMOJI_CHECK_MARK} Scan completed")

        # The library changed; drop cached filter values.
        db_rom_handler.invalidate_filter_values_cache()

        # Smart collection membership is derived from the library, and is no
        # longer recomputed while serving a gallery page. The scan itself is
        # done, so a failure here must not report it as one.
        try:
            db_collection_handler.refresh_smart_collections()
        except (ScanWriteRejected, IndeterminateOwnedPublicationError, SQLAlchemyError):
            raise
        except Exception as e:
            log.error(f"Couldn't refresh smart collections after the scan: {e}")

        # Export metadata files if enabled in config
        config = cm.get_config()

        # Update the list of platforms after the scan to ensure we have the latest data
        db_platforms = db_platform_handler.get_platforms()
        db_platforms_by_slug = {p.fs_slug: p for p in db_platforms}

        if config.GAMELIST_AUTO_EXPORT_ON_SCAN or config.PEGASUS_AUTO_EXPORT_ON_SCAN:
            from handler.filesystem.scan_output_publication import export_scan_platform

            for platform_slug in platform_list:
                platform = db_platforms_by_slug.get(platform_slug)
                if platform is not None:
                    export_scan_platform(
                        platform.id,
                        gamelist=config.GAMELIST_AUTO_EXPORT_ON_SCAN,
                        pegasus=config.PEGASUS_AUTO_EXPORT_ON_SCAN,
                    )

        await socket_manager.emit("scan:done", scan_stats.to_dict())
    except ScanStoppedException:
        await stop_scan()
    except (ScanWriteRejected, IndeterminateOwnedPublicationError, SQLAlchemyError):
        raise
    except Exception as e:
        log.error(f"Error in scan_platform: {e}")
        # Catch all exceptions and emit error to the client
        await socket_manager.emit("scan:done_ko", str(e))
        # Re-raise the exception to be caught by the error handler
        raise e

    return scan_stats


async def execute_mapping_scan(
    command: MappedScanCommand,
    *,
    metadata_sources: list[str],
    scan_type: ScanType = ScanType.QUICK,
    roms_ids: list[int] | None = None,
    launchbox_remote_enabled: bool = True,
    playmatch_enabled: bool = True,
    metadata_locale: str | None = None,
    metadata_only: bool = False,
    media_only: bool = False,
) -> ScanStats:
    """Run a scan from immutable mapping identity, never a caller-supplied path."""
    mapping = db_storage_handler.get_mapping(command.mapping_id)
    scope_path = dict(command.options).get("relative_path")

    async def _scan_batch(
        _command: MappedScanCommand, _entries: list[str], _context: object
    ) -> ScanStats:
        scoped_handler = fs_rom_handler.for_mapping(mapping, scope_path)
        with use_fs_rom_handler(scoped_handler):
            return await scan_platforms(
                platform_ids=[mapping.platform_id],
                metadata_sources=metadata_sources,
                scan_type=ScanType(command.scan_type),
                roms_ids=roms_ids,
                launchbox_remote_enabled=launchbox_remote_enabled,
                playmatch_enabled=playmatch_enabled,
                metadata_locale=metadata_locale,
                metadata_only=metadata_only,
                media_only=media_only,
                filesystem_platform_scope=[mapping.platform.fs_slug],
                filesystem_scope_path=scope_path,
            )

    return await execute_mapped_scan(
        cast(HandlerMappedScanCommand, command),
        _scan_batch,
    )


def mapping_scan_commands(
    platform_ids: list[int],
    *,
    trigger: ScanTrigger,
    scope: ScanScope,
    scan_type: ScanType,
    platform_fs_slugs: list[str] | None = None,
    filesystem_scope_paths: dict[str, str] | None = None,
) -> list[MappedScanCommand]:
    """Freeze the active mapping revision for each selected platform."""
    platforms = db_platform_handler.get_platforms()
    selected_fs_slugs = set(platform_fs_slugs or [])
    selected = (
        [platform for platform in platforms if platform.id in platform_ids]
        if platform_ids
        else [
            platform
            for platform in platforms
            if not selected_fs_slugs or platform.fs_slug in selected_fs_slugs
        ]
    )
    commands = []
    for platform in selected:
        try:
            mapping = db_storage_handler.get_active_mapping(platform.id)
            health = get_storage_root_health_snapshot(mapping.storage_root)
            if health.non_writable is not True:
                log.info(
                    "Skipping writable or unhealthy mapping for platform %s",
                    platform.fs_slug,
                )
                continue
        except (MissingPlatformStorageMappingError, StorageResolutionError):
            continue
        options: tuple[tuple[str, str], ...] = ()
        scope_path = (filesystem_scope_paths or {}).get(platform.fs_slug)
        if scope_path:
            options = (("relative_path", scope_path),)
        commands.append(
            MappedScanCommand(
                mapping_id=mapping.id,
                expected_revision=mapping.version,
                trigger=trigger,
                scope=scope,
                scan_type=scan_type.value,
                options=options,
            )
        )
    return commands


async def execute_mapping_scans(
    commands: list[MappedScanCommand],
    *,
    metadata_sources: list[str],
    roms_ids: list[int] | None = None,
    launchbox_remote_enabled: bool = True,
    playmatch_enabled: bool = True,
    metadata_locale: str | None = None,
    metadata_only: bool = False,
    media_only: bool = False,
) -> ScanStats:
    """Execute mapping commands through the common executor."""
    combined = ScanStats()
    for command in commands:
        result = await execute_mapping_scan(
            command,
            metadata_sources=metadata_sources,
            roms_ids=roms_ids,
            launchbox_remote_enabled=launchbox_remote_enabled,
            playmatch_enabled=playmatch_enabled,
            metadata_locale=metadata_locale,
            metadata_only=metadata_only,
            media_only=media_only,
        )
        for field in result.to_dict():
            setattr(combined, field, getattr(combined, field) + getattr(result, field))
    return combined


async def execute_mixed_scans(
    commands: list[MappedScanCommand],
    *,
    platform_ids: list[int],
    platform_fs_slugs: list[str],
    metadata_sources: list[str],
    scan_type: ScanType = ScanType.QUICK,
    roms_ids: list[int] | None = None,
    launchbox_remote_enabled: bool = True,
    playmatch_enabled: bool = True,
    metadata_locale: str | None = None,
    metadata_only: bool = False,
    media_only: bool = False,
) -> ScanStats:
    "Run protected PC mappings and writable legacy platforms exactly once."
    combined = ScanStats()
    if commands:
        mapped_result = await execute_mapping_scans(
            commands,
            metadata_sources=metadata_sources,
            roms_ids=roms_ids,
            launchbox_remote_enabled=launchbox_remote_enabled,
            playmatch_enabled=playmatch_enabled,
            metadata_locale=metadata_locale,
            metadata_only=metadata_only,
            media_only=media_only,
        )
        for field in mapped_result.to_dict():
            setattr(
                combined,
                field,
                getattr(combined, field) + getattr(mapped_result, field),
            )

    mapped_platform_ids = {
        db_storage_handler.get_mapping(command.mapping_id).platform_id
        for command in commands
    }
    mapped_fs_slugs = {
        platform.fs_slug
        for platform in db_platform_handler.get_platforms()
        if platform.id in mapped_platform_ids
    }
    legacy_ids = [
        platform_id
        for platform_id in platform_ids
        if platform_id not in mapped_platform_ids
    ]
    if platform_ids or platform_fs_slugs:
        legacy_fs_slugs = [
            slug for slug in platform_fs_slugs if slug not in mapped_fs_slugs
        ]
    else:
        all_fs_slugs = await fs_platform_handler.get_platforms()
        legacy_fs_slugs = [slug for slug in all_fs_slugs if slug not in mapped_fs_slugs]

    if (
        legacy_ids
        or legacy_fs_slugs
        or (not platform_ids and not platform_fs_slugs and not mapped_platform_ids)
    ):
        legacy_result = await scan_platforms(
            platform_ids=legacy_ids,
            metadata_sources=metadata_sources,
            scan_type=scan_type,
            roms_ids=roms_ids,
            launchbox_remote_enabled=launchbox_remote_enabled,
            playmatch_enabled=playmatch_enabled,
            platform_fs_slugs=legacy_fs_slugs,
            metadata_locale=metadata_locale,
            metadata_only=metadata_only,
            media_only=media_only,
        )
        for field in legacy_result.to_dict():
            setattr(
                combined,
                field,
                getattr(combined, field) + getattr(legacy_result, field),
            )
    return combined


async def reject_unauthorized_scan(sid: str) -> bool:
    """Return ``True`` (and notify the caller) if the socket may not run scans.

    Scans are a privileged, destructive operation, so gate them on the same
    ``TASKS_RUN`` scope the REST task endpoints require, resolved from the
    server-side session (never from the client payload).
    """
    user = await get_authenticated_user(sid)
    if user is not None and Scope.TASKS_RUN in user.oauth_scopes:
        return False

    log.warning(f"{emoji.EMOJI_STOP_SIGN} Unauthorized scan request rejected")
    await socket_handler.socket_server.emit(
        "scan:done_ko",
        "You are not authorized to run scans",
        to=sid,
    )
    return True


@socket_handler.socket_server.on("scan")  # type: ignore
async def scan_handler(sid: str, options: dict[str, Any]):
    """Scan socket endpoint

    Args:
        options (dict): Socket options
    """

    if await reject_unauthorized_scan(sid):
        return

    from uuid import uuid4

    from endpoints.responses.scan_operations import ScanOperationRequest
    from handler.database.scan_operations_handler import (
        DBScanOperationsHandler,
        OperationConflict,
    )
    from handler.scan_operation_commands import normalize_scan_request
    from tasks.scan_operation_dispatch import dispatch_operation

    user = await get_authenticated_user(sid)
    if user is None:
        return
    try:
        body = ScanOperationRequest.model_validate(
            options
            | {"request_key": options.get("request_key") or "socket-" + str(uuid4())}
        )
        command = normalize_scan_request(body)
        accepted = DBScanOperationsHandler().accept(user.id, body.request_key, command)
        dispatch_operation(accepted.id)
        return accepted.model_dump(mode="json")
    except (ValueError, OperationConflict, StorageResolutionError):
        await socket_handler.socket_server.emit(
            "scan:done_ko", "scan_request_rejected", to=sid
        )
        return {"error": "scan_request_rejected"}


@socket_handler.socket_server.on("scan:stop")  # type: ignore
async def stop_scan_handler(sid: str):
    """Stop scan socket endpoint"""

    if await reject_unauthorized_scan(sid):
        return

    from uuid import uuid4

    from handler.database.scan_operations_handler import DBScanOperationsHandler
    from models.user import Role

    user = await get_authenticated_user(sid)
    repository = DBScanOperationsHandler()
    active = (
        repository.find_active(user.id, admin=user.role == Role.ADMIN)
        if user is not None
        else None
    )
    if active is None:
        durable_callable = "handler.scan_operation_worker.run_scan_operation"
        queued = [
            job
            for job in _get_queued_scan_jobs()
            if get_job_func_name(job) != durable_callable
        ]
        running = _get_running_scan_job()
        if running is not None and get_job_func_name(running) == durable_callable:
            running = None
        for job in queued:
            job.cancel()
        if running is not None:
            running.cancel()
            redis_client.set(STOP_SCAN_FLAG, 1)
        return None
    if user is None:
        return
    stopped = repository.request_cancel(
        active.id,
        user.id,
        active.version,
        "socket-" + str(uuid4()),
        admin=user.role == Role.ADMIN,
    )
    return stopped.model_dump(mode="json")
