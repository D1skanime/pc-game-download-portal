from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class InventoryKind(StrEnum):
    READ = "read"
    MUTATION = "mutation"
    EXCLUSION = "exclusion"


class InventoryDisposition(StrEnum):
    POLICY_GOVERNED = "policy_governed"
    OWNED_ONLY = "owned_only"
    NON_RUNTIME = "non_runtime"


@dataclass(frozen=True)
class Evidence:
    path: str
    test: str


@dataclass(frozen=True)
class InventoryRow:
    family: str
    module: str
    symbol: str
    kind: InventoryKind
    source_class: str
    destination_class: str
    operations: tuple[str, ...]
    disposition: InventoryDisposition
    enforcement: str
    evidence: Evidence
    explanation: str = ""


_EXTERNAL = "external_read_only"
_OWNED = "romm_owned"
_NONE = "none"
EXTERNAL_AUTHORITY_PROVIDER = (
    "handler.filesystem.storage_composition",
    "build_storage_composition",
)
_READ_EVIDENCE = Evidence(
    "tests/handler/filesystem/test_external_read_consumers.py",
    "test_enumeration_and_scan_modules_declare_exact_capabilities",
)
_ROM_EVIDENCE = Evidence(
    "tests/handler/filesystem/test_external_read_consumers.py",
    "test_rom_consumers_declare_exact_capabilities",
)
_ENDPOINT_EVIDENCE = Evidence(
    "tests/endpoints/test_storage_policy_denials.py",
    "test_external_api_denial_is_bounded_and_precedes_io",
)
_OWNED_EVIDENCE = Evidence(
    "tests/handler/filesystem/test_owned_storage.py",
    "test_composition_classifies_every_closed_owned_location",
)
_TASK_EVIDENCE = Evidence(
    "tests/tasks/test_storage_policy.py",
    "test_cleanup_denial_is_terminal_before_io",
)
_LEGACY_DETECTION_EVIDENCE = Evidence(
    "tests/handler/storage/test_legacy_migration.py",
    "test_detection_uses_only_list_and_stat_capabilities",
)


def _read(
    family: str,
    module: str,
    symbol: str,
    operations: tuple[str, ...],
    evidence: Evidence = _READ_EVIDENCE,
) -> InventoryRow:
    return InventoryRow(
        family,
        module,
        symbol,
        InventoryKind.READ,
        _EXTERNAL,
        _NONE,
        operations,
        InventoryDisposition.POLICY_GOVERNED,
        "handler.filesystem.storage_access:open_storage_access",
        evidence,
    )


def _mutation(
    family: str,
    module: str,
    symbol: str,
    source: str,
    destination: str,
    operations: tuple[str, ...],
    disposition: InventoryDisposition,
    enforcement: str,
    evidence: Evidence,
) -> InventoryRow:
    return InventoryRow(
        family,
        module,
        symbol,
        InventoryKind.MUTATION,
        source,
        destination,
        operations,
        disposition,
        enforcement,
        evidence,
    )


