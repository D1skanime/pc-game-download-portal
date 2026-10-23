"""Immutable attempt media and durable, bounded filesystem recovery receipts."""

import errno
import re
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import PurePosixPath
from types import SimpleNamespace
from uuid import UUID, uuid4

from decorators.database import begin_session
from exceptions.storage_exceptions import StorageResolutionError
from handler.database.scan_write_fence import (
    checked_scan_write,
    require_scan_write_context,
)
from handler.filesystem.owned_content_proof import (
    OwnedContentProofRejected,
    content_proof_scope,
)
from handler.filesystem.owned_writer_domain import owned_writer_domain
from handler.filesystem.resource_download import store_resource as store_resource
from handler.filesystem.scan_media_manifest import (
    MAX_MANIFEST_BYTES as MAX_MANIFEST_BYTES,
)
from handler.filesystem.scan_media_manifest import MAX_OUTPUTS as MAX_OUTPUTS
from handler.filesystem.scan_media_manifest import RESERVED as RESERVED
from handler.filesystem.scan_media_manifest import (
    ManifestValidationError as ManifestValidationError,
)
from handler.filesystem.scan_media_manifest import (
    encode_manifest,
)
from handler.filesystem.scan_media_manifest import parse_manifest as parse_manifest
from handler.filesystem.scan_media_manifest import (
    prior_reference_fingerprint,
)
from handler.filesystem.scan_media_manifest import (
    validate_manifest as validate_manifest,
)
from handler.filesystem.storage_access import (
    OwnedCreate,
    OwnedDirectory,
    PreparedOwnedFile,
    open_owned_access,
)
from handler.filesystem.storage_policy import StorageOperation
from handler.filesystem.storage_resolver import normalize_relative_path


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

        self.expected_prior = prior_reference_fingerprint(
            _prior_paths(db_rom_handler.locked_scan_media_references(rom_id), self.root)
        )
        ensure_directory(storage, self.manifest_directory)
        self._snapshot()

    def _document(self, pending=None, *, reserve=False):
        outputs = [
            dict(
                final=o.path,
                private=o.private_path,
                digest=o.digest,
                size=o.size,
                ownership=o.capability.ownership,
            )
            for o in self.outputs
        ]
        if pending:
            outputs.append(pending)
        if reserve:
            for output in outputs:
                output.update(
                    digest="0" * 64,
                    size=2**63 - 1,
                    ownership=dict(
                        parent=[2**64 - 1] * 2,
                        file=[2**64 - 1] * 2,
                        sealed=[2**64 - 1] * 3,
                    ),
                )
        return dict(
            schema=2,
            operation=self.context.operation_id,
            attempt=self.context.attempt_id,
            batch=self.token,
            rom=self.rom_id,
            platform=self.platform_id,
            outputs=outputs,
            expected_prior=self.expected_prior,
        )

    def _snapshot(self, pending=None):
        document = self._document(pending)
        path = f"{self.manifest_directory}/receipt-{self.sequence:04d}.json"
        with open_owned_access(self.storage, StorageOperation.CREATE, path) as access:
            assert isinstance(access, OwnedCreate)
            access.create(encode_manifest(document))
        self.sequence += 1

    def _output_path(self, original_path):
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
        return final

    def can_prepare(self, original_path):
        if self._closed or len(self.outputs) >= MAX_OUTPUTS:
            return False
        final = self._output_path(original_path)
        path = PurePosixPath(final)
        private = str(path.parent / f".{path.name}.{'0' * 32}.tmp")
        if len(final) > 1024 or len(private) > 1024:
            raise ValueError("scan_media_manifest_path")
        pending = dict(
            final=final, private=private, digest=None, size=None, ownership=None
        )
        try:
            encode_manifest(self._document(pending, reserve=True))
        except ValueError:
            return False
        return True

    def prepare(self, original_path):
        if not self.can_prepare(original_path):
            raise ValueError("scan_media_batch_closed_or_full")
        final = self._output_path(original_path)
        path = PurePosixPath(final)
        self._snapshot(
            dict(final=final, private=None, digest=None, size=None, ownership=None)
        )
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
        output.digest, output.size = output.capability.seal()
        self._snapshot()

    def publish_and_associate(self, associate, *, session=None, before_publish=None):
        units = self._publication_units()
        expected_bytes = sum(
            (output.size or 0) * 2 for unit in units for output in unit.outputs
        )
        try:
            with content_proof_scope(
                expected_bytes=expected_bytes,
                expected_records=sum(len(unit.outputs) * 2 for unit in units),
            ), owned_writer_domain():
                return _publish_media_batches(
                    units, associate, session=session, before_publish=before_publish
                )
        except OwnedContentProofRejected:
            for unit in units:
                unit._retain = True
            raise

    def _publication_units(self):
        return [self]

    def abort(self):
        if getattr(self, "_retain", False):
            self._closed = True
            return
        try:
            expected_bytes = sum(output.size or 0 for output in self.outputs)
            with content_proof_scope(
                expected_bytes=expected_bytes, expected_records=len(self.outputs)
            ), owned_writer_domain():
                for output in self.outputs:
                    output.capability.abort()
        except StorageResolutionError:
            pass
        self._closed = True


