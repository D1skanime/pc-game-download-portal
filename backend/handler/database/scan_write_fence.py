"""Attempt identity and SQL transaction checks shared by scan consumers."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import event, select

_CONTEXT: ContextVar["ScanWriteContext | None"] = ContextVar(
    "scan_write_context", default=None
)
_SESSION_KEY = "scan_write_context"
_LISTENER_KEY = "scan_write_listeners"


class ScanWriteRejected(RuntimeError):
    """The durable attempt no longer authorizes a catalog or media write."""


@dataclass(frozen=True, slots=True)
class ScanWriteContext:
    operation_id: str
    attempt_id: str
    lease_owner: str


def current_scan_write_context() -> ScanWriteContext | None:
    return _CONTEXT.get()


def require_scan_write_context() -> ScanWriteContext:
    context = current_scan_write_context()
    if context is None:
        raise ScanWriteRejected("scan_context_required")
    return context


@contextmanager
def bind_scan_write_context(context: ScanWriteContext):
    if not isinstance(context, ScanWriteContext):
        raise ScanWriteRejected("scan_context_invalid")
    previous = current_scan_write_context()
    if previous is not None and previous != context:
        raise ScanWriteRejected("scan_context_conflict")
    token = _CONTEXT.set(context)
    try:
        yield context
    finally:
        _CONTEXT.reset(token)


def _check(session, context, expected_version=None):
    # Lazy model imports keep decorators independent of repository initialization.
    from models.scan_operation import ScanExecutionSlot, ScanOperation

    with session.no_autoflush:
        active = session.scalar(
            select(ScanExecutionSlot.active_operation_id)
            .where(ScanExecutionSlot.id == 1)
            .with_for_update()
        )
        row = session.execute(
            select(
                ScanOperation.id,
                ScanOperation.attempt_id,
                ScanOperation.lease_owner,
                ScanOperation.lease_expires_at,
                ScanOperation.state,
                ScanOperation.intentional_cancel,
                ScanOperation.version,
            )
            .where(ScanOperation.id == context.operation_id)
            .with_for_update()
        ).one_or_none()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if (
            active != context.operation_id
            or row is None
            or row.attempt_id != context.attempt_id
            or row.lease_owner != context.lease_owner
            or row.state != "running"
            or row.intentional_cancel
            or row.lease_expires_at is None
            or row.lease_expires_at.replace(tzinfo=None) <= now
            or (expected_version is not None and row.version != expected_version)
        ):
            raise ScanWriteRejected("scan_attempt_revoked")
        return session.get(ScanOperation, context.operation_id, populate_existing=True)


def _before_commit(session):
    context = session.info.get(_SESSION_KEY)
    if context is not None:
        _check(session, context)


def _before_flush(session, flush_context, instances):
    _before_commit(session)


def _transaction_ended(session, transaction):
    if transaction.parent is None:
        session.info.pop(_SESSION_KEY, None)


def _enlist(session, context):
    previous = session.info.get(_SESSION_KEY)
    if previous is not None and previous != context:
        raise ScanWriteRejected("scan_transaction_context_conflict")
    session.info[_SESSION_KEY] = context
    if not session.info.get(_LISTENER_KEY):
        event.listen(session, "before_commit", _before_commit)
        event.listen(session, "before_flush", _before_flush)
        event.listen(session, "after_transaction_end", _transaction_ended)
        session.info[_LISTENER_KEY] = True


@contextmanager
def checked_scan_write(session, *, expected_version=None):
    context = require_scan_write_context()
    _enlist(session, context)
    row = _check(session, context, expected_version)
    yield row


@contextmanager
def fence_bound_session(session):
    context = current_scan_write_context()
    if context is None:
        # An enlisted explicit session retains its identity after binding exit.
        _before_commit(session)
        yield
    else:
        with checked_scan_write(session):
            yield
