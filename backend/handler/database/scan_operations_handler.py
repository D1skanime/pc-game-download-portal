"""One SQL transaction owns acceptance, dispatch intent and the execution fence."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pydantic import TypeAdapter
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from decorators.database import begin_session
from endpoints.responses.scan_operations import (
    RequestKey,
    ScanOperationItemResult,
)
from handler.database.base_handler import DBBaseHandler
from handler.database.scan_operation_lifecycle import ScanOperationLifecycle
from handler.filesystem.storage_resolver import normalize_relative_path
from handler.metadata.metadata_locale import (
    capture_metadata_locale,
    ensure_metadata_locale,
)
from handler.scan_command import MappedScanCommand, ScanScope, ScanTrigger
from handler.scan_operation_projection import operation_snapshot
from handler.scan_operation_state import TERMINAL
from handler.scan_operation_state import validate_transition as _validate_transition
from models.scan_operation import ScanExecutionSlot, ScanOperation, ScanOperationItem

_UNSET = object()


class OperationConflict(ValueError):
    pass


class OperationNotFound(LookupError):
    pass


def validate_transition(*args, **kwargs):
    try:
        _validate_transition(*args, **kwargs)
    except ValueError as error:
        raise OperationConflict(str(error)) from None


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def payload_digest(payload):
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()


def _alive(expiry):
    return expiry is not None and expiry.replace(tzinfo=None) > utc_now()


def _slot(session):
    return session.scalars(
        select(ScanExecutionSlot).where(ScanExecutionSlot.id == 1).with_for_update()
    ).one()


def _row(session, identity, *, actor=None, admin=False):
    row = session.scalar(
        select(ScanOperation).where(ScanOperation.id == identity).with_for_update()
    )
    if row is None or (actor is not None and row.actor_id != actor and not admin):
        raise OperationNotFound("operation_not_found")
    return row


def _cas(session, row, version, attempt=_UNSET, **changes):
    if row.version != version or (attempt is not _UNSET and row.attempt_id != attempt):
        raise OperationConflict("stale_operation")
    statement = update(ScanOperation).where(
        ScanOperation.id == row.id, ScanOperation.version == version
    )
    if attempt is not _UNSET:
        statement = statement.where(ScanOperation.attempt_id == attempt)
    result = session.execute(
        statement.values(
            **changes, version=version + 1, updated_at=utc_now()
        ).execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise OperationConflict("stale_operation")
    session.refresh(row)


def _release(slot, row):
    if slot.active_operation_id == row.id and row.state in TERMINAL:
        slot.active_operation_id = None
        slot.version += 1


class DBScanOperationsHandler(ScanOperationLifecycle, DBBaseHandler):
    @begin_session
    def replay(self, actor, request_key, digest, *, session: Session = None):  # type: ignore
        _slot(session)
        row = session.scalar(
            select(ScanOperation)
            .where(
                ScanOperation.actor_id == actor,
                ScanOperation.request_key == request_key,
            )
            .with_for_update()
        )
        if row is None:
            return None
        if row.payload_digest != digest:
            raise OperationConflict("request_payload_conflict")
        return operation_snapshot(session, row)

    @begin_session
    def accept(self, actor, request_key, normalized_commands, digest=None, *, session: Session = None):  # type: ignore
        TypeAdapter(RequestKey).validate_python(request_key)
        calculated = payload_digest(
            normalized_commands.get("request", normalized_commands)
        )
        if digest is not None and digest != calculated:
            raise ValueError("invalid_payload_digest")
        slot = _slot(session)
        existing = self.replay(actor, request_key, calculated, session=session)
        if existing is not None:
            return existing
        if slot.active_operation_id is not None:
            raise OperationConflict("scan_already_active")
        commands = normalized_commands.get("commands", [])
        if not commands or len(commands) > 256:
            raise ValueError("missing_scan_scope")
        for data in commands:
            command = MappedScanCommand(
                **(
                    data
                    | {
                        "trigger": ScanTrigger(data["trigger"]),
                        "scope": ScanScope(data["scope"]),
                        "options": tuple(tuple(v) for v in data.get("options", [])),
                    }
                )
            )
            for key, value in command.options:
                if key == "relative_path":
                    normalize_relative_path(value)
        identity = str(uuid4())
        row = ScanOperation(
            id=identity,
            actor_id=actor,
            request_key=request_key,
            payload_digest=calculated,
            command=capture_metadata_locale(normalized_commands),
            rq_job_id="scan-" + identity,
            dispatch_due=utc_now(),
        )
        session.add(row)
        session.flush()
        slot.active_operation_id = row.id
        slot.version += 1
        return operation_snapshot(session, row)

    @begin_session
    def get_by_request_key(self, actor, request_key, *, session: Session = None):  # type: ignore
        row = session.scalar(
            select(ScanOperation).where(
                ScanOperation.actor_id == actor,
                ScanOperation.request_key == request_key,
            )
        )
        if row is None:
            raise OperationNotFound("operation_not_found")
        return operation_snapshot(session, row)

    @begin_session
    def get_by_id(self, identity, actor, *, admin=False, offset=0, limit=100, session: Session = None):  # type: ignore
        row = session.get(ScanOperation, identity)
        if row is None or (row.actor_id != actor and not admin):
            raise OperationNotFound("operation_not_found")
        return operation_snapshot(session, row, offset=offset, limit=limit)

    @begin_session
    def find_active(self, actor, *, admin=False, session: Session = None):  # type: ignore
        row = session.scalar(
            select(ScanOperation).join(
                ScanExecutionSlot,
                ScanExecutionSlot.active_operation_id == ScanOperation.id,
            )
        )
        return (
            operation_snapshot(session, row)
            if row is not None and (admin or row.actor_id == actor)
            else None
        )

    @begin_session
    def claim_dispatch(self, identity, version, owner, *, seconds=30, session: Session = None):  # type: ignore
        _slot(session)
        row = _row(session, identity)
        if (
            row.state not in {"accepted", "recovering"}
            or row.dispatch_due is None
            or row.dispatch_due > utc_now()
            or _alive(row.dispatch_claim_until)
        ):
            raise OperationConflict("dispatch_not_claimable")
        if not owner or len(owner) > 64 or not 1 <= seconds <= 300:
            raise ValueError("invalid_dispatch_claim")
        _cas(
            session,
            row,
            version,
            dispatch_owner=owner,
            dispatch_claim_until=utc_now() + timedelta(seconds=seconds),
        )
        return operation_snapshot(session, row)

    @begin_session
    def mark_enqueued(self, identity, version, owner, *, session: Session = None):  # type: ignore
        _slot(session)
        row = _row(session, identity)
        if (
            row.dispatch_owner != owner
            or not _alive(row.dispatch_claim_until)
            or row.state not in {"accepted", "recovering"}
        ):
            raise OperationConflict("stale_dispatch")
        _cas(
            session,
            row,
            version,
            state="queued",
            cause_code=None,
            next_action=None,
            dispatch_due=None,
            dispatch_owner=None,
            dispatch_claim_until=None,
        )
        return operation_snapshot(session, row)

    @begin_session
    def claim_attempt(self, identity, version, owner, *, seconds=60, session: Session = None):  # type: ignore
        slot = _slot(session)
        row = _row(session, identity)
        if (
            slot.active_operation_id != identity
            or (
                row.state != "queued"
                and not (
                    row.state in {"accepted", "recovering"}
                    and _alive(row.dispatch_claim_until)
                )
            )
            or _alive(row.lease_expires_at)
        ):
            raise OperationConflict("attempt_not_claimable")
        if not owner or len(owner) > 64 or not 1 <= seconds <= 300:
            raise ValueError("invalid_lease")
        _cas(
            session,
            row,
            version,
            state="running",
            command=ensure_metadata_locale(row.command),
            attempt_id=row.attempt_id or str(uuid4()),
            lease_owner=owner,
            lease_expires_at=utc_now() + timedelta(seconds=seconds),
            dispatch_due=None,
            dispatch_owner=None,
            dispatch_claim_until=None,
            cause_code=None,
            next_action=None,
            checkpoint={
                key: value
                for key, value in row.checkpoint.items()
                if key
                not in {
                    "previous_rq_job_id",
                    "previous_never_started",
                    "stopped_job_id",
                }
            },
        )
        return operation_snapshot(session, row)

    @begin_session
    def renew_lease(self, identity, version, attempt_id, owner, *, seconds=60, session: Session = None):  # type: ignore
        _slot(session)
        row = _row(session, identity)
        if (
            row.state != "running"
            or row.lease_owner != owner
            or not _alive(row.lease_expires_at)
            or not 1 <= seconds <= 300
        ):
            raise OperationConflict("stale_lease")
        _cas(
            session,
            row,
            version,
            attempt_id,
            lease_expires_at=utc_now() + timedelta(seconds=seconds),
        )
        return operation_snapshot(session, row)

    @begin_session
    def transition(self, identity, version, attempt_id, state, *, scan_stats=None, cause_code=None, next_action=None, session: Session = None):  # type: ignore
        slot = _slot(session)
        row = _row(session, identity)
        if (
            row.state == "running"
            and not _alive(row.lease_expires_at)
            and state not in {"interrupted", "blocked", "failed", "stopping"}
        ):
            raise OperationConflict("stale_lease")
        validate_transition(
            row.state, state, lease=_alive(row.lease_expires_at), confirmed_stop=False
        )
        changes = dict(state=state, cause_code=cause_code, next_action=next_action)
        if scan_stats is not None:
            changes["scan_stats"] = scan_stats
        if state in TERMINAL or state in {"blocked", "interrupted"}:
            changes.update(
                lease_owner=None,
                lease_expires_at=None,
                dispatch_due=None,
                dispatch_owner=None,
                dispatch_claim_until=None,
            )
        _cas(session, row, version, attempt_id, **changes)
        _release(slot, row)
        return operation_snapshot(session, row)

    @begin_session
    def record_item(self, identity, version, attempt_id, item, *, checkpoint=None, source_evidence=None, _advance_version=True, session: Session = None):  # type: ignore
        _slot(session)
        row = _row(session, identity)
        if row.state != "running" or not _alive(row.lease_expires_at):
            raise OperationConflict("stale_attempt")
        from handler.scan_inventory_status import provider_facts

        provider_facts((checkpoint or {}).get("provider_observation"))
        validated = ScanOperationItemResult(id=1, attempt_id=attempt_id, **item)
        path = normalize_relative_path(validated.relative_path)
        matches = [
            c
            for c in row.command["commands"]
            if c["mapping_id"] == validated.mapping_id
            and c["expected_revision"] == validated.expected_revision
        ]
        if not matches or not any(
            not dict(c.get("options", [])).get("relative_path")
            or path == dict(c["options"])["relative_path"]
            or path.startswith(dict(c["options"])["relative_path"] + "/")
            for c in matches
        ):
            raise OperationConflict("item_outside_scan_scope")
        providers = row.command.get("policies", row.command.get("request", {})).get(
            "apis", []
        )
        if validated.provider not in providers:
            raise OperationConflict("provider_outside_scan_scope")
        if (
            len(json.dumps(checkpoint or {})) > 8192
            or len(json.dumps(source_evidence or {})) > 8192
        ):
            raise ValueError("item_evidence_too_large")
        if _advance_version:
            _cas(session, row, version, attempt_id)
        else:
            if row.version != version or row.attempt_id != attempt_id:
                raise OperationConflict("stale_operation")
            from handler.database.scan_operation_lifecycle import observe_execution

            observe_execution(session, row, {})
        result = session.scalar(
            select(ScanOperationItem).where(
                ScanOperationItem.operation_id == identity,
                ScanOperationItem.target_key == validated.target_key,
                ScanOperationItem.provider == validated.provider,
            )
        )
        values = validated.model_dump(
            exclude={"id", "inventory", "provider_execution"}
        ) | {
            "checkpoint": checkpoint or {},
            "source_evidence": source_evidence or {},
        }
        if result is None:
            session.add(ScanOperationItem(operation_id=identity, **values))
        else:
            for key, value in values.items():
                setattr(result, key, value)
        session.flush()
        return operation_snapshot(session, row)

    @begin_session
    def request_cancel(self, identity, actor, version, request_key, *, admin=False, session: Session = None):  # type: ignore
        _slot(session)
        row = _row(session, identity, actor=actor, admin=admin)
        TypeAdapter(RequestKey).validate_python(request_key)
        key = "cancel:" + request_key
        if len(row.mutation_keys) >= 128 and key not in row.mutation_keys:
            raise OperationConflict("mutation_history_full")
        if key in row.mutation_keys or row.state == "cancelled":
            return operation_snapshot(session, row)
        validate_transition(
            row.state,
            "stopping",
            lease=_alive(row.lease_expires_at),
            confirmed_stop=False,
        )
        _cas(
            session,
            row,
            version,
            state="stopping",
            intentional_cancel=True,
            dispatch_due=None,
            mutation_keys=row.mutation_keys | {key: True},
        )
        return operation_snapshot(session, row)

    @begin_session
    def confirm_stopped(self, identity, version, attempt_id, *, session: Session = None):  # type: ignore
        slot = _slot(session)
        row = _row(session, identity)
        validate_transition(row.state, "cancelled", lease=False, confirmed_stop=True)
        _cas(
            session,
            row,
            version,
            attempt_id,
            state="cancelled",
            lease_owner=None,
            lease_expires_at=None,
            dispatch_due=None,
            dispatch_owner=None,
            dispatch_claim_until=None,
        )
        _release(slot, row)
        return operation_snapshot(session, row)

    @begin_session
    def request_resume(self, identity, actor, version, request_key, *, admin=False, item_ids=None, session: Session = None):  # type: ignore
        slot = _slot(session)
        row = _row(session, identity, actor=actor, admin=admin)
        TypeAdapter(RequestKey).validate_python(request_key)
        key, signature = "resume:" + request_key, payload_digest(sorted(item_ids or []))
        if key in row.mutation_keys:
            if row.mutation_keys[key] != signature:
                raise OperationConflict("resume_payload_conflict")
            return operation_snapshot(session, row)
        if (
            row.state
            not in {
                "cancelled",
                "interrupted",
                "blocked",
                "failed",
                "completed-with-warnings",
            }
            or _alive(row.lease_expires_at)
            or _alive(row.dispatch_claim_until)
            or slot.active_operation_id not in {None, identity}
        ):
            raise OperationConflict("execution_not_fenced")
        if len(row.mutation_keys) >= 128:
            raise OperationConflict("mutation_history_full")
        if item_ids:
            items = list(
                session.scalars(
                    select(ScanOperationItem).where(
                        ScanOperationItem.operation_id == identity,
                        ScanOperationItem.id.in_(item_ids),
                        ScanOperationItem.outcome.in_(["failed", "warning"]),
                    )
                )
            )
            if len(items) != len(set(item_ids)) or len(item_ids) > 100:
                raise OperationConflict("invalid_metadata_retry_scope")
        else:
            items = []
        validate_transition(
            row.state,
            "recovering",
            lease=False,
            confirmed_stop=True,
            explicit_resume=True,
        )
        _cas(
            session,
            row,
            version,
            state="recovering",
            attempt_id=str(uuid4()),
            rq_job_id="scan-" + identity + "-" + str(uuid4()),
            intentional_cancel=False,
            lease_owner=None,
            lease_expires_at=None,
            dispatch_due=None,
            cause_code="source_verification_required",
            next_action="verify_source",
            mutation_keys=row.mutation_keys | {key: signature},
            checkpoint=row.checkpoint
            | {
                "retry_item_ids": ",".join(str(i.id) for i in items),
                "previous_rq_job_id": row.rq_job_id,
                "previous_never_started": row.attempt_id is None,
            },
        )
        slot.active_operation_id = identity
        slot.version += 1
        return operation_snapshot(session, row)
