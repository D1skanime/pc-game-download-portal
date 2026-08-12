import base64
import binascii
import heapq
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

from fastapi import HTTPException, Query, Request, status

from config import TASK_RESULT_TTL
from decorators.auth import protected_route
from endpoints.responses.storage import (
    LegacyDetectionErrorCode,
    LegacyDetectionErrorDetail,
    LegacyDetectionErrorResponse,
    LegacyDetectionJobSchema,
    LegacyDetectionRequestSchema,
    LegacyDetectionResultSchema,
    LegacyImpactConfirmationSchema,
    LegacyImpactPlannedEffectsSchema,
    LegacyImpactPreviewRequestSchema,
    LegacyImpactPreviewSchema,
    LegacyImpactProblemSchema,
    LegacyImpactProposedMappingSchema,
    StorageConflictDetail,
    StorageConflictErrorCode,
    StorageConflictResponse,
    StorageDirectoryEntrySchema,
    StorageDirectoryPageSchema,
    StorageErrorDetail,
    StorageErrorResponse,
    StorageMappingAuditPageSchema,
    StorageMappingAuditSchema,
    StorageMappingCreateSchema,
    StorageMappingPreviewSchema,
    StorageMappingPreviewStateSchema,
    StorageMappingRemovalConfirmationSchema,
    StorageMappingRemovalConsequencesSchema,
    StorageMappingSchema,
    StorageMappingSnapshotSchema,
    StorageMappingTestSchema,
    StorageMappingUpdateSchema,
    StorageMappingVersionSchema,
    StorageReadErrorCode,
    StorageRootHealthSchema,
    StorageRootSchema,
)
from exceptions.storage_exceptions import (
    DuplicateStorageMappingError,
    InvalidRelativePathError,
    InvalidStorageCursorError,
    MissingPlatformStorageMappingError,
    MissingStorageRootError,
    MissingStorageTargetError,
    SafeStorageFilesystemError,
    StaleStorageMappingVersionError,
    StorageMappingConsequencesChangedError,
    StorageMappingOverlapError,
    StorageResolutionError,
    StorageScanLimitError,
    UnsafeSymlinkError,
)
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_admin
from handler.database import (
    db_legacy_migration_handler,
    db_mapping_previews_handler,
    db_storage_handler,
)
from handler.database.legacy_migration_handler import LegacyDetectionResultError
from handler.filesystem.storage_resolver import (
    MAX_DIRECTORY_PAGE_SIZE,
    MAX_DIRECTORY_SCAN_ENTRIES,
    MAX_STORAGE_CURSOR_LENGTH,
    browse_storage_directories,
    get_storage_root_health_snapshot,
    resolve_directory,
)
from handler.redis_handler import low_prio_queue
from models.storage import (
    STORAGE_MAPPING_PATH_MAX_LENGTH,
    LegacyDetectionResult,
    PlatformStorageMapping,
    StorageMappingAudit,
    StorageMappingAuditAction,
    StorageRoot,
)
from tasks.manual.detect_legacy_storage import detect_legacy_storage_task
from tasks.manual.preview_mapping import preview_mapping_task
from utils.router import APIRouter

router = APIRouter(prefix="/storage", tags=["storage"])


@dataclass(frozen=True, slots=True)
class StorageMappingPreview:
    examined_entry_count: int
    candidate_file_count: int
    candidate_directory_count: int
    truncated: bool
    next_cursor: str | None


