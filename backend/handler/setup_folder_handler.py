from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from config import LIBRARY_BASE_PATH
from config.config_manager import config_manager as cm
from exceptions.storage_exceptions import MissingPlatformStorageMappingError
from handler.database import db_platform_handler, db_storage_handler
from handler.filesystem.storage_resolver import (
    get_storage_root_health_snapshot,
    normalize_relative_path,
)
from models.platform import Platform
from models.storage import StorageRoot
from utils.platform_identity import legacy_platform_slug_for_filesystem_slug
from utils.platforms import get_supported_platforms

MAX_SETUP_FOLDERS = 100
ROOT_LABEL = "Games"


@dataclass(frozen=True, slots=True)
class DiscoveredFolder:
    name: str
    relative_path: str
    association: str
    suggested_platform: str | None


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    folders: tuple[DiscoveredFolder, ...]
    platform_options: tuple[dict[str, str], ...]


@dataclass(frozen=True, slots=True)
class AssignmentResult:
    mappings: tuple[dict[str, Any], ...]
    ready: bool
    root_health: Any


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


class SetupFolderHandler:
    def root(self, *, session: Session | None = None) -> StorageRoot:
        shared = {"session": session} if session is not None else {}
        for root in db_storage_handler.get_roots(**shared):
            if root.active and (
                root.name == ROOT_LABEL or root.container_path == LIBRARY_BASE_PATH
            ):
                return root
        return db_storage_handler.register_root(ROOT_LABEL, LIBRARY_BASE_PATH, **shared)

    @staticmethod
    def _platform_options() -> list[Any]:
        return list(get_supported_platforms())

    @staticmethod
    def _suggestion(name: str, platforms: list[Any]) -> str | None:
        config = cm.get_config()
        exact: list[str] = []
        for platform in platforms:
            if name in {platform.slug, platform.fs_slug, platform.name}:
                exact.append(platform.slug)
            elif (
                config.PLATFORMS_BINDING.get(name) == platform.slug
                or config.PLATFORMS_VERSIONS.get(name) == platform.slug
            ):
                exact.append(platform.slug)
        if len(set(exact)) == 1:
            return exact[0]
        if exact:
            return None
        candidate = name.casefold()
        alias = legacy_platform_slug_for_filesystem_slug(
            candidate, {platform.slug for platform in platforms}
        )
        if alias != candidate:
            return alias
        normalized_name = _normalized(name)
        matches = {
            platform.slug
            for platform in platforms
            if normalized_name
            in {
                _normalized(platform.slug),
                _normalized(platform.fs_slug),
                _normalized(platform.name),
            }
        }
        return next(iter(matches)) if len(matches) == 1 else None

    def discover(self, root: StorageRoot) -> DiscoveryResult:
        if not root.active:
            raise ValueError("Games storage root is inactive")
        platforms = self._platform_options()
        try:
            children = sorted(
                Path(root.container_path).iterdir(),
                key=lambda entry: entry.name.encode("utf-8"),
            )
        except OSError as error:
            raise ValueError("Games storage root cannot be listed safely") from error
        entries: list[DiscoveredFolder] = []
        names: set[str] = set()
        for entry in children:
            name = entry.name
            if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                continue
            if name in names:
                raise ValueError("Duplicate folder names are not safe")
            names.add(name)
            if "/" in name or "\\" in name:
                raise ValueError("Folder names must be safe relative paths")
            try:
                relative_path = normalize_relative_path(name)
            except Exception as error:
                raise ValueError("Folder names must be safe relative paths") from error
            suggestion = self._suggestion(name, platforms)
            entries.append(
                DiscoveredFolder(
                    name,
                    relative_path,
                    "known" if suggestion else "unknown",
                    suggestion,
                )
            )
            if len(entries) > MAX_SETUP_FOLDERS:
                raise ValueError("Too many direct folders")
        options = tuple(
            {"slug": platform.slug, "display_name": platform.name}
            for platform in platforms
        )
        return DiscoveryResult(tuple(entries), options)

    def discover_response(self) -> dict[str, Any]:
        result = self.discover(self.root())
        return {
            "root_label": ROOT_LABEL,
            "folders": [asdict(folder) for folder in result.folders],
            "platform_options": list(result.platform_options),
        }

    def _resolve_platform(self, slug: str, *, session: Session | None = None) -> Any:
        shared = {"session": session} if session is not None else {}
        options = {platform.slug: platform for platform in self._platform_options()}
        option = options.get(slug)
        if option is None:
            raise ValueError("Unsupported platform")
        platform = db_platform_handler.get_platform_by_slug(
            slug, **shared
        ) or db_platform_handler.get_platform_by_fs_slug(option.fs_slug, **shared)
        if platform is None:
            platform = db_platform_handler.add_platform(
                Platform(name=option.name, slug=option.slug, fs_slug=option.fs_slug),
                **shared,
            )
        return platform

    @staticmethod
    def _root_health(root: StorageRoot) -> Any:
        return get_storage_root_health_snapshot(root)

    def _reconcile(
        self,
        root: StorageRoot,
        platform: Any,
        relative_path: str,
        actor: dict[str, Any],
        *,
        session: Session | None = None,
    ) -> Any:
        shared = {"session": session} if session is not None else {}
        try:
            mapping = db_storage_handler.get_active_mapping(platform.id, **shared)
        except MissingPlatformStorageMappingError:
            return db_storage_handler.create_mapping(
                platform.id, root.id, relative_path, **actor, **shared
            )
        if (
            mapping.storage_root_id == root.id
            and mapping.relative_path == relative_path
        ):
            return mapping
        return db_storage_handler.update_mapping(
            mapping.id,
            root.id,
            relative_path,
            expected_version=mapping.version,
            **actor,
            **shared,
        )

    def assign(
        self,
        root: StorageRoot,
        assignments: list[dict[str, str]],
        actor: dict[str, Any],
        *,
        session: Session | None = None,
    ) -> AssignmentResult:
        shared = {"session": session} if session is not None else {}
        expected = {
            folder.name: folder.relative_path for folder in self.discover(root).folders
        }
        provided = {
            item.get("folder_name", ""): item.get("platform_slug", "")
            for item in assignments
        }
        if set(provided) != set(expected) or any(not name for name in provided):
            raise ValueError("every discovered folder must be assigned exactly once")
        if len(provided) != len(assignments) or len(set(provided.values())) != len(
            assignments
        ):
            raise ValueError("Folder and platform assignments must be unique")
        platforms = {
            name: self._resolve_platform(slug, **shared)
            for name, slug in provided.items()
        }
        for name, platform in platforms.items():
            relative_path = expected[name]
            try:
                existing = db_storage_handler.get_active_mapping(platform.id, **shared)
            except MissingPlatformStorageMappingError:
                existing = None
            if existing is None:
                db_storage_handler.test_mapping(
                    platform.id, root.id, relative_path, **shared
                )
            elif (
                existing.storage_root_id != root.id
                or existing.relative_path != relative_path
            ):
                db_storage_handler.test_mapping(
                    platform.id,
                    root.id,
                    relative_path,
                    exclude_mapping_id=existing.id,
                    **shared,
                )
        mappings = []
        for name in sorted(expected, key=lambda value: value.encode("utf-8")):
            platform = platforms[name]
            mapping = self._reconcile(root, platform, expected[name], actor, **shared)
            mappings.append(
                {
                    "folder_name": name,
                    "platform_slug": platform.slug,
                    "mapping_id": mapping.id,
                    "relative_path": mapping.relative_path,
                }
            )
        health = self._root_health(root)
        ready = bool(
            health.reachable
            and health.readable
            and health.non_writable
            and len(mappings) == len(expected)
        )
        return AssignmentResult(tuple(mappings), ready, health)

    @staticmethod
    def response(result: AssignmentResult) -> dict[str, Any]:
        return {
            "mappings": list(result.mappings),
            "ready": result.ready,
            "root_health": {
                "reachable": result.root_health.reachable,
                "readable": result.root_health.readable,
                "non_writable": result.root_health.non_writable,
            },
        }


setup_folder_handler = SetupFolderHandler()
