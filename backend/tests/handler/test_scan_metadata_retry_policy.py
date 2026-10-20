"""Fake-clock retry eligibility, observed requests and global budget."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from handler.database.scan_inventory_state import InventoryBinding
from handler.scan_metadata_retry_policy import (
    RetryCandidate,
    RetryIdentity,
    RetryState,
    assess_retry,
    observe_outcome,
    select_retries,
)

NOW = datetime(2026, 10, 20, 12)


def CLOCK():
    return NOW


def identity(
    path="Collection/Game", provider="steam", mapping=1, query=" Game ", config="b" * 64
):
    binding = InventoryBinding(mapping, 2, "PC", 3, path, 4, "a" * 32, "c" * 64)
    return RetryIdentity(binding, provider, query, "en_US", config)


def due(key=None, **changes):
    return RetryState(
        key or identity(), next_eligible_at=NOW - timedelta(hours=1), **changes
    )


def assess(state=None, **changes):
    values = dict(
        identity=identity(),
        state=state,
        baseline_adopted_at=NOW - timedelta(days=2),
        clock=CLOCK,
    )
    values.update(changes)
    return assess_retry(**values)


def test_adoption_and_new_discovery():
    assert assess(baseline_adopted_at=NOW).reason == "cooldown"
    assert assess(baseline_adopted_at=NOW - timedelta(hours=24)).eligible
    assert assess(baseline_adopted_at=None).reason == "baseline_required"
    assert assess(newly_discovered=True, baseline_adopted_at=None).reason == "initial"


def test_boundary_and_utc_clock():
    state = replace(due(), next_eligible_at=NOW)
    assert assess(state).eligible
    assert not assess(
        replace(state, next_eligible_at=NOW + timedelta(microseconds=1))
    ).eligible
    assert assess(state, clock=lambda: NOW.replace(tzinfo=timezone.utc)).eligible


@pytest.mark.parametrize("flag", ["configured", "selected", "authority_current"])
def test_disabled_unselected_or_stale_never_dispatch(flag):
    assert not assess(due(), **{flag: False}, explicit_accepted=True).eligible


def test_identified_not_retry_and_explicit_cooldown_bypass():
    blocked = due(config_blocked=True)
    assert assess(blocked).reason == "configuration_blocked"
    assert assess(blocked, explicit_accepted=True).eligible
    assert not assess(due(), identified=True).eligible


def test_identity_uses_normalized_query_locale_full_binding_and_config():
    key = identity()
    assert key == identity(query="game")
    assert key.locale == "en-us"
    assert key != identity(path="Other/Game")
    assert key != identity(mapping=8)
    assert key != identity(config="d" * 64)
    assert key != identity(query="new game")
    assert key != identity(provider="igdb")
    assert assess(
        due(key, config_blocked=True), identity=identity(config="d" * 64)
    ).eligible
    assert (
        assess(
            due(key), identity=identity(query="new game"), baseline_adopted_at=NOW
        ).reason
        == "cooldown"
    )


@pytest.mark.parametrize(
    "outcome,base_hours,cap", [("no_match", 24, 168), ("transient", 1, 24)]
)
def test_actual_requests_backoff_and_caps(outcome, base_hours, cap):
    state = None
    for streak in range(1, 12):
        state = observe_outcome(
            identity(),
            state,
            outcome=outcome,
            invoked_at=NOW,
            request_at=NOW,
            clock=CLOCK,
        )
        hours = min(base_hours * 2 ** (streak - 1), cap)
        assert state.next_eligible_at is not None
        delay = (state.next_eligible_at - NOW).total_seconds() / 3600
        assert 0.9 * hours <= delay <= 1.1 * hours
        assert state.last_request_at == NOW
        assert getattr(state, outcome + "_streak") == streak


def test_jitter_deterministic_binding_specific_and_retry_after_is_floor():
    def attempt(key, **kw):
        return observe_outcome(
            key,
            None,
            outcome="transient",
            invoked_at=NOW,
            request_at=NOW,
            clock=CLOCK,
            **kw,
        )

    assert attempt(identity()) == attempt(identity())
    assert (
        attempt(identity()).next_eligible_at
        != attempt(identity("Other/Game")).next_eligible_at
    )
    later = NOW + timedelta(days=3)
    assert attempt(identity(), retry_after=later).next_eligible_at == later
    assert (
        attempt(identity(), retry_after=NOW - timedelta(days=1)).next_eligible_at > NOW
    )


@pytest.mark.parametrize("outcome", ["not_invoked", "unknown", "no_match", "transient"])
def test_no_request_does_not_invent_attempt_or_streak(outcome):
    previous = due(no_match_streak=3, last_request_at=NOW - timedelta(days=1))
    result = observe_outcome(identity(), previous, outcome=outcome, clock=CLOCK)
    assert result.last_request_at == previous.last_request_at
    assert result.no_match_streak == 3
    assert result.next_eligible_at == previous.next_eligible_at
    assert result.last_invoked_at is None


def test_cache_only_reevaluation_has_24h_floor_without_external_attempt():
    previous = due(
        no_match_streak=3, transient_streak=2, last_request_at=NOW - timedelta(days=2)
    )
    result = observe_outcome(
        identity(), previous, outcome="cache_hit", invoked_at=NOW, clock=CLOCK
    )
    assert result.next_eligible_at is not None
    assert result.next_eligible_at >= NOW + timedelta(hours=24)
    assert result.last_invoked_at == NOW
    assert result.last_request_at == previous.last_request_at
    assert (result.no_match_streak, result.transient_streak) == (3, 2)


def test_config_failure_blocks_until_config_identity_changes():
    state = observe_outcome(
        identity(), None, outcome="configuration_blocked", invoked_at=NOW, clock=CLOCK
    )
    assert assess(state).reason == "configuration_blocked"
    assert assess(state, identity=identity(config="e" * 64)).eligible
    assert assess(state, explicit_accepted=True).eligible


def test_changed_content_cannot_invent_request_and_changed_query_resets_streak():
    previous = due(no_match_streak=9, last_request_at=NOW)
    changed = observe_outcome(
        identity(query="other"), previous, outcome="cache_hit", clock=CLOCK
    )
    assert changed.last_request_at is None
    assert changed.no_match_streak == 0


def test_global_budget_oldest_game_then_full_identity_and_all_due_providers():
    candidates = []
    for i in range(8):
        for provider in ("steam", "igdb"):
            key = identity(
                path=f"Collection{i}/Game", provider=provider, mapping=i % 3 + 1
            )
            state = replace(due(key), next_eligible_at=NOW - timedelta(hours=i))
            candidates.append(RetryCandidate(key, assess(state, identity=key)))
    decisions = select_retries(reversed(candidates))
    selected = [item for item in decisions if item.assessment.eligible]
    deferred = [
        item for item in decisions if item.assessment.reason == "budget_deferred"
    ]
    assert len({item.identity.game_key for item in selected}) == 5
    assert len(selected) == 10
    assert len(deferred) == 6
    assert {item.identity.binding.game_relative_path for item in selected} == {
        f"Collection{i}/Game" for i in range(3, 8)
    }
    assert decisions == select_retries(candidates)


def test_duplicate_candidates_cannot_spend_budget_and_initial_explicit_bypass():
    key = identity()
    ordinary = RetryCandidate(key, assess(due()))
    explicit = RetryCandidate(
        identity("Explicit"),
        assess(
            due(identity("Explicit")),
            identity=identity("Explicit"),
            explicit_accepted=True,
        ),
    )
    initial = RetryCandidate(
        identity("New"), assess(identity=identity("New"), newly_discovered=True)
    )
    selected = select_retries([ordinary, ordinary, explicit, initial], budget=0)
    assert len(selected) == 3
    assert [x.assessment.reason for x in selected].count("budget_deferred") == 1
    assert sum(x.assessment.eligible for x in selected) == 2


def test_invalid_observations_and_state_fail_closed():
    with pytest.raises(ValueError):
        observe_outcome(
            identity(), None, outcome="no_match", request_at=NOW, clock=CLOCK
        )
    with pytest.raises(ValueError):
        observe_outcome(identity(), None, outcome="invented", clock=CLOCK)
    with pytest.raises(ValueError):
        RetryState(identity(), no_match_streak=-1)
    with pytest.raises(ValueError):
        select_retries([], budget=6)


def test_query_change_does_not_unlock_same_provider_configuration():
    blocked = due(config_blocked=True)
    assert (
        assess(blocked, identity=identity(query="other")).reason
        == "configuration_blocked"
    )
    assert assess(
        blocked, identity=identity(query="other"), explicit_accepted=True
    ).eligible


def test_record_projection_matches_shared_persisted_identity_and_clocks():
    key = identity()
    row = SimpleNamespace(
        **key.fields(),
        identity_digest=key.key,
        next_eligible_at=NOW,
        last_invoked_at=NOW,
        last_request_at=NOW,
        no_match_streak=2,
        transient_streak=0,
        outcome="no_match",
        config_blocked=False,
    )
    state = RetryState.from_record(key, row)
    assert state.persistence()["request_at"] == NOW
    assert state.persistence()["query"] == "game"
    row.game_relative_path = "Other/Game"
    with pytest.raises(ValueError, match="identity_collision"):
        RetryState.from_record(key, row)


def test_stale_request_observations_rejected_without_changing_previous():
    previous = due(last_invoked_at=NOW, last_request_at=NOW)
    with pytest.raises(ValueError, match="stale_inventory"):
        observe_outcome(
            identity(),
            previous,
            outcome="no_match",
            invoked_at=NOW - timedelta(hours=1),
            request_at=NOW - timedelta(hours=1),
            clock=CLOCK,
        )
    assert previous.last_request_at == NOW


def test_disabled_and_unselected_candidates_do_not_consume_fair_budget():
    key = identity()
    disabled = RetryCandidate(key, assess(due(), configured=False))
    candidates = [disabled]
    for i in range(6):
        key = identity(f"Collection{i}/Game")
        candidates.append(RetryCandidate(key, assess(due(key), identity=key)))
    selected = select_retries(candidates)
    assert sum(item.assessment.eligible for item in selected) == 5
    assert sum(item.assessment.reason == "budget_deferred" for item in selected) == 1
    assert selected == select_retries(reversed(candidates))