def _preview_cursor(mapping: PlatformStorageMapping, name: str) -> str:
    payload = json.dumps(
        {
            "v": 1,
            "mapping": mapping.id,
            "version": mapping.version,
            "path": mapping.relative_path,
            "name": name,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _preview_after(mapping: PlatformStorageMapping, cursor: str | None) -> bytes | None:
    if cursor is None:
        return None
    if not cursor or len(cursor) > MAX_STORAGE_CURSOR_LENGTH:
        raise InvalidStorageCursorError
    try:
        payload = json.loads(
            base64.b64decode(
                cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True
            )
        )
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise InvalidStorageCursorError from None
    if (
        not isinstance(payload, dict)
        or set(payload) != {"v", "mapping", "version", "path", "name"}
        or payload["v"] != 1
        or payload["mapping"] != mapping.id
        or payload["version"] != mapping.version
        or payload["path"] != mapping.relative_path
        or not isinstance(payload["name"], str)
    ):
        raise InvalidStorageCursorError
    return payload["name"].encode()


def preview_storage_mapping(
    mapping: PlatformStorageMapping,
    storage_root: StorageRoot,
    limit: int,
    cursor: str | None,
) -> StorageMappingPreview:
    directory = resolve_directory(storage_root, mapping.relative_path)
    after = _preview_after(mapping, cursor)
    examined = 0

    def candidates():
        nonlocal examined
        try:
            with os.scandir(directory) as iterator:
                for item in iterator:
                    examined += 1
                    if examined > MAX_DIRECTORY_SCAN_ENTRIES:
                        raise StorageScanLimitError(storage_root.id)
                    if item.is_symlink():
                        raise UnsafeSymlinkError
                    key = item.name.encode()
                    if after is not None and key <= after:
                        continue
                    if item.is_dir(follow_symlinks=False):
                        yield key, item.name, True
                    elif item.is_file(follow_symlinks=False):
                        yield key, item.name, False
        except (StorageScanLimitError, UnsafeSymlinkError):
            raise
        except OSError:
            raise SafeStorageFilesystemError(storage_root.id) from None

    selected = heapq.nsmallest(limit + 1, candidates(), key=lambda item: item[0])
    visible = selected[:limit]
    truncated = len(selected) > limit
    return StorageMappingPreview(
        examined_entry_count=examined,
        candidate_file_count=sum(not item[2] for item in visible),
        candidate_directory_count=sum(item[2] for item in visible),
        truncated=truncated,
        next_cursor=_preview_cursor(mapping, visible[-1][1]) if truncated else None,
    )


_ERROR_STATUS = {
    InvalidRelativePathError: status.HTTP_400_BAD_REQUEST,
    InvalidStorageCursorError: status.HTTP_400_BAD_REQUEST,
    MissingStorageRootError: status.HTTP_404_NOT_FOUND,
    MissingStorageTargetError: status.HTTP_404_NOT_FOUND,
}
_ERROR_MESSAGES = {
    "invalid_relative_path": "Storage path must be a safe relative path",
    "invalid_storage_cursor": "Storage cursor is invalid",
    "missing_storage_root": "Storage root was not found",
    "missing_storage_target": "Storage target was not found",
    "inactive_storage_root": "Storage root is inactive",
    "non_directory_storage_target": "Storage target is not a directory",
    "unreadable_storage_target": "Storage target is not readable",
    "unsafe_storage_symlink": "Storage path contains an unsafe symbolic link",
    "storage_escape": "Storage path escapes its approved root",
    "unsafe_writable_root": "Storage root is writable",
    "storage_scan_limit_exceeded": "Storage directory scan limit was exceeded",
    "storage_filesystem_error": "Storage directory could not be read",
    "storage_resolution_error": "Storage operation could not be completed",
}
_ERROR_RESPONSES = {
    400: {"model": StorageErrorResponse},
    404: {"model": StorageErrorResponse},
    422: {"model": StorageErrorResponse},
}
_MAPPING_RESPONSES = {
    **_ERROR_RESPONSES,
    409: {"model": StorageConflictResponse},
}
_LEGACY_ERROR_MESSAGES = {
    "legacy_detection_missing": "Legacy detection result was not found",
    "legacy_detection_stale": "Legacy detection result is stale",
    "legacy_detection_expired": "Legacy detection result has expired",
    "legacy_detection_cross_platform": "Legacy detection result belongs to another platform",
    "legacy_detection_unselectable": "Legacy detection result cannot be selected",
    "legacy_detection_invalid_state": "Legacy detection result state is invalid",
    "legacy_impact_stale": "Legacy migration impact changed; preview again",
}
_LEGACY_ERROR_STATUS = {
    "legacy_detection_missing": status.HTTP_404_NOT_FOUND,
    "legacy_detection_expired": status.HTTP_410_GONE,
}
_LEGACY_RESPONSES = {
    404: {"model": LegacyDetectionErrorResponse},
    409: {"model": LegacyDetectionErrorResponse},
    410: {"model": LegacyDetectionErrorResponse},
}

_CONFLICT_MESSAGES = {
    "platform_mapping_missing": "Platform has no active storage mapping",
    "duplicate_storage_mapping": "Platform already has an active storage mapping",
    "storage_mapping_overlap": "Storage mapping overlaps an active mapping",
    "storage_mapping_stale_version": "Storage mapping changed; reload before retrying",
    "storage_mapping_consequences_changed": (
        "Storage mapping removal consequences changed; preview again"
    ),
}


def _raise_safe_storage_error(error: StorageResolutionError) -> None:
    code = error.code if error.code in _ERROR_MESSAGES else "storage_resolution_error"
    detail = StorageErrorDetail(
        code=StorageReadErrorCode(code), message=_ERROR_MESSAGES[code]
    )
    raise HTTPException(
        status_code=_ERROR_STATUS.get(
            type(error), status.HTTP_422_UNPROCESSABLE_CONTENT
        ),
        detail=detail.model_dump(mode="json"),
    ) from None


def _root_schema(root: StorageRoot) -> StorageRootSchema:
    health = get_storage_root_health_snapshot(root)
    return StorageRootSchema(
        id=root.id,
        name=root.name,
        mode=root.mode,
        active=root.active,
        created_at=root.created_at,
        updated_at=root.updated_at,
        health=StorageRootHealthSchema(
            reachable=health.reachable,
            readable=health.readable,
            non_writable=health.non_writable,
            checked_at=health.checked_at,
            error=health.error,
        ),
    )


def _mapping_schema(mapping: PlatformStorageMapping) -> StorageMappingSchema:
    return StorageMappingSchema(
        id=mapping.id,
        platform_id=mapping.platform_id,
        storage_root_id=mapping.storage_root_id,
        relative_path=mapping.relative_path,
        active=mapping.active,
        version=mapping.version,
    )


def _removal_consequences_schema(
    consequences,
) -> StorageMappingRemovalConsequencesSchema:
    return StorageMappingRemovalConsequencesSchema(
        mapping_id=consequences.mapping_id,
        platform_id=consequences.platform_id,
        mapping_version=consequences.mapping_version,
        retained_visible_unreachable_catalog_count=(
            consequences.retained_visible_unreachable_catalog_count
        ),
        preserves_metadata=consequences.preserves_metadata,
        preserves_saves=consequences.preserves_saves,
        preserves_states=consequences.preserves_states,
        preserves_play_history=consequences.preserves_play_history,
        source_immutable=consequences.source_immutable,
        mapping_revision_invalidated=consequences.mapping_revision_invalidated,
        cancels_mapping_work_at_safe_boundaries=(
            consequences.cancels_mapping_work_at_safe_boundaries
        ),
    )


def _snapshot_schema(
    audit: StorageMappingAudit, prefix: str
) -> StorageMappingSnapshotSchema | None:
    root_id = getattr(audit, f"{prefix}_storage_root_id")
    if root_id is None:
        return None
    return StorageMappingSnapshotSchema(
        storage_root_id=root_id,
        relative_path=getattr(audit, f"{prefix}_relative_path"),
        version=getattr(audit, f"{prefix}_version"),
        active=getattr(audit, f"{prefix}_active"),
    )


def _audit_schema(audit: StorageMappingAudit) -> StorageMappingAuditSchema:
    return StorageMappingAuditSchema(
        id=audit.id,
        actor_user_id=audit.actor_user_id,
        actor_display_name=audit.actor_display_name,
        platform_id=audit.platform_id,
        mapping_id=audit.mapping_id,
        action=audit.action,
        old=_snapshot_schema(audit, "old"),
        new=_snapshot_schema(audit, "new"),
        created_at=audit.created_at,
    )


def _actor(request: Request) -> dict[str, object]:
    return {
        "actor_user_id": request.user.id,
        "actor_display_name": request.user.username,
    }


def _raise_mapping_conflict(error: StorageResolutionError) -> None:
    code = error.code
    if code not in _CONFLICT_MESSAGES:
        _raise_safe_storage_error(error)
    detail = StorageConflictDetail(
        code=StorageConflictErrorCode(code),
        message=_CONFLICT_MESSAGES[code],
        platform_id=getattr(error, "platform_id", None),
        mapping_id=getattr(error, "mapping_id", None),
        current_version=getattr(error, "current_version", None),
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail.model_dump(mode="json", exclude_none=True),
    ) from None


def _legacy_result_expired(result: LegacyDetectionResult) -> bool:
    expires_at = result.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


def _legacy_detection_result_schema(
    result: LegacyDetectionResult,
) -> LegacyDetectionResultSchema:
    return LegacyDetectionResultSchema(
        id=result.id,
        platform_id=result.platform_id,
        storage_root_id=result.storage_root_id,
        state=result.state,
        proposed_relative_path=result.proposed_relative_path,
        observed_files=result.observed_files,
        observed_bytes=result.observed_bytes,
        lower_bound=result.lower_bound,
        selectable=result.selectable,
        safe_problem_code=result.safe_problem_code,
        observed_mapping_id=result.observed_mapping_id,
        observed_mapping_version=result.observed_mapping_version,
        version=result.version,
        created_at=result.created_at,
        completed_at=result.completed_at,
        expires_at=result.expires_at,
        expired=_legacy_result_expired(result),
    )


def _raise_legacy_detection_error(error: LegacyDetectionResultError) -> None:
    code = (
        error.code if error.code in _LEGACY_ERROR_MESSAGES else "legacy_detection_stale"
    )
    detail = LegacyDetectionErrorDetail(
        code=LegacyDetectionErrorCode(code),
        message=_LEGACY_ERROR_MESSAGES[code],
        result_id=error.result_id,
        platform_id=error.platform_id,
        current_version=error.current_version,
    )
    raise HTTPException(
        status_code=_LEGACY_ERROR_STATUS.get(code, status.HTTP_409_CONFLICT),
        detail=detail.model_dump(mode="json", exclude_none=True),
    ) from None


@protected_route(
    router.post,
    "/legacy-detections",
    [Scope.USERS_WRITE],
    response_model=LegacyDetectionJobSchema,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**_ERROR_RESPONSES, **_LEGACY_RESPONSES},
)
def start_legacy_storage_detection(
    request: Request, body: LegacyDetectionRequestSchema
) -> LegacyDetectionJobSchema:
    assert_admin(request)
    try:
        db_legacy_migration_handler.validate_detection_request(
            body.platform_id, body.storage_root_id
        )
    except StorageResolutionError as error:
        _raise_safe_storage_error(error)
    job = low_prio_queue.enqueue(
        detect_legacy_storage_task.run,
        kwargs={
            "platform_id": body.platform_id,
            "storage_root_id": body.storage_root_id,
            "actor_user_id": int(request.user.id),
        },
        job_timeout=detect_legacy_storage_task.timeout,
        result_ttl=TASK_RESULT_TTL,
        meta={
            "task_name": detect_legacy_storage_task.title,
            "task_type": detect_legacy_storage_task.task_type.value,
        },
    )
    return LegacyDetectionJobSchema(
        job_id=job.id,
        platform_id=body.platform_id,
        storage_root_id=body.storage_root_id,
        state="pending",
    )


@protected_route(
    router.get,
    "/legacy-detections/{result_id}",
    [Scope.USERS_READ],
    response_model=LegacyDetectionResultSchema,
    responses=_LEGACY_RESPONSES,
)
def get_legacy_storage_detection(
    request: Request, result_id: int
) -> LegacyDetectionResultSchema:
    assert_admin(request)
    try:
        result = db_legacy_migration_handler.get_detection_result(result_id)
    except LegacyDetectionResultError as error:
        _raise_legacy_detection_error(error)
    return _legacy_detection_result_schema(result)


def _legacy_impact_schema(impact) -> LegacyImpactPreviewSchema:
    proposed = impact.proposed_mapping
    effects = impact.planned_owned_effects
    confirmation = impact.confirmation
    return LegacyImpactPreviewSchema(
        state=impact.state,
        proposed_mapping=(
            LegacyImpactProposedMappingSchema(
                platform_id=proposed.platform_id,
                storage_root_id=proposed.storage_root_id,
                relative_path=proposed.relative_path,
            )
            if proposed is not None
            else None
        ),
        reconnectable_catalog_count=impact.reconnectable_catalog_count,
        unmatched_catalog_count=impact.unmatched_catalog_count,
        problems=[
            LegacyImpactProblemSchema(code=item.code, count=item.count)
            for item in impact.problems
        ],
        planned_owned_effects=LegacyImpactPlannedEffectsSchema(
            mapping_create_count=effects.mapping_create_count,
            catalog_reconnect_count=effects.catalog_reconnect_count,
            catalog_preserve_unmatched_count=effects.catalog_preserve_unmatched_count,
            audit_record_count=effects.audit_record_count,
            rollback_record_count=effects.rollback_record_count,
            source_mutation_count=effects.source_mutation_count,
        ),
        confirmation=(
            LegacyImpactConfirmationSchema(
                detection_result_id=confirmation.detection_result_id,
                result_version=confirmation.result_version,
                platform_id=confirmation.platform_id,
                storage_root_id=confirmation.storage_root_id,
                relative_path=confirmation.relative_path,
                observed_mapping_id=confirmation.observed_mapping_id,
                observed_mapping_version=confirmation.observed_mapping_version,
                reconnectable_catalog_count=confirmation.reconnectable_catalog_count,
                unmatched_catalog_count=confirmation.unmatched_catalog_count,
                expires_at=confirmation.expires_at,
            )
            if confirmation is not None
            else None
        ),
        source_immutable=impact.source_immutable,
        legacy_fallback_enabled=impact.legacy_fallback_enabled,
    )


@protected_route(
    router.post,
    "/legacy-detections/{result_id}/impact",
    [Scope.USERS_WRITE],
    response_model=LegacyImpactPreviewSchema,
    responses=_LEGACY_RESPONSES,
)
def preview_legacy_migration_impact(
    request: Request, result_id: int, body: LegacyImpactPreviewRequestSchema
) -> LegacyImpactPreviewSchema:
    assert_admin(request)
    try:
        impact = db_legacy_migration_handler.preview_migration_impact(
            result_id,
            platform_id=body.platform_id,
            expected_result_version=body.expected_result_version,
        )
    except LegacyDetectionResultError as error:
        _raise_legacy_detection_error(error)
    return _legacy_impact_schema(impact)


@protected_route(
    router.get,
    "/roots",
    [Scope.USERS_READ],
    response_model=list[StorageRootSchema],
    responses=_ERROR_RESPONSES,
)
def get_storage_roots(request: Request) -> list[StorageRootSchema]:
    assert_admin(request)
    return [_root_schema(root) for root in db_storage_handler.get_roots()]


@protected_route(
    router.get,
    "/roots/{storage_root_id}",
    [Scope.USERS_READ],
    response_model=StorageRootSchema,
    responses=_ERROR_RESPONSES,
)
def get_storage_root(request: Request, storage_root_id: int) -> StorageRootSchema:
    assert_admin(request)
    try:
        return _root_schema(db_storage_handler.get_root(storage_root_id))
    except StorageResolutionError as error:
        _raise_safe_storage_error(error)


@protected_route(
    router.get,
    "/roots/{storage_root_id}/browse",
    [Scope.USERS_READ],
    response_model=StorageDirectoryPageSchema,
    responses=_ERROR_RESPONSES,
)
def browse_storage_root(
    request: Request,
    storage_root_id: int,
    parent: Annotated[str, Query(max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)] = "",
    limit: Annotated[int, Query(ge=1, le=MAX_DIRECTORY_PAGE_SIZE)] = 50,
    cursor: Annotated[str | None, Query(max_length=MAX_STORAGE_CURSOR_LENGTH)] = None,
) -> StorageDirectoryPageSchema:
    assert_admin(request)
    try:
        root = db_storage_handler.get_root(storage_root_id)
        page = browse_storage_directories(root, parent, limit=limit, cursor=cursor)
    except StorageResolutionError as error:
        _raise_safe_storage_error(error)

    return StorageDirectoryPageSchema(
        entries=[
            StorageDirectoryEntrySchema(
                name=entry.name,
                relative_path=entry.relative_path,
                navigable=entry.navigable,
            )
            for entry in page.entries
        ],
        next_cursor=page.next_cursor,
    )


@protected_route(
    router.get,
    "/mappings/platforms/{platform_id}",
    [Scope.USERS_READ],
    response_model=StorageMappingSchema,
    responses=_MAPPING_RESPONSES,
)
def get_platform_storage_mapping(
    request: Request, platform_id: int
) -> StorageMappingSchema:
    assert_admin(request)
    try:
        return _mapping_schema(db_storage_handler.get_active_mapping(platform_id))
    except StorageResolutionError as error:
        _raise_mapping_conflict(error)


@protected_route(
    router.post,
    "/mappings/test",
    [Scope.USERS_WRITE],
    response_model=StorageMappingTestSchema,
    responses=_MAPPING_RESPONSES,
)
def test_storage_mapping(
    request: Request, body: StorageMappingCreateSchema
) -> StorageMappingTestSchema:
    assert_admin(request)
    try:
        mapping = db_storage_handler.test_mapping(
            body.platform_id, body.storage_root_id, body.relative_path
        )
    except StorageResolutionError as error:
        if isinstance(
            error, (DuplicateStorageMappingError, StorageMappingOverlapError)
        ):
            _raise_mapping_conflict(error)
        _raise_safe_storage_error(error)
    return StorageMappingTestSchema(
        platform_id=mapping.platform_id,
        storage_root_id=mapping.storage_root_id,
        relative_path=mapping.relative_path,
    )


@protected_route(
    router.get,
    "/mappings/platforms/{platform_id}/preview",
    [Scope.USERS_READ],
    response_model=StorageMappingPreviewSchema,
    responses=_MAPPING_RESPONSES,
)
def preview_platform_storage_mapping(
    request: Request,
    platform_id: int,
    limit: Annotated[int, Query(ge=1, le=MAX_DIRECTORY_PAGE_SIZE)] = 50,
    cursor: Annotated[str | None, Query(max_length=MAX_STORAGE_CURSOR_LENGTH)] = None,
) -> StorageMappingPreviewSchema:
    assert_admin(request)
    try:
        mapping = db_storage_handler.get_active_mapping(platform_id)
        root = db_storage_handler.get_root(mapping.storage_root_id)
        preview = preview_storage_mapping(mapping, root, limit, cursor)
    except StorageResolutionError as error:
        if isinstance(error, MissingPlatformStorageMappingError):
            _raise_mapping_conflict(error)
        _raise_safe_storage_error(error)
    return StorageMappingPreviewSchema(
        mapping_id=mapping.id,
        platform_id=mapping.platform_id,
        storage_root_id=mapping.storage_root_id,
        mapping_version=mapping.version,
        relative_path=mapping.relative_path,
        examined_entry_count=preview.examined_entry_count,
        candidate_file_count=preview.candidate_file_count,
        candidate_directory_count=preview.candidate_directory_count,
        truncated=preview.truncated,
        next_cursor=preview.next_cursor,
    )


def _preview_state_schema(mapping, preview) -> StorageMappingPreviewStateSchema:
    health = get_storage_root_health_snapshot(mapping.storage_root)
    return StorageMappingPreviewStateSchema(
        mapping_id=mapping.id,
        mapping_version=preview.observed_revision,
        health=StorageRootHealthSchema(
            reachable=health.reachable,
            readable=health.readable,
            non_writable=health.non_writable,
            checked_at=health.checked_at,
            error=health.error,
        ),
        state=preview.state,
        observed_files=preview.observed_files,
        observed_directories=preview.observed_directories,
        observed_bytes=preview.observed_bytes,
        lower_bound=preview.lower_bound,
        budget_reason=preview.budget_reason,
        timestamp=preview.completed_at,
        problems=preview.problems,
        stale=preview.stale,
    )


@protected_route(
    router.post,
    "/mappings/{mapping_id}/preview",
    [Scope.USERS_WRITE],
    response_model=StorageMappingPreviewStateSchema,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_MAPPING_RESPONSES,
)
def refresh_platform_storage_mapping_preview(
    request: Request, mapping_id: int
) -> StorageMappingPreviewStateSchema:
    assert_admin(request)
    mapping = db_storage_handler.get_mapping(mapping_id)
    preview = db_mapping_previews_handler.mark_pending(mapping.id, mapping.version)
    low_prio_queue.enqueue(
        preview_mapping_task.run,
        kwargs={
            "mapping_id": mapping.id,
            "expected_revision": mapping.version,
        },
        job_timeout=preview_mapping_task.timeout,
        result_ttl=TASK_RESULT_TTL,
        meta={
            "task_name": preview_mapping_task.title,
            "task_type": preview_mapping_task.task_type.value,
        },
    )
    return _preview_state_schema(mapping, preview)


@protected_route(
    router.get,
    "/mappings/{mapping_id}/preview",
    [Scope.USERS_READ],
    response_model=StorageMappingPreviewStateSchema,
    responses=_MAPPING_RESPONSES,
)
def get_platform_storage_mapping_preview(
    request: Request, mapping_id: int
) -> StorageMappingPreviewStateSchema:
    assert_admin(request)
    mapping = db_storage_handler.get_mapping(mapping_id)
    preview = db_mapping_previews_handler.get(mapping_id)
    if preview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "mapping_preview_missing",
                "message": "No preview has been started for this mapping",
            },
        )
    return _preview_state_schema(mapping, preview)


