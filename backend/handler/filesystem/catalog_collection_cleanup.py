"""Durable exact-file cleanup for explicitly promoted collection parents."""

import errno
import hashlib
import itertools
import json
import os
import re
import stat
from io import BufferedReader
from typing import cast

from sqlalchemy import select

from decorators.database import begin_session
from exceptions.storage_exceptions import (
    MissingStorageTargetError,
    StorageResolutionError,
)
from handler.database import db_rom_handler
from handler.database.catalog_lifecycle_handler import CatalogLifecycleHandler
from handler.filesystem import storage_composition
from handler.filesystem.owned_content_proof import content_proof_scope
from handler.filesystem.owned_writer_domain import owned_writer_domain
from handler.filesystem.scan_media_recovery import (
    _contains,
    _identity,
    _verify_output_content,
)
from handler.filesystem.storage_access import (
    OwnedDelete,
    OwnedDirectory,
    OwnedRead,
    _open_root,
    _open_target,
    open_owned_access,
)
from handler.filesystem.storage_policy import OwnedStorageKind, StorageOperation
from handler.filesystem.storage_resolver import normalize_relative_path
from models.base import utc_now
from models.catalog_lifecycle import (
    OwnedCleanupIntent,
    OwnedCleanupState,
    RetainedCatalogIdentity,
)
from models.rom import Rom
from models.scan_operation import ScanExecutionSlot

MAX_OUTPUTS = 512
MAX_DIRECTORIES = 256
MAX_BYTES = 512 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
BATCH_SIZE = 16


def _storage(storage=None):
    storage = (
        storage
        if storage is not None
        else storage_composition.owned[OwnedStorageKind.RESOURCES]
    )
    if storage.kind != OwnedStorageKind.RESOURCES:
        raise ValueError("collection_cleanup_owned_resources_only")
    return storage


def _root_identity(storage):
    descriptor = _open_root(storage)
    try:
        info = os.fstat(descriptor)
        return [info.st_dev, info.st_ino]
    finally:
        os.close(descriptor)


def _snapshot_file(storage, path):
    with open_owned_access(storage, StorageOperation.READ, path) as access:
        assert isinstance(access, OwnedRead)
        before = os.fstat(access.fileno())
        if before.st_size > MAX_BYTES or not stat.S_ISREG(before.st_mode):
            raise ValueError("collection_cleanup_file_budget")
        with access.binary_file() as stream:
            digest = hashlib.file_digest(
                cast(BufferedReader, stream), "sha256"
            ).hexdigest()
        if _identity(before) != _identity(os.fstat(access.fileno())):
            raise ValueError("collection_cleanup_changed_during_prepare")
        with open_owned_access(storage, StorageOperation.DELETE, path) as target:
            assert isinstance(target, OwnedDelete)
            parent = os.fstat(target._require_parent())
        return dict(
            final=path,
            digest=digest,
            size=before.st_size,
            ownership=dict(
                file=[before.st_dev, before.st_ino],
                parent=[parent.st_dev, parent.st_ino],
            ),
            identity=list(_identity(before)),
        )


def prepare_collection_cleanup(parent, *, storage=None):
    storage = _storage(storage)
    root = normalize_relative_path(parent.fs_resources_path)
    if root != f"roms/{parent.platform_id}/{parent.id}":
        raise ValueError("collection_cleanup_parent_scope")
    document = dict(
        schema=1,
        parent_rom_id=parent.id,
        parent_incarnation=parent.incarnation_token,
        root_identity=_root_identity(storage),
        outputs=[],
        directories=[],
        retained=[],
    )
    paths = [root]
    total_bytes = 0
    with owned_writer_domain():
        while paths:
            path = paths.pop()
            try:
                descriptor = _open_target(storage, path, directory=True)
            except MissingStorageTargetError:
                continue
            try:
                info = os.fstat(descriptor)
                document["directories"].append(
                    dict(path=path, identity=[info.st_dev, info.st_ino])
                )
                if (
                    len(document["directories"]) > MAX_DIRECTORIES
                    or len(path.split("/")) > 32
                ):
                    raise ValueError("collection_cleanup_directory_budget")
                with os.scandir(descriptor) as iterator:
                    entries = list(
                        itertools.islice(iterator, MAX_OUTPUTS + MAX_DIRECTORIES + 1)
                    )
                if len(entries) > MAX_OUTPUTS + MAX_DIRECTORIES:
                    raise ValueError("collection_cleanup_entry_budget")
                for entry in sorted(entries, key=lambda item: item.name):
                    child = normalize_relative_path(path + "/" + entry.name)
                    metadata = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(metadata.st_mode):
                        paths.append(child)
                    elif stat.S_ISREG(metadata.st_mode):
                        output = _snapshot_file(storage, child)
                        total_bytes += output["size"]
                        document["outputs"].append(output)
                        if (
                            len(document["outputs"]) > MAX_OUTPUTS
                            or total_bytes > MAX_BYTES
                        ):
                            raise ValueError("collection_cleanup_manifest_budget")
                    else:
                        document["retained"].append(
                            dict(path=child, reason="unproven_entry")
                        )
            finally:
                os.close(descriptor)
    for path in [
        parent.path_cover_s,
        parent.path_cover_l,
        parent.path_manual,
        *(parent.path_screenshots or []),
    ]:
        if path and not path.startswith(root + "/"):
            document["retained"].append(
                dict(path=path, reason="outside_parent_owned_scope")
            )
    if len(json.dumps(document).encode()) > MAX_MANIFEST_BYTES:
        raise ValueError("collection_cleanup_manifest_budget")
    return document


