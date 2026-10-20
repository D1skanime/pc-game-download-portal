"""Bounded durable receipt schema shared by publication and recovery."""

import hashlib
import json
import re
from pathlib import PurePosixPath
from uuid import UUID

from exceptions.storage_exceptions import StorageResolutionError
from handler.filesystem.storage_resolver import normalize_relative_path

RESERVED = ".scan-media-staging"
MAX_OUTPUTS = 128
MAX_MANIFEST_BYTES = 128 * 1024
_GENERATED = re.compile(
    r"[A-Za-z0-9_-]+[.]scan-([a-f0-9]{32})-([a-f0-9]{32})-([0-9]{1,3})[.][a-z0-9]{1,8}"
)


def encode_manifest(document):
    content = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    if len(content) > MAX_MANIFEST_BYTES:
        raise ValueError("scan_media_manifest_limit")
    return content


def prior_reference_fingerprint(paths):
    values = sorted(set(paths))
    digest = hashlib.sha256()
    for path in values:
        value = path.encode()
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return {"count": len(values), "sha256": digest.hexdigest()}


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
        or document["schema"] not in (1, 2)
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
    if document["schema"] == 1:
        if type(prior) is not list or any(type(path) is not str for path in prior):
            raise ManifestValidationError("scan_media_manifest_prior")
    elif (
        type(prior) is not dict
        or set(prior) != {"count", "sha256"}
        or type(prior["count"]) is not int
        or prior["count"] < 0
        or type(prior["sha256"]) is not str
        or not re.fullmatch(r"[a-f0-9]{64}", prior["sha256"])
    ):
        raise ManifestValidationError("scan_media_manifest_prior")
    if type(outputs) is not list or len(outputs) > MAX_OUTPUTS:
        raise ManifestValidationError("scan_media_manifest_limit")
    seen = set()
    for output in outputs:
        if type(output) is not dict or set(output) - {"ownership"} != {
            "final",
            "private",
            "digest",
            "size",
        }:
            raise ManifestValidationError("scan_media_manifest_output")
        ownership = output.get("ownership")
        if ownership is not None:
            if type(ownership) is not dict or set(ownership) != {
                "parent",
                "file",
                "sealed",
            }:
                raise ManifestValidationError("scan_media_manifest_ownership")
            for key, length in (("parent", 2), ("file", 2), ("sealed", 3)):
                value = ownership[key]
                if key == "sealed" and value is None:
                    continue
                if (
                    type(value) is not list
                    or len(value) != length
                    or any(
                        type(part) is not int or not 0 <= part < 2**64 for part in value
                    )
                ):
                    raise ManifestValidationError("scan_media_manifest_ownership")
            if (ownership["sealed"] is None) != (output["digest"] is None):
                raise ManifestValidationError("scan_media_manifest_ownership")
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