@protected_route(
    router.post,
    "/mappings",
    [Scope.USERS_WRITE],
    status_code=status.HTTP_201_CREATED,
    response_model=StorageMappingSchema,
    responses=_MAPPING_RESPONSES,
)
def create_storage_mapping(
    request: Request, body: StorageMappingCreateSchema
) -> StorageMappingSchema:
    assert_admin(request)
    try:
        mapping = db_storage_handler.create_mapping(
            body.platform_id,
            body.storage_root_id,
            body.relative_path,
            **_actor(request),
        )
    except StorageResolutionError as error:
        if isinstance(
            error, (DuplicateStorageMappingError, StorageMappingOverlapError)
        ):
            _raise_mapping_conflict(error)
        _raise_safe_storage_error(error)
    return _mapping_schema(mapping)


@protected_route(
    router.put,
    "/mappings/{mapping_id}",
    [Scope.USERS_WRITE],
    response_model=StorageMappingSchema,
    responses=_MAPPING_RESPONSES,
)
def update_storage_mapping(
    request: Request, mapping_id: int, body: StorageMappingUpdateSchema
) -> StorageMappingSchema:
    assert_admin(request)
    try:
        mapping = db_storage_handler.update_mapping(
            mapping_id,
            body.storage_root_id,
            body.relative_path,
            expected_version=body.expected_version,
            **_actor(request),
        )
    except StorageResolutionError as error:
        if isinstance(
            error,
            (
                DuplicateStorageMappingError,
                StorageMappingOverlapError,
                StaleStorageMappingVersionError,
                MissingPlatformStorageMappingError,
            ),
        ):
            _raise_mapping_conflict(error)
        _raise_safe_storage_error(error)
    return _mapping_schema(mapping)


