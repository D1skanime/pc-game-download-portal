import base64
import binascii
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from decorators.database import begin_session
from exceptions.storage_exceptions import (
    DuplicateStorageMappingError,
    InvalidRelativePathError,
    InvalidStorageCursorError,
    MissingPlatformStorageMappingError,
    MissingStoragePlatformError,
    MissingStorageRootError,
    StaleStorageMappingVersionError,
    StorageMappingOverlapError,
    StoragePersistenceError,
    StorageResolutionError,
    UnsafeSymlinkError,
    UnsafeWritableRootError,
)
from handler.filesystem.storage_resolver import (
    check_storage_root_health,
    normalize_relative_path,
    resolve_directory,
)
from models.platform import Platform
from models.storage import (
    EXTERNAL_READ_ONLY_MODE,
    PlatformStorageMapping,
    StorageMappingAudit,
    StorageMappingAuditAction,
    StorageRoot,
)

from .base_handler import DBBaseHandler


class DBStorageHandler(DBBaseHandler):
    _MAPPING_UNIQUE_CONSTRAINTS = {
        "uq_platform_storage_mappings_platform_id",
        "uq_platform_storage_mappings_root_relative_path",
    }

    @classmethod
    def _is_mapping_unique_violation(cls, error: IntegrityError) -> bool:
        diagnostic = getattr(error.orig, "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", None)
        if constraint_name is not None:
            return constraint_name in cls._MAPPING_UNIQUE_CONSTRAINTS
        errno = getattr(error.orig, "errno", None)
        if errno != 1062:
            return False
        message = str(error.orig)
        return any(name in message for name in cls._MAPPING_UNIQUE_CONSTRAINTS)

    @begin_session
    def register_root(
        self,
        name: str,
        container_path: str,
        *,
        mode: str = EXTERNAL_READ_ONLY_MODE,
        session: Session = None,  # type: ignore
    ) -> StorageRoot:
        path = Path(container_path)
        if not path.is_absolute():
            raise InvalidRelativePathError

        root = StorageRoot(
            name=name,
            container_path=str(path),
            mode=EXTERNAL_READ_ONLY_MODE,
            active=True,
        )
        check_storage_root_health(root)
        if not root.reachable:
            if root.safe_error and "symbolic link" in root.safe_error:
                raise UnsafeSymlinkError
            raise MissingStorageRootError(0)
        if not root.readable:
            raise StorageResolutionError("Storage root is not readable")
        if not root.non_writable:
            raise UnsafeWritableRootError(0)

        session.add(root)
        session.flush()
        return root

    @staticmethod
    def _load_and_validate(
        session: Session,
        storage_root_id: int,
        relative_path: str,
        exclude_mapping_id: int | None = None,
    ) -> tuple[StorageRoot, str]:
        relative_path = normalize_relative_path(relative_path)
        roots = session.scalars(
            select(StorageRoot)
            .where(StorageRoot.active.is_(True))
            .order_by(StorageRoot.id)
            .with_for_update()
        ).all()
        root = next((item for item in roots if item.id == storage_root_id), None)
        if root is None:
            raise MissingStorageRootError(storage_root_id)

        candidate = resolve_directory(root, relative_path)
        mappings = session.scalars(
            select(PlatformStorageMapping)
            .where(PlatformStorageMapping.active.is_(True))
            .order_by(PlatformStorageMapping.id)
            .options(selectinload(PlatformStorageMapping.storage_root))
            .with_for_update(of=PlatformStorageMapping)
        ).all()
        if exclude_mapping_id is not None:
            mappings = [
                mapping for mapping in mappings if mapping.id != exclude_mapping_id
            ]
        for mapping in mappings:
            if mapping.storage_root.active:
                existing = resolve_directory(
                    mapping.storage_root, mapping.relative_path
                )
                if (
                    candidate == existing
                    or candidate in existing.parents
                    or existing in candidate.parents
                ):
                    raise StorageMappingOverlapError(
                        storage_root_id,
                        platform_id=mapping.platform_id,
                        mapping_id=mapping.id,
                    )
        return root, relative_path

    @begin_session
    def save_mapping(
        self,
        platform_id: int,
        storage_root_id: int,
        relative_path: str,
        session: Session = None,  # type: ignore
    ) -> PlatformStorageMapping:
        platform_exists = session.scalar(
            select(Platform.id)
            .where(Platform.id == platform_id)
            .with_for_update(of=Platform)
        )
        if platform_exists is None:
            raise MissingStoragePlatformError(platform_id)
        _, relative_path = self._load_and_validate(
            session, storage_root_id, relative_path
        )
        active_mapping_id = session.scalar(
            select(PlatformStorageMapping.id)
            .where(
                PlatformStorageMapping.platform_id == platform_id,
                PlatformStorageMapping.active.is_(True),
            )
            .with_for_update(of=PlatformStorageMapping)
        )
        if active_mapping_id is not None:
            raise DuplicateStorageMappingError(platform_id, storage_root_id)
        # Re-load under the same root lock immediately before persistence.
        self._load_and_validate(session, storage_root_id, relative_path)
        mapping = PlatformStorageMapping(
            platform_id=platform_id,
            storage_root_id=storage_root_id,
            relative_path=relative_path,
        )
        session.add(mapping)
        try:
            session.flush()
        except IntegrityError as error:
            if self._is_mapping_unique_violation(error):
                raise DuplicateStorageMappingError(
                    platform_id, storage_root_id
                ) from error
            raise StoragePersistenceError from error
        return mapping

    @staticmethod
    def _lock_platform(session: Session, platform_id: int) -> None:
        platform_exists = session.scalar(
            select(Platform.id)
            .where(Platform.id == platform_id)
            .with_for_update(of=Platform)
        )
        if platform_exists is None:
            raise MissingStoragePlatformError(platform_id)

    @staticmethod
    def _snapshot(mapping: PlatformStorageMapping) -> dict[str, object]:
        return {
            "storage_root_id": mapping.storage_root_id,
            "relative_path": mapping.relative_path,
            "version": mapping.version,
            "active": mapping.active,
        }

    @staticmethod
    def _append_audit(
        session: Session,
        mapping: PlatformStorageMapping,
        action: StorageMappingAuditAction,
        old: dict[str, object] | None,
        new: dict[str, object] | None,
        actor_user_id: int,
        actor_display_name: str,
    ) -> None:
        old = old or {}
        new = new or {}
        session.add(
            StorageMappingAudit(
                actor_user_id=actor_user_id,
                actor_display_name=actor_display_name[:255],
                platform_id=mapping.platform_id,
                mapping_id=mapping.id,
                action=action.value,
                old_storage_root_id=old.get("storage_root_id"),
                old_relative_path=old.get("relative_path"),
                old_version=old.get("version"),
                old_active=old.get("active"),
                new_storage_root_id=new.get("storage_root_id"),
                new_relative_path=new.get("relative_path"),
                new_version=new.get("version"),
                new_active=new.get("active"),
            )
        )
        session.flush()

    @begin_session
    def get_active_mapping(
        self, platform_id: int, *, session: Session = None  # type: ignore
    ) -> PlatformStorageMapping:
        mapping = session.scalar(
            select(PlatformStorageMapping).where(
                PlatformStorageMapping.platform_id == platform_id,
                PlatformStorageMapping.active.is_(True),
            )
        )
        if mapping is None:
            raise MissingPlatformStorageMappingError(platform_id)
        return mapping

    @begin_session
    def test_mapping(
        self,
        platform_id: int,
        storage_root_id: int,
        relative_path: str,
        *,
        session: Session = None,  # type: ignore
    ) -> PlatformStorageMapping:
        self._lock_platform(session, platform_id)
        _, relative_path = self._load_and_validate(
            session, storage_root_id, relative_path
        )
        active_mapping = session.scalar(
            select(PlatformStorageMapping.id).where(
                PlatformStorageMapping.platform_id == platform_id,
                PlatformStorageMapping.active.is_(True),
            )
        )
        if active_mapping is not None:
            raise DuplicateStorageMappingError(platform_id, storage_root_id)
        return PlatformStorageMapping(
            platform_id=platform_id,
            storage_root_id=storage_root_id,
            relative_path=relative_path,
            active=True,
            version=1,
        )

    @begin_session
    def create_mapping(
        self,
        platform_id: int,
        storage_root_id: int,
        relative_path: str,
        *,
        actor_user_id: int,
        actor_display_name: str,
        session: Session = None,  # type: ignore
    ) -> PlatformStorageMapping:
        self._lock_platform(session, platform_id)
        _, relative_path = self._load_and_validate(
            session, storage_root_id, relative_path
        )
        active_mapping_id = session.scalar(
            select(PlatformStorageMapping.id)
            .where(
                PlatformStorageMapping.platform_id == platform_id,
                PlatformStorageMapping.active.is_(True),
            )
            .with_for_update(of=PlatformStorageMapping)
        )
        if active_mapping_id is not None:
            raise DuplicateStorageMappingError(platform_id, storage_root_id)
        mapping = PlatformStorageMapping(
            platform_id=platform_id,
            storage_root_id=storage_root_id,
            relative_path=relative_path,
            active=True,
            version=1,
        )
        session.add(mapping)
        try:
            session.flush()
        except IntegrityError as error:
            if self._is_mapping_unique_violation(error):
                raise DuplicateStorageMappingError(
                    platform_id, storage_root_id
                ) from error
            raise StoragePersistenceError from error
        self._append_audit(
            session,
            mapping,
            StorageMappingAuditAction.CREATE,
            None,
            self._snapshot(mapping),
            actor_user_id,
            actor_display_name,
        )
        return mapping

    @staticmethod
    def _load_mapping_for_change(
        session: Session, mapping_id: int
    ) -> PlatformStorageMapping:
        platform_id = session.scalar(
            select(PlatformStorageMapping.platform_id).where(
                PlatformStorageMapping.id == mapping_id
            )
        )
        if platform_id is None:
            raise MissingPlatformStorageMappingError(0)
        DBStorageHandler._lock_platform(session, platform_id)
        session.scalars(
            select(StorageRoot)
            .where(StorageRoot.active.is_(True))
            .order_by(StorageRoot.id)
            .with_for_update()
        ).all()
        mappings = session.scalars(
            select(PlatformStorageMapping)
            .order_by(PlatformStorageMapping.id)
            .with_for_update(of=PlatformStorageMapping)
        ).all()
        mapping = next(
            (item for item in mappings if item.id == mapping_id),
            None,
        )
        if mapping is None:
            raise MissingPlatformStorageMappingError(platform_id)
        return mapping

    @staticmethod
    def _check_version(mapping: PlatformStorageMapping, expected_version: int) -> None:
        if mapping.version != expected_version:
            raise StaleStorageMappingVersionError(mapping.id, mapping.version)

    @begin_session
    def update_mapping(
        self,
        mapping_id: int,
        storage_root_id: int,
        relative_path: str,
        *,
        expected_version: int,
        actor_user_id: int,
        actor_display_name: str,
        session: Session = None,  # type: ignore
    ) -> PlatformStorageMapping:
        mapping = self._load_mapping_for_change(session, mapping_id)
        self._check_version(mapping, expected_version)
        if not mapping.active:
            raise MissingPlatformStorageMappingError(mapping.platform_id)
        _, relative_path = self._load_and_validate(
            session,
            storage_root_id,
            relative_path,
            exclude_mapping_id=mapping.id,
        )
        old = self._snapshot(mapping)
        mapping.storage_root_id = storage_root_id
        mapping.relative_path = relative_path
        mapping.version += 1
        session.flush()
        self._append_audit(
            session,
            mapping,
            StorageMappingAuditAction.UPDATE,
            old,
            self._snapshot(mapping),
            actor_user_id,
            actor_display_name,
        )
        return mapping

    def _set_inactive(
        self,
        session: Session,
        mapping_id: int,
        expected_version: int,
        actor_user_id: int,
        actor_display_name: str,
        action: StorageMappingAuditAction,
    ) -> PlatformStorageMapping:
        mapping = self._load_mapping_for_change(session, mapping_id)
        self._check_version(mapping, expected_version)
        if not mapping.active:
            raise MissingPlatformStorageMappingError(mapping.platform_id)
        old = self._snapshot(mapping)
        mapping.active = False
        mapping.version += 1
        session.flush()
        self._append_audit(
            session,
            mapping,
            action,
            old,
            self._snapshot(mapping),
            actor_user_id,
            actor_display_name,
        )
        return mapping

    @begin_session
    def deactivate_mapping(
        self,
        mapping_id: int,
        *,
        expected_version: int,
        actor_user_id: int,
        actor_display_name: str,
        session: Session = None,  # type: ignore
    ) -> PlatformStorageMapping:
        return self._set_inactive(
            session,
            mapping_id,
            expected_version,
            actor_user_id,
            actor_display_name,
            StorageMappingAuditAction.DEACTIVATE,
        )

    @begin_session
    def remove_mapping(
        self,
        mapping_id: int,
        *,
        expected_version: int,
        actor_user_id: int,
        actor_display_name: str,
        session: Session = None,  # type: ignore
    ) -> PlatformStorageMapping:
        return self._set_inactive(
            session,
            mapping_id,
            expected_version,
            actor_user_id,
            actor_display_name,
            StorageMappingAuditAction.REMOVE,
        )

    @begin_session
    def reactivate_mapping(
        self,
        mapping_id: int,
        *,
        expected_version: int,
        actor_user_id: int,
        actor_display_name: str,
        session: Session = None,  # type: ignore
    ) -> PlatformStorageMapping:
        mapping = self._load_mapping_for_change(session, mapping_id)
        self._check_version(mapping, expected_version)
        if mapping.active:
            raise DuplicateStorageMappingError(
                mapping.platform_id, mapping.storage_root_id
            )
        self._load_and_validate(
            session,
            mapping.storage_root_id,
            mapping.relative_path,
            exclude_mapping_id=mapping.id,
        )
        active_mapping_id = session.scalar(
            select(PlatformStorageMapping.id)
            .where(
                PlatformStorageMapping.platform_id == mapping.platform_id,
                PlatformStorageMapping.active.is_(True),
            )
            .with_for_update(of=PlatformStorageMapping)
        )
        if active_mapping_id is not None:
            raise DuplicateStorageMappingError(
                mapping.platform_id, mapping.storage_root_id
            )
        old = self._snapshot(mapping)
        mapping.active = True
        mapping.version += 1
        session.flush()
        self._append_audit(
            session,
            mapping,
            StorageMappingAuditAction.ACTIVATE,
            old,
            self._snapshot(mapping),
            actor_user_id,
            actor_display_name,
        )
        return mapping

    @staticmethod
    def _audit_filter_key(
        platform_id: int | None, mapping_id: int | None, action: str | None
    ) -> list[object]:
        return [platform_id, mapping_id, action]

    @begin_session
    def list_mapping_audits(
        self,
        *,
        platform_id: int | None = None,
        mapping_id: int | None = None,
        action: str | None = None,
        cursor: str | None = None,
        limit: int = 50,
        session: Session = None,  # type: ignore
    ) -> tuple[list[StorageMappingAudit], str | None]:
        if limit < 1 or limit > 100:
            raise InvalidStorageCursorError
        query = select(StorageMappingAudit)
        if platform_id is not None:
            query = query.where(StorageMappingAudit.platform_id == platform_id)
        if mapping_id is not None:
            query = query.where(StorageMappingAudit.mapping_id == mapping_id)
        if action is not None:
            if action not in {item.value for item in StorageMappingAuditAction}:
                raise InvalidStorageCursorError
            query = query.where(StorageMappingAudit.action == action)
        if cursor is not None and len(cursor) > 2048:
            raise InvalidStorageCursorError
        if cursor is not None:
            try:
                payload = json.loads(
                    base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
                )
                if payload["v"] != 1 or payload["f"] != self._audit_filter_key(
                    platform_id, mapping_id, action
                ):
                    raise ValueError
                created_at = datetime.fromisoformat(payload["t"])
                audit_id = int(payload["i"])
            except (
                binascii.Error,
                KeyError,
                TypeError,
                ValueError,
                UnicodeError,
                json.JSONDecodeError,
            ):
                raise InvalidStorageCursorError from None
            query = query.where(
                or_(
                    StorageMappingAudit.created_at < created_at,
                    and_(
                        StorageMappingAudit.created_at == created_at,
                        StorageMappingAudit.id < audit_id,
                    ),
                )
            )
        rows = session.scalars(
            query.order_by(
                StorageMappingAudit.created_at.desc(), StorageMappingAudit.id.desc()
            ).limit(limit + 1)
        ).all()
        page = list(rows[:limit])
        next_cursor = None
        if len(rows) > limit:
            last = page[-1]
            payload = {
                "v": 1,
                "f": self._audit_filter_key(platform_id, mapping_id, action),
                "t": last.created_at.isoformat(),
                "i": last.id,
            }
            next_cursor = base64.urlsafe_b64encode(
                json.dumps(payload, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
        return page, next_cursor
