"""Exact, reference-safe reconciliation through the existing cleanup scheduler."""

import hashlib
import itertools
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

from sqlalchemy import select

from decorators.database import begin_session
from exceptions.storage_exceptions import (
    MissingStorageTargetError,
    StorageResolutionError,
)
from handler.database import db_rom_handler
from handler.filesystem.scan_media_publication import (
    MAX_MANIFEST_BYTES,
    RESERVED,
    validate_manifest,
)
from handler.filesystem.storage_access import (
    OwnedDelete,
    OwnedDirectory,
    OwnedRead,
    open_owned_access,
)
from handler.filesystem.storage_policy import StorageOperation
from logger.logger import log
from models.owned_media_cleanup import OwnedMediaCleanupIntent, OwnedMediaCleanupState
from models.scan_operation import ScanExecutionSlot, ScanOperation


def _children(storage, relative, limit=512):
    directory = Path(storage._root_path) / relative
    try:
        if directory.is_symlink():
            raise ValueError("scan_media_recovery_symlink")
        with os.scandir(directory) as entries:
            children = list(itertools.islice(entries, limit + 1))
        if len(children) > limit:
            raise ValueError("scan_media_recovery_limit")
        return children
    except FileNotFoundError:
        return []


def _lock_attempt(session, identity):
    session.scalar(
        select(ScanExecutionSlot).where(ScanExecutionSlot.id == 1).with_for_update()
    )
    return session.scalar(
        select(ScanOperation).where(ScanOperation.id == identity).with_for_update()
    )


def _live(row, attempt):
    return (
        row is not None
        and row.attempt_id == attempt
        and row.lease_expires_at is not None
        and row.lease_expires_at.replace(tzinfo=None)
        > datetime.now(timezone.utc).replace(tzinfo=None)
        and row.state in {"running", "stopping"}
    )


def _contains(values, path, depth=0):
    if depth > 64:
        raise ValueError("scan_media_reference_limit")
    if isinstance(values, str):
        return values == path
    if isinstance(values, dict):
        return any(_contains(value, path, depth + 1) for value in values.values())
    if isinstance(values, (list, tuple)):
        return any(_contains(value, path, depth + 1) for value in values)
    return False


def _delete(storage, path):
    try:
        with open_owned_access(storage, StorageOperation.DELETE, path) as access:
            assert isinstance(access, OwnedDelete)
            access.delete()
    except MissingStorageTargetError:
        pass


def _digest_matches(storage, output):
    try:
        with open_owned_access(
            storage, StorageOperation.READ, output["final"]
        ) as access:
            assert isinstance(access, OwnedRead)
            if output["digest"] is None:
                raise ValueError("scan_media_unproven_final")
            before = os.fstat(access.fileno())
            digest = hashlib.sha256()
            total = 0
            with access.binary_file() as stream:
                while chunk := stream.read(1024 * 1024):
                    total += len(chunk)
                    digest.update(chunk)
            if digest.hexdigest() != output["digest"] or total != output["size"]:
                raise ValueError("scan_media_final_changed")
            after = os.fstat(access.fileno())
            if _identity(before) != _identity(after):
                raise ValueError("scan_media_final_changed")
            return _identity(after)
    except MissingStorageTargetError:
        return None


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def reconcile_manifest(storage, directory, *, session=None):
    receipts = _children(storage, directory)
    names = [
        entry.name
        for entry in receipts
        if re.fullmatch(r"receipt-[0-9]{4}[.]json", entry.name)
    ]
    if not names:
        return False
    with open_owned_access(
        storage, StorageOperation.READ, directory + "/" + max(names)
    ) as access:
        assert isinstance(access, OwnedRead)
        if os.fstat(access.fileno()).st_size > MAX_MANIFEST_BYTES:
            raise ValueError("scan_media_manifest_limit")
        document = validate_manifest(json.loads(access.read()), directory)
    if any(
        not re.fullmatch(r"receipt-[0-9]{4}[.]json", entry.name)
        and not re.fullmatch(
            r"[.]receipt-[0-9]{4}[.]json[.][a-f0-9]{32}[.]tmp", entry.name
        )
        for entry in receipts
    ):
        raise ValueError("scan_media_manifest_unknown_child")
    # Hashing finishes before acquiring SQL row locks.
    identities = {
        output["final"]: _digest_matches(storage, output)
        for output in document["outputs"]
    }
    return _reconcile_manifest(
        storage, directory, receipts, document, identities, session=session
    )