def _change_mapping_state(
    request: Request, mapping_id: int, body: StorageMappingVersionSchema, operation: str
) -> StorageMappingSchema:
    handler = getattr(db_storage_handler, operation)
    try:
        mapping = handler(
            mapping_id, expected_version=body.expected_version, **_actor(request)
        )
    except StorageResolutionError as error:
        if isinstance(
            error,
            (
                DuplicateStorageMappingError,
                StorageMappingOverlapError,
                StaleStorageMappingVersionError,
                MissingPlatformStorageMappingError,
            ),
        ):
            _raise_mapping_conflict(error)
        _raise_safe_storage_error(error)
    return _mapping_schema(mapping)


@protected_route(
    router.post,
    "/mappings/{mapping_id}/deactivate",
    [Scope.USERS_WRITE],
    response_model=StorageMappingSchema,
    responses=_MAPPING_RESPONSES,
)
def deactivate_storage_mapping(
    request: Request, mapping_id: int, body: StorageMappingVersionSchema
) -> StorageMappingSchema:
    assert_admin(request)
    return _change_mapping_state(request, mapping_id, body, "deactivate_mapping")


@protected_route(
    router.post,
    "/mappings/{mapping_id}/removal-consequences",
    [Scope.USERS_WRITE],
    response_model=StorageMappingRemovalConsequencesSchema,
    responses=_MAPPING_RESPONSES,
)
def preview_storage_mapping_removal(
    request: Request, mapping_id: int, body: StorageMappingVersionSchema
) -> StorageMappingRemovalConsequencesSchema:
    assert_admin(request)
    try:
        consequences = db_storage_handler.preview_mapping_removal(
            mapping_id, expected_version=body.expected_version
        )
    except StorageResolutionError as error:
        if isinstance(
            error,
            (
                StaleStorageMappingVersionError,
                MissingPlatformStorageMappingError,
            ),
        ):
            _raise_mapping_conflict(error)
        _raise_safe_storage_error(error)
    return _removal_consequences_schema(consequences)