INVENTORY: tuple[InventoryRow, ...] = (
    _read(
        "legacy-detection",
        "tasks.manual.detect_legacy_storage",
        "DetectLegacyStorageTask.run",
        ("LIST", "STAT", "HASH"),
        _LEGACY_DETECTION_EVIDENCE,
    ),
    _read(
        "composition",
        "handler.filesystem.storage_composition",
        "build_storage_composition",
        ("RESOLVE",),
        Evidence(
            "tests/handler/filesystem/test_external_read_consumers.py",
            "test_external_handler_binds_caller_paths_to_composition_descriptor",
        ),
    ),
    _read(
        "firmware",
        "handler.filesystem.firmware_handler",
        "FSFirmwareHandler.get_firmware",
        ("LIST", "READ", "HASH"),
        Evidence(
            "tests/handler/filesystem/test_external_read_consumers.py",
            "test_firmware_hashes_use_read_capability",
        ),
    ),
    _read(
        "platform",
        "handler.filesystem.platforms_handler",
        "FSPlatformsHandler.get_platforms",
        ("LIST",),
    ),
    _read("heartbeat", "endpoints.heartbeat", "heartbeat", ("LIST",)),
    _read(
        "config",
        "config.config_manager",
        "ConfigManager.get_platforms",
        ("LIST",),
    ),
    _read("scan", "handler.scan_handler", "scan_platform", ("SCAN",)),
    _read("socket", "endpoints.sockets.scan", "scan_platform", ("SCAN",)),
    _read("watcher", "watcher", "LibraryEventHandler", ("STAT", "SCAN")),
    _read(
        "rom",
        "handler.filesystem.roms_handler",
        "FSRomsHandler.get_roms",
        ("LIST", "STAT"),
        _ROM_EVIDENCE,
    ),
    _read(
        "hash",
        "handler.filesystem.roms_handler",
        "FSRomsHandler.get_file_hashes",
        ("HASH",),
        _ROM_EVIDENCE,
    ),
    _read(
        "stream",
        "endpoints.streaming",
        "claim_session",
        ("STREAM",),
        _ROM_EVIDENCE,
    ),
    _read(
        "direct-download",
        "endpoints.roms.files",
        "get_romfile_content",
        ("DOWNLOAD",),
        Evidence(
            "tests/handler/filesystem/test_external_read_consumers.py",
            "test_external_downloads_do_not_construct_path_responses",
        ),
    ),
    _mutation(
        "endpoint-mutation",
        "endpoints.roms.upload",
        "upload_rom",
        _OWNED,
        _EXTERNAL,
        ("WRITE",),
        InventoryDisposition.POLICY_GOVERNED,
        "endpoints.storage_policy:authorize_api_storage_operation",
        _ENDPOINT_EVIDENCE,
    ),
    _mutation(
        "archive",
        "utils.archives",
        "extract_file",
        _EXTERNAL,
        _OWNED,
        ("READ", "CREATE", "DELETE"),
        InventoryDisposition.POLICY_GOVERNED,
        "handler.filesystem.storage_access:OwnedCreate",
        Evidence(
            "tests/utils/test_archives.py",
            "test_archive_subprocess_uses_proc_fd_and_pass_fds",
        ),
    ),
    _mutation(
        "zip",
        "utils.zip_cache",
        "build_cached_zip",
        _EXTERNAL,
        _OWNED,
        ("DOWNLOAD", "REPLACE"),
        InventoryDisposition.POLICY_GOVERNED,
        "handler.filesystem.storage_access:OwnedReplace",
        Evidence(
            "tests/utils/test_zip_cache.py",
            "test_build_cached_zip_copies_download_capabilities_to_owned_output",
        ),
    ),
    _mutation(
        "patch",
        "utils.rom_patcher.patcher",
        "RomPatcher.apply_patch",
        _EXTERNAL,
        _OWNED,
        ("READ", "CREATE"),
        InventoryDisposition.POLICY_GOVERNED,
        "handler.filesystem.storage_access:OwnedCreate",
        Evidence(
            "tests/utils/test_rom_patcher.py",
            "test_apply_patch_uses_only_inherited_capability_descriptors",
        ),
    ),
    _mutation(
        "export",
        "utils.gamelist_exporter",
        "export_platform_to_file",
        _OWNED,
        _OWNED,
        ("READ", "REPLACE"),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:OwnedReplace",
        Evidence(
            "tests/utils/test_gamelist_exporter.py",
            "test_export_platform_to_file_requires_owned_destination",
        ),
    ),
    _mutation(
        "export",
        "utils.pegasus_exporter",
        "export_platform_to_file",
        _OWNED,
        _OWNED,
        ("READ", "REPLACE"),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:OwnedReplace",
        Evidence(
            "tests/utils/test_pegasus_exporter.py",
            "test_export_platform_to_file_requires_owned_destination",
        ),
    ),
    _mutation(
        "audio",
        "utils.audio_tags",
        "write_audio_cover",
        _OWNED,
        _OWNED,
        ("READ", "REPLACE", "DELETE"),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        Evidence(
            "tests/utils/test_audio_tags.py",
            "test_audio_cover_write_and_delete_require_separate_owned_capabilities",
        ),
    ),
    _mutation(
        "sync",
        "handler.filesystem.sync_handler",
        "FSSyncHandler",
        _OWNED,
        _OWNED,
        ("LIST", "HASH", "CREATE", "WRITE", "DELETE"),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        Evidence(
            "tests/handler/filesystem/test_sync_handler.py",
            "test_sync_operations_authorize_owned_storage_before_io",
        ),
    ),
    _mutation(
        "sync",
        "handler.sync.ssh_handler",
        "SSHHandler",
        _OWNED,
        _OWNED,
        ("STAT", "CREATE", "WRITE"),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _OWNED_EVIDENCE,
    ),
    _mutation(
        "watcher",
        "sync_watcher",
        "SyncWatcher.move_to_conflict",
        _OWNED,
        _OWNED,
        ("MOVE",),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        Evidence(
            "tests/tasks/test_storage_policy.py",
            "test_cleanup_denial_is_terminal_before_io",
        ),
    ),
    _mutation(
        "bootstrap",
        "handler.filesystem.platforms_handler",
        "FSPlatformsHandler.create_setup_platforms",
        _EXTERNAL,
        _EXTERNAL,
        ("MKDIR",),
        InventoryDisposition.POLICY_GOVERNED,
        "handler.filesystem.storage_policy:StoragePolicy",
        _ENDPOINT_EVIDENCE,
    ),
    _mutation(
        "cleanup",
        "tasks.scheduled.cleanup_orphaned_resources",
        "CleanupOrphanedResourcesTask.run",
        _OWNED,
        _OWNED,
        ("RMTREE",),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _TASK_EVIDENCE,
    ),
    _mutation(
        "cleanup",
        "tasks.scheduled.cleanup_upload_tmp",
        "CleanupUploadTmpTask.run",
        _OWNED,
        _OWNED,
        ("LIST", "STAT", "RMTREE"),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _TASK_EVIDENCE,
    ),
    _mutation(
        "cleanup",
        "tasks.scheduled.cleanup_zip_cache",
        "CleanupZipCacheTask.run",
        _OWNED,
        _OWNED,
        ("LIST", "STAT", "DELETE"),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _TASK_EVIDENCE,
    ),
    _mutation(
        "task",
        "tasks.tasks",
        "Task.run",
        _OWNED,
        _OWNED,
        ("JOB",),
        InventoryDisposition.OWNED_ONLY,
        "exceptions.storage_exceptions:StoragePolicyDenied",
        Evidence(
            "tests/tasks/test_storage_policy.py",
            "test_job_metadata_denial_is_not_swallowed",
        ),
    ),
    InventoryRow(
        "migration-exclusion",
        "alembic.versions.0019_add_fs_resources",
        "upgrade",
        InventoryKind.EXCLUSION,
        _OWNED,
        _OWNED,
        ("MIGRATION",),
        InventoryDisposition.NON_RUNTIME,
        "",
        Evidence(
            "tests/handler/filesystem/test_storage_inventory.py",
            "test_historical_migrations_are_explicit_non_runtime_exclusions",
        ),
        "Alembic migration executes only during schema upgrade and addresses owned resource storage.",
    ),
    InventoryRow(
        "migration-exclusion",
        "alembic.versions.0040_move_images",
        "upgrade",
        InventoryKind.EXCLUSION,
        _OWNED,
        _OWNED,
        ("MIGRATION",),
        InventoryDisposition.NON_RUNTIME,
        "",
        Evidence(
            "tests/handler/filesystem/test_storage_inventory.py",
            "test_historical_migrations_are_explicit_non_runtime_exclusions",
        ),
        "Alembic migration executes only during schema upgrade and addresses owned asset storage.",
    ),
)

