from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import NamedTuple
from urllib.parse import urlsplit

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from decorators.database import begin_session
from models.pc_automation import (
    PcAutomationOutcome,
    PcAutomationQueue,
    PcAutomationQueueState,
    PcAutomationTargetKind,
)
from models.rom import Rom, RomComponent, RomComponentKind

from .base_handler import DBBaseHandler

_ELIGIBLE_COMPONENT_KINDS = frozenset((RomComponentKind.DLC, RomComponentKind.EXTRA))
_MAX_RETRY_COUNT = 8
_MAX_RETRY_DELAY_SECONDS = 24 * 60 * 60


class PcAutomationQueueResult(NamedTuple):
    outcome: PcAutomationOutcome
    item: PcAutomationQueue | None


class _TargetSnapshot(NamedTuple):
    target: Rom | RomComponent
    parent: Rom


class DBPcAutomationHandler(DBBaseHandler):
    """Persist only reviewable, version-bound PC automation evidence."""

    @begin_session
    def get_parent_target(
        self, rom_id: int, session: Session = None  # type: ignore
    ) -> Rom | None:
        return session.get(Rom, rom_id)

    @begin_session
    def get_component_target(
        self, rom_id: int, component_id: int, session: Session = None  # type: ignore
    ) -> RomComponent | None:
        snapshot = self._load_target(
            session, PcAutomationTargetKind.COMPONENT, rom_id, component_id
        )
        return snapshot.target if snapshot is not None else None

    @begin_session
    def upsert_pending(
        self,
        *,
        target_kind: PcAutomationTargetKind,
        rom_id: int,
        component_id: int | None,
        expected_target_updated_at: datetime,
        normalized_query: str,
        candidate_fingerprint: str,
        candidate_title: str | None = None,
        candidate_cover_url: str | None = None,
        provider: str | None = None,
        provider_candidate_id: str | None = None,
        reason: str | None = None,
        session: Session = None,  # type: ignore
    ) -> PcAutomationQueueResult:
        snapshot = self._load_target(
            session, target_kind, rom_id, component_id, for_update=True
        )
        if snapshot is None:
            return PcAutomationQueueResult(PcAutomationOutcome.MISSING_TARGET, None)
        if self._is_protected(snapshot):
            return PcAutomationQueueResult(PcAutomationOutcome.PROTECTED_TARGET, None)
        if snapshot.target.updated_at != expected_target_updated_at:
            return PcAutomationQueueResult(PcAutomationOutcome.STALE_TARGET, None)

        query = self._bounded_text(normalized_query, 350, required=True)
        fingerprint = self._bounded_text(candidate_fingerprint, 255, required=True)
        if query is None or fingerprint is None:
            return PcAutomationQueueResult(PcAutomationOutcome.CONFLICT, None)

        target_identity = self._target_identity(target_kind, rom_id, component_id)
        existing = session.scalar(
            select(PcAutomationQueue).where(
                PcAutomationQueue.target_identity == target_identity
            )
        )
        values = self._evidence_values(
            snapshot,
            target_kind,
            rom_id,
            component_id,
            query,
            fingerprint,
            candidate_title,
            candidate_cover_url,
            provider,
            provider_candidate_id,
            reason,
        )
        if existing is None:
            item = PcAutomationQueue(**values)
            session.add(item)
            session.flush()
            session.refresh(item)
            return PcAutomationQueueResult(PcAutomationOutcome.CREATED, item)

        unchanged = (
            existing.target_incarnation == values["target_incarnation"]
            and existing.target_updated_at == values["target_updated_at"]
            and existing.candidate_fingerprint == fingerprint
        )
        if unchanged:
            return PcAutomationQueueResult(PcAutomationOutcome.UNCHANGED, existing)

        for key, value in values.items():
            setattr(existing, key, value)
        existing.state = PcAutomationQueueState.PENDING
        existing.retry_count = 0
        existing.next_retry_at = None
        existing.last_attempt_at = None
        existing.skipped_at = None
        session.flush()
        session.refresh(existing)
        return PcAutomationQueueResult(PcAutomationOutcome.REOPENED, existing)

    @begin_session
    def list_pending(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        session: Session = None,  # type: ignore
    ) -> tuple[list[PcAutomationQueue], int]:
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        predicate = PcAutomationQueue.state == PcAutomationQueueState.PENDING
        total = session.scalar(
            select(func.count()).select_from(PcAutomationQueue).where(predicate)
        )
        items = list(
            session.scalars(
                select(PcAutomationQueue)
                .where(predicate)
                .order_by(PcAutomationQueue.created_at, PcAutomationQueue.id)
                .limit(limit)
                .offset(offset)
            )
        )
        return items, total or 0

    @begin_session
    def get_review_item(
        self, queue_id: int, session: Session = None  # type: ignore
    ) -> PcAutomationQueue | None:
        return session.get(PcAutomationQueue, queue_id)

    @begin_session
    def mark_skipped(
        self,
        queue_id: int,
        expected_queue_updated_at: datetime,
        session: Session = None,  # type: ignore
    ) -> PcAutomationQueueResult:
        item = self._current_queue_item(session, queue_id, expected_queue_updated_at)
        if item is None:
            return PcAutomationQueueResult(PcAutomationOutcome.CONFLICT, None)
        snapshot = self._load_item_target(session, item, for_update=True)
        if snapshot is None:
            return PcAutomationQueueResult(PcAutomationOutcome.MISSING_TARGET, None)
        if self._is_protected(snapshot):
            return PcAutomationQueueResult(PcAutomationOutcome.PROTECTED_TARGET, None)
        if not self._matches_target(item, snapshot):
            return PcAutomationQueueResult(PcAutomationOutcome.STALE_TARGET, None)
        item.state = PcAutomationQueueState.SKIPPED
        item.skipped_at = datetime.now(timezone.utc)
        session.flush()
        session.refresh(item)
        return PcAutomationQueueResult(PcAutomationOutcome.SKIPPED, item)

    @begin_session
    def requeue(
        self,
        queue_id: int,
        expected_queue_updated_at: datetime,
        session: Session = None,  # type: ignore
    ) -> PcAutomationQueueResult:
        item = self._current_queue_item(session, queue_id, expected_queue_updated_at)
        if item is None:
            return PcAutomationQueueResult(PcAutomationOutcome.CONFLICT, None)
        snapshot = self._load_item_target(session, item, for_update=True)
        if snapshot is None:
            return PcAutomationQueueResult(PcAutomationOutcome.MISSING_TARGET, None)
        if self._is_protected(snapshot):
            return PcAutomationQueueResult(PcAutomationOutcome.PROTECTED_TARGET, None)
        if not self._matches_target(item, snapshot):
            return PcAutomationQueueResult(PcAutomationOutcome.STALE_TARGET, None)
        item.state = PcAutomationQueueState.PENDING
        item.next_retry_at = None
        item.last_attempt_at = None
        item.skipped_at = None
        session.flush()
        session.refresh(item)
        return PcAutomationQueueResult(PcAutomationOutcome.REQUEUED, item)

    @begin_session
    def mark_retryable_failure(
        self,
        queue_id: int,
        expected_queue_updated_at: datetime,
        *,
        retry_after_seconds: int,
        session: Session = None,  # type: ignore
    ) -> PcAutomationQueueResult:
        item = self._current_queue_item(session, queue_id, expected_queue_updated_at)
        if item is None:
            return PcAutomationQueueResult(PcAutomationOutcome.CONFLICT, None)
        snapshot = self._load_item_target(session, item, for_update=True)
        if snapshot is None:
            return PcAutomationQueueResult(PcAutomationOutcome.MISSING_TARGET, None)
        if self._is_protected(snapshot):
            return PcAutomationQueueResult(PcAutomationOutcome.PROTECTED_TARGET, None)
        if not self._matches_target(item, snapshot):
            return PcAutomationQueueResult(PcAutomationOutcome.STALE_TARGET, None)
        if item.retry_count >= _MAX_RETRY_COUNT:
            return PcAutomationQueueResult(PcAutomationOutcome.CONFLICT, item)
        delay = min(max(retry_after_seconds, 0), _MAX_RETRY_DELAY_SECONDS)
        item.retry_count += 1
        item.state = PcAutomationQueueState.RETRYABLE_FAILURE
        item.last_attempt_at = datetime.now(timezone.utc)
        item.next_retry_at = item.last_attempt_at + timedelta(seconds=delay)
        session.flush()
        session.refresh(item)
        return PcAutomationQueueResult(PcAutomationOutcome.RETRY_SCHEDULED, item)

    @begin_session
    def claim(
        self,
        queue_id: int,
        expected_queue_updated_at: datetime,
        expected_target_updated_at: datetime,
        session: Session = None,  # type: ignore
    ) -> PcAutomationQueueResult:
        item = self._current_queue_item(session, queue_id, expected_queue_updated_at)
        if item is None:
            return PcAutomationQueueResult(PcAutomationOutcome.CONFLICT, None)
        snapshot = self._load_item_target(session, item, for_update=True)
        if snapshot is None:
            return PcAutomationQueueResult(PcAutomationOutcome.MISSING_TARGET, None)
        if self._is_protected(snapshot):
            return PcAutomationQueueResult(PcAutomationOutcome.PROTECTED_TARGET, None)
        if (
            snapshot.target.updated_at != expected_target_updated_at
            or not self._matches_target(item, snapshot)
        ):
            return PcAutomationQueueResult(PcAutomationOutcome.STALE_TARGET, None)
        item.state = PcAutomationQueueState.CLAIMED
        item.last_attempt_at = datetime.now(timezone.utc)
        session.flush()
        session.refresh(item)
        return PcAutomationQueueResult(PcAutomationOutcome.CLAIMED, item)

    @begin_session
    def resolve_after_manual_selection(
        self,
        *,
        target_kind: PcAutomationTargetKind,
        rom_id: int,
        component_id: int | None,
        consumed_target_updated_at: datetime,
        session: Session = None,  # type: ignore
    ) -> PcAutomationQueueResult:
        """Claim the exact pending review item consumed by a manual selection."""
        snapshot = self._load_target(
            session, target_kind, rom_id, component_id, for_update=True
        )
        if snapshot is None:
            return PcAutomationQueueResult(PcAutomationOutcome.MISSING_TARGET, None)
        item = session.scalar(
            select(PcAutomationQueue)
            .where(
                PcAutomationQueue.target_identity
                == self._target_identity(target_kind, rom_id, component_id)
            )
            .with_for_update()
        )
        if (
            item is None
            or item.state != PcAutomationQueueState.PENDING
            or item.target_incarnation != snapshot.parent.incarnation_token
            or item.target_updated_at != consumed_target_updated_at
        ):
            return PcAutomationQueueResult(PcAutomationOutcome.UNCHANGED, None)
        item.state = PcAutomationQueueState.CLAIMED
        item.last_attempt_at = datetime.now(timezone.utc)
        session.flush()
        session.refresh(item)
        return PcAutomationQueueResult(PcAutomationOutcome.CLAIMED, item)

    @staticmethod
    def _target_identity(
        target_kind: PcAutomationTargetKind, rom_id: int, component_id: int | None
    ) -> str:
        if target_kind == PcAutomationTargetKind.PARENT and component_id is None:
            return f"parent:{rom_id}"
        if target_kind == PcAutomationTargetKind.COMPONENT and component_id is not None:
            return f"component:{rom_id}:{component_id}"
        return ""

    @staticmethod
    def _bounded_text(value: str | None, length: int, *, required: bool) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value or len(value) > length or any(ord(char) < 32 for char in value):
            return None
        return value

    @staticmethod
    def _safe_cover_url(value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) > 2048 or any(ord(char) < 32 for char in value):
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            return None
        return value

    def _evidence_values(
        self,
        snapshot: _TargetSnapshot,
        target_kind: PcAutomationTargetKind,
        rom_id: int,
        component_id: int | None,
        normalized_query: str,
        candidate_fingerprint: str,
        candidate_title: str | None,
        candidate_cover_url: str | None,
        provider: str | None,
        provider_candidate_id: str | None,
        reason: str | None,
    ) -> dict[str, object]:
        return {
            "target_identity": self._target_identity(target_kind, rom_id, component_id),
            "target_kind": target_kind,
            "rom_id": rom_id,
            "component_id": component_id,
            "target_incarnation": snapshot.parent.incarnation_token,
            "target_updated_at": snapshot.target.updated_at,
            "normalized_query": normalized_query,
            "candidate_fingerprint": candidate_fingerprint,
            "candidate_title": self._bounded_text(candidate_title, 350, required=False),
            "candidate_cover_url": self._safe_cover_url(candidate_cover_url),
            "provider": self._bounded_text(provider, 100, required=False),
            "provider_candidate_id": self._bounded_text(
                provider_candidate_id, 255, required=False
            ),
            "reason": self._bounded_text(reason, 255, required=False),
        }

    @staticmethod
    def _current_queue_item(
        session: Session, queue_id: int, expected_updated_at: datetime
    ) -> PcAutomationQueue | None:
        return session.scalar(
            select(PcAutomationQueue)
            .where(
                PcAutomationQueue.id == queue_id,
                PcAutomationQueue.updated_at == expected_updated_at,
            )
            .with_for_update()
        )

    @staticmethod
    def _is_protected(snapshot: _TargetSnapshot) -> bool:
        if snapshot.target is snapshot.parent:
            return bool(snapshot.parent.manual_metadata)
        metadata = snapshot.target.component_metadata
        return metadata is not None and metadata.metadata_source == "manual"

    @staticmethod
    def _matches_target(item: PcAutomationQueue, snapshot: _TargetSnapshot) -> bool:
        return (
            item.target_incarnation == snapshot.parent.incarnation_token
            and item.target_updated_at == snapshot.target.updated_at
        )

    def _load_item_target(
        self, session: Session, item: PcAutomationQueue, *, for_update: bool
    ) -> _TargetSnapshot | None:
        return self._load_target(
            session,
            item.target_kind,
            item.rom_id,
            item.component_id,
            for_update=for_update,
        )

    @staticmethod
    def _load_target(
        session: Session,
        target_kind: PcAutomationTargetKind,
        rom_id: int,
        component_id: int | None,
        *,
        for_update: bool = False,
    ) -> _TargetSnapshot | None:
        if target_kind == PcAutomationTargetKind.PARENT and component_id is None:
            statement = select(Rom).where(Rom.id == rom_id)
            if for_update:
                statement = statement.with_for_update()
            parent = session.scalar(statement)
            return _TargetSnapshot(parent, parent) if parent is not None else None
        if target_kind != PcAutomationTargetKind.COMPONENT or component_id is None:
            return None
        statement = (
            select(RomComponent)
            .options(
                selectinload(RomComponent.component_metadata),
                selectinload(RomComponent.rom),
            )
            .where(
                and_(
                    RomComponent.id == component_id,
                    RomComponent.rom_id == rom_id,
                    RomComponent.kind.in_(_ELIGIBLE_COMPONENT_KINDS),
                )
            )
        )
        if for_update:
            statement = statement.with_for_update()
        component = session.scalar(statement)
        if component is None or component.rom is None:
            return None
        return _TargetSnapshot(component, component.rom)
