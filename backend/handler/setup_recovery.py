"""Read-only setup reconciliation using persisted mappings and the shared resolver."""

from dataclasses import asdict
from time import sleep

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import LIBRARY_BASE_PATH
from decorators.database import begin_session
from endpoints.responses.setup import (
    SetupFolderMappingSchema,
    SetupFolderSchema,
    SetupRecoverySnapshot,
    SetupRootHealthSchema,
)
from exceptions.storage_exceptions import (
    MissingPlatformStorageMappingError,
    OwnedWriterBusyError,
    StorageResolutionError,
)
from handler.database import db_storage_handler, db_user_handler
from handler.filesystem.storage_resolver import (
    get_storage_root_health_snapshot,
    normalize_relative_path,
    resolve_directory,
)
from handler.setup_folder_handler import ROOT_LABEL, setup_folder_handler
from models.platform import Platform
from models.storage import EXTERNAL_READ_ONLY_MODE, PlatformStorageMapping, StorageRoot
from models.user import Role, User


class SetupRecoveryHandler:
    @staticmethod
    def root(session: Session) -> StorageRoot:
        roots = db_storage_handler.get_roots(session=session)
        candidates = [
            root
            for root in roots
            if root.name == ROOT_LABEL or root.container_path == LIBRARY_BASE_PATH
        ]
        return next((root for root in candidates if root.active), None) or next(
            iter(candidates),
            StorageRoot(
                id=0,
                name=ROOT_LABEL,
                container_path=LIBRARY_BASE_PATH,
                mode=EXTERNAL_READ_ONLY_MODE,
                active=True,
            ),
        )

    @staticmethod
    def saved(root: StorageRoot, session: Session) -> list[SetupFolderMappingSchema]:
        rows = session.execute(
            select(PlatformStorageMapping, Platform.slug)
            .join(Platform, Platform.id == PlatformStorageMapping.platform_id)
            .where(
                PlatformStorageMapping.active.is_(True),
                PlatformStorageMapping.storage_root_id == root.id,
            )
            .order_by(PlatformStorageMapping.id)
            .limit(101)
        ).all()
        result = []
        for mapping, slug in rows:
            normalize_relative_path(mapping.relative_path, allow_root=True)
            result.append(
                SetupFolderMappingSchema(
                    folder_name=mapping.relative_path,
                    platform_slug=slug,
                    mapping_id=mapping.id,
                    relative_path=mapping.relative_path,
                )
            )
        return result

    @begin_session
    def snapshot(self, *, session: Session = None) -> SetupRecoverySnapshot:  # type: ignore
        enrolled = bool(db_user_handler.get_admin_users(session=session))
        root = self.root(session)
        health = get_storage_root_health_snapshot(root)
        root_health = SetupRootHealthSchema(
            reachable=health.reachable,
            readable=health.readable,
            non_writable=health.non_writable,
        )
        cause = None
        saved = []
        missing = []
        if not root.active:
            cause = "root_inactive"
        elif not health.reachable:
            cause = "root_missing"
        elif not health.readable:
            cause = "root_unreadable"
        elif not health.non_writable or root.mode != EXTERNAL_READ_ONLY_MODE:
            cause = "root_not_read_only"
        try:
            saved = self.saved(root, session)
            if len(saved) > 100:
                saved = saved[:100]
                cause = cause or "mapping_conflict"
            if cause is None:
                discovery = setup_folder_handler.discover(root)
                by_path = {row.relative_path: row for row in saved}
                supported = {option["slug"] for option in discovery.platform_options}
                for folder in discovery.folders:
                    mapping = by_path.get(folder.relative_path)
                    if mapping is None or mapping.platform_slug not in supported:
                        missing.append(SetupFolderSchema(**asdict(folder)))
                    else:
                        resolve_directory(root, mapping.relative_path)
                paths = {folder.relative_path for folder in discovery.folders}
                if any(row.relative_path not in paths for row in saved):
                    cause = "mapping_conflict"
                elif missing:
                    cause = "assignments_missing"
        except (ValueError, OSError, StorageResolutionError):
            cause = cause or "root_discovery_failed"
        complete = enrolled and cause is None
        action = (
            "create_admin"
            if not enrolled
            else (
                "start_first_scan"
                if complete
                else (
                    "assign_missing"
                    if cause == "assignments_missing"
                    else (
                        "resolve_conflicts"
                        if cause == "mapping_conflict"
                        else "retry_check"
                    )
                )
            )
        )
        return SetupRecoverySnapshot(
            enrolled=enrolled,
            setup_complete=complete,
            current_step=(
                "account" if not enrolled else "complete" if complete else "folders"
            ),
            saved_assignments=saved,
            missing_assignments=missing,
            root_health=root_health,
            cause_code=cause,
            next_action=action,
        )

    def assign(
        self, assignments: list[dict[str, str]], actor: dict, *, session: Session = None
    ) -> dict:  # type: ignore
        for attempt in range(3):
            try:
                return self._assign(assignments, actor, session=session)
            except OwnedWriterBusyError:
                if session is not None or attempt == 2:
                    raise
                sleep(0.01)
        raise AssertionError("unreachable setup retry")

    @begin_session
    def _assign(
        self, assignments: list[dict[str, str]], actor: dict, *, session: Session = None
    ) -> dict:  # type: ignore
        # Serialize setup retries, including first root registration, across admins.
        session.scalars(
            select(User)
            .where(User.role == Role.ADMIN)
            .order_by(User.id)
            .with_for_update()
        ).all()
        snapshot = self.snapshot(session=session)
        if snapshot.cause_code not in {None, "assignments_missing"}:
            raise ValueError(snapshot.cause_code)
        root = setup_folder_handler.root(session=session)
        saved = {
            row.folder_name: row.platform_slug for row in snapshot.saved_assignments
        }
        provided = {row["folder_name"]: row["platform_slug"] for row in assignments}
        if len(provided) != len(assignments):
            raise ValueError("setup_assignment_conflict")
        for name, slug in provided.items():
            if name in saved and saved[name] != slug:
                raise ValueError("setup_assignment_conflict")
            platform = setup_folder_handler._resolve_platform(slug, session=session)
            try:
                mapping = db_storage_handler.get_active_mapping(
                    platform.id, session=session
                )
            except MissingPlatformStorageMappingError:
                continue
            if mapping.storage_root_id != root.id or mapping.relative_path != name:
                raise ValueError("setup_assignment_conflict")
        merged = [
            {"folder_name": name, "platform_slug": slug}
            for name, slug in (saved | provided).items()
        ]
        result = setup_folder_handler.assign(root, merged, actor, session=session)
        response = setup_folder_handler.response(result)
        recovery = self.snapshot(session=session)
        response.update(ready=recovery.setup_complete, recovery=recovery.model_dump())
        return response


setup_recovery_handler = SetupRecoveryHandler()
