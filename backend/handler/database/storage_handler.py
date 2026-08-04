from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from decorators.database import begin_session
from exceptions.storage_exceptions import (
    DuplicateStorageMappingError,
    InvalidRelativePathError,
    MissingStorageRootError,
    StorageMappingOverlapError,
    StorageResolutionError,
    UnsafeSymlinkError,
    UnsafeWritableRootError,
)
from handler.filesystem.storage_resolver import (
    check_storage_root_health,
    normalize_relative_path,
    resolve_directory,
)
from models.storage import (
    EXTERNAL_READ_ONLY_MODE,
    PlatformStorageMapping,
    StorageRoot,
)

from .base_handler import DBBaseHandler


class DBStorageHandler(DBBaseHandler):
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
            .options(joinedload(PlatformStorageMapping.storage_root))
            .with_for_update()
        ).all()
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
                    raise StorageMappingOverlapError(storage_root_id, relative_path)
        return root, relative_path

    @begin_session
    def save_mapping(
        self,
        platform_id: int,
        storage_root_id: int,
        relative_path: str,
        session: Session = None,  # type: ignore
    ) -> PlatformStorageMapping:
        _, relative_path = self._load_and_validate(
            session, storage_root_id, relative_path
        )
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
            raise DuplicateStorageMappingError(platform_id, storage_root_id) from error
        return mapping
