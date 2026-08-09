from .assets_handler import FSAssetsHandler
from .firmware_handler import FSFirmwareHandler
from .launchbox_handler import FSLaunchboxHandler, get_fs_launchbox_handler
from .platforms_handler import FSPlatformsHandler
from .resources_handler import FSResourcesHandler
from .roms_handler import FSRomsHandler
from .storage_access import (
    DownloadCapability,
    HashCapability,
    ListCapability,
    ReadCapability,
    ResolveCapability,
    ScanCapability,
    StatCapability,
    StreamCapability,
    open_storage_access,
)
from .storage_composition import (
    StorageComposition,
    StorageCompositionConfig,
    build_storage_composition,
    trusted_storage_config,
)
from .storage_policy import OwnedStorageKind
from .sync_handler import FSSyncHandler, get_fs_sync_handler

storage_composition = build_storage_composition()
legacy_external_storage = storage_composition.legacy_external

fs_asset_handler = FSAssetsHandler(storage_composition.owned[OwnedStorageKind.ASSETS])
fs_firmware_handler = FSFirmwareHandler(legacy_external_storage)
fs_platform_handler = FSPlatformsHandler(legacy_external_storage)
fs_rom_handler = FSRomsHandler(legacy_external_storage)
fs_resource_handler = FSResourcesHandler(
    storage_composition.owned[OwnedStorageKind.RESOURCES]
)

__all__ = [
    "FSAssetsHandler",
    "FSFirmwareHandler",
    "FSLaunchboxHandler",
    "FSPlatformsHandler",
    "FSResourcesHandler",
    "FSRomsHandler",
    "FSSyncHandler",
    "DownloadCapability",
    "HashCapability",
    "ListCapability",
    "ReadCapability",
    "ResolveCapability",
    "ScanCapability",
    "StatCapability",
    "StorageComposition",
    "StorageCompositionConfig",
    "StreamCapability",
    "build_storage_composition",
    "fs_asset_handler",
    "fs_firmware_handler",
    "fs_platform_handler",
    "fs_resource_handler",
    "fs_rom_handler",
    "get_fs_launchbox_handler",
    "get_fs_sync_handler",
    "legacy_external_storage",
    "open_storage_access",
    "storage_composition",
    "trusted_storage_config",
]
