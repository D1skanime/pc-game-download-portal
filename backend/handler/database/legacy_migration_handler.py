from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from decorators.database import begin_session
from exceptions.storage_exceptions import (
    MissingStoragePlatformError,
    MissingStorageRootError,
)
from handler.database.base_handler import DBBaseHandler
from models.platform import Platform
from models.storage import (
    LegacyDetectionResult,
    LegacyDetectionState,
    PlatformStorageMapping,
    StorageRoot,
)

if TYPE_CHECKING:
    from handler.storage.legacy_migration import LegacyDetectionOutcome

LEGACY_DETECTION_TTL_HOURS = 24


@dataclass(frozen=True, slots=True)
class LegacyDetectionContext:
    platform_id: int
    storage_root_id: int
    fs_slug: str
    container_path: str
    root_active: bool
    observed_mapping_id: int | None
    observed_mapping_version: int | None


class LegacyDetectionResultError(Exception):
    def __init__(
        self,
        code: str,
        *,
        result_id: int | None = None,
        platform_id: int | None = None,
        current_version: int | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.result_id = result_id
        self.platform_id = platform_id
        self.current_version = current_version


class DBLegacyMigrationHandler(DBBaseHandler):
    @staticmethod
    def _lock_context(
        session: Session, platform_id: int, storage_root_id: int
    ) -> tuple[Platform, StorageRoot, list[PlatformStorageMapping]]:
        platform = session.scalar(
            select(Platform)
            .where(Platform.id == platform_id)
            .with_for_update(of=Platform)
        )
        if platform is None:
            raise MissingStoragePlatformError(platform_id)
        roots = session.scalars(
            select(StorageRoot).order_by(StorageRoot.id).with_for_update()
        ).all()
        root = next((item for item in roots if item.id == storage_root_id), None)
        if root is None:
            raise MissingStorageRootError(storage_root_id)
        mappings = list(
            session.scalars(
                select(PlatformStorageMapping)
                .where(PlatformStorageMapping.active.is_(True))
                .order_by(PlatformStorageMapping.id)
                .with_for_update(of=PlatformStorageMapping)
            ).all()
        )
        return platform, root, mappings

    @begin_session
    def get_detection_context(
        self,
        platform_id: int,
        storage_root_id: int,
        *,
        session: Session = None,  # type: ignore
    ) -> LegacyDetectionContext:
        platform, root, mappings = self._lock_context(
            session, platform_id, storage_root_id
        )
        mapping = next(
            (item for item in mappings if item.platform_id == platform_id), None
        )
        return LegacyDetectionContext(
            platform_id=platform.id,
            storage_root_id=root.id,
            fs_slug=platform.fs_slug,
            container_path=root.container_path,
            root_active=root.active,
            observed_mapping_id=mapping.id if mapping is not None else None,
            observed_mapping_version=mapping.version if mapping is not None else None,
        )

    def validate_detection_request(
        self, platform_id: int, storage_root_id: int
    ) -> None:
        self.get_detection_context(platform_id, storage_root_id)

    @staticmethod
    def _mapping_identity(
        mappings: list[PlatformStorageMapping], platform_id: int
    ) -> tuple[int | None, int | None]:
        mapping = next(
            (item for item in mappings if item.platform_id == platform_id), None
        )
        if mapping is None:
            return None, None
        return mapping.id, mapping.version

    @staticmethod
    def _paths_overlap(first: str, second: str) -> bool:
        first_path = PurePosixPath(first)
        second_path = PurePosixPath(second)
        return (
            first_path == second_path
            or first_path in second_path.parents
            or second_path in first_path.parents
        )

    @begin_session
    def save_detection_result(
        self,
        context: LegacyDetectionContext,
        outcome: LegacyDetectionOutcome,
        *,
        actor_user_id: int,
        now: datetime | None = None,
        session: Session = None,  # type: ignore
    ) -> LegacyDetectionResult:
        platform, root, mappings = self._lock_context(
            session, context.platform_id, context.storage_root_id
        )
        mapping_id, mapping_version = self._mapping_identity(
            mappings, context.platform_id
        )
        if (
            platform.fs_slug != context.fs_slug
            or root.active != context.root_active
            or mapping_id != context.observed_mapping_id
            or mapping_version != context.observed_mapping_version
        ):
            raise LegacyDetectionResultError(
                "legacy_detection_stale", platform_id=context.platform_id
            )
        if (
            outcome.platform_id != context.platform_id
            or outcome.storage_root_id != context.storage_root_id
        ):
            raise LegacyDetectionResultError(
                "legacy_detection_cross_platform",
                platform_id=context.platform_id,
            )
        try:
            LegacyDetectionState(outcome.state)
        except ValueError:
            raise LegacyDetectionResultError(
                "legacy_detection_invalid_state",
                platform_id=context.platform_id,
            ) from None

        final = outcome
        problem_code: str | None = None
        if mapping_id is not None:
            problem_code = "active_mapping_conflict"
        elif outcome.proposed_relative_path is not None:
            for mapping in mappings:
                if (
                    mapping.storage_root_id == context.storage_root_id
                    and self._paths_overlap(
                        outcome.proposed_relative_path, mapping.relative_path
                    )
                ):
                    problem_code = "mapping_overlap"
                    break
        if problem_code is not None:
            final = replace(
                outcome,
                state=LegacyDetectionState.CONFLICT.value,
                selectable=False,
                safe_problem_code=problem_code,
            )

        completed_at = now or datetime.now(timezone.utc)
        result = LegacyDetectionResult(
            platform_id=context.platform_id,
            storage_root_id=context.storage_root_id,
            state=final.state,
            proposed_relative_path=final.proposed_relative_path,
            observed_files=final.observed_files,
            observed_bytes=final.observed_bytes,
            lower_bound=final.lower_bound,
            selectable=final.selectable,
            safe_problem_code=final.safe_problem_code,
            observed_mapping_id=mapping_id,
            observed_mapping_version=mapping_version,
            version=1,
            actor_user_id=actor_user_id,
            expires_at=completed_at + timedelta(hours=LEGACY_DETECTION_TTL_HOURS),
            completed_at=completed_at,
        )
        session.add(result)
        session.flush()
        return result

    @begin_session
    def get_detection_result(
        self,
        result_id: int,
        *,
        session: Session = None,  # type: ignore
    ) -> LegacyDetectionResult:
        result = session.get(LegacyDetectionResult, result_id)
        if result is None:
            raise LegacyDetectionResultError(
                "legacy_detection_missing", result_id=result_id
            )
        return result

    @begin_session
    def require_detection_result(
        self,
        result_id: int,
        *,
        platform_id: int,
        expected_version: int,
        consume: bool = False,
        now: datetime | None = None,
        session: Session = None,  # type: ignore
    ) -> LegacyDetectionResult:
        result = session.scalar(
            select(LegacyDetectionResult)
            .where(LegacyDetectionResult.id == result_id)
            .with_for_update(of=LegacyDetectionResult)
        )
        if result is None:
            raise LegacyDetectionResultError(
                "legacy_detection_missing", result_id=result_id
            )
        if result.platform_id != platform_id:
            raise LegacyDetectionResultError(
                "legacy_detection_cross_platform",
                result_id=result_id,
                platform_id=platform_id,
            )
        if result.version != expected_version:
            raise LegacyDetectionResultError(
                "legacy_detection_stale",
                result_id=result_id,
                platform_id=platform_id,
                current_version=result.version,
            )
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        expires_at = result.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= current_time:
            raise LegacyDetectionResultError(
                "legacy_detection_expired",
                result_id=result_id,
                platform_id=platform_id,
                current_version=result.version,
            )
        if result.completed_at is None or not result.selectable:
            raise LegacyDetectionResultError(
                "legacy_detection_unselectable",
                result_id=result_id,
                platform_id=platform_id,
                current_version=result.version,
            )
        if consume:
            result.version += 1
            session.flush()
        return result
