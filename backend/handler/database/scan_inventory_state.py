"""Transactional advisory state bound to current mapping, ROM and scan attempt."""

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from types import SimpleNamespace

from sqlalchemy import event, select

from decorators.database import begin_session
from handler.database.scan_write_fence import ScanWriteRejected, checked_scan_write
from handler.filesystem.storage_resolver import normalize_relative_path
from handler.scan_collection_policy import digest_path, mapping_binding
from handler.scan_inventory_contracts import InventoryEvidence
from models.rom import Rom
from models.scan_inventory import ScanInventoryBaseline, ScanMetadataRetry
from models.storage import PlatformStorageMapping, StorageRoot

_DIGEST = re.compile(r"[0-9a-f]{64}")
_BINDINGS = "scan_inventory_bindings"
_LISTENERS = "scan_inventory_listeners"


def _fingerprint(value):
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError("invalid_inventory_fingerprint")
    return value


def _digest(values):
    return digest_path(json.dumps(values, sort_keys=True, separators=(",", ":")))


@dataclass(frozen=True, slots=True)
class InventoryBinding:
    mapping_id: int
    storage_root_id: int
    mapping_relative_path: str
    mapping_revision: int
    game_relative_path: str
    rom_id: int
    rom_incarnation: str
    policy_fingerprint: str
    inventory_version: int = 1
    classifier_version: int = 1

    def __post_init__(self):
        for path in (self.mapping_relative_path, self.game_relative_path):
            normalize_relative_path(path)
            if len(path) > 700:
                raise ValueError("inventory_path_too_long")
        _fingerprint(self.policy_fingerprint)
        if not re.fullmatch(r"[0-9a-f]{32}", self.rom_incarnation):
            raise ValueError("invalid_inventory_incarnation")
        for value in (
            self.mapping_id,
            self.storage_root_id,
            self.mapping_revision,
            self.rom_id,
            self.inventory_version,
            self.classifier_version,
        ):
            if type(value) is not int or value < 1:
                raise ValueError("invalid_inventory_identity")

    @classmethod
    def from_mapping(
        cls, mapping, rom, game_relative_path, policy_fingerprint, **versions
    ):
        return cls(
            mapping.id,
            mapping.storage_root_id,
            mapping.relative_path,
            mapping.version,
            game_relative_path,
            rom.id,
            rom.incarnation_token,
            policy_fingerprint,
            **versions
        )

    def fields(self):
        return dict(
            asdict(self),
            binding_digest=mapping_binding(
                SimpleNamespace(
                    storage_root_id=self.storage_root_id,
                    relative_path=self.mapping_relative_path,
                )
            ),
            path_digest=digest_path(self.game_relative_path),
        )


def _matches(mapping, root, rom, binding):
    if (
        not mapping.active
        or not root.active
        or root.mode != "external_read_only"
        or mapping.version != binding.mapping_revision
        or mapping.storage_root_id != binding.storage_root_id
        or mapping.relative_path != binding.mapping_relative_path
        or rom.incarnation_token != binding.rom_incarnation
        or rom.platform_id != mapping.platform_id
    ):
        return False
    try:
        actual = (
            (PurePosixPath(rom.fs_path) / rom.fs_name)
            .relative_to(PurePosixPath(mapping.relative_path))
            .as_posix()
        )
    except ValueError:
        return False
    return actual == binding.game_relative_path


def _current(session, binding, *, lock=False):
    with session.no_autoflush:
        rows = []
        for model, identity, names in (
            (
                PlatformStorageMapping,
                binding.mapping_id,
                (
                    "active",
                    "version",
                    "storage_root_id",
                    "relative_path",
                    "platform_id",
                ),
            ),
            (StorageRoot, binding.storage_root_id, ("active", "mode")),
            (
                Rom,
                binding.rom_id,
                ("incarnation_token", "platform_id", "fs_path", "fs_name"),
            ),
        ):
            query = select(*(getattr(model, name) for name in names)).where(
                model.id == identity
            )
            if lock:
                query = query.with_for_update(of=model)
            row = session.execute(query).one_or_none()
            if row is None:
                return False
            rows.append(row)
        if not _matches(rows[0], rows[1], rows[2], binding):
            return False
        # Pending ORM edits must pass the same check before their first flush.
        objects = [
            session.get(model, identity)
            for model, identity in (
                (PlatformStorageMapping, binding.mapping_id),
                (StorageRoot, binding.storage_root_id),
                (Rom, binding.rom_id),
            )
        ]
        return _matches(objects[0], objects[1], objects[2], binding)


def _check_bindings(session, *args):
    for binding in session.info.get(_BINDINGS, ()):
        if not _current(session, binding, lock=True):
            raise ScanWriteRejected("inventory_binding_changed")


def _end_bindings(session, transaction):
    if transaction.parent is None:
        session.info.pop(_BINDINGS, None)


def _enlist(session, binding, operation):
    if not _current(session, binding, lock=True):
        raise ScanWriteRejected("inventory_binding_changed")
    targets = operation.command.get("commands", [])
    matches = [
        target
        for target in targets
        if target.get("mapping_id") == binding.mapping_id
        and target.get("expected_revision") == binding.mapping_revision
    ]
    if not any(
        dict(target.get("options", [])).get("relative_path")
        in (None, binding.game_relative_path)
        for target in matches
    ):
        raise ScanWriteRejected("inventory_command_mismatch")
    session.info.setdefault(_BINDINGS, set()).add(binding)
    if not session.info.get(_LISTENERS):
        event.listen(session, "before_flush", _check_bindings)
        event.listen(session, "before_commit", _check_bindings)
        event.listen(session, "after_transaction_end", _end_bindings)
        session.info[_LISTENERS] = True