def _manifest(document, retained):
    if not isinstance(document, dict) or document.get("schema") != 1:
        raise ValueError("collection_cleanup_manifest_schema")
    root = f"roms/{retained.platform_id}/{retained.detached_rom_id}"
    if document.get("parent_rom_id") != retained.detached_rom_id or not re.fullmatch(
        r"[a-f0-9]{32}", document.get("parent_incarnation", "")
    ):
        raise ValueError("collection_cleanup_parent_identity")
    outputs = document.get("outputs")
    directories = document.get("directories")
    if (
        not isinstance(outputs, list)
        or len(outputs) > MAX_OUTPUTS
        or not isinstance(directories, list)
        or len(directories) > MAX_DIRECTORIES
    ):
        raise ValueError("collection_cleanup_manifest_budget")
    if len(json.dumps(document).encode()) > MAX_MANIFEST_BYTES:
        raise ValueError("collection_cleanup_manifest_budget")
    for output in outputs:
        final = normalize_relative_path(output["final"])
        if (
            not final.startswith(root + "/")
            or not re.fullmatch(r"[a-f0-9]{64}", output["digest"])
            or type(output["size"]) is not int
            or not 0 <= output["size"] <= MAX_BYTES
        ):
            raise ValueError("collection_cleanup_output_scope")
        if (
            any(type(value) is not int or value < 0 for value in output["identity"])
            or len(output["identity"]) != 5
        ):
            raise ValueError("collection_cleanup_output_identity")
        if any(
            len(output["ownership"][key]) != 2
            or any(
                type(value) is not int or value < 0
                for value in output["ownership"][key]
            )
            for key in ("file", "parent")
        ):
            raise ValueError("collection_cleanup_ownership")
    for directory in directories:
        path = normalize_relative_path(directory["path"])
        if path != root and not path.startswith(root + "/"):
            raise ValueError("collection_cleanup_directory_scope")
        if len(directory["identity"]) != 2 or any(
            type(value) is not int or value < 0 for value in directory["identity"]
        ):
            raise ValueError("collection_cleanup_directory_identity")
    return document


def _delete_output(storage, output):
    try:
        with open_owned_access(
            storage, StorageOperation.READ, output["final"]
        ) as access:
            assert isinstance(access, OwnedRead)
            if _identity(os.fstat(access.fileno())) != tuple(output["identity"]):
                raise ValueError("collection_cleanup_file_replaced")
    except MissingStorageTargetError:
        return
    actual = _verify_output_content(storage, output)
    if actual is None:
        return
    if actual != tuple(output["identity"]):
        raise ValueError("collection_cleanup_file_replaced")
    with open_owned_access(storage, StorageOperation.DELETE, output["final"]) as access:
        assert isinstance(access, OwnedDelete)
        current = os.stat(
            access._name, dir_fd=access._require_parent(), follow_symlinks=False
        )
        parent = os.fstat(access._require_parent())
        if (
            _identity(current) != actual
            or [parent.st_dev, parent.st_ino] != output["ownership"]["parent"]
        ):
            raise ValueError("collection_cleanup_file_replaced")
        access.delete()