_ADDITIONAL_SEAMS = (
    (
        "audio",
        "utils.audio_tags",
        "remove_persisted_cover",
        _OWNED,
        _OWNED,
        ("DELETE",),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        Evidence(
            "tests/utils/test_audio_tags.py",
            "test_audio_cover_write_and_delete_require_separate_owned_capabilities",
        ),
    ),
    (
        "zip",
        "utils.zip_cache",
        "cleanup_stale_zips",
        _OWNED,
        _OWNED,
        ("LIST", "STAT", "DELETE"),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        Evidence(
            "tests/utils/test_zip_cache.py",
            "test_build_cached_zip_copies_download_capabilities_to_owned_output",
        ),
    ),
    (
        "sync",
        "handler.sync.ssh_handler",
        "SSHSyncHandler.__init__",
        _OWNED,
        _OWNED,
        ("MKDIR",),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _OWNED_EVIDENCE,
    ),
    (
        "sync",
        "handler.sync.ssh_handler",
        "SSHSyncHandler.upload_save",
        _OWNED,
        _OWNED,
        ("CREATE",),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _OWNED_EVIDENCE,
    ),
    (
        "sync",
        "handler.sync.ssh_handler",
        "SSHSyncHandler.delete_remote_save",
        _OWNED,
        _OWNED,
        ("DELETE",),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _OWNED_EVIDENCE,
    ),
    (
        "archive",
        "utils.archives",
        "_extract_member_to_dir",
        _EXTERNAL,
        _OWNED,
        ("CREATE",),
        InventoryDisposition.POLICY_GOVERNED,
        "handler.filesystem.storage_access:OwnedCreate",
        Evidence(
            "tests/utils/test_archives.py",
            "test_archive_subprocess_uses_proc_fd_and_pass_fds",
        ),
    ),
    (
        "archive",
        "utils.archives",
        "extract_largest_archive_member",
        _EXTERNAL,
        _OWNED,
        ("CREATE",),
        InventoryDisposition.POLICY_GOVERNED,
        "handler.filesystem.storage_access:OwnedCreate",
        Evidence(
            "tests/utils/test_archives.py",
            "test_archive_subprocess_uses_proc_fd_and_pass_fds",
        ),
    ),
    (
        "watcher",
        "sync_watcher",
        "_process_incoming_file",
        _OWNED,
        _OWNED,
        ("MOVE",),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _TASK_EVIDENCE,
    ),
    (
        "endpoint-mutation",
        "endpoints.roms.upload",
        "_cleanup_tmp",
        _OWNED,
        _OWNED,
        ("RMTREE",),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _ENDPOINT_EVIDENCE,
    ),
    (
        "endpoint-mutation",
        "endpoints.roms.upload",
        "start_chunked_upload",
        _OWNED,
        _OWNED,
        ("MKDIR",),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _ENDPOINT_EVIDENCE,
    ),
    (
        "endpoint-mutation",
        "endpoints.roms.upload",
        "upload_chunk",
        _OWNED,
        _OWNED,
        ("WRITE",),
        InventoryDisposition.OWNED_ONLY,
        "handler.filesystem.storage_access:open_owned_access",
        _ENDPOINT_EVIDENCE,
    ),
    (
        "endpoint-mutation",
        "endpoints.roms.upload",
        "complete_chunked_upload",
        _OWNED,
        _EXTERNAL,
        ("REPLACE", "DELETE"),
        InventoryDisposition.POLICY_GOVERNED,
        "endpoints.storage_policy:authorize_api_storage_operation",
        _ENDPOINT_EVIDENCE,
    ),
    (
        "zip",
        "endpoints.roms",
        "_resolve_capability_cached_zip",
        _EXTERNAL,
        _OWNED,
        ("CREATE",),
        InventoryDisposition.POLICY_GOVERNED,
        "handler.filesystem.storage_access:OwnedReplace",
        Evidence(
            "tests/utils/test_zip_cache.py",
            "test_build_cached_zip_copies_download_capabilities_to_owned_output",
        ),
    ),
)

INVENTORY = (
    *INVENTORY,
    *(
        _mutation(
            family,
            module,
            symbol,
            source,
            destination,
            operations,
            disposition,
            enforcement,
            evidence,
        )
        for (
            family,
            module,
            symbol,
            source,
            destination,
            operations,
            disposition,
            enforcement,
            evidence,
        ) in _ADDITIONAL_SEAMS
    ),
)
