"""Pure contracts for the trusted owned-media cleanup worker."""

from tasks.scheduled.owned_media_cleanup import retry_delay


def test_cleanup_retry_backoff_is_bounded_and_exponential() -> None:
    assert retry_delay(1) == 60
    assert retry_delay(2) == 120
    assert retry_delay(99) == 3600