@protected_route(
    router.delete,
    "/mappings/{mapping_id}",
    [Scope.USERS_WRITE],
    response_model=StorageMappingRemovalConsequencesSchema,
    responses=_MAPPING_RESPONSES,
)
def remove_storage_mapping(
    request: Request,
    mapping_id: int,
    body: StorageMappingRemovalConfirmationSchema,
) -> StorageMappingRemovalConsequencesSchema:
    assert_admin(request)
    try:
        result = db_storage_handler.remove_mapping(
            mapping_id,
            expected_version=body.expected_version,
            expected_unreachable_catalog_count=(
                body.expected_unreachable_catalog_count
            ),
            **_actor(request),
        )
    except StorageResolutionError as error:
        if isinstance(
            error,
            (
                StaleStorageMappingVersionError,
                StorageMappingConsequencesChangedError,
                MissingPlatformStorageMappingError,
            ),
        ):
            _raise_mapping_conflict(error)
        _raise_safe_storage_error(error)
    return _removal_consequences_schema(result.consequences)


@protected_route(
    router.post,
    "/mappings/{mapping_id}/activate",
    [Scope.USERS_WRITE],
    response_model=StorageMappingSchema,
    responses=_MAPPING_RESPONSES,
)
def activate_storage_mapping(
    request: Request, mapping_id: int, body: StorageMappingVersionSchema
) -> StorageMappingSchema:
    assert_admin(request)
    return _change_mapping_state(request, mapping_id, body, "reactivate_mapping")


@protected_route(
    router.get,
    "/mapping-audits",
    [Scope.USERS_READ],
    response_model=StorageMappingAuditPageSchema,
    responses=_MAPPING_RESPONSES,
)
def get_storage_mapping_audits(
    request: Request,
    platform_id: Annotated[int | None, Query(gt=0)] = None,
    mapping_id: Annotated[int | None, Query(gt=0)] = None,
    action: StorageMappingAuditAction | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> StorageMappingAuditPageSchema:
    assert_admin(request)
    try:
        entries, next_cursor = db_storage_handler.list_mapping_audits(
            platform_id=platform_id,
            mapping_id=mapping_id,
            action=action.value if action is not None else None,
            cursor=cursor,
            limit=limit,
        )
    except StorageResolutionError as error:
        _raise_safe_storage_error(error)
    return StorageMappingAuditPageSchema(
        entries=[_audit_schema(entry) for entry in entries], next_cursor=next_cursor
    )
