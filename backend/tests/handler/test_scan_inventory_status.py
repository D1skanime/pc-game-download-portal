"""Exact inventory game units and observed provider dispatch units."""


def test_exact_units_and_replay():
    from handler.scan_inventory_status import aggregate_inventory

    games = [
        {
            "key": str(i),
            "inventory_state": state,
            "identified_windows": i == 0,
            "existing_game": i != 2,
        }
        for i, state in enumerate(
            ["unchanged", "changed", "refresh_required", "incomplete", "unchanged"]
        )
    ]
    observations = [
        {
            "key": "1",
            "provider": "igdb",
            "invoked": True,
            "requests": 2,
            "cached": False,
        },
        {
            "key": "1",
            "provider": "steam",
            "invoked": True,
            "requests": 3,
            "cached": False,
        },
        {
            "key": "2",
            "provider": "igdb",
            "invoked": True,
            "requests": 1,
            "cached": False,
        },
        {
            "key": "4",
            "provider": "igdb",
            "invoked": True,
            "requests": 0,
            "cached": True,
        },
    ]
    counts = aggregate_inventory(games + games, observations + observations)
    assert counts == {
        "inventory_checked": 5,
        "inventory_unchanged": 2,
        "inventory_changed": 1,
        "inventory_refresh_required": 1,
        "inventory_incomplete": 1,
        "unresolved_games": 4,
        "metadata_retry_games": 2,
        "provider_requests": 6,
        "metadata_cache_hits": 1,
    }
    assert counts["inventory_checked"] == sum(
        counts["inventory_" + state]
        for state in ("unchanged", "changed", "refresh_required", "incomplete")
    )


def test_eligibility_wrapper_and_unavailable_observations_are_not_requests():
    from handler.scan_inventory_status import aggregate_inventory

    game = {
        "key": "unknown",
        "inventory_state": "unchanged",
        "identified_windows": False,
        "existing_game": True,
        "retry_eligible": True,
    }
    result = aggregate_inventory(
        [game], [{"key": "unknown", "provider": "igdb", "outcome": "completed"}]
    )
    assert result["unresolved_games"] == 1
    assert result["metadata_retry_games"] == 0
    assert result["provider_requests"] == 0
    assert "metadata_cache_hits" not in result
