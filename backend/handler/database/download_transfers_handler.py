from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from decorators.database import begin_session
from models.download_manifest import DownloadManifest, DownloadManifestStatus
from models.download_transfer import (
    DownloadTransferEvent,
    DownloadTransferItem,
    DownloadTransferItemStatus,
    DownloadTransferMode,
    DownloadTransferSession,
    DownloadTransferSessionStatus,
)

from .base_handler import DBBaseHandler

_EVENT_LIMIT = 64
_SESSION_RETENTION = timedelta(days=90)
_CLEANUP_BATCH_LIMIT = 100
_MAX_OBSERVED_BYTES = 2**63 - 1
_TERMINAL_ITEMS = {
    DownloadTransferItemStatus.VERIFIED,
    DownloadTransferItemStatus.CANCELLED,
    DownloadTransferItemStatus.FAILED,
    DownloadTransferItemStatus.STALE,
}
_TERMINAL_SESSIONS = {
    DownloadTransferSessionStatus.COMPLETED,
    DownloadTransferSessionStatus.CANCELLED,
    DownloadTransferSessionStatus.FAILED,
    DownloadTransferSessionStatus.EXPIRED,
    DownloadTransferSessionStatus.STALE,
}


class DBDownloadTransfersHandler(DBBaseHandler):
    @begin_session
    def cleanup_sessions(
        self,
        now: datetime | None = None,
        batch_limit: int = _CLEANUP_BATCH_LIMIT,
        session: Session = None,  # type: ignore
    ) -> dict[str, int]:
        """Reconcile expired manifests and remove old terminal history."""
        current_time = now or datetime.now(UTC)
        cutoff = current_time - _SESSION_RETENTION
        limit = min(max(batch_limit, 1), _CLEANUP_BATCH_LIMIT)

        active_sessions = session.scalars(
            select(DownloadTransferSession)
            .join(
                DownloadManifest,
                DownloadManifest.id == DownloadTransferSession.manifest_id,
            )
            .where(
                DownloadTransferSession.status == DownloadTransferSessionStatus.ACTIVE,
                (
                    (DownloadManifest.status != DownloadManifestStatus.VALID)
                    | (DownloadManifest.expires_at <= current_time)
                ),
            )
            .order_by(DownloadTransferSession.id)
            .limit(limit)
            .with_for_update()
        ).all()
        staled = 0
        for transfer in active_sessions:
            transfer.status = DownloadTransferSessionStatus.STALE
            transfer.ended_at = current_time
            candidates = [
                item for item in transfer.items if item.status not in _TERMINAL_ITEMS
            ]
            for item in candidates:
                item.status = DownloadTransferItemStatus.STALE
                item.ended_at = current_time
                ordinal = (
                    session.scalar(
                        select(func.max(DownloadTransferEvent.ordinal)).where(
                            DownloadTransferEvent.session_id == transfer.id
                        )
                    )
                    or 0
                )
                if ordinal >= _EVENT_LIMIT:
                    continue
                session.add(
                    DownloadTransferEvent(
                        session_id=transfer.id,
                        item_id=item.id,
                        ordinal=ordinal + 1,
                        event_type="stale",
                        observed_bytes=item.observed_bytes,
                        error_code=(
                            "manifest_revoked"
                            if transfer.manifest.status
                            is DownloadManifestStatus.REVOKED
                            else "manifest_expired"
                        ),
                        occurred_at=current_time,
                    )
                )
            staled += 1

        terminal_sessions = session.scalars(
            select(DownloadTransferSession)
            .where(
                DownloadTransferSession.status.in_(_TERMINAL_SESSIONS),
                DownloadTransferSession.ended_at.is_not(None),
                DownloadTransferSession.ended_at <= cutoff,
            )
            .order_by(
                DownloadTransferSession.ended_at,
                DownloadTransferSession.id,
            )
            .limit(limit)
            .with_for_update()
        ).all()
        for transfer in terminal_sessions:
            session.delete(transfer)
        session.flush()
        return {"staled": staled, "deleted": len(terminal_sessions)}

    @begin_session
    def create_session(
        self,
        user_id: int,
        manifest_id: str,
        mode: DownloadTransferMode,
        session: Session = None,  # type: ignore
    ) -> DownloadTransferSession:
        manifest = session.scalar(
            select(DownloadManifest)
            .where(
                DownloadManifest.id == manifest_id, DownloadManifest.user_id == user_id
            )
            .with_for_update()
        )
        if manifest is None:
            raise ValueError("manifest not found")
        if (
            manifest.status is not DownloadManifestStatus.VALID
            or manifest.expires_at <= datetime.now(UTC)
        ):
            raise ValueError("manifest is not active")
        members = [
            member for component in manifest.components for member in component.members
        ]
        transfer = DownloadTransferSession(
            user_id=user_id,
            rom_id=manifest.rom_id,
            manifest_id=manifest.id,
            mode=mode,
            selected_items=len(members),
            selected_bytes=sum(member.size_bytes for member in members),
        )
        transfer.items = [
            DownloadTransferItem(
                manifest_member_id=member.manifest_member_id,
                manifest_member_public_id=member.public_id,
                expected_bytes=member.size_bytes,
                expected_sha256=member.sha256,
            )
            for member in members
        ]
        session.add(transfer)
        session.flush()
        return transfer

    @begin_session
    def get_session(
        self, transfer_id: str, user_id: int, session: Session = None  # type: ignore
    ) -> DownloadTransferSession | None:
        return session.scalar(
            select(DownloadTransferSession).where(
                DownloadTransferSession.id == transfer_id,
                DownloadTransferSession.user_id == user_id,
            )
        )

    @begin_session
    def get_sessions(
        self, user_id: int, limit: int = 50, session: Session = None  # type: ignore
    ) -> Sequence[DownloadTransferSession]:
        return session.scalars(
            select(DownloadTransferSession)
            .where(DownloadTransferSession.user_id == user_id)
            .order_by(DownloadTransferSession.started_at.desc())
            .limit(min(max(limit, 1), 100))
        ).all()

    @begin_session
    def append_observation(
        self,
        transfer_id: str,
        user_id: int,
        item_id: int,
        event_type: str,
        observed_bytes: int = 0,
        error_code: str | None = None,
        sha256: str | None = None,
        session: Session = None,  # type: ignore
    ) -> DownloadTransferEvent:
        if event_type == "served":
            raise ValueError("served is a server fact")
        if event_type not in {
            "handoff",
            "progress",
            "pause",
            "resume",
            "verified",
            "cancel",
            "fail",
        }:
            raise ValueError("invalid event type")
        if observed_bytes < 0 or observed_bytes > _MAX_OBSERVED_BYTES:
            raise ValueError("observed bytes out of bounds")
        if error_code is not None and (
            len(error_code) > 64 or not error_code.isascii()
        ):
            raise ValueError("error code out of bounds")
        transfer = session.scalar(
            select(DownloadTransferSession)
            .where(
                DownloadTransferSession.id == transfer_id,
                DownloadTransferSession.user_id == user_id,
            )
            .with_for_update()
        )
        if transfer is None or transfer.status in _TERMINAL_SESSIONS:
            raise ValueError("session is closed or unavailable")
        item = session.scalar(
            select(DownloadTransferItem)
            .where(
                DownloadTransferItem.id == item_id,
                DownloadTransferItem.session_id == transfer_id,
            )
            .with_for_update()
        )
        if item is None:
            raise ValueError("item not found")
        if item.status in _TERMINAL_ITEMS:
            raise ValueError("item is closed")
        if observed_bytes < item.observed_bytes:
            raise ValueError("observed bytes must be monotonic")
        if event_type == "verified":
            if transfer.mode is DownloadTransferMode.STANDARD:
                raise ValueError("standard transfers cannot verify")
            if observed_bytes != item.expected_bytes or sha256 != item.expected_sha256:
                raise ValueError("local digest does not match manifest")
            next_status = DownloadTransferItemStatus.VERIFIED
        elif event_type == "handoff":
            if item.status is not DownloadTransferItemStatus.QUEUED:
                raise ValueError("handoff requires queued item")
            next_status = DownloadTransferItemStatus.HANDED_TO_BROWSER
        elif event_type == "progress":
            if transfer.mode is DownloadTransferMode.STANDARD:
                raise ValueError("standard transfers do not report progress")
            next_status = item.status
        elif event_type == "pause":
            if transfer.mode is DownloadTransferMode.STANDARD:
                raise ValueError("standard transfers cannot pause")
            next_status = DownloadTransferItemStatus.PAUSED
        elif event_type == "resume":
            if (
                transfer.mode is DownloadTransferMode.STANDARD
                or item.status is not DownloadTransferItemStatus.PAUSED
            ):
                raise ValueError("resume requires enhanced paused item")
            next_status = DownloadTransferItemStatus.HANDED_TO_BROWSER
        elif event_type == "cancel":
            next_status = DownloadTransferItemStatus.CANCELLED
        else:
            next_status = DownloadTransferItemStatus.FAILED
        ordinal = (
            session.scalar(
                select(func.max(DownloadTransferEvent.ordinal)).where(
                    DownloadTransferEvent.session_id == transfer_id
                )
            )
            or 0
        )
        if ordinal >= _EVENT_LIMIT:
            raise ValueError("event history is full")
        item.observed_bytes = observed_bytes
        item.status = next_status
        item.last_activity_at = datetime.now(UTC)
        event = DownloadTransferEvent(
            session_id=transfer_id,
            item_id=item_id,
            ordinal=ordinal + 1,
            event_type=event_type,
            observed_bytes=observed_bytes,
            error_code=error_code,
        )
        session.add(event)
        transfer.observed_bytes = sum(entry.observed_bytes for entry in transfer.items)
        transfer.last_activity_at = item.last_activity_at
        session.flush()
        return event

    @begin_session
    def mark_served(
        self, transfer_id: str, user_id: int, item_id: int, session: Session = None  # type: ignore
    ) -> DownloadTransferItem:
        transfer = session.scalar(
            select(DownloadTransferSession)
            .where(
                DownloadTransferSession.id == transfer_id,
                DownloadTransferSession.user_id == user_id,
            )
            .with_for_update()
        )
        item = session.scalar(
            select(DownloadTransferItem)
            .where(
                DownloadTransferItem.id == item_id,
                DownloadTransferItem.session_id == transfer_id,
            )
            .with_for_update()
        )
        if transfer is None or item is None or transfer.status in _TERMINAL_SESSIONS:
            raise ValueError("session is closed or unavailable")
        if item.status not in {
            DownloadTransferItemStatus.HANDED_TO_BROWSER,
            DownloadTransferItemStatus.PAUSED,
        }:
            raise ValueError("item is not ready to serve")
        item.status = DownloadTransferItemStatus.SERVED
        item.observed_bytes = item.expected_bytes
        session.add(
            DownloadTransferEvent(
                session_id=transfer_id,
                item_id=item_id,
                ordinal=(
                    session.scalar(
                        select(func.max(DownloadTransferEvent.ordinal)).where(
                            DownloadTransferEvent.session_id == transfer_id
                        )
                    )
                    or 0
                )
                + 1,
                event_type="served",
                observed_bytes=item.expected_bytes,
            )
        )
        session.flush()
        return item

    @begin_session
    def cancel_session(self, transfer_id: str, user_id: int, session: Session = None) -> None:  # type: ignore
        transfer = session.scalar(
            select(DownloadTransferSession)
            .where(
                DownloadTransferSession.id == transfer_id,
                DownloadTransferSession.user_id == user_id,
            )
            .with_for_update()
        )
        if transfer is None:
            raise ValueError("session not found")
        if transfer.status in _TERMINAL_SESSIONS:
            return
        transfer.status = DownloadTransferSessionStatus.CANCELLED
        transfer.ended_at = datetime.now(UTC)
        for item in transfer.items:
            if item.status not in _TERMINAL_ITEMS:
                item.status = DownloadTransferItemStatus.CANCELLED
                item.ended_at = transfer.ended_at

    @begin_session
    def mark_stale(
        self,
        transfer_id: str,
        user_id: int,
        item_id: int,
        http_status: int,
        session: Session = None,  # type: ignore
    ) -> DownloadTransferItem:
        if http_status not in {409, 410, 412}:
            raise ValueError("only stale transfer responses can mark an item stale")
        transfer = session.scalar(
            select(DownloadTransferSession)
            .where(
                DownloadTransferSession.id == transfer_id,
                DownloadTransferSession.user_id == user_id,
            )
            .with_for_update()
        )
        item = session.scalar(
            select(DownloadTransferItem)
            .where(
                DownloadTransferItem.id == item_id,
                DownloadTransferItem.session_id == transfer_id,
            )
            .with_for_update()
        )
        if transfer is None or item is None or transfer.status in _TERMINAL_SESSIONS:
            raise ValueError("session is closed or unavailable")
        item.status = DownloadTransferItemStatus.STALE
        item.ended_at = datetime.now(UTC)
        transfer.status = DownloadTransferSessionStatus.STALE
        transfer.ended_at = item.ended_at
        ordinal = (
            session.scalar(
                select(func.max(DownloadTransferEvent.ordinal)).where(
                    DownloadTransferEvent.session_id == transfer_id
                )
            )
            or 0
        )
        session.add(
            DownloadTransferEvent(
                session_id=transfer_id,
                item_id=item_id,
                ordinal=ordinal + 1,
                event_type="stale",
                observed_bytes=item.observed_bytes,
                error_code=f"http_{http_status}",
            )
        )
        session.flush()
        return item
