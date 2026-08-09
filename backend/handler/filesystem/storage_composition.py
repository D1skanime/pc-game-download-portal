from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePath
from types import MappingProxyType
from typing import Mapping

from config import (
    ASSETS_BASE_PATH,
    AUDIT_BASE_PATH,
    CACHE_BASE_PATH,
    CONFIG_BASE_PATH,
    DATABASE_BASE_PATH,
    HASHES_BASE_PATH,
    LIBRARY_BASE_PATH,
    RESOURCES_BASE_PATH,
    ROM_UPLOAD_TMP_BASE,
    SCAN_STATE_BASE_PATH,
    SYNC_BASE_PATH,
)

from .storage_policy import (
    ExternalStorageDescriptor,
    OwnedStorageDescriptor,
    OwnedStorageKind,
    _create_bound_owned_descriptor,
    _create_external_descriptor,
    validate_disjoint_storage_roots,
)

OWNED_STORAGE_PATHS: Mapping[OwnedStorageKind, Path] = MappingProxyType(
    {
        OwnedStorageKind.DATABASE: Path(DATABASE_BASE_PATH),
        OwnedStorageKind.RESOURCES: Path(RESOURCES_BASE_PATH),
        OwnedStorageKind.ASSETS: Path(ASSETS_BASE_PATH),
        OwnedStorageKind.CONFIG: Path(CONFIG_BASE_PATH),
        OwnedStorageKind.CACHE: Path(CACHE_BASE_PATH),
        OwnedStorageKind.HASHES: Path(HASHES_BASE_PATH),
        OwnedStorageKind.SCAN_STATE: Path(SCAN_STATE_BASE_PATH),
        OwnedStorageKind.TEMP: Path(ROM_UPLOAD_TMP_BASE),
        OwnedStorageKind.SYNC: Path(SYNC_BASE_PATH),
        OwnedStorageKind.AUDIT: Path(AUDIT_BASE_PATH),
    }
)


@dataclass(frozen=True, slots=True)
class StorageCompositionConfig:
    library_base_path: Path
    owned_paths: Mapping[OwnedStorageKind, Path]


@dataclass(frozen=True, slots=True)
class StorageComposition:
    legacy_external: ExternalStorageDescriptor
    legacy_external_path: PurePath
    owned: Mapping[OwnedStorageKind, OwnedStorageDescriptor]


def trusted_storage_config() -> StorageCompositionConfig:
    return StorageCompositionConfig(
        library_base_path=Path(LIBRARY_BASE_PATH),
        owned_paths=OWNED_STORAGE_PATHS,
    )


def build_storage_composition(
    config: StorageCompositionConfig | None = None,
) -> StorageComposition:
    trusted_config = config if config is not None else trusted_storage_config()
    if set(trusted_config.owned_paths) != set(OwnedStorageKind):
        raise ValueError("owned storage configuration must classify every closed kind")
    if not all(
        isinstance(kind, OwnedStorageKind) and isinstance(path, (str, PurePath))
        for kind, path in trusted_config.owned_paths.items()
    ):
        raise TypeError("owned storage configuration requires closed kinds and paths")

    external_path = PurePath(trusted_config.library_base_path)
    owned_paths = {
        kind: PurePath(path) for kind, path in trusted_config.owned_paths.items()
    }
    validate_disjoint_storage_roots(
        (str(external_path),),
        (str(path) for path in owned_paths.values()),
    )

    external = _create_external_descriptor(0, external_path)
    owned = MappingProxyType(
        {
            kind: _create_bound_owned_descriptor(kind, kind.value, path)
            for kind, path in owned_paths.items()
        }
    )
    return StorageComposition(external, external_path, owned)
