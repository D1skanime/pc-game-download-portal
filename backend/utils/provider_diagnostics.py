"""Optional request-local provider diagnostics without adapter/domain coupling."""

from contextlib import contextmanager
from contextvars import ContextVar


class ProviderUnavailable(RuntimeError):
    """A configured metadata source has no usable current data."""


class MalformedProviderResponse(RuntimeError):
    """A metadata source returned invalid structured content."""


_REPORTER = ContextVar("provider_diagnostic_reporter", default=None)


@contextmanager
def bind_provider_diagnostics(reporter):
    token = _REPORTER.set(reporter)
    try:
        yield
    finally:
        _REPORTER.reset(token)


def report_provider_fault(error):
    reporter = _REPORTER.get()
    if reporter is not None:
        reporter(error)
