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
    DownloadTransferSessionResult,
    DownloadTransferSessionStatus,
)

from .base_handler import DBBaseHandler

_EVENT_LIMIT = 64
_SESSION_RETENTION = timedelta(days=90)
_CLEANUP_BATCH_LIMIT = 100
_MAX_OBSERVED_BYTES = 2**63 - 1
_TERMINAL_ITEMS = {
    DownloadTransferItemStatus.SERVED,
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


def _as_utc(value: datetime) -> datetime:
    """Normalize MariaDB's naive UTC datetimes before Python comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class DBDownloadTransfersHandler(DBBaseHandler):
    @staticmethod
    def _reconcile_locked(
        transfer: DownloadTransferSession,
        now: datetime,
    ) -> None:
        transfer.observed_bytes = sum(item.observed_bytes for item in transfer.items)
        for item in transfer.items:
            if item.status in _TERMINAL_ITEMS and item.ended_at is None:
                item.ended_at = now
        if any(item.status not in _TERMINAL_ITEMS for item in transfer.items):
            return
        if transfer.status is DownloadTransferSessionStatus.STALE:
            transfer.result = DownloadTransferSessionResult.FAILED
        elif transfer.status is DownloadTransferSessionStatus.CANCELLED:
            transfer.result = DownloadTransferSessionResult.CANCELLED
        else:
            transfer.status = DownloadTransferSessionStatus.COMPLETED
            successful = all(
                item.status
                in {
                    DownloadTransferItemStatus.SERVED,
                    DownloadTransferItemStatus.VERIFIED,
                }
                for item in transfer.items
            )
            failed = any(
                item.status
                in {
                    DownloadTransferItemStatus.FAILED,
                    DownloadTransferItemStatus.STALE,
                }
                for item in transfer.items
            )
            cancelled = any(
                item.status is DownloadTransferItemStatus.CANCELLED
                for item in transfer.items
            )
            if successful:
                transfer.result = DownloadTransferSessionResult.SUCCESS
            elif failed and any(
                item.status
                in {
                    DownloadTransferItemStatus.SERVED,
                    DownloadTransferItemStatus.VERIFIED,
                }
                for item in transfer.items
            ):
                transfer.result = DownloadTransferSessionResult.PARTIAL
            elif cancelled and not failed:
                transfer.result = DownloadTransferSessionResult.CANCELLED
            else:
                transfer.result = DownloadTransferSessionResult.FAILED
        if transfer.ended_at is None:
            transfer.ended_at = now

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
        if manifest.status is not DownloadManifestStatus.VALID or _as_utc(
            manifest.expires_at
        ) <= datetime.now(UTC):
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
                manifest_member_id=member.id,
                manifest_member_public_id=member.public_id,
                expected_bytes=member.size_bytes,
                expected_sha256=member.sha256,
            )
            for member in members
        ]
        session.add(transfer)
        session.flush()
        # The endpoint serializes the new session after this transaction closes.
        # Load the select-in relationship while the session is still bound.
        _ = transfer.events
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
    def get_attributed_item(
        self,
        transfer_id: str,
        user_id: int,
        manifest_id: str,
        manifest_member_id: int,
        item_id: int,
        session: Session = None,  # type: ignore
    ) -> DownloadTransferItem | None:
        transfer = session.scalar(
            select(DownloadTransferSession)
            .where(
                DownloadTransferSession.id == transfer_id,
                DownloadTransferSession.user_id == user_id,
                DownloadTransferSession.manifest_id == manifest_id,
            )
            .with_for_update()
        )
        if transfer is None or transfer.status in _TERMINAL_SESSIONS:
            return None
        item = session.scalar(
            select(DownloadTransferItem)
            .where(
                DownloadTransferItem.id == item_id,
                DownloadTransferItem.session_id == transfer_id,
                DownloadTransferItem.manifest_member_id == manifest_member_id,
            )
            .with_for_update()
        )
        if item is None or item.status in _TERMINAL_ITEMS:
            return None
        return item

    @begin_session
    def get_sessions(
        self,
        user_id: int,
        limit: int = 50,
        rom_id: int | None = None,
        manifest_id: str | None = None,
        session: Session = None,  # type: ignore
    ) -> Sequence[DownloadTransferSession]:
        stmt = select(DownloadTransferSession).where(
            DownloadTransferSession.user_id == user_id
        )
        if rom_id is not None:
            stmt = stmt.where(DownloadTransferSession.rom_id == rom_id)
        if manifest_id is not None:
            stmt = stmt.where(DownloadTransferSession.manifest_id == manifest_id)
        return session.scalars(
            stmt.order_by(DownloadTransferSession.started_at.desc()).limit(
                min(max(limit, 1), 100)
            )
        ).all()

    @begin_session
    def delete_session(
        self,
        transfer_id: str,
        user_id: int,
        session: Session = None,  # type: ignore
    ) -> bool:
        transfer = session.scalar(
            select(DownloadTransferSession)
            .where(
                DownloadTransferSession.id == transfer_id,
                DownloadTransferSession.user_id == user_id,
            )
            .with_for_update()
        )
        if transfer is None:
            return False
        if transfer.status not in _TERMINAL_SESSIONS:
            raise ValueError("active session must be cancelled before removal")
        session.delete(transfer)
        return True

    @begin_session
    def delete_item(
        self,
        transfer_id: str,
        user_id: int,
        item_id: int,
        session: Session = None,  # type: ignore
    ) -> bool:
        transfer = session.scalar(
            select(DownloadTransferSession)
            .where(
                DownloadTransferSession.id == transfer_id,
                DownloadTransferSession.user_id == user_id,
            )
            .with_for_update()
        )
        if transfer is None:
            return False
        if transfer.status not in _TERMINAL_SESSIONS:
            raise ValueError("active session must be cancelled before removal")
        item = session.scalar(
            select(DownloadTransferItem)
            .where(
                DownloadTransferItem.id == item_id,
                DownloadTransferItem.session_id == transfer_id,
            )
            .with_for_update()
        )
        if item is None:
            return False
        if item.status not in _TERMINAL_ITEMS:
            raise ValueError("active item must be cancelled before removal")
        if len(transfer.items) == 1:
            session.delete(transfer)
        else:
            session.delete(item)
        return True

    @begin_session
    def delete_terminal_sessions(
        self,
        user_id: int,
        rom_id: int | None = None,
        session: Session = None,  # type: ignore
    ) -> int:
        stmt = select(DownloadTransferSession).where(
            DownloadTransferSession.user_id == user_id,
            DownloadTransferSession.status.in_(_TERMINAL_SESSIONS),
        )
        if rom_id is not None:
            stmt = stmt.where(DownloadTransferSession.rom_id == rom_id)
        transfers = session.scalars(stmt.with_for_update()).all()
        for transfer in transfers:
            session.delete(transfer)
        return len(transfers)

    @begin_session
    def cancel_session(
        self,
        transfer_id: str,
        user_id: int,
        session: Session = None,  # type: ignore
    ) -> bool:
        transfer = session.scalar(
            select(DownloadTransferSession)
            .where(
                DownloadTransferSession.id == transfer_id,
                DownloadTransferSession.user_id == user_id,
            )
            .with_for_update()
        )
        if transfer is None:
            return False
        now = datetime.now(UTC)
        transfer.status = DownloadTransferSessionStatus.CANCELLED
        for item in transfer.items:
            if item.status not in _TERMINAL_ITEMS:
                item.status = DownloadTransferItemStatus.CANCELLED
                item.ended_at = now
        self._reconcile_locked(transfer, now)
        return True

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
            if item.status not in {
                DownloadTransferItemStatus.ACTIVE,
                DownloadTransferItemStatus.HANDED_TO_BROWSER,
            }:
                raise ValueError("verified requires an active item")
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
            if item.status not in {
                DownloadTransferItemStatus.QUEUED,
                DownloadTransferItemStatus.ACTIVE,
            }:
                raise ValueError("progress requires a queued or active item")
            next_status = DownloadTransferItemStatus.ACTIVE
        elif event_type == "pause":
            if transfer.mode is DownloadTransferMode.STANDARD:
                raise ValueError("standard transfers cannot pause")
            if item.status not in {
                DownloadTransferItemStatus.ACTIVE,
                DownloadTransferItemStatus.HANDED_TO_BROWSER,
            }:
                raise ValueError("pause requires an active item")
            next_status = DownloadTransferItemStatus.PAUSED
        elif event_type == "resume":
            if (
                transfer.mode is DownloadTransferMode.STANDARD
                or item.status is not DownloadTransferItemStatus.PAUSED
            ):
                raise ValueError("resume requires enhanced paused item")
            next_status = DownloadTransferItemStatus.ACTIVE
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
        now = datetime.now(UTC)
        item.observed_bytes = observed_bytes
        item.status = next_status
        item.started_at = item.started_at or now
        item.last_activity_at = now
        if next_status in _TERMINAL_ITEMS:
            item.ended_at = now
        event = DownloadTransferEvent(
            session_id=transfer_id,
            item_id=item_id,
            ordinal=ordinal + 1,
            event_type=event_type,
            observed_bytes=observed_bytes,
            error_code=error_code,
        )
        session.add(event)
        transfer.last_activity_at = item.last_activity_at
        self._reconcile_locked(transfer, now)
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
        if transfer.mode is DownloadTransferMode.ENHANCED:
            raise ValueError("enhanced transfers require local verification")
        if item.status not in {
            DownloadTransferItemStatus.HANDED_TO_BROWSER,
            DownloadTransferItemStatus.PAUSED,
        }:
            raise ValueError("item is not ready to serve")
        item.status = DownloadTransferItemStatus.SERVED
        item.observed_bytes = item.expected_bytes
        now = datetime.now(UTC)
        item.started_at = item.started_at or now
        item.last_activity_at = now
        item.ended_at = now
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
        transfer.last_activity_at = now
        self._reconcile_locked(transfer, now)
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
        now = datetime.now(UTC)
        transfer.last_activity_at = now
        for item in transfer.items:
            if item.status not in _TERMINAL_ITEMS:
                item.status = DownloadTransferItemStatus.CANCELLED
                item.ended_at = now
        self._reconcile_locked(transfer, now)

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
        now = datetime.now(UTC)
        transfer.status = DownloadTransferSessionStatus.STALE
        transfer.last_activity_at = now
        for candidate in transfer.items:
            if candidate.status not in _TERMINAL_ITEMS:
                candidate.status = DownloadTransferItemStatus.STALE
                candidate.ended_at = now
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
        self._reconcile_locked(transfer, now)
        session.flush()
        return item