def _find(session, model, fields):
    row = session.scalar(select(model).where(model.identity_digest == _digest(fields)))
    if row is not None and any(
        getattr(row, key) != value for key, value in fields.items()
    ):
        raise ValueError("inventory_identity_collision")
    return row


def _valid_evidence(evidence, binding):
    return (
        isinstance(evidence, InventoryEvidence)
        and evidence.complete
        and evidence.schema_version == binding.inventory_version == 1
        and evidence.classifier_version == binding.classifier_version == 1
        and _DIGEST.fullmatch(evidence.digest) is not None
        and type(evidence.entry_count) is int
        and 1 <= evidence.entry_count <= 20000
    )


@begin_session
def load_baseline(binding, current_inventory, *, session=None):
    """Return compact committed advice only after a fresh complete inventory."""
    if not _valid_evidence(current_inventory, binding) or not _current(
        session, binding
    ):
        return None
    row = _find(session, ScanInventoryBaseline, binding.fields())
    if row is None or not row.reusable:
        return None
    return InventoryEvidence(
        row.inventory_digest,
        row.entry_count,
        True,
        schema_version=row.inventory_version,
        classifier_version=row.classifier_version,
    )


@begin_session
def save_completed_baseline(
    binding, before, after, *, components_reconciled, files_reconciled, session=None
):
    with checked_scan_write(session) as operation:
        _enlist(session, binding, operation)
        fields = binding.fields()
        row = _find(session, ScanInventoryBaseline, fields)
        valid = (
            components_reconciled is True
            and files_reconciled is True
            and _valid_evidence(before, binding)
            and _valid_evidence(after, binding)
            and before.digest == after.digest
            and before.entry_count == after.entry_count
        )
        if not valid:
            if row is not None:
                row.reusable = False
            session.flush()
            return False
        if row is None:
            row = ScanInventoryBaseline(**fields, identity_digest=_digest(fields))
            session.add(row)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        row.inventory_digest, row.entry_count = after.digest, after.entry_count
        row.validated_at, row.completed_at, row.reusable = now, now, True
        session.flush()
        return True


def _retry_fields(binding, provider, query, locale, config_fingerprint):
    if (
        not isinstance(provider, str)
        or re.fullmatch(r"[a-z0-9_-]{1,32}", provider) is None
    ):
        raise ValueError("invalid_inventory_provider")
    normalized = " ".join(query.split()).casefold()
    locale = locale.replace("_", "-").lower()
    if (
        not normalized
        or len(normalized) > 700
        or not locale
        or len(locale) > 32
        or any(ord(char) < 32 or ord(char) == 127 for char in normalized + locale)
    ):
        raise ValueError("invalid_inventory_query")
    return dict(
        binding.fields(),
        provider=provider,
        normalized_query=normalized,
        locale=locale,
        config_fingerprint=_fingerprint(config_fingerprint),
    )


@begin_session
def load_retry_states(binding, *, session=None):
    if not _current(session, binding):
        return []
    fields = binding.fields()
    rows = list(
        session.scalars(
            select(ScanMetadataRetry)
            .where(
                *(
                    getattr(ScanMetadataRetry, key) == value
                    for key, value in fields.items()
                )
            )
            .order_by(ScanMetadataRetry.id)
            .limit(101)
        )
    )
    if len(rows) > 100:
        raise ValueError("inventory_retry_state_limit")
    for row in rows:
        raw = _retry_fields(
            binding,
            row.provider,
            row.normalized_query,
            row.locale,
            row.config_fingerprint,
        )
        if row.identity_digest != _digest(raw):
            raise ValueError("inventory_retry_identity_collision")
    return rows


@begin_session
def record_retry_outcome(
    binding,
    *,
    provider,
    query,
    locale,
    config_fingerprint,
    outcome,
    next_eligible_at,
    invoked_at=None,
    request_at=None,
    no_match_streak=0,
    transient_streak=0,
    config_blocked=False,
    session=None
):
    fields = _retry_fields(binding, provider, query, locale, config_fingerprint)
    if outcome not in {
        "matched",
        "no_match",
        "transient",
        "configuration_blocked",
        "cache_hit",
        "not_invoked",
        "unknown",
    }:
        raise ValueError("invalid_inventory_retry_outcome")
    if any(
        type(value) is not int or not 0 <= value <= 2147483647
        for value in (no_match_streak, transient_streak)
    ):
        raise ValueError("invalid_inventory_retry_streak")
    if request_at is not None and invoked_at is None:
        raise ValueError("inventory_request_without_invocation")
    with checked_scan_write(session) as operation:
        _enlist(session, binding, operation)
        row = _find(session, ScanMetadataRetry, fields)
        if row is None:
            row = ScanMetadataRetry(**fields, identity_digest=_digest(fields))
            session.add(row)
        row.outcome, row.next_eligible_at = outcome, next_eligible_at
        if invoked_at is not None:
            row.last_invoked_at = invoked_at
        if request_at is not None:
            row.last_request_at = request_at
        row.no_match_streak, row.transient_streak = no_match_streak, transient_streak
        row.config_blocked = config_blocked
        session.flush()
        return row
