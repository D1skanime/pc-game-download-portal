"""Exact, reference-safe reconciliation through the existing cleanup scheduler."""

import errno
import itertools
import os
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from decorators.database import begin_session
from exceptions.storage_exceptions import (
    MissingStorageTargetError,
    StorageResolutionError,
)
from handler.database import db_rom_handler
from handler.filesystem.owned_content_proof import (
    content_proof_scope,
    verify_owned_content,
)
from handler.filesystem.owned_publication import _private_metadata
from handler.filesystem.owned_writer_domain import owned_writer_domain
from handler.filesystem.scan_media_publication import (
    MAX_MANIFEST_BYTES,
    parse_manifest,
)
from handler.filesystem.scan_media_traversal import RecoveryWalk, open_directory
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
    try:
        descriptor = open_directory(storage, relative)
    except MissingStorageTargetError:
        return []
    try:
        with os.scandir(descriptor) as entries:
            children = list(itertools.islice(entries, limit + 1))
        if len(children) > limit:
            raise ValueError("scan_media_recovery_receipt_limit")
        return children
    finally:
        os.close(descriptor)


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


def _verify_output_content(storage, output):
    try:
        with open_owned_access(
            storage, StorageOperation.READ, output["final"]
        ) as access:
            assert isinstance(access, OwnedRead)
            if output["digest"] is None:
                raise ValueError("scan_media_unproven_final")
            before = os.fstat(access.fileno())
            ownership = output.get("ownership")
            if ownership is not None:
                if list((before.st_dev, before.st_ino)) != ownership["file"]:
                    raise ValueError("scan_media_final_changed")
                with open_owned_access(
                    storage, StorageOperation.DELETE, output["final"]
                ) as parent:
                    assert isinstance(parent, OwnedDelete)
                    if (
                        list(
                            (
                                os.fstat(parent._require_parent()).st_dev,
                                os.fstat(parent._require_parent()).st_ino,
                            )
                        )
                        != ownership["parent"]
                    ):
                        raise ValueError("scan_media_parent_changed")
            verify_owned_content(
                access.fileno(), output["digest"], output["size"], _identity(before)
            )
            if _identity(before) != _identity(os.fstat(access.fileno())):
                raise ValueError("scan_media_final_changed")
            return _identity(before)
    except MissingStorageTargetError:
        return None


def _digest_matches(storage, output):
    return _verify_output_content(storage, output)


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _private_identity(storage, output, *, delete=False, expected=None):
    path = output["private"]
    try:
        with open_owned_access(storage, StorageOperation.DELETE, path) as access:
            assert isinstance(access, OwnedDelete)
            ownership = output.get("ownership")
            if ownership is not None:
                info = _private_metadata(
                    access._require_parent(), access._name, ownership
                )
            else:
                if not delete:
                    return _digest_matches(storage, {**output, "final": path})
                info = os.stat(
                    access._name, dir_fd=access._require_parent(), follow_symlinks=False
                )
            identity = _identity(info)
            if output["digest"] is not None:
                actual = _verify_output_content(storage, {**output, "final": path})
                if actual != identity:
                    raise ValueError("scan_media_private_changed")
            elif ownership is None or ownership["sealed"] is not None:
                raise ValueError("scan_media_unproven_private")
            if delete:
                if identity != expected:
                    raise ValueError("scan_media_private_changed")
                access.delete()
            return identity
    except (FileNotFoundError, MissingStorageTargetError):
        return None


def _prepare_manifest(storage, directory, *, session=None):
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
        with access.binary_file() as stream:
            document = parse_manifest(stream.read(MAX_MANIFEST_BYTES + 1), directory)
    if any(output["private"] is None for output in document["outputs"]):
        raise ValueError("scan_media_unrecorded_private")
    if any(
        not re.fullmatch(r"receipt-[0-9]{4}[.]json", entry.name)
        and not re.fullmatch(
            r"[.]receipt-[0-9]{4}[.]json[.][a-f0-9]{32}[.]tmp", entry.name
        )
        for entry in receipts
    ):
        raise ValueError("scan_media_manifest_unknown_child")
    with content_proof_scope(
        expected_bytes=sum((output["size"] or 0) * 4 for output in document["outputs"]),
        expected_records=len(document["outputs"]) * 4,
        operation=document["operation"],
        attempt=document["attempt"],
    ):
        return _prepare_reconciliation(
            storage, directory, receipts, document, session=session
        )


def reconcile_manifest(storage, directory, *, session=None):
    return _prepare_manifest(storage, directory, session=session)


def _prepare_reconciliation(storage, directory, receipts, document, *, session=None):
    # Initial proof is outside SQL. Final proof shares the writer domain with mutation.
    identities = {
        output["final"]: _digest_matches(storage, output)
        for output in document["outputs"]
    }
    private_identities = {
        output["private"]: _private_identity(storage, output)
        for output in document["outputs"]
    }
    with owned_writer_domain():
        return _reconcile_manifest(
            storage,
            directory,
            receipts,
            document,
            identities,
            private_identities,
            session=session,
        )


@begin_session
def _reconcile_manifest(
    storage,
    directory,
    receipts,
    document,
    identities,
    private_identities,
    *,
    session=None,
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
                if _verify_output_content(storage, output) != identities[final]:
                    raise ValueError("scan_media_final_changed")
                _delete(storage, final)
        _private_identity(
            storage, output, delete=True, expected=private_identities[output["private"]]
        )
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


@begin_session
def _prune_ancestor(storage, directory, *, session=None):
    parts = directory.split("/")
    if len(parts) not in {2, 3}:
        return
    row = _lock_attempt(session, parts[1])
    if row is not None and _live(row, row.attempt_id):
        return
    try:
        with open_owned_access(storage, StorageOperation.MKDIR, directory) as access:
            assert isinstance(access, OwnedDirectory)
            access.rmdir()
    except StorageResolutionError as error:
        if not isinstance(error.__cause__, OSError) or error.__cause__.errno not in {
            errno.ENOENT,
            errno.ENOTEMPTY,
            errno.EEXIST,
        }:
            raise


def reconcile_scan_media(storage, limit=32):
    if type(limit) is not int or not 1 <= limit <= 32:
        raise ValueError("scan_media_recovery_budget")
    processed = 0
    with RecoveryWalk(storage) as walk:
        for _ in range(512):
            kind, path = walk.step()
            if kind == "done":
                break
            try:
                if kind == "exit":
                    _prune_ancestor(storage, path)
                elif kind == "batch":
                    reconcile_manifest(storage, path)
                    processed += 1
            except (ValueError, OSError, StorageResolutionError) as error:
                log.warning(
                    "Scan media recovery retained ambiguous receipt (%s)",
                    type(error).__name__,
                )
                if kind == "batch":
                    processed += 1
            if processed >= limit:
                break
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
