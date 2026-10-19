"""Immutable attempt media and durable, bounded filesystem recovery receipts."""

import errno
import hashlib
import json
import os
import re
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from decorators.database import begin_session
from exceptions.storage_exceptions import StorageResolutionError
from handler.database.scan_write_fence import (
    checked_scan_write,
    require_scan_write_context,
)
from handler.filesystem.resource_download import store_resource as store_resource
from handler.filesystem.storage_access import (
    OwnedCreate,
    OwnedDirectory,
    PreparedOwnedFile,
    open_owned_access,
)
from handler.filesystem.storage_policy import StorageOperation
from handler.filesystem.storage_resolver import normalize_relative_path

RESERVED = ".scan-media-staging"
MAX_OUTPUTS = 128
MAX_MANIFEST_BYTES = 128 * 1024
_GENERATED = re.compile(
    r"[A-Za-z0-9_-]+[.]scan-([a-f0-9]{32})-([a-f0-9]{32})-([0-9]{1,3})[.][a-z0-9]{1,8}"
)


def ensure_directory(storage, relative):
    path = normalize_relative_path(relative)
    parts = path.split("/")
    for end in range(1, len(parts) + 1):
        with open_owned_access(
            storage, StorageOperation.MKDIR, "/".join(parts[:end])
        ) as access:
            assert isinstance(access, OwnedDirectory)
            try:
                access.mkdir()
            except StorageResolutionError as error:
                if (
                    not isinstance(error.__cause__, OSError)
                    or error.__cause__.errno != errno.EEXIST
                ):
                    raise
        # Opening the next capability checks an existing directory without following links.


def _prior_paths(value, root, depth=0):
    if depth > 64:
        raise ValueError("scan_media_reference_limit")
    if isinstance(value, str) and value.startswith(root + "/"):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _prior_paths(child, root, depth + 1)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _prior_paths(child, root, depth + 1)


def encode_manifest(document):
    content = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    if len(content) > MAX_MANIFEST_BYTES:
        raise ValueError("scan_media_manifest_limit")
    return content


@dataclass
class PreparedScanMedia:
    path: str
    private_path: str
    capability: PreparedOwnedFile
    digest: str | None = None
    size: int | None = None

    @property
    def file(self):
        return self.capability.file

    @property
    def private_basename(self):
        return self.capability.private_basename


