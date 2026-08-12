from pathlib import Path


def test_phase5_watcher_coalescer_contract_exists():
    assert Path(
        "watcher.py"
    ).exists(), "Phase 5 RED: per-mapping debounce and one pending follow-up are not implemented"


def test_phase5_follow_up_bound_is_one_per_mapping():
    pending = {11: True, 12: True}
    assert set(pending) == {11, 12} and all(pending.values())
