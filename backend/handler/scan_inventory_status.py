"""Game inventory units and concrete provider units share one aggregation owner."""

from collections.abc import Iterable

_BUCKETS = ("unchanged", "changed", "refresh_required", "incomplete")


def aggregate_inventory(games: Iterable[dict], observations: Iterable[dict]):
    """Games are full identities; provider counts are cumulative per identity/provider."""
    unique = {game["key"]: game for game in games}
    providers = {(item["key"], item["provider"]): item for item in observations}
    counts = {"inventory_" + state: 0 for state in _BUCKETS}
    unresolved = set()
    existing = set()
    for key, game in unique.items():
        counts["inventory_" + game["inventory_state"]] += 1
        if game.get("identified_windows") is False:
            unresolved.add(key)
        if game.get("existing_game") is True:
            existing.add(key)
    retry_games = set()
    requests = 0
    cache_hits = 0
    cache_observed = False
    for (key, _), observation in providers.items():
        value = observation.get("requests")
        if type(value) is int and 0 <= value <= 2147483647:
            requests += value
        if observation.get("invoked") is True and key in existing:
            retry_games.add(key)
        if type(observation.get("cached")) is bool:
            cache_observed = True
            cache_hits += int(observation["cached"])
    counts.update(
        inventory_checked=sum(counts.values()),
        unresolved_games=len(unresolved),
        metadata_retry_games=len(retry_games),
        provider_requests=requests,
    )
    if cache_observed:
        counts["metadata_cache_hits"] = cache_hits
    return counts