class ScanMediaBatch:
    def __enter__(self):
        self._binding = _ACTIVE_BATCH.set(self)
        return self

    def __exit__(self, *_args):
        _ACTIVE_BATCH.reset(self._binding)
        self.abort()

    def __init__(self, rom_id, platform_id, storage):
        self.context = require_scan_write_context()
        UUID(self.context.operation_id)
        UUID(self.context.attempt_id)
        if (
            type(rom_id) is not int
            or rom_id <= 0
            or type(platform_id) is not int
            or platform_id <= 0
        ):
            raise ValueError("scan_media_identity")
        self.storage = storage
        self.rom_id = rom_id
        self.platform_id = platform_id
        self.token = uuid4().hex
        self.root = f"roms/{platform_id}/{rom_id}"
        self.manifest_directory = f"{RESERVED}/{self.context.operation_id}/{self.context.attempt_id}/{self.token}"
        self.outputs = []
        self.sequence = 0
        self._closed = False
        self.publication_started = False
        from handler.database import db_rom_handler

        self.expected_prior = list(
            _prior_paths(db_rom_handler.locked_scan_media_references(rom_id), self.root)
        )
        ensure_directory(storage, self.manifest_directory)
        self._snapshot()

    def _snapshot(self, pending=None):
        outputs = [
            dict(final=o.path, private=o.private_path, digest=o.digest, size=o.size)
            for o in self.outputs
        ]
        if pending:
            outputs.append(pending)
        document = dict(
            schema=1,
            operation=self.context.operation_id,
            attempt=self.context.attempt_id,
            batch=self.token,
            rom=self.rom_id,
            platform=self.platform_id,
            outputs=outputs,
            expected_prior=self.expected_prior,
        )
        path = f"{self.manifest_directory}/receipt-{self.sequence:04d}.json"
        with open_owned_access(self.storage, StorageOperation.CREATE, path) as access:
            assert isinstance(access, OwnedCreate)
            access.create(encode_manifest(document))
        self.sequence += 1

    def prepare(self, original_path):
        if self._closed or len(self.outputs) >= MAX_OUTPUTS:
            raise ValueError("scan_media_batch_closed_or_full")
        path = PurePosixPath(normalize_relative_path(original_path))
        if not str(path).startswith(self.root + "/"):
            raise ValueError("scan_media_outside_rom")
        # Generated names stay in the existing family directory, including manuals.
        stem = re.sub(r"[^A-Za-z0-9_-]", "_", path.stem)[:64] or "media"
        extension = path.suffix.lower().lstrip(".")
        if not re.fullmatch(r"[a-z0-9]{1,8}", extension):
            raise ValueError("scan_media_extension")
        final = str(
            path.with_name(
                f"{stem}.scan-{UUID(self.context.attempt_id).hex}-{self.token}-{len(self.outputs)}.{extension}"
            )
        )
        self._snapshot(dict(final=final, private=None, digest=None, size=None))
        ensure_directory(self.storage, str(path.parent))
        prepared = None
        try:
            with open_owned_access(
                self.storage, StorageOperation.CREATE, final
            ) as access:
                assert isinstance(access, OwnedCreate)
                prepared = access.prepare_binary_file()
            private = str(path.parent / prepared.private_basename)
            output = PreparedScanMedia(final, private, prepared)
            self.outputs.append(output)
            self._snapshot()
            return output
        except BaseException:
            if prepared:
                prepared.abort()
            raise

    def finish(self, output):
        if output not in self.outputs or self._closed:
            raise ValueError("scan_media_output_invalid")
        output.file.flush()
        os.fsync(output.file.fileno())
        output.file.seek(0)
        digest = hashlib.sha256()
        total = 0
        while chunk := output.file.read(1024 * 1024):
            digest.update(chunk)
            total += len(chunk)
        output.digest, output.size = digest.hexdigest(), total
        self._snapshot()

    @begin_session
    def publish_and_associate(self, associate, *, session=None):
        if require_scan_write_context() != self.context or self._closed:
            raise ValueError("scan_media_batch_context")
        if any(output.digest is None for output in self.outputs):
            raise ValueError("scan_media_unfinished")
        with checked_scan_write(session):
            self.publication_started = True
            for output in self.outputs:
                output.capability.publish()
            self._closed = True
            # Unknown commit outcomes always retain receipts for authoritative recovery.
            from handler.database import db_rom_handler

            prior = list(
                _prior_paths(
                    db_rom_handler.locked_scan_media_references(
                        self.rom_id, session=session
                    ),
                    self.root,
                )
            )
            result = associate(session)
            session.flush()
            retained = set(
                _prior_paths(
                    db_rom_handler.locked_scan_media_references(
                        self.rom_id, session=session
                    ),
                    self.root,
                )
            )
            for path in set(prior) - retained:
                db_rom_handler.create_owned_media_cleanup_intent(
                    self.rom_id, 0, path, session=session
                )
            return result

    def abort(self):
        for output in self.outputs:
            output.capability.abort()
        self._closed = True


class ManifestValidationError(ValueError):
    """Untrusted evidence cannot grant recovery authority."""


def parse_manifest(content, directory):
    if len(content) > MAX_MANIFEST_BYTES:
        raise ManifestValidationError("scan_media_manifest_limit")
    depth, quoted, escaped = 0, False, False
    for char in content:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > 8:
                raise ManifestValidationError("scan_media_manifest_depth")
        elif char in (93, 125):
            depth -= 1
    try:
        return validate_manifest(json.loads(content), directory)
    except (ValueError, TypeError, RecursionError) as error:
        raise ManifestValidationError("scan_media_manifest_invalid") from error


def validate_manifest(document, directory):
    try:
        return _validate_manifest(document, directory)
    except (ValueError, KeyError, TypeError, StorageResolutionError) as error:
        raise ManifestValidationError("scan_media_manifest_invalid") from error


