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
                item.get("cause_code")
                for item in results
                if item.get("cause_code") is not None
                and item.get("auxiliary_path") == relative_path
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

    scope = dict(command.options).get("relative_path", "").rpartition("/")[0]
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
    observations = next(
        (
            entry["observation"]
            for entry in reversed(results)
            if entry.get("auxiliary_path") == relative_path
            and entry.get("provider") == str(provider)
            and entry.get("mapping_id") == command.mapping_id
            and entry.get("expected_revision") == command.expected_revision
            and "observation" in entry
        ),
        None,
    )
    checkpoint = {"rom_id": rom.id} if rom is not None else {}
    if observations is not None:
        checkpoint["provider_observation"] = observations
    repository.record_worker_item(
        context,
        item,
        checkpoint=checkpoint,
        source_evidence=evidence,
    )
    results.append(item)
    del results[:-512]


def record_provider_observation(provider, relative_path, observation):
    results = _RESULTS.get()
    command = current_checkpoint_command()
    if results is None or command is None:
        return
    key = {
        "auxiliary_path": relative_path,
        "provider": str(provider),
        "mapping_id": command.mapping_id,
        "expected_revision": command.expected_revision,
    }
    previous = next(
        (
            item
            for item in results
            if all(item.get(k) == v for k, v in key.items()) and "observation" in item
        ),
        None,
    )
    payload = {
        name: getattr(observation, name)
        for name in (
            "selected",
            "eligible",
            "invoked",
            "cached",
            "requests",
            "outcome",
            "retry_after_seconds",
        )
    }
    for name in ("invoked_at", "request_at"):
        value = getattr(observation, name)
        payload[name] = value.isoformat() if value else None
    if previous is not None:
        old = previous["observation"]
        payload["requests"] += old["requests"]
        for name in ("selected", "eligible", "invoked", "cached"):
            payload[name] = payload[name] or old[name]
        if payload["outcome"] == "not_invoked" or old["outcome"] == "failed":
            payload["outcome"] = old["outcome"]
        payload["invoked_at"] = old["invoked_at"] or payload["invoked_at"]
        payload["request_at"] = payload["request_at"] or old["request_at"]
        durations = [
            value
            for value in (payload["retry_after_seconds"], old["retry_after_seconds"])
            if value is not None
        ]
        payload["retry_after_seconds"] = max(durations) if durations else None
        previous["observation"] = payload
    else:
        results.append(key | {"observation": payload, "outcome": "completed"})
        del results[:-512]


def record_auxiliary_warning(provider, relative_path, cause):
    if cause is None:
        return
    from utils.scan_provider_observation import current_provider_observation

    observation = current_provider_observation()
    if (
        observation is not None
        and observation.provider == str(provider)
        and observation.game == relative_path
    ):
        observation.outcome = "failed"
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


async def observe_provider_fetch(provider, coroutine, relative_path, *, selected=True):
    from handler.scan_provider_execution import execute_provider

    return await execute_provider(provider, coroutine, relative_path, selected=selected)


async def resolve_provider_fetch(
    provider, coroutine, relative_path, fallback, *, selected=True
):
    try:
        return await observe_provider_fetch(
            provider, coroutine, relative_path, selected=selected
        )
    except Exception as error:
        cause = classify_provider_failure(error)
        if cause is not None:
            record_auxiliary_warning(provider, relative_path, cause)
        return fallback