def _prune(storage, directories, retained):
    for directory in sorted(
        directories, key=lambda item: item["path"].count("/"), reverse=True
    ):
        try:
            descriptor = _open_target(storage, directory["path"], directory=True)
            try:
                info = os.fstat(descriptor)
                if [info.st_dev, info.st_ino] != directory["identity"]:
                    retained.append(
                        dict(path=directory["path"], reason="directory_replaced")
                    )
                    continue
                with open_owned_access(
                    storage, StorageOperation.MKDIR, directory["path"]
                ) as access:
                    assert isinstance(access, OwnedDirectory)
                    current = os.stat(
                        access._name,
                        dir_fd=access._require_parent(),
                        follow_symlinks=False,
                    )
                    if [current.st_dev, current.st_ino] != directory["identity"]:
                        retained.append(
                            dict(path=directory["path"], reason="directory_replaced")
                        )
                        continue
                    access.rmdir()
            finally:
                os.close(descriptor)
        except MissingStorageTargetError:
            pass
        except StorageResolutionError as error:
            if not isinstance(
                error.__cause__, OSError
            ) or error.__cause__.errno not in {errno.ENOTEMPTY, errno.EEXIST}:
                raise


@begin_session
def process_collection_cleanup_intent(intent_id, expected_version, *, session=None):
    session.scalar(
        select(ScanExecutionSlot).where(ScanExecutionSlot.id == 1).with_for_update()
    )
    row = session.scalar(
        select(OwnedCleanupIntent)
        .where(OwnedCleanupIntent.id == intent_id)
        .with_for_update()
    )
    if row is None:
        return False
    if row.exact_manifest is None:
        return None
    if row.state != OwnedCleanupState.PROCESSING or row.version != expected_version:
        return False
    retained = session.get(RetainedCatalogIdentity, row.retained_catalog_id)
    if retained is None:
        raise ValueError("collection_cleanup_retained_identity_missing")
    document = _manifest(row.exact_manifest, retained)
    storage = _storage()
    if _root_identity(storage) != document["root_identity"]:
        raise ValueError("collection_cleanup_root_replaced")
    progress = row.exact_progress or {"cursor": 0, "retained": []}
    cursor = progress.get("cursor", 0)
    if type(cursor) is not int or not 0 <= cursor <= len(document["outputs"]):
        raise ValueError("collection_cleanup_progress")
    kept = list(progress.get("retained", []))
    for entry in document.get("retained", []):
        if entry not in kept:
            kept.append(entry)
    parent = session.scalar(
        select(Rom.id).where(Rom.id == document["parent_rom_id"]).with_for_update()
    )
    outputs = document["outputs"][cursor : cursor + BATCH_SIZE]
    with content_proof_scope(
        expected_bytes=sum(item["size"] * 2 for item in outputs),
        expected_records=len(outputs) * 2,
    ):
        for output in outputs:
            references = db_rom_handler.locked_scan_media_references(
                None, session=session
            )
            if parent is not None or _contains(references, output["final"]):
                kept.append(
                    dict(
                        path=output["final"],
                        reason=(
                            "live_reference"
                            if parent is None
                            else "parent_identity_live"
                        ),
                    )
                )
            else:
                try:
                    _delete_output(storage, output)
                except ValueError:
                    kept.append(
                        dict(path=output["final"], reason="file_replaced_or_unproven")
                    )
            cursor += 1
    row.exact_progress = dict(cursor=cursor, retained=kept)
    row.version += 1
    if cursor == len(document["outputs"]):
        if parent is None:
            _prune(storage, document["directories"], kept)
        row.exact_progress = dict(cursor=cursor, retained=kept)
        row.state = OwnedCleanupState.COMPLETED
        row.completed_at = utc_now()
        row.next_attempt_at = None
        row.safe_error = None
        session.flush()
        return True
    row.state = OwnedCleanupState.PENDING
    row.next_attempt_at = utc_now()
    session.flush()
    return False


def process_pending_collection_cleanup(*, limit=8):
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("collection_cleanup_limit")
    lifecycle = CatalogLifecycleHandler()
    results = dict(completed=0, failed=0)
    for intent in lifecycle.claim_cleanup_intents(limit=limit, collection_only=True):
        try:
            outcome = process_collection_cleanup_intent(intent.id, intent.version)
        except (OSError, ValueError, StorageResolutionError, KeyError, TypeError):
            lifecycle.fail_cleanup_intent(intent.id, expected_version=intent.version)
            results["failed"] += 1
        else:
            results["completed"] += int(outcome is True)
    return results
