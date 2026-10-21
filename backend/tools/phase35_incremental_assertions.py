"""Strict comparisons for connected synthetic acceptance evidence."""

from pathlib import PurePosixPath

PROTECTED = (
    "roms",
    "files",
    "components",
    "members",
    "baselines",
    "retries",
    "collections",
    "media",
)


def assert_preserved(before, after, *, keys=PROTECTED):
    for key in keys:
        if key not in before or key not in after or before[key] != after[key]:
            raise RuntimeError("worker changed protected " + key)


def assert_authority(receipt):
    barrier = receipt.get("barrier", {})
    if not barrier.get("operation") or barrier.get("phase") not in {
        "detection",
        "completion",
    }:
        raise RuntimeError("missing actual worker barrier")
    if receipt.get("job_status") not in {"finished", "failed", "stopped"}:
        raise RuntimeError("authority worker exit unconfirmed")
    if receipt.get("state") in {"completed", "completed-with-warnings"}:
        raise RuntimeError("revoked worker reported successful completion")
    assert_preserved(receipt["mutated"], receipt["after"])


def assert_game_files(catalog, expected):
    game = next(row for row in catalog["roms"] if row["name"] == "Known.Game")
    ordinary = {}
    for row in catalog["files"]:
        if row["rom_id"] == game["id"] and not row.get("missing", False):
            path = (
                (PurePosixPath(row["path"]) / row["name"])
                .relative_to("Known.Game")
                .as_posix()
            )
            ordinary[path] = row["size"]
    if ordinary != {path: row["size"] for path, row in expected.items()}:
        raise RuntimeError(
            "ordinary files differ from synthetic source: " + repr(ordinary)
        )
    components = {
        row["id"]: row["name"]
        for row in catalog["components"]
        if row["rom_id"] == game["id"]
    }
    members = {}
    for row in catalog["members"]:
        if row["component_id"] in components and not row["missing"]:
            path = PurePosixPath(row["path"]).as_posix()
            members[path] = {"size": row["size"], "sha256": row["sha256"]}
    if members != expected:
        raise RuntimeError(
            "component manifest differs from synthetic source: " + repr(members)
        )


def assert_stage_counts(name, snapshot):
    expected = {
        "cold": {
            "total_roms": 8,
            "inventory_refresh_required": 8,
            "unresolved_games": 8,
            "provider_requests": 16,
        },
        "adopt-identified": {
            "inventory_unchanged": 8,
            "unresolved_games": 7,
            "provider_requests": 0,
        },
        "promote": {
            "total_roms": 1,
            "new_roms": 1,
            "inventory_refresh_required": 1,
            "provider_requests": 2,
        },
        "collection-discovery": {
            "total_roms": 9,
            "new_roms": 1,
            "inventory_unchanged": 8,
            "provider_requests": 2,
        },
        "warm-manual": {
            "total_roms": 9,
            "inventory_unchanged": 9,
            "unresolved_games": 8,
            "provider_requests": 0,
        },
        "warm-scheduled": {
            "total_roms": 10,
            "inventory_unchanged": 9,
            "unresolved_games": 8,
            "provider_requests": 0,
        },
        "add": {
            "inventory_changed": 1,
            "inventory_unchanged": 8,
            "provider_requests": 0,
        },
        "change": {
            "inventory_changed": 1,
            "inventory_unchanged": 8,
            "provider_requests": 0,
        },
        "delete": {
            "inventory_changed": 1,
            "inventory_unchanged": 8,
            "provider_requests": 0,
        },
        "due-five": {"metadata_retry_games": 5, "provider_requests": 10},
        "due-rest": {"metadata_retry_games": 5, "provider_requests": 10},
        "backoff": {"metadata_retry_games": 0, "provider_requests": 0},
    }.get(name, {})
    for key, value in expected.items():
        if snapshot["scan_stats"].get(key, 0) != value:
            raise RuntimeError("unexpected " + name + " counter " + key)
