"""Conservative retry advice; provider dispatch and fenced writes remain external."""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any

from handler.database.scan_inventory_state import (
    InventoryBinding,
    _digest,
    _retry_fields,
)

Clock = Callable[[], datetime]


def _utc(value: datetime) -> datetime:
    return (
        value.astimezone(timezone.utc).replace(tzinfo=None)
        if value.tzinfo is not None
        else value
    )


@dataclass(frozen=True, slots=True)
class RetryIdentity:
    binding: InventoryBinding
    provider: str
    query: str
    locale: str
    config_fingerprint: str
    purpose: str = "unknown"

    def __post_init__(self):
        fields = self.fields()
        object.__setattr__(self, "query", fields["normalized_query"])
        object.__setattr__(self, "locale", fields["locale"])
        if self.purpose not in {"unknown", "description"} or (
            self.purpose == "description"
            and re.fullmatch(
                r"descriptions:v1:[1-9][0-9]*:(parent|component:[1-9][0-9]*)",
                self.query,
            )
            is None
        ):
            raise ValueError("invalid_inventory_retry_purpose")

    def fields(self) -> dict[str, Any]:
        return _retry_fields(
            self.binding,
            self.provider,
            self.query,
            self.locale,
            self.config_fingerprint,
        )

    @property
    def key(self) -> str:
        return _digest(self.fields())

    @property
    def game_key(self) -> str:
        return _digest(self.binding.fields())


@dataclass(frozen=True, slots=True)
class RetryState:
    identity: RetryIdentity
    next_eligible_at: datetime | None = None
    last_invoked_at: datetime | None = None
    last_request_at: datetime | None = None
    no_match_streak: int = 0
    transient_streak: int = 0
    outcome: str = "not_invoked"
    config_blocked: bool = False

    def __post_init__(self):
        for value in (self.no_match_streak, self.transient_streak):
            if type(value) is not int or not 0 <= value <= 2147483647:
                raise ValueError("invalid_inventory_retry_streak")

    @classmethod
    def from_record(cls, identity: RetryIdentity, row: Any) -> "RetryState":
        fields = identity.fields()
        if row.identity_digest != identity.key or any(
            getattr(row, key) != value for key, value in fields.items()
        ):
            raise ValueError("inventory_retry_identity_collision")
        return cls(
            identity,
            row.next_eligible_at,
            row.last_invoked_at,
            row.last_request_at,
            row.no_match_streak,
            row.transient_streak,
            row.outcome,
            row.config_blocked,
        )

    def persistence(self) -> dict[str, Any]:
        """Arguments for record_retry_outcome, inside the caller's checked transaction."""
        return dict(
            provider=self.identity.provider,
            query=self.identity.query,
            locale=self.identity.locale,
            config_fingerprint=self.identity.config_fingerprint,
            outcome=self.outcome,
            next_eligible_at=self.next_eligible_at,
            invoked_at=self.last_invoked_at,
            request_at=self.last_request_at,
            no_match_streak=self.no_match_streak,
            transient_streak=self.transient_streak,
            config_blocked=self.config_blocked,
        )


@dataclass(frozen=True, slots=True)
class RetryAssessment:
    eligible: bool
    reason: str
    due_at: datetime | None = None


def assess_retry(
    identity: RetryIdentity,
    state: RetryState | None,
    *,
    baseline_adopted_at: datetime | None,
    clock: Clock,
    newly_discovered: bool = False,
    configured: bool = True,
    selected: bool = True,
    identified: bool = False,
    authority_current: bool = True,
    explicit_accepted: bool = False,
) -> RetryAssessment:
    """Eligibility is not evidence that an invocation or wire request occurred."""
    now = _utc(clock())
    if not authority_current:
        return RetryAssessment(False, "stale_authority")
    if identified or not configured or not selected:
        return RetryAssessment(False, "not_selected")
    if explicit_accepted:
        return RetryAssessment(True, "explicit", now)
    if newly_discovered:
        return RetryAssessment(True, "initial", now)
    if (
        state is not None
        and state.config_blocked
        and state.identity.binding == identity.binding
        and state.identity.provider == identity.provider
        and state.identity.config_fingerprint == identity.config_fingerprint
    ):
        return RetryAssessment(False, "configuration_blocked")
    if state is not None and state.identity != identity:
        state = None
    due = state.next_eligible_at if state is not None else None
    if due is None:
        if identity.purpose == "description":
            return RetryAssessment(True, "due", now)
        if baseline_adopted_at is None:
            return RetryAssessment(False, "baseline_required")
        due = _utc(baseline_adopted_at) + timedelta(hours=24)
    due = _utc(due)
    return RetryAssessment(due <= now, "due" if due <= now else "cooldown", due)


