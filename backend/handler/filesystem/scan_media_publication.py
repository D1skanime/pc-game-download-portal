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
from handler.filesystem.storage_access import OwnedCreate, open_owned_access
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
    capability: object
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


def validate_manifest(document, directory):
    if not isinstance(document, dict) or document.get("schema") != 1:
        raise ValueError("scan_media_manifest_invalid")
    operation, attempt, batch = (
        document["operation"],
        document["attempt"],
        document["batch"],
    )
    if (
        str(UUID(operation)) != operation
        or str(UUID(attempt)) != attempt
        or not re.fullmatch(r"[a-f0-9]{32}", batch)
    ):
        raise ValueError("scan_media_manifest_identity")
    if directory != f"{RESERVED}/{operation}/{attempt}/{batch}":
        raise ValueError("scan_media_manifest_scope")
    rom, platform = document["rom"], document["platform"]
    if type(rom) is not int or rom <= 0 or type(platform) is not int or platform <= 0:
        raise ValueError("scan_media_manifest_identity")
    outputs = document["outputs"]
    if not isinstance(outputs, list) or len(outputs) > MAX_OUTPUTS:
        raise ValueError("scan_media_manifest_limit")
    seen = set()
    for output in outputs:
        final = output["final"]
        if normalize_relative_path(final) != final or not final.startswith(
            f"roms/{platform}/{rom}/"
        ):
            raise ValueError("scan_media_manifest_path")
        name = PurePosixPath(final).name
        match = _GENERATED.fullmatch(name)
        if (
            not match
            or match[1] != UUID(attempt).hex
            or match[2] != batch
            or final in seen
        ):
            raise ValueError("scan_media_manifest_generation")
        seen.add(final)
        private = output["private"]
        if private is not None and (
            PurePosixPath(private).parent != PurePosixPath(final).parent
            or not re.fullmatch(
                r"[.]" + re.escape(name) + r"[.][a-f0-9]{32}[.]tmp",
                PurePosixPath(private).name,
            )
        ):
            raise ValueError("scan_media_manifest_private")
        if output["digest"] is not None and (
            not re.fullmatch(r"[a-f0-9]{64}", output["digest"])
            or type(output["size"]) is not int
            or output["size"] < 0
        ):
            raise ValueError("scan_media_manifest_digest")
    return document


_ACTIVE_BATCH = ContextVar("scan_media_batch", default=None)


def require_scan_media_batch():
    require_scan_write_context()
    batch = _ACTIVE_BATCH.get()
    if batch is None:
        raise ValueError("scan_media_batch_required")
    return batch


async def store_resource(handler, url, path, allowed, *, cover_size=None, image=False):
    """Stream provider or local bytes before the short publication transaction."""
    import httpx
    from anyio import open_file
    from PIL import Image

    from adapters.services.screenscraper import media_download_slot
    from config import ENABLE_SCHEDULED_CONVERT_IMAGES_TO_WEBP
    from handler.database.scan_write_fence import current_scan_write_context
    from handler.filesystem import resources_handler as resource_module
    from handler.filesystem.resources_handler import (
        LOCAL_FILE_SCHEMES,
        _check_content_type,
        _is_chroma_key_placeholder,
        _resolve_local_file_uri,
    )

    async def chunks():
        if url.startswith(LOCAL_FILE_SCHEMES):
            resolved = _resolve_local_file_uri(url)
            if resolved is None:
                raise ValueError("scan_media_source_invalid")
            async with await open_file(resolved, "rb") as source:
                while chunk := await source.read(1024 * 1024):
                    yield chunk
        else:
            async with media_download_slot(url) as timeout:
                async with resource_module.ctx_httpx_client.get().stream(
                    "GET", url, timeout=timeout
                ) as response:
                    if response.status_code != 200 or not _check_content_type(
                        response, allowed, "resource"
                    ):
                        raise ValueError("scan_media_response_invalid")
                    import zlib

                    decoder = (
                        zlib.decompressobj(16 + zlib.MAX_WBITS)
                        if response.headers.get("content-encoding", "").lower()
                        == "gzip"
                        else None
                    )
                    async for chunk in response.aiter_raw():
                        if decoder is None:
                            yield chunk
                        else:
                            try:
                                while chunk:
                                    decoded = decoder.decompress(chunk, 1024 * 1024)
                                    chunk = decoder.unconsumed_tail
                                    if decoded:
                                        yield decoded
                            except zlib.error:
                                decoder = None
                                yield chunk

    if current_scan_write_context() is not None:
        unit = require_scan_media_batch()
        if cover_size and ENABLE_SCHEDULED_CONVERT_IMAGES_TO_WEBP:
            path = str(PurePosixPath(path).with_suffix(".webp"))
        output = unit.prepare(path)
        try:
            async for chunk in chunks():
                output.file.write(chunk)
            output.file.flush()
            if image or cover_size:
                output.file.seek(0)
                if _is_chroma_key_placeholder(output.file):
                    raise ValueError("scan_media_chroma_key")
                output.file.seek(0)
                with Image.open(output.file) as original:
                    original.load()
                    transformed = original.copy()
                if cover_size == "small":
                    ratio = 0.2 if transformed.height >= 1000 else 0.4
                    transformed = transformed.resize(
                        (
                            max(1, int(transformed.width * ratio)),
                            max(1, int(transformed.height * ratio)),
                        )
                    )
                if cover_size:
                    transformed = handler.image_converter._convert_image_mode(
                        transformed
                    )
                    output.file.seek(0)
                    output.file.truncate()
                    transformed.save(
                        output.file, "WEBP" if path.endswith(".webp") else "PNG"
                    )
            unit.finish(output)
            return output.path
        except BaseException:
            output.capability.abort()
            raise
    directory, filename = path.rsplit("/", 1)
    await handler.make_directory(directory)
    try:
        async with await handler.write_file_streamed(
            directory, filename
        ) as destination:
            async for chunk in chunks():
                await destination.write(chunk)
        if image or cover_size:
            if await handler._discard_if_chroma_key(path):
                return None
        if cover_size == "small":
            with Image.open(handler.validate_path(path)) as original:
                handler.resize_cover_to_small(
                    original, str(handler.validate_path(path))
                )
        if cover_size and ENABLE_SCHEDULED_CONVERT_IMAGES_TO_WEBP:
            handler.image_converter.convert_to_webp(
                handler.validate_path(path), force=True
            )
        return path
    except (ValueError, OSError, httpx.TransportError):
        await handler._discard_partial_file(path)
        return None
