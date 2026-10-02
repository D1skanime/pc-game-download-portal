"""Protected review routes for durable PC metadata automation evidence."""

from typing import Annotated

from fastapi import HTTPException, Path, Query, Request, status

from decorators.auth import protected_route
from endpoints.responses.rom import (
    PcAutomationBatchRequest,
    PcAutomationBatchResponse,
    PcAutomationQueueItemSchema,
    PcAutomationQueueResponse,
    PcAutomationReviewActionRequest,
    PcAutomationReviewActionResponse,
)
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_rom_visible
from handler.database import db_rom_handler
from handler.database.pc_automation_handler import PcAutomationQueueResult
from handler.metadata.pc_automation import (
    ReviewAction,
    ReviewBatchAction,
    pc_automation_handler,
)
from models.pc_automation import PcAutomationOutcome, PcAutomationTargetKind
from models.rom import RomComponentKind
from utils.router import APIRouter

router = APIRouter()


def _schema(item) -> PcAutomationQueueItemSchema:
    component_kind = None
    if item.component_id is not None:
        component = db_rom_handler.get_pc_component_by_id(
            item.rom_id, item.component_id
        )
        if component is not None and component.kind in {
            RomComponentKind.DLC,
            RomComponentKind.EXTRA,
        }:
            component_kind = component.kind
    return PcAutomationQueueItemSchema(
        id=item.id,
        rom_id=item.rom_id,
        component_id=item.component_id,
        component_kind=component_kind,
        target_kind=item.target_kind,
        candidate_fingerprint=item.candidate_fingerprint,
        candidate_title=item.candidate_title,
        candidate_cover_url=item.candidate_cover_url,
        provider=item.provider,
        reason=item.reason,
        state=item.state,
        expected_queue_version=item.updated_at,
        expected_target_version=item.target_updated_at,
    )


def _visible_item(request: Request, queue_id: int):
    item = pc_automation_handler.get_review_item(queue_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    rom = db_rom_handler.get_rom(item.rom_id)
    if rom is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    assert_rom_visible(request, rom)
    return item


def _raise_for_outcome(result: PcAutomationQueueResult) -> None:
    if result.outcome not in {PcAutomationOutcome.CLAIMED} or result.item is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)


@protected_route(router.get, "/pc-automation/review-queue", [Scope.ROMS_READ])
async def get_review_queue(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PcAutomationQueueResponse:
    items, _total = await pc_automation_handler.list_pending(limit=limit, offset=offset)
    visible = []
    for item in items:
        rom = db_rom_handler.get_rom(item.rom_id)
        if rom is None:
            continue
        try:
            assert_rom_visible(request, rom)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_404_NOT_FOUND:
                raise
            continue
        response_item = _schema(item)
        if (
            item.target_kind == PcAutomationTargetKind.COMPONENT
            and response_item.component_kind is None
        ):
            continue
        visible.append(response_item)
    # Do not let a hidden target change a count visible to this caller.
    return PcAutomationQueueResponse(
        items=visible, total=len(visible), limit=limit, offset=offset
    )


@protected_route(
    router.post, "/pc-automation/review-queue/{queue_id}/accept", [Scope.ROMS_WRITE]
)
async def accept_review_item(
    request: Request,
    queue_id: Annotated[int, Path(ge=1)],
    action: PcAutomationReviewActionRequest,
) -> PcAutomationReviewActionResponse:
    _visible_item(request, queue_id)
    result = await pc_automation_handler.apply_review_item(
        queue_id=queue_id,
        expected_queue_updated_at=action.expected_queue_version,
        expected_target_updated_at=action.expected_target_version,
        candidate_fingerprint=action.candidate_fingerprint,
    )
    _raise_for_outcome(result)
    return PcAutomationReviewActionResponse(item=_schema(result.item))


@protected_route(
    router.post, "/pc-automation/review-queue/{queue_id}/skip", [Scope.ROMS_WRITE]
)
async def skip_review_item(
    request: Request,
    queue_id: Annotated[int, Path(ge=1)],
    action: PcAutomationReviewActionRequest,
) -> PcAutomationReviewActionResponse:
    item = _visible_item(request, queue_id)
    if (
        item.candidate_fingerprint != action.candidate_fingerprint
        or item.target_updated_at != action.expected_target_version
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    result = pc_automation_handler.queue_handler.mark_skipped(
        queue_id, action.expected_queue_version
    )
    if result.outcome != PcAutomationOutcome.SKIPPED or result.item is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    return PcAutomationReviewActionResponse(item=_schema(result.item))


@protected_route(
    router.post, "/pc-automation/review-queue/{queue_id}/requeue", [Scope.ROMS_WRITE]
)
async def requeue_review_item(
    request: Request,
    queue_id: Annotated[int, Path(ge=1)],
    action: PcAutomationReviewActionRequest,
) -> PcAutomationReviewActionResponse:
    item = _visible_item(request, queue_id)
    if (
        item.candidate_fingerprint != action.candidate_fingerprint
        or item.target_updated_at != action.expected_target_version
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    result = pc_automation_handler.queue_handler.requeue(
        queue_id, action.expected_queue_version
    )
    if result.outcome != PcAutomationOutcome.REQUEUED or result.item is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    return PcAutomationReviewActionResponse(item=_schema(result.item))


@protected_route(
    router.post, "/pc-automation/review-queue/batch-accept", [Scope.ROMS_WRITE]
)
async def batch_accept_review_items(
    request: Request, action: PcAutomationBatchRequest
) -> PcAutomationBatchResponse:
    for batch_item in action.items:
        _visible_item(request, batch_item.queue_id)
    results = await pc_automation_handler.apply_review_batch(
        ReviewBatchAction(
            target_kind=action.target_kind,
            candidate_fingerprint=action.candidate_fingerprint,
            items=[
                ReviewAction(
                    queue_id=item.queue_id,
                    expected_queue_updated_at=item.expected_queue_version,
                    expected_target_updated_at=item.expected_target_version,
                )
                for item in action.items
            ],
        )
    )
    if len(results) != len(action.items):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    for result in results:
        _raise_for_outcome(result)
    return PcAutomationBatchResponse(items=[_schema(result.item) for result in results])