def _delay(identity: RetryIdentity, streak: int, *, transient: bool) -> timedelta:
    hours = min(
        (1 if transient else 24) * 2 ** min(streak - 1, 8), 24 if transient else 168
    )
    # The existing digest owner binds jitter to the complete non-secret identity.
    digest = _digest([identity.key, streak, "transient" if transient else "no_match"])
    jitter = 0.9 + int(digest[:16], 16) / (2**64 - 1) * 0.2
    return timedelta(seconds=max(0, hours * 3600 * jitter))


def observe_outcome(
    identity: RetryIdentity,
    previous: RetryState | None,
    *,
    outcome: str,
    clock: Clock,
    invoked_at: datetime | None = None,
    request_at: datetime | None = None,
    retry_after: datetime | None = None,
) -> RetryState:
    """Project observed facts; a cache hit never manufactures an external attempt."""
    if outcome not in {
        "matched",
        "no_match",
        "transient",
        "configuration_blocked",
        "cache_hit",
        "not_invoked",
        "unknown",
    }:
        raise ValueError("invalid_inventory_retry_outcome")
    now = _utc(clock())
    invoked = _utc(invoked_at) if invoked_at is not None else None
    requested = _utc(request_at) if request_at is not None else None
    if (
        (requested is not None and (invoked is None or requested < invoked))
        or (invoked is not None and invoked > now)
        or (requested is not None and requested > now)
    ):
        raise ValueError("invalid_inventory_request_observation")
    if outcome == "cache_hit" and requested is not None:
        raise ValueError("cache_hit_with_external_request")
    state = (
        previous
        if previous is not None and previous.identity == identity
        else RetryState(identity)
    )
    if (
        invoked is not None
        and state.last_invoked_at is not None
        and invoked < _utc(state.last_invoked_at)
    ) or (
        requested is not None
        and state.last_request_at is not None
        and requested < _utc(state.last_request_at)
    ):
        raise ValueError("stale_inventory_request_observation")
    state = replace(
        state,
        outcome=outcome,
        last_invoked_at=invoked if invoked is not None else state.last_invoked_at,
        last_request_at=requested if requested is not None else state.last_request_at,
    )
    if outcome == "configuration_blocked":
        return replace(state, config_blocked=True)
    if outcome == "cache_hit":
        due = max(
            now + timedelta(hours=24),
            _utc(state.next_eligible_at) if state.next_eligible_at is not None else now,
        )
        return replace(state, next_eligible_at=due)
    if requested is None:
        return state
    if outcome == "matched":
        return replace(
            state, config_blocked=False, no_match_streak=0, transient_streak=0
        )
    if outcome not in {"no_match", "transient"}:
        return state
    transient = outcome == "transient"
    streak = min(
        (state.transient_streak if transient else state.no_match_streak) + 1, 2147483647
    )
    due = requested + _delay(identity, streak, transient=transient)
    if retry_after is not None:
        due = max(due, _utc(retry_after))
    return replace(
        state,
        config_blocked=False,
        next_eligible_at=due,
        no_match_streak=0 if transient else streak,
        transient_streak=streak if transient else 0,
    )


@dataclass(frozen=True, slots=True)
class RetryCandidate:
    identity: RetryIdentity
    assessment: RetryAssessment


def select_retries(
    candidates: Iterable[RetryCandidate], *, budget: int = 5
) -> tuple[RetryCandidate, ...]:
    """Select across the entire operation, after collecting every mapping's candidates."""
    if type(budget) is not int or not 0 <= budget <= 5:
        raise ValueError("invalid_inventory_retry_budget")
    unique: dict[str, RetryCandidate] = {}
    for candidate in candidates:
        key = candidate.identity.key
        if key in unique and unique[key] != candidate:
            raise ValueError("conflicting_inventory_retry_candidate")
        unique[key] = candidate
    automatic = [
        item
        for item in unique.values()
        if item.assessment.eligible and item.assessment.reason == "due"
    ]
    ordered = sorted(
        automatic,
        key=lambda item: (
            item.assessment.due_at or datetime.max,
            item.identity.game_key,
            item.identity.key,
        ),
    )
    games: set[str] = set()
    for item in ordered:
        if len(games) < budget:
            games.add(item.identity.game_key)
    return tuple(
        (
            replace(
                item,
                assessment=RetryAssessment(
                    False, "budget_deferred", item.assessment.due_at
                ),
            )
            if item in automatic and item.identity.game_key not in games
            else item
        )
        for item in sorted(unique.values(), key=lambda item: item.identity.key)
    )
