"""Concurrent provider execution with truthful, bounded task-local observations."""

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar

from utils.scan_provider_observation import (
    ProviderObservation,
    bind_provider_observation,
)

_OBSERVATIONS: ContextVar[list | None] = ContextVar(
    "scan_provider_results", default=None
)


@contextmanager
def bind_provider_results():
    observations: list[ProviderObservation] = []
    token = _OBSERVATIONS.set(observations)
    try:
        yield observations
    finally:
        _OBSERVATIONS.reset(token)


def _matched(result):
    if isinstance(result, tuple):
        return any(_matched(value) for value in result)
    return isinstance(result, dict) and any(
        key.endswith("_id") and value for key, value in result.items()
    )


async def execute_provider(provider, coroutine, relative_path, *, selected=True):
    from handler.database.scan_write_fence import current_scan_write_context
    from handler.scan_metadata_result import (
        classify_provider_failure,
        record_auxiliary_warning,
        record_provider_observation,
    )
    from utils.provider_diagnostics import bind_provider_diagnostics

    context = current_scan_write_context()
    with bind_provider_observation(
        provider,
        relative_path,
        selected=selected,
        operation_id=context.operation_id if context else None,
        attempt_id=context.attempt_id if context else None,
    ) as observation:

        def report(error):
            cause = classify_provider_failure(error)
            if cause is not None:
                observation.outcome = "failed"
                record_auxiliary_warning(provider, relative_path, cause)

        try:
            with bind_provider_diagnostics(report):
                result = await coroutine
            if observation.outcome != "failed" and observation.invoked:
                observation.outcome = "matched" if _matched(result) else "no_match"
            return result
        except Exception as error:
            cause = classify_provider_failure(error)
            observation.outcome = "failed" if cause else "no_match"
            raise
        finally:
            observations = _OBSERVATIONS.get()
            if observations is not None:
                observations.append(observation)
                del observations[:-512]
            record_provider_observation(provider, relative_path, observation)


async def gather_provider_results(
    providers, fetches, relative_path, selected, *, rom=None, files=None
):
    from handler.scan_metadata_result import record_provider_result

    results = await asyncio.gather(
        *(
            execute_provider(
                provider, coroutine, relative_path, selected=provider in selected
            )
            for provider, (coroutine, _) in zip(providers, fetches, strict=True)
        ),
        return_exceptions=True
    )
    resolved = []
    for provider, (_, fallback), result in zip(
        providers, fetches, results, strict=True
    ):
        if isinstance(result, BaseException):
            if not isinstance(result, Exception):
                raise result
            record_provider_result(
                provider, relative_path, error=result, rom=rom, files=files
            )
            resolved.append(fallback)
        else:
            if provider in selected:
                record_provider_result(provider, relative_path, rom=rom, files=files)
            resolved.append(result)
    return resolved
