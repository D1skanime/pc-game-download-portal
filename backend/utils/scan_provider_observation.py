"""Optional task-local observations, never an authority to perform scan writes."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime


@dataclass
class ProviderObservation:
    provider: str
    game: str
    operation_id: str | None = None
    attempt_id: str | None = None
    selected: bool = True
    eligible: bool = False
    invoked: bool = False
    cached: bool = False
    requests: int = 0
    invoked_at: datetime | None = None
    request_at: datetime | None = None
    retry_after_seconds: float | None = None
    outcome: str = "not_invoked"


_CURRENT: ContextVar[ProviderObservation | None] = ContextVar(
    "scan_provider_observation", default=None
)


def current_provider_observation():
    return _CURRENT.get()


@contextmanager
def bind_provider_observation(
    provider, game, *, operation_id=None, attempt_id=None, selected=True
):
    observation = ProviderObservation(
        str(provider), game, operation_id, attempt_id, selected
    )
    token = _CURRENT.set(observation)
    try:
        yield observation
    finally:
        _CURRENT.reset(token)


def mark_provider_invoked(enabled=True):
    observation = _CURRENT.get()
    if observation is not None and enabled:
        observation.eligible = True
        observation.invoked = True
        if observation.invoked_at is None:
            observation.invoked_at = datetime.now(UTC)


def mark_provider_cached():
    observation = _CURRENT.get()
    if observation is not None:
        observation.cached = True


def _dispatch():
    observation = _CURRENT.get()
    if observation is not None:
        observation.requests += 1
        observation.request_at = datetime.now(UTC)


async def observe_aiohttp_headers(session, context, params):
    _dispatch()


async def observe_aiohttp_response(session, context, params):
    observe_retry_after(params.response.headers.get("Retry-After"))


def observe_httpcore_trace_sync(event, info):
    if event in {
        "http11.send_request_headers.started",
        "http2.send_request_headers.started",
    }:
        _dispatch()


async def observe_httpcore_trace(event, info):
    observe_httpcore_trace_sync(event, info)


def observe_retry_after(value):
    observation = _CURRENT.get()
    if observation is None or not isinstance(value, str) or len(value) > 128:
        return
    try:
        if value.isascii() and value.isdecimal():
            seconds = float(value)
        else:
            timestamp = parsedate_to_datetime(value)
            if timestamp.tzinfo is None:
                return
            seconds = (timestamp - datetime.now(UTC)).total_seconds()
    except (ValueError, TypeError, OverflowError):
        return
    if 0 <= seconds <= 604800:
        observation.retry_after_seconds = max(
            observation.retry_after_seconds or 0, seconds
        )


def install_httpx_trace(request):
    prior = request.extensions.get("trace")
    if prior is not None and request.extensions.get("scan_provider_trace") is prior:
        return

    def trace(event, info):
        observe_httpcore_trace_sync(event, info)
        if prior is not None:
            prior(event, info)

    request.extensions["scan_provider_trace"] = trace
    request.extensions["trace"] = trace


async def install_httpx_trace_async(request):
    prior = request.extensions.get("trace")
    if prior is not None and request.extensions.get("scan_provider_trace") is prior:
        return

    async def trace(event, info):
        await observe_httpcore_trace(event, info)
        if prior is not None:
            await prior(event, info)

    request.extensions["scan_provider_trace"] = trace
    request.extensions["trace"] = trace


def observe_httpx_response(response):
    observe_retry_after(response.headers.get("Retry-After"))


async def observe_httpx_response_async(response):
    observe_httpx_response(response)
