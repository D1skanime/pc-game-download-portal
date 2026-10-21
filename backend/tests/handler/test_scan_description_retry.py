"""Description repair shares the operation retry policy and budget."""

from dataclasses import replace
from datetime import datetime

from tests.handler.test_windows_quick_execution import binding

from handler.scan_metadata_retry_policy import (
    RetryCandidate,
    RetryIdentity,
    assess_retry,
    observe_outcome,
    select_retries,
)


def identity(index=0, query="descriptions:v1:10:parent"):
    return RetryIdentity(
        replace(binding(), rom_id=index + 1, mapping_id=index + 1),
        "steam",
        query,
        "de-DE",
        "f" * 64,
    )


def test_missing_known_id_description_is_due_without_baseline_delay():
    current = identity()
    advice = assess_retry(
        current, None, baseline_adopted_at=None, clock=lambda: datetime(2026, 10, 21)
    )
    assert advice.eligible and advice.reason == "due"
    unknown = replace(current, query="Game")
    assert not assess_retry(
        unknown, None, baseline_adopted_at=None, clock=lambda: datetime(2026, 10, 21)
    ).eligible


def test_description_cooldown_survives_restart_and_shared_game_budget():
    now = datetime(2026, 10, 21)
    current = identity()
    state = observe_outcome(
        current,
        None,
        outcome="no_match",
        clock=lambda: now,
        invoked_at=now,
        request_at=now,
    )
    assert not assess_retry(
        current, state, baseline_adopted_at=None, clock=lambda: now
    ).eligible
    candidates = []
    for index in range(6):
        for query in ("descriptions:v1:10:parent", "Game"):
            item = identity(index, query)
            candidates.append(
                RetryCandidate(
                    item,
                    assess_retry(
                        item,
                        None,
                        baseline_adopted_at=datetime(2026, 10, 1),
                        clock=lambda: now,
                    ),
                )
            )
    chosen = select_retries(candidates)
    assert (
        len({item.identity.game_key for item in chosen if item.assessment.eligible})
        == 5
    )
    assert sum(item.assessment.reason == "budget_deferred" for item in chosen) == 2


def target(component_id=None, provider="steam", current=None):
    from handler.scan_description_retry import DescriptionTarget

    return DescriptionTarget(
        component_id,
        provider,
        10,
        datetime(2026, 10, 21),
        current
        or {provider + "_id": 10, provider + "_metadata": {}, "manual_metadata": {}},
        "win" if provider == "steam" else "snes",
        "Game",
    )


def setup_retry(monkeypatch, sources=("steam", "ss"), policy=None):
    from types import SimpleNamespace

    from handler import scan_description_retry as descriptions
    from handler import scan_retry_execution as execution

    retry = execution.RetryCoordinator(
        policy
        or {
            "apis": list(sources),
            "metadata_locale": "fr",
            "description_languages": ("de", "en"),
        },
        clock=lambda: datetime(2026, 10, 21),
    )
    monkeypatch.setattr(execution, "configured_sources", lambda policy: list(sources))
    monkeypatch.setattr(descriptions, "load_retry_states", lambda binding: [])
    quick = SimpleNamespace(binding=binding())
    rom = SimpleNamespace(
        id=binding().rom_id,
        platform_slug="win",
        steam_id=10,
        updated_at=datetime(2026, 10, 21),
        steam_metadata={},
        manual_metadata={},
        fs_name="Game",
    )
    return retry, quick, rom


