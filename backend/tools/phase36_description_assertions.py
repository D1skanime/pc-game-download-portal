"""Acceptance assertions over actual SQL/API and transport observations."""


def assert_repair(before, result, seen):
    rows = result["catalog"]["descriptions"]
    old = {row["id"]: row for row in before["descriptions"]}
    for row in rows:
        if (
            row["summary"] != old[row["id"]]["summary"]
            or row["manual"] != old[row["id"]]["manual"]
        ):
            raise RuntimeError("description repair changed protected scalar/manual")
    known = next(row for row in rows if row["name"] == "Known.Game")
    variants = known["steam"]["text_variants"]
    if (
        not all(variants.get(tag, {}).get("summary") for tag in ("de", "en"))
        or variants["de"]["summary"] == variants["en"]["summary"]
    ):
        raise RuntimeError("actual German/English slots missing")
    if any(
        row["kind"] in {"hash", "components", "media_prepare", "capsule_http"}
        for row in seen
    ):
        raise RuntimeError("description-only repair did expensive work")
    if (
        before["files"] != result["catalog"]["files"]
        or before["components"] != result["catalog"]["components"]
    ):
        raise RuntimeError("description repair changed inventory")
    for key in ("auth", "media", "baselines", "members"):
        if before[key] != result["catalog"][key]:
            raise RuntimeError("description repair changed protected " + key)
    old_components = {row["id"]: row for row in before["component_descriptions"]}
    for row in result["catalog"]["component_descriptions"]:
        if (row["manual"], row["summary"]) != (
            old_components[row["id"]]["manual"],
            old_components[row["id"]]["summary"],
        ):
            raise RuntimeError(
                "component description repair changed protected manual/scalar"
            )
    dispatch = [row for row in seen if row["kind"] == "description_dispatch"]
    games = {row["rom_id"] for row in dispatch}
    if len(games) > 5 or any(
        sum(row["rom_id"] == game for row in dispatch) > 8 for game in games
    ):
        raise RuntimeError(
            "actual description work exceeded five-game/eight-target budget"
        )
    actual = sum(
        row["kind"] == "provider_http"
        and row["endpoint"].endswith(("appdetails", "jeuInfos.php"))
        for row in seen
    )
    counted = result["scan_stats"].get("provider_requests", 0)
    if actual != counted:
        raise RuntimeError(
            "actual description wire count "
            + str(actual)
            + " != durable provider_requests "
            + str(counted)
        )


def assert_authority(result):
    if result["mutated"] != result["after"]:
        raise RuntimeError("revoked description worker changed protected catalog")
    if result["stats_before"] != result["stats_after"]:
        raise RuntimeError("revoked description worker changed durable counters")
    if result["state"] == "completed" or result["job_status"] not in {
        "finished",
        "failed",
        "stopped",
    }:
        raise RuntimeError(
            "revoked description worker falsely completed or still active"
        )
    if not result["intentional_mutation"].get("verified"):
        raise RuntimeError("unverified disposable mutation")