@begin_session
def _reconcile_manifest(
    storage, directory, receipts, document, identities, *, session=None
):
    row = _lock_attempt(session, document["operation"])
    if _live(row, document["attempt"]):
        return False
    references = db_rom_handler.locked_scan_media_references(
        document["rom"], session=session
    )
    for output in document["outputs"]:
        final = output["final"]
        if not _contains(references, final) and identities[final] is not None:
            with open_owned_access(storage, StorageOperation.READ, final) as access:
                assert isinstance(access, OwnedRead)
                if _identity(os.fstat(access.fileno())) != identities[final]:
                    raise ValueError("scan_media_final_changed")
                _delete(storage, final)
        parent = str(PurePosixPath(final).parent)
        grammar = re.compile(
            r"[.]" + re.escape(PurePosixPath(final).name) + r"[.][a-f0-9]{32}[.]tmp"
        )
        for entry in _children(storage, parent):
            if grammar.fullmatch(entry.name):
                _delete(storage, parent + "/" + entry.name)
    for entry in receipts:
        if re.fullmatch(r"receipt-[0-9]{4}[.]json", entry.name) or re.fullmatch(
            r"[.]receipt-[0-9]{4}[.]json[.][a-f0-9]{32}[.]tmp", entry.name
        ):
            _delete(storage, directory + "/" + entry.name)
        else:
            raise ValueError("scan_media_manifest_unknown_child")
    with open_owned_access(storage, StorageOperation.MKDIR, directory) as access:
        assert isinstance(access, OwnedDirectory)
        access.rmdir()
    return True


def reconcile_scan_media(storage, limit=32):
    processed = 0
    for operation in _children(storage, RESERVED):
        if not operation.is_dir(follow_symlinks=False):
            continue
        for attempt in _children(storage, RESERVED + "/" + operation.name):
            if not attempt.is_dir(follow_symlinks=False):
                continue
            parent = RESERVED + "/" + operation.name + "/" + attempt.name
            for batch in _children(storage, parent):
                if processed >= limit:
                    return processed
                if not batch.is_dir(follow_symlinks=False):
                    continue
                try:
                    reconcile_manifest(storage, parent + "/" + batch.name)
                except (
                    ValueError,
                    KeyError,
                    TypeError,
                    OSError,
                    StorageResolutionError,
                ) as error:
                    log.warning(
                        "Scan media recovery retained ambiguous receipt (%s)",
                        type(error).__name__,
                    )
                processed += 1
    return processed


@begin_session
def reconcile_cleanup_intent(storage, intent_id, *, session=None):
    session.scalar(
        select(ScanExecutionSlot).where(ScanExecutionSlot.id == 1).with_for_update()
    )
    intent = session.scalar(
        select(OwnedMediaCleanupIntent)
        .where(OwnedMediaCleanupIntent.id == intent_id)
        .with_for_update()
    )
    if intent is None or intent.state not in {
        OwnedMediaCleanupState.PENDING,
        OwnedMediaCleanupState.PROCESSING,
    }:
        return False
    references = db_rom_handler.locked_scan_media_references(
        intent.rom_id, session=session
    )
    if _contains(references, intent.owned_path):
        return False
    if intent.state == OwnedMediaCleanupState.PENDING:
        db_rom_handler.claim_owned_media_cleanup_intent(intent.id, session=session)
    try:
        _delete(storage, intent.owned_path)
    except Exception as error:
        db_rom_handler.mark_owned_media_cleanup_failed(
            intent.id,
            type(error).__name__,
            datetime.now(timezone.utc)
            + timedelta(seconds=min(60 * 2**intent.attempt_count, 3600)),
            session=session,
        )
        return False
    db_rom_handler.complete_owned_media_cleanup_intent(intent.id, session=session)
    return True