def _validate_manifest(document, directory):
    if (
        type(document) is not dict
        or set(document)
        != {
            "schema",
            "operation",
            "attempt",
            "batch",
            "rom",
            "platform",
            "outputs",
            "expected_prior",
        }
        or type(document["schema"]) is not int
        or document["schema"] != 1
    ):
        raise ManifestValidationError("scan_media_manifest_schema")
    operation, attempt, batch = (
        document[key] for key in ("operation", "attempt", "batch")
    )
    if any(type(value) is not str for value in (operation, attempt, batch)):
        raise ManifestValidationError("scan_media_manifest_identity")
    if (
        len(operation) != 36
        or len(attempt) != 36
        or str(UUID(operation)) != operation
        or str(UUID(attempt)) != attempt
        or not re.fullmatch(r"[a-f0-9]{32}", batch)
    ):
        raise ManifestValidationError("scan_media_manifest_identity")
    if directory != f"{RESERVED}/{operation}/{attempt}/{batch}":
        raise ManifestValidationError("scan_media_manifest_scope")
    rom, platform = document["rom"], document["platform"]
    if type(rom) is not int or rom <= 0 or type(platform) is not int or platform <= 0:
        raise ManifestValidationError("scan_media_manifest_identity")
    prior, outputs = document["expected_prior"], document["outputs"]
    if type(prior) is not list or any(type(path) is not str for path in prior):
        raise ManifestValidationError("scan_media_manifest_prior")
    if type(outputs) is not list or len(outputs) > MAX_OUTPUTS:
        raise ManifestValidationError("scan_media_manifest_limit")
    seen = set()
    for output in outputs:
        if type(output) is not dict or set(output) != {
            "final",
            "private",
            "digest",
            "size",
        }:
            raise ManifestValidationError("scan_media_manifest_output")
        final, private, digest, size = (
            output[key] for key in ("final", "private", "digest", "size")
        )
        if type(final) is not str or (private is not None and type(private) is not str):
            raise ManifestValidationError("scan_media_manifest_path")
        if (
            len(final) > 1024
            or normalize_relative_path(final) != final
            or not final.startswith(f"roms/{platform}/{rom}/")
        ):
            raise ManifestValidationError("scan_media_manifest_path")
        name = PurePosixPath(final).name
        match = _GENERATED.fullmatch(name)
        if (
            not match
            or match[1] != UUID(attempt).hex
            or match[2] != batch
            or final in seen
        ):
            raise ManifestValidationError("scan_media_manifest_generation")
        seen.add(final)
        if private is not None and (
            len(private) > 1024
            or PurePosixPath(private).parent != PurePosixPath(final).parent
            or not re.fullmatch(
                r"[.]" + re.escape(name) + r"[.][a-f0-9]{32}[.]tmp",
                PurePosixPath(private).name,
            )
        ):
            raise ManifestValidationError("scan_media_manifest_private")
        if (digest is None and size is not None) or (
            digest is not None
            and (
                type(digest) is not str
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
                or type(size) is not int
                or size < 0
            )
        ):
            raise ManifestValidationError("scan_media_manifest_digest")
    return document


_ACTIVE_BATCH: ContextVar[ScanMediaBatch | None] = ContextVar(
    "scan_media_batch", default=None
)


def require_scan_media_batch():
    require_scan_write_context()
    batch = _ACTIVE_BATCH.get()
    if batch is None:
        raise ValueError("scan_media_batch_required")
    return batch


def preserve_scan_media_references(scanned, previous):
    from copy import deepcopy

    def retain(value, old):
        if isinstance(value, dict):
            result = dict(value)
            for key in set(result) | set(old if isinstance(old, dict) else {}):
                prior = old.get(key) if isinstance(old, dict) else None
                if key.endswith("_path") or key.startswith("badge_path"):
                    result[key] = prior
                elif isinstance(result.get(key), (dict, list)):
                    result[key] = retain(result[key], prior)
            return result
        if isinstance(value, list):
            prior = {
                item.get("id"): item for item in old or [] if isinstance(item, dict)
            }
            return [
                (
                    retain(item, prior.get(item.get("id"), {}))
                    if isinstance(item, dict)
                    else item
                )
                for item in value
            ]
        return value

    scanned._pending_scan_media = {}
    for field in (
        "ss_metadata",
        "gamelist_metadata",
        "launchbox_metadata",
        "ra_metadata",
    ):
        wanted = deepcopy(getattr(scanned, field) or {})
        scanned._pending_scan_media[field] = wanted
        prior = getattr(previous, field) or {}
        held = retain(wanted, prior) if wanted else deepcopy(prior)
        if field == "ra_metadata" and prior.get("achievements"):
            held["achievements"] = deepcopy(prior["achievements"])
        setattr(scanned, field, held)
    for field in ("path_cover_s", "path_cover_l", "path_manual", "path_screenshots"):
        setattr(scanned, field, deepcopy(getattr(previous, field)))


async def publish_rom_resources(handler, rom, previous, *, complete=False):
    from handler.database import db_rom_handler
    from handler.metadata.ss_handler import add_ss_auth_to_url

    with ScanMediaBatch(rom.id, rom.platform_id, handler.storage) as unit:
        small, large = await handler.get_cover(
            rom,
            complete or rom.url_cover != previous.url_cover,
            add_ss_auth_to_url(rom.url_cover),
        )
        manual = await handler.get_manual(
            rom,
            complete or rom.url_manual != previous.url_manual,
            add_ss_auth_to_url(rom.url_manual),
        )
        screenshots = await handler.get_rom_screenshots(
            rom,
            complete or rom.url_screenshots != previous.url_screenshots,
            [add_ss_auth_to_url(url) for url in rom.url_screenshots or []],
        )
        return unit.publish_and_associate(
            lambda session: db_rom_handler.update_rom(
                rom.id,
                dict(
                    path_cover_s=small,
                    path_cover_l=large,
                    path_manual=manual,
                    path_screenshots=screenshots,
                ),
                session=session,
            )
        )