@begin_session
def _publish_media_batches(units, associate, *, session=None, before_publish=None):
    context = require_scan_write_context()
    if not units or any(unit.context != context or unit._closed for unit in units):
        raise ValueError("scan_media_batch_context")
    if any(output.digest is None for unit in units for output in unit.outputs):
        raise ValueError("scan_media_unfinished")
    from handler.database import db_rom_handler

    first = units[0]
    with checked_scan_write(session):
        prior = set(
            _prior_paths(
                db_rom_handler.locked_scan_media_references(
                    first.rom_id, session=session
                ),
                first.root,
            )
        )

        def final_authority_check():
            with checked_scan_write(session):
                pass

        if before_publish is not None:
            before_publish(session)
        for unit in units:
            unit.publication_started = True
        for unit in units:
            for output in unit.outputs:
                output.capability.publish(final_authority_check=final_authority_check)
            unit._closed = True
        result = associate(session)
        session.flush()
        retained = set(
            _prior_paths(
                db_rom_handler.locked_scan_media_references(
                    first.rom_id, session=session
                ),
                first.root,
            )
        )
        for path in prior - retained:
            db_rom_handler.create_owned_media_cleanup_intent(
                first.rom_id, 0, path, session=session
            )
        return result


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


@begin_session
def preserve_current_scan_media(scanned, *, session=None):
    from handler.database import db_rom_handler

    snapshot = db_rom_handler.locked_scan_media_references(
        scanned.id, snapshot=True, session=session
    )
    current = SimpleNamespace(**snapshot) if snapshot is not None else None
    if current is None:
        raise ValueError("scan_media_catalog_missing")
    pending = getattr(scanned, "_pending_scan_media", None)
    preserve_scan_media_references(scanned, current)
    if pending is not None:
        scanned._pending_scan_media = pending
    return scanned


@begin_session
def merge_scan_rom(scanned, *, session=None):
    from handler.database import db_rom_handler

    preserve_current_scan_media(scanned, session=session)
    return db_rom_handler.add_rom(scanned, session=session)


async def publish_rom_resources(handler, rom, previous, *, complete=False):
    from handler.database import db_rom_handler
    from handler.database.provider_media_suppression import candidate_key
    from handler.metadata.rom_media import discover_provider_media
    from handler.metadata.ss_handler import add_ss_auth_to_url

    source = {
        "url_artworks": [rom.url_cover] if rom.url_cover else [],
        "url_screenshots": rom.url_screenshots or [],
    }
    # Legacy providers can include local paths; only HTTPS identities are comparable.
    candidates = []
    for key, values in source.items():
        for url in values:
            try:
                candidates.extend(discover_provider_media("provider", {key: [url]}))
            except ValueError:
                continue
    suppressed = db_rom_handler.get_provider_media_suppressions(rom.id, candidates)
    skipped = {
        (item.url, item.role)
        for item in candidates
        if candidate_key(item) in suppressed
    }
    from handler.metadata.rom_media import normalize_provider_url

    def allowed(url, role):
        try:
            return (normalize_provider_url(url), role) not in skipped
        except ValueError:
            return True

    from models.rom import RomOwnedMediaRole

    cover_allowed = not rom.url_cover or allowed(
        rom.url_cover, RomOwnedMediaRole.ARTWORK
    )
    screenshot_urls = [
        url
        for url in rom.url_screenshots or []
        if allowed(url, RomOwnedMediaRole.SCREENSHOT)
    ]
    attempted = [item for item in candidates if candidate_key(item) not in suppressed]
    with ScanMediaBatch(rom.id, rom.platform_id, handler.storage) as unit:
        small, large = (
            await handler.get_cover(
                rom,
                complete or rom.url_cover != previous.url_cover,
                add_ss_auth_to_url(rom.url_cover),
            )
            if cover_allowed
            else ("", "")
        )
        manual = await handler.get_manual(
            rom,
            complete or rom.url_manual != previous.url_manual,
            add_ss_auth_to_url(rom.url_manual),
        )
        screenshots = (
            await handler.get_rom_screenshots(
                rom,
                complete
                or bool(skipped)
                or rom.url_screenshots != previous.url_screenshots,
                [add_ss_auth_to_url(url) for url in screenshot_urls],
            )
            if screenshot_urls
            else ([] if rom.url_screenshots else rom.path_screenshots or [])
        )

        def check_suppression(session):
            # Keep deletion authoritative under the existing parent lock and fence,
            # before staged files become visible or references can be associated.
            if db_rom_handler.get_provider_media_suppressions(
                rom.id, attempted, session=session
            ):
                raise ValueError("Provider media suppressed during publication")

        def associate(session):
            check_suppression(session)
            return db_rom_handler.update_rom(
                rom.id,
                dict(
                    path_cover_s=small,
                    path_cover_l=large,
                    path_manual=manual,
                    path_screenshots=screenshots,
                ),
                session=session,
            )

        return unit.publish_and_associate(associate, before_publish=check_suppression)