def test_eight_target_cap_parent_first_and_fair_progress(monkeypatch):
    from types import SimpleNamespace

    from handler import scan_description_retry as descriptions

    retry, quick, rom = setup_retry(monkeypatch)
    offered = [target(index) for index in range(1, 14)] + [target()]
    retry.consider_descriptions(quick, rom, None, targets=reversed(offered))
    assert len(retry.candidates) == 8
    assert {item.component_id for item in retry.description_targets.values()} == {
        None,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
    }
    records = []
    for item in retry.candidates:
        state = observe_outcome(
            item.identity,
            None,
            outcome="no_match",
            clock=retry.clock,
            invoked_at=retry.clock(),
            request_at=retry.clock(),
        )
        records.append(
            SimpleNamespace(
                **item.identity.fields(),
                identity_digest=item.identity.key,
                next_eligible_at=state.next_eligible_at,
                last_invoked_at=state.last_invoked_at,
                last_request_at=state.last_request_at,
                no_match_streak=1,
                transient_streak=0,
                outcome=state.outcome,
                config_blocked=False,
            )
        )
    monkeypatch.setattr(descriptions, "load_retry_states", lambda binding: records)
    retry.candidates.clear()
    retry.description_targets.clear()
    retry.consider_descriptions(quick, rom, None, targets=offered)
    assert {item.component_id for item in retry.description_targets.values()} == {
        8,
        9,
        10,
        11,
        12,
        13,
    }


def test_identity_does_not_change_with_missing_subset_or_mutable_input(monkeypatch):
    from handler.scan_description_retry import description_identity

    policy = {
        "apis": ["steam"],
        "metadata_locale": "fr",
        "description_languages": ["de", "en"],
    }
    retry, quick, rom = setup_retry(monkeypatch, policy=policy)
    before = description_identity(retry, quick.binding, target())
    partial = target(
        current={
            "steam_id": 10,
            "steam_metadata": {
                "app_id": 10,
                "source": "storefront",
                "text_variants": {
                    "fr": {"summary": "Francais", "source_language": "french"}
                },
            },
        }
    )
    assert description_identity(retry, quick.binding, partial) == before
    policy["metadata_locale"] = "de"
    policy["description_languages"] = ["de", "en", "ja"]
    assert description_identity(retry, quick.binding, target()) == before
    assert retry.policy["metadata_locale"] == "fr"


def test_complete_warm_manual_and_platform_provider_eligibility(monkeypatch):
    retry, quick, rom = setup_retry(monkeypatch)
    complete = target(
        current={
            "steam_id": 10,
            "steam_metadata": {},
            "manual_metadata": {
                "descriptions": {"fr": "Manuel", "de": "Manuell", "en": "Manual"}
            },
        }
    )
    retry.consider_descriptions(quick, rom, None, targets=[complete])
    assert retry.candidates == []
    retry.consider_descriptions(quick, rom, None, targets=[target(provider="ss")])
    assert len(retry.candidates) == 1 and retry.candidates[0].identity.provider == "ss"
    retry, quick, rom = setup_retry(monkeypatch, sources=())
    retry.consider_descriptions(quick, rom, None, targets=[target()])
    assert not retry.candidates


def test_partial_matching_id_cannot_clear_cooldown_and_cache_clocks_remain_truthful():
    from handler.scan_description_retry import description_outcome

    now = datetime(2026, 10, 21)
    item = identity()
    previous = observe_outcome(
        item,
        None,
        outcome="no_match",
        clock=lambda: now,
        invoked_at=now,
        request_at=now,
    )
    facts = {
        "invoked": True,
        "cached": False,
        "requests": 2,
        "outcome": "matched",
        "invoked_at": now.isoformat(),
        "request_at": now.isoformat(),
    }
    result = description_outcome(
        item, previous, facts, complete=False, clock=lambda: now
    )
    assert result.outcome == "no_match" and result.no_match_streak == 2
    assert result.next_eligible_at > previous.next_eligible_at
    facts.update(requests=0, cached=True, request_at=None)
    cached = description_outcome(item, result, facts, complete=False, clock=lambda: now)
    assert (
        cached.no_match_streak == 2 and cached.last_request_at == result.last_request_at
    )
    assert cached.outcome == "cache_hit"
    facts.update(cached=False, invoked=False, invoked_at=None)
    noop = description_outcome(item, None, facts, complete=False, clock=lambda: now)
    assert noop.last_request_at is None and noop.last_invoked_at is None
    assert noop.next_eligible_at > now
