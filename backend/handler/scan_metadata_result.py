"""Narrow provider-failure classification and durable game/provider diagnostics."""

import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from json import JSONDecodeError
from typing import Any
from xml.etree.ElementTree import (  # nosec B405 - exception type only; no XML parsing
    ParseError,
)

import aiohttp
from fastapi import HTTPException
from httpx import DecodingError, HTTPStatusError, TimeoutException, TransportError
from pydantic import ValidationError

from handler.database.scan_write_fence import current_scan_write_context
from handler.scan_operation_checkpoint import current_checkpoint_command
from utils.provider_diagnostics import MalformedProviderResponse, ProviderUnavailable

_RESULTS: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "scan_metadata_results", default=None
)


@contextmanager
def bind_metadata_results():
    results: list[dict[str, Any]] = []
    token = _RESULTS.set(results)
    try:
        yield results
    finally:
        _RESULTS.reset(token)


def classify_provider_failure(error):
    if isinstance(error, ProviderUnavailable):
        return "metadata_provider_unavailable"
    if isinstance(error, MalformedProviderResponse):
        return "malformed_provider_response"
    if isinstance(error, (TimeoutException, TimeoutError)):
        return "metadata_timeout"
    if isinstance(error, HTTPException):
        if error.status_code == 404:
            return None
        if error.__cause__ is not None:
            return classify_provider_failure(error.__cause__)
        if error.status_code == 429:
            return "metadata_rate_limited"
        if error.status_code >= 500:
            return "metadata_provider_unavailable"
        raise error
    if isinstance(error, (aiohttp.ContentTypeError, aiohttp.ClientPayloadError)):
        return "malformed_provider_response"
    if isinstance(error, aiohttp.ClientResponseError):
        if error.status == 404:
            return None
        if error.status in {429, 430, 431}:
            return "metadata_rate_limited"
        if error.status >= 500 or error.status == 423:
            return "metadata_provider_unavailable"
        raise error
    if isinstance(error, aiohttp.ClientConnectionError):
        return "metadata_provider_unavailable"
    if isinstance(error, HTTPStatusError):
        if error.response.status_code == 404:
            return None
        if error.response.status_code == 429:
            return "metadata_rate_limited"
        if error.response.status_code >= 500:
            return "metadata_provider_unavailable"
        raise error
    if isinstance(error, TransportError):
        return "metadata_provider_unavailable"
    if isinstance(
        error,
        (
            DecodingError,
            ValidationError,
            JSONDecodeError,
            UnicodeDecodeError,
            ParseError,
        ),
    ):
        return "malformed_provider_response"
    raise error


def record_provider_result(
    provider, relative_path, *, error=None, rom=None, files=None
):
    context = current_scan_write_context()
    command = current_checkpoint_command()
    results = _RESULTS.get()
    cause = classify_provider_failure(error) if error is not None else None
    if cause is None and results is not None:
        cause = next(
            (
                item["cause_code"]
                for item in results
                if item.get("auxiliary_path") == relative_path
                and item.get("provider") == str(provider)
                and command is not None
                and item.get("mapping_id") == command.mapping_id
                and item.get("expected_revision") == command.expected_revision
            ),
            None,
        )
    if context is None or command is None or results is None:
        return
    from handler.database.scan_operations_handler import DBScanOperationsHandler

    scope = dict(command.options).get("relative_path", "")
    path = "/".join(part for part in (scope, relative_path) if part)
    item = {
        "target_key": "game-"
        + hashlib.sha256(f"{command.mapping_id}:{path}".encode()).hexdigest(),
        "mapping_id": command.mapping_id,
        "expected_revision": command.expected_revision,
        "relative_path": path,
        "provider": str(provider),
        "outcome": "warning" if cause else "completed",
        "cause_code": cause,
    }
    repository = DBScanOperationsHandler()
    from handler.scan_operation_checkpoint import game_file_evidence

    evidence = game_file_evidence(command, rom, files) if rom is not None else {}
    repository.record_worker_item(
        context,
        item,
        checkpoint={"rom_id": rom.id} if rom is not None else {},
        source_evidence=evidence,
    )
    results.append(item)
    del results[:-512]


def record_auxiliary_warning(provider, relative_path, cause):
    if cause is None:
        return
    results = _RESULTS.get()
    command = current_checkpoint_command()
    mapping_id = command.mapping_id if command else None
    revision = command.expected_revision if command else None
    if results is not None:
        if any(
            item.get("auxiliary_path") == relative_path
            and item.get("provider") == str(provider)
            and item.get("mapping_id") == mapping_id
            and item.get("expected_revision") == revision
            and item.get("cause_code") == cause
            for item in results
        ):
            return
        results.append(
            {
                "auxiliary_path": relative_path,
                "provider": str(provider),
                "mapping_id": mapping_id,
                "expected_revision": revision,
                "outcome": "warning",
                "cause_code": cause,
            }
        )
        del results[:-512]


async def observe_provider_fetch(provider, coroutine, relative_path):
    if _RESULTS.get() is None:
        return await coroutine
    from utils.provider_diagnostics import bind_provider_diagnostics

    def report(error):
        cause = classify_provider_failure(error)
        if cause is not None:
            record_auxiliary_warning(provider, relative_path, cause)

    with bind_provider_diagnostics(report):
        return await coroutine


async def resolve_provider_fetch(provider, coroutine, relative_path, fallback):
    try:
        return await observe_provider_fetch(provider, coroutine, relative_path)
    except Exception as error:
        cause = classify_provider_failure(error)
        if cause is not None:
            record_auxiliary_warning(provider, relative_path, cause)
        return fallback
