from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from decorators.database import begin_session
from exceptions.storage_exceptions import (
    MissingStoragePlatformError,
    MissingStorageRootError,
    StorageResolutionError,
)
from handler.database.base_handler import DBBaseHandler
from models.platform import Platform
from models.rom import Rom, RomFile
from models.storage import (
    LegacyDetectionResult,
    LegacyDetectionState,
    LegacyMigration,
    LegacyMigrationState,
    PlatformStorageMapping,
    StorageMappingAuditAction,
    StorageRoot,
)

if TYPE_CHECKING:
    from handler.storage.legacy_migration import (
        LegacyDetectionOutcome,
        LegacyImpactConfirmation,
        LegacyImpactPlannedEffects,
        LegacyImpactProblem,
        LegacyMigrationImpact,
    )

LEGACY_DETECTION_TTL_HOURS = 24
_IMPACT_CODES = {
    "active_mapping_conflict",
    "canonical_layout_empty",
    "canonical_layout_missing",
    "entry_budget",
    "inactive_storage_root",
    "mapping_overlap",
    "multiple_canonical_layouts",
    "storage_root_unreachable",
    "time_budget",
    "unreadable_directory",
    "unreadable_entry",
    "unsafe_catalog_identity",
    "unsafe_entry",
    "unsafe_platform_identity",
    "unsupported_entry",
    "ambiguous_catalog_identity",
}


@dataclass(frozen=True, slots=True)
class LegacyMigrationOutcome:
    state: str
    migration_id: int
    migration_version: int
    mapping_id: int
    mapping_version: int
    platform_id: int
    storage_root_id: int
    reconnected_catalog_count: int
    unmatched_catalog_count: int
    source_immutable: bool = True
    legacy_fallback_enabled: bool = False


@dataclass(frozen=True, slots=True)
class LegacyRollbackStatus:
    migration_id: int
    migration_version: int
    platform_id: int
    mapping_id: int
    mapping_version: int
    state: str
    rollback_eligible: bool
    first_used: bool
    first_use_operation: str | None
    expires_at: datetime
    expired: bool
    source_immutable: bool = True
    legacy_fallback_enabled: bool = False


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


