"""Final serial frontend quality, using the existing guarded quality owner."""

from phase35_browser_quality import execute_quality

__all__ = ["execute_quality"]


RVZ_SKIPS = {
    "tests/utils/test_rvz_hasher.py::test_real_gamecube_rvz_matches_retroachievements_hash": "mock GameCube RVZ not present",
    "tests/utils/test_rvz_hasher.py::test_real_wii_rvz_matches_retroachievements_hash": "mock Wii RVZ not present",
}


def validate_backend_summary(payload):
    """Keep existing missing-fixture skips distinct from passing tests."""
    if payload.get("full_suite") is not True or payload.get("tests", 0) < 500:
        raise RuntimeError("missing full backend suite")
    for key in ("tests", "failures", "errors", "skipped"):
        if type(payload.get(key)) is not int or payload[key] < 0:
            raise RuntimeError("invalid backend test counts")
    if payload["failures"] or payload["errors"]:
        raise RuntimeError("backend suite has failures or errors")
    rows = payload.get("skip_details", [])
    if not isinstance(rows, list) or len(rows) != payload["skipped"]:
        raise RuntimeError("backend skip count mismatch")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("invalid backend skip record")
        nodeid = row.get("nodeid")
        if (
            nodeid not in RVZ_SKIPS
            or row.get("reason") != RVZ_SKIPS[nodeid]
            or nodeid in seen
        ):
            raise RuntimeError("unregistered or duplicate backend skip")
        seen.add(nodeid)
    if payload["skipped"] > payload["tests"]:
        raise RuntimeError("backend skip count exceeds tests")