class LegacyRollbackError(Exception):
    def __init__(
        self,
        code: str,
        *,
        migration_id: int | None = None,
        platform_id: int | None = None,
        current_version: int | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.migration_id = migration_id
        self.platform_id = platform_id
        self.current_version = current_version


class DBLegacyMigrationHandler(DBBaseHandler):
    @staticmethod
    def _after_migration_flush(_stage: str) -> None:
        pass

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

    @staticmethod
    def _impact_problem(code: str | None, count: int = 1) -> LegacyImpactProblem:
        from handler.storage.legacy_migration import LegacyImpactProblem

        return LegacyImpactProblem(
            code if code in _IMPACT_CODES else "canonical_layout_missing", count
        )

    @staticmethod
    def _zero_effects() -> LegacyImpactPlannedEffects:
        from handler.storage.legacy_migration import LegacyImpactPlannedEffects

        return LegacyImpactPlannedEffects(0, 0, 0, 0, 0)

    @classmethod
    def _manual_impact(cls, result, code: str | None) -> LegacyMigrationImpact:
        from handler.storage.legacy_migration import (
            LegacyImpactProposedMapping,
            LegacyMigrationImpact,
        )

        proposed = (
            LegacyImpactProposedMapping(
                result.platform_id,
                result.storage_root_id,
                result.proposed_relative_path,
            )
            if result.proposed_relative_path is not None
            else None
        )
        return LegacyMigrationImpact(
            "manual_mapping_required",
            proposed,
            0,
            0,
            (cls._impact_problem(code),),
            cls._zero_effects(),
            None,
        )

    @staticmethod
    def _catalog_impact(session: Session, platform_id: int):
        from handler.filesystem.storage_resolver import normalize_relative_path
        from handler.storage.legacy_migration import LegacyImpactProblem

        rows = session.execute(
            select(Rom.id, Rom.fs_path, Rom.fs_name)
            .where(Rom.platform_id == platform_id)
            .order_by(Rom.id)
        ).all()
        identities: dict[str, int] = {}
        unsafe = 0
        for row in rows:
            logical = "/".join(part for part in (row.fs_path, row.fs_name) if part)
            try:
                logical = normalize_relative_path(logical)
            except StorageResolutionError:
                unsafe += 1
                continue
            identities[logical] = identities.get(logical, 0) + 1
        ambiguous = sum(count for count in identities.values() if count > 1)
        reconnectable = sum(1 for count in identities.values() if count == 1)
        problems = []
        if unsafe:
            problems.append(LegacyImpactProblem("unsafe_catalog_identity", unsafe))
        if ambiguous:
            problems.append(
                LegacyImpactProblem("ambiguous_catalog_identity", ambiguous)
            )
        return reconnectable, unsafe + ambiguous, tuple(problems)

    def _preview_impact(
        self,
        session: Session,
        result_id: int,
        *,
        platform_id: int,
        expected_result_version: int,
        now: datetime | None,
    ) -> LegacyMigrationImpact:
        from handler.filesystem.storage_resolver import normalize_relative_path
        from handler.storage.legacy_migration import (
            LegacyImpactConfirmation,
            LegacyImpactPlannedEffects,
            LegacyImpactProposedMapping,
            LegacyMigrationImpact,
        )

        identity = session.execute(
            select(
                LegacyDetectionResult.platform_id, LegacyDetectionResult.storage_root_id
            ).where(LegacyDetectionResult.id == result_id)
        ).one_or_none()
        if identity is None:
            raise LegacyDetectionResultError(
                "legacy_detection_missing", result_id=result_id
            )
        if identity.platform_id != platform_id:
            raise LegacyDetectionResultError(
                "legacy_detection_cross_platform",
                result_id=result_id,
                platform_id=platform_id,
            )
        _, root, mappings = self._lock_context(
            session, identity.platform_id, identity.storage_root_id
        )
        result = session.scalar(
            select(LegacyDetectionResult)
            .where(LegacyDetectionResult.id == result_id)
            .with_for_update(of=LegacyDetectionResult)
        )
        if result is None:
            raise LegacyDetectionResultError(
                "legacy_detection_missing", result_id=result_id
            )
        if result.version != expected_result_version:
            raise LegacyDetectionResultError(
                "legacy_detection_stale",
                result_id=result_id,
                platform_id=platform_id,
                current_version=result.version,
            )
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        expiry = result.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= current:
            raise LegacyDetectionResultError(
                "legacy_detection_expired",
                result_id=result_id,
                platform_id=platform_id,
                current_version=result.version,
            )
        if any(mapping.platform_id == platform_id for mapping in mappings):
            return self._manual_impact(result, "active_mapping_conflict")
        if not root.active:
            return self._manual_impact(result, "inactive_storage_root")
        if not result.selectable or result.proposed_relative_path is None:
            return self._manual_impact(result, result.safe_problem_code)
        try:
            relative_path = normalize_relative_path(result.proposed_relative_path)
        except StorageResolutionError:
            return self._manual_impact(result, "unsafe_platform_identity")
        if any(
            mapping.storage_root_id == result.storage_root_id
            and self._paths_overlap(relative_path, mapping.relative_path)
            for mapping in mappings
        ):
            return self._manual_impact(result, "mapping_overlap")
        reconnectable, unmatched, problems = self._catalog_impact(session, platform_id)
        if result.safe_problem_code is not None:
            problems = (self._impact_problem(result.safe_problem_code),) + problems
        proposed = LegacyImpactProposedMapping(
            platform_id, result.storage_root_id, relative_path
        )
        confirmation = LegacyImpactConfirmation(
            result.id,
            result.version,
            platform_id,
            result.storage_root_id,
            relative_path,
            result.observed_mapping_id,
            result.observed_mapping_version,
            reconnectable,
            unmatched,
            expiry,
        )
        return LegacyMigrationImpact(
            "ready",
            proposed,
            reconnectable,
            unmatched,
            problems[:10],
            LegacyImpactPlannedEffects(1, reconnectable, unmatched, 1, 1),
            confirmation,
        )

    @begin_session
    def preview_migration_impact(
        self,
        result_id: int,
        *,
        platform_id: int,
        expected_result_version: int,
        now: datetime | None = None,
        session: Session = None,  # type: ignore
    ) -> LegacyMigrationImpact:
        return self._preview_impact(
            session,
            result_id,
            platform_id=platform_id,
            expected_result_version=expected_result_version,
            now=now,
        )

    @begin_session
    def validate_impact_confirmation(
        self,
        confirmation: LegacyImpactConfirmation,
        *,
        now: datetime | None = None,
        session: Session = None,  # type: ignore
    ) -> LegacyMigrationImpact:
        impact = self._preview_impact(
            session,
            confirmation.detection_result_id,
            platform_id=confirmation.platform_id,
            expected_result_version=confirmation.result_version,
            now=now,
        )
        if impact.confirmation != confirmation:
            raise LegacyDetectionResultError(
                "legacy_impact_stale",
                result_id=confirmation.detection_result_id,
                platform_id=confirmation.platform_id,
                current_version=confirmation.result_version,
            )
        return impact

    @begin_session
    def migrate_platform(
        self,
        confirmation: LegacyImpactConfirmation,
        *,
        actor_user_id: int,
        actor_display_name: str,
        now: datetime | None = None,
        session: Session = None,  # type: ignore
    ) -> LegacyMigrationOutcome:
        from exceptions.storage_exceptions import (
            DuplicateStorageMappingError,
            StoragePersistenceError,
        )
        from handler.database.roms_handler import DBRomsHandler
        from handler.database.storage_handler import DBStorageHandler

        impact = self._preview_impact(
            session,
            confirmation.detection_result_id,
            platform_id=confirmation.platform_id,
            expected_result_version=confirmation.result_version,
            now=now,
        )
        if impact.state != "ready" or impact.confirmation != confirmation:
            raise LegacyDetectionResultError(
                "legacy_impact_stale",
                result_id=confirmation.detection_result_id,
                platform_id=confirmation.platform_id,
                current_version=confirmation.result_version,
            )

        existing = session.scalar(
            select(LegacyMigration)
            .where(
                LegacyMigration.detection_result_id == confirmation.detection_result_id
            )
            .with_for_update(of=LegacyMigration)
        )
        if existing is not None:
            raise LegacyDetectionResultError(
                "legacy_migration_conflict",
                result_id=confirmation.detection_result_id,
                platform_id=confirmation.platform_id,
                current_version=confirmation.result_version,
            )

        try:
            mapping = DBStorageHandler._create_mapping_record(
                session,
                confirmation.platform_id,
                confirmation.storage_root_id,
                confirmation.relative_path,
            )
        except (DuplicateStorageMappingError, StoragePersistenceError):
            raise LegacyDetectionResultError(
                "legacy_impact_stale",
                result_id=confirmation.detection_result_id,
                platform_id=confirmation.platform_id,
                current_version=confirmation.result_version,
            ) from None
        self._after_migration_flush("mapping")

        reconnected, unmatched = DBRomsHandler().reconnect_legacy_catalog(
            confirmation.platform_id, session=session
        )
        if (
            reconnected != confirmation.reconnectable_catalog_count
            or unmatched != confirmation.unmatched_catalog_count
        ):
            raise LegacyDetectionResultError(
                "legacy_impact_stale",
                result_id=confirmation.detection_result_id,
                platform_id=confirmation.platform_id,
                current_version=confirmation.result_version,
            )
        session.flush()
        self._after_migration_flush("catalog")

        DBStorageHandler._append_audit(
            session,
            mapping,
            StorageMappingAuditAction.CREATE,
            None,
            DBStorageHandler._snapshot(mapping),
            actor_user_id,
            actor_display_name,
        )
        self._after_migration_flush("audit")

        completed_at = now or datetime.now(timezone.utc)
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        migration = LegacyMigration(
            detection_result_id=confirmation.detection_result_id,
            platform_id=confirmation.platform_id,
            storage_root_id=confirmation.storage_root_id,
            mapping_id=mapping.id,
            relative_path=confirmation.relative_path,
            state=LegacyMigrationState.COMPLETED,
            version=1,
            actor_user_id=actor_user_id,
            prior_mapping_id=confirmation.observed_mapping_id,
            prior_mapping_version=confirmation.observed_mapping_version,
            prior_mapping_active=(confirmation.observed_mapping_id is not None),
            reconnected_catalog_count=reconnected,
            unmatched_catalog_count=unmatched,
            expires_at=confirmation.expires_at,
            completed_at=completed_at,
        )
        result = session.get(LegacyDetectionResult, confirmation.detection_result_id)
        if result is None or result.version != confirmation.result_version:
            raise LegacyDetectionResultError(
                "legacy_detection_stale",
                result_id=confirmation.detection_result_id,
                platform_id=confirmation.platform_id,
                current_version=(result.version if result is not None else None),
            )
        result.version += 1
        session.add(migration)
        try:
            session.flush()
        except IntegrityError:
            raise LegacyDetectionResultError(
                "legacy_migration_conflict",
                result_id=confirmation.detection_result_id,
                platform_id=confirmation.platform_id,
                current_version=confirmation.result_version,
            ) from None
        self._after_migration_flush("rollback")

        return LegacyMigrationOutcome(
            state=LegacyMigrationState.COMPLETED.value,
            migration_id=migration.id,
            migration_version=migration.version,
            mapping_id=mapping.id,
            mapping_version=mapping.version,
            platform_id=mapping.platform_id,
            storage_root_id=mapping.storage_root_id,
            reconnected_catalog_count=reconnected,
            unmatched_catalog_count=unmatched,
        )

    @staticmethod
    def _rollback_status(
        migration: LegacyMigration,
        mapping: PlatformStorageMapping,
        prior_mapping: PlatformStorageMapping | None = None,
        *,
        now: datetime | None = None,
    ) -> LegacyRollbackStatus:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        expires_at = migration.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        expired = expires_at <= current
        mapping_matches = (
            migration.mapping_id == mapping.id
            and migration.platform_id == mapping.platform_id
            and migration.storage_root_id == mapping.storage_root_id
            and migration.relative_path == mapping.relative_path
        )
        prior_state_matches = not migration.prior_mapping_active or (
            prior_mapping is not None
            and prior_mapping.platform_id == migration.platform_id
            and prior_mapping.version == migration.prior_mapping_version
            and not prior_mapping.active
        )
        eligible = (
            migration.state == LegacyMigrationState.COMPLETED
            and migration.first_used_at is None
            and not expired
            and mapping_matches
            and mapping.active
            and mapping.version == 1
            and prior_state_matches
        )
        return LegacyRollbackStatus(
            migration_id=migration.id,
            migration_version=migration.version,
            platform_id=migration.platform_id,
            mapping_id=mapping.id,
            mapping_version=mapping.version,
            state=migration.state,
            rollback_eligible=eligible,
            first_used=migration.first_used_at is not None,
            first_use_operation=migration.first_use_operation,
            expires_at=expires_at,
            expired=expired,
        )

    @staticmethod
    def _load_rollback_mappings(
        session: Session, migration: LegacyMigration
    ) -> tuple[PlatformStorageMapping, PlatformStorageMapping | None]:
        if migration.mapping_id is None:
            raise LegacyRollbackError(
                "legacy_rollback_stale",
                migration_id=migration.id,
                platform_id=migration.platform_id,
                current_version=migration.version,
            )
        mapping_ids = {migration.mapping_id}
        if migration.prior_mapping_id is not None:
            mapping_ids.add(migration.prior_mapping_id)
        mappings = list(
            session.scalars(
                select(PlatformStorageMapping)
                .where(PlatformStorageMapping.id.in_(mapping_ids))
                .order_by(PlatformStorageMapping.id)
                .with_for_update(of=PlatformStorageMapping)
            ).all()
        )
        mapping = next(
            (item for item in mappings if item.id == migration.mapping_id), None
        )
        if mapping is None:
            raise LegacyRollbackError(
                "legacy_rollback_stale",
                migration_id=migration.id,
                platform_id=migration.platform_id,
                current_version=migration.version,
            )
        prior = next(
            (item for item in mappings if item.id == migration.prior_mapping_id),
            None,
        )
        return mapping, prior

    @begin_session
    def get_rollback_status(
        self,
        migration_id: int,
        *,
        platform_id: int,
        now: datetime | None = None,
        session: Session = None,  # type: ignore
    ) -> LegacyRollbackStatus:
        migration = session.get(LegacyMigration, migration_id)
        if migration is None:
            raise LegacyRollbackError(
                "legacy_rollback_missing", migration_id=migration_id
            )
        if migration.platform_id != platform_id:
            raise LegacyRollbackError(
                "legacy_rollback_cross_platform",
                migration_id=migration_id,
                platform_id=platform_id,
            )
        mapping, prior_mapping = self._load_rollback_mappings(session, migration)
        return self._rollback_status(migration, mapping, prior_mapping, now=now)

    @begin_session
    def rollback_migration(
        self,
        migration_id: int,
        *,
        platform_id: int,
        expected_version: int,
        actor_user_id: int,
        actor_display_name: str,
        now: datetime | None = None,
        session: Session = None,  # type: ignore
    ) -> LegacyRollbackStatus:
        from handler.database.storage_handler import DBStorageHandler

        migration = session.scalar(
            select(LegacyMigration)
            .where(LegacyMigration.id == migration_id)
            .with_for_update(of=LegacyMigration)
        )
        if migration is None:
            raise LegacyRollbackError(
                "legacy_rollback_missing", migration_id=migration_id
            )
        if migration.platform_id != platform_id:
            raise LegacyRollbackError(
                "legacy_rollback_cross_platform",
                migration_id=migration_id,
                platform_id=platform_id,
            )
        if migration.version != expected_version:
            raise LegacyRollbackError(
                "legacy_rollback_stale",
                migration_id=migration_id,
                platform_id=platform_id,
                current_version=migration.version,
            )

        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        expires_at = migration.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= current:
            raise LegacyRollbackError(
                "legacy_rollback_expired",
                migration_id=migration_id,
                platform_id=platform_id,
                current_version=migration.version,
            )
        if migration.state != LegacyMigrationState.COMPLETED:
            raise LegacyRollbackError(
                "legacy_rollback_stale",
                migration_id=migration_id,
                platform_id=platform_id,
                current_version=migration.version,
            )
        if migration.first_used_at is not None:
            raise LegacyRollbackError(
                "legacy_rollback_ineligible",
                migration_id=migration_id,
                platform_id=platform_id,
                current_version=migration.version,
            )

        mapping, prior_mapping = self._load_rollback_mappings(session, migration)
        status = self._rollback_status(migration, mapping, prior_mapping, now=current)
        if not status.rollback_eligible:
            raise LegacyRollbackError(
                "legacy_rollback_stale",
                migration_id=migration_id,
                platform_id=platform_id,
                current_version=migration.version,
            )

        roms = list(
            session.scalars(
                select(Rom)
                .where(Rom.platform_id == platform_id)
                .order_by(Rom.id)
                .with_for_update(of=Rom)
            ).all()
        )
        rom_ids = [rom.id for rom in roms]
        if rom_ids:
            session.scalars(
                select(RomFile)
                .where(RomFile.rom_id.in_(rom_ids))
                .order_by(RomFile.id)
                .with_for_update(of=RomFile)
            ).all()

        old = DBStorageHandler._snapshot(mapping)
        mapping.active = False
        mapping.version += 1
        session.flush()
        if migration.prior_mapping_active:
            if (
                prior_mapping is None
                or prior_mapping.platform_id != migration.platform_id
                or prior_mapping.version != migration.prior_mapping_version
            ):
                raise LegacyRollbackError(
                    "legacy_rollback_stale",
                    migration_id=migration_id,
                    platform_id=platform_id,
                    current_version=migration.version,
                )
            prior_old = DBStorageHandler._snapshot(prior_mapping)
            prior_mapping.active = True
            prior_mapping.version += 1
            session.flush()
            DBStorageHandler._append_audit(
                session,
                prior_mapping,
                StorageMappingAuditAction.ACTIVATE,
                prior_old,
                DBStorageHandler._snapshot(prior_mapping),
                actor_user_id,
                actor_display_name,
            )
        self._after_migration_flush("rollback_mapping")

        if rom_ids:
            session.execute(
                update(Rom)
                .where(Rom.id.in_(rom_ids))
                .values(missing_from_fs=True)
                .execution_options(synchronize_session=False)
            )
            session.execute(
                update(RomFile)
                .where(RomFile.rom_id.in_(rom_ids))
                .values(missing_from_fs=True)
                .execution_options(synchronize_session=False)
            )
        session.flush()
        self._after_migration_flush("rollback_catalog")

        DBStorageHandler._append_audit(
            session,
            mapping,
            StorageMappingAuditAction.REMOVE,
            old,
            DBStorageHandler._snapshot(mapping),
            actor_user_id,
            actor_display_name,
        )
        self._after_migration_flush("rollback_audit")

        migration.state = LegacyMigrationState.ROLLED_BACK
        migration.version += 1
        migration.rolled_back_at = current
        session.flush()
        self._after_migration_flush("rollback_state")
        return self._rollback_status(migration, mapping, now=current)

    @begin_session
    def mark_first_use(
        self,
        mapping_id: int,
        *,
        expected_revision: int,
        operation: str,
        now: datetime | None = None,
        session: Session = None,  # type: ignore
    ) -> LegacyMigration | None:
        if operation not in {"scan", "hash", "stream", "play", "download"}:
            raise ValueError("unsupported legacy first-use operation")

        migration = session.scalar(
            select(LegacyMigration)
            .where(LegacyMigration.mapping_id == mapping_id)
            .with_for_update(of=LegacyMigration)
        )
        if migration is None:
            return None

        mapping = session.scalar(
            select(PlatformStorageMapping)
            .where(PlatformStorageMapping.id == mapping_id)
            .with_for_update(of=PlatformStorageMapping)
        )
        if (
            migration.state != LegacyMigrationState.COMPLETED
            or mapping is None
            or mapping.id != migration.mapping_id
            or not mapping.active
            or mapping.version != expected_revision
        ):
            from exceptions.storage_read import StaleMappedReadError

            raise StaleMappedReadError(mapping_id, expected_revision)

        if migration.first_used_at is None:
            first_used_at = now or datetime.now(timezone.utc)
            if first_used_at.tzinfo is None:
                first_used_at = first_used_at.replace(tzinfo=timezone.utc)
            migration.first_used_at = first_used_at
            migration.first_use_operation = operation
            migration.version += 1
            session.flush()
        return migration

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
