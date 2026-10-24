"""Validate final-source SQL, schema, Actions and current-link evidence."""

from phase38_cutover_source import require, revision, source_proof, test_membership

REPOSITORY_ID = 1415481891
WEB = "https://github.com/D1skanime/zockarchive"
REQUIRED_LINKS = {
    "source": WEB,
    "readme": WEB + "/blob/main/README.md",
    "install": WEB + "/blob/main/docs/PORTAINER_INSTALL.md",
    "releases": WEB + "/releases",
    "release_api": "https://api.github.com/repos/D1skanime/zockarchive/releases",
    "actions": WEB + "/actions",
}
LIMITATIONS = {
    "artwork",
    "physical_controller",
    "native_desktop",
    "registry",
    "production_portainer",
}
SCHEMA_STEPS = ["upgrade-head", "downgrade-base", "upgrade-head"]


def action(row, head):
    require(type(row.get("id")) is int and row["id"] > 0, "missing Actions ID")
    require(row.get("repository_id") == REPOSITORY_ID, "foreign Actions repository")
    require(row.get("head_sha") == head, "stale Actions source")
    require(
        row.get("url") == WEB + "/actions/runs/" + str(row["id"]), "foreign Actions URL"
    )
    require(
        row.get("status") == "completed" and row.get("conclusion") == "success",
        "unsuccessful Actions run",
    )


def validate(row):
    require(
        row.get("schema") == 1 and row.get("repository_id") == REPOSITORY_ID,
        "invalid validation identity/schema",
    )
    head = revision(row["pr_head"])
    require(row["final_source"]["commit"] == head, "final source is not PR head")
    source_proof(row["final_source"], head, "full")
    expected = test_membership(head)
    require(bool(expected), "empty full-suite membership")
    seen = set()
    for gate in row["backend"]:
        key = (gate["dialect"], gate["shard"])
        require(key not in seen, "duplicate backend shard")
        seen.add(key)
        require(
            gate["dialect"] in ("mariadb", "postgresql")
            and type(gate["shard"]) is int
            and 1 <= gate["shard"] <= 8,
            "invalid backend shard",
        )
        require(
            gate["files"] == expected[gate["shard"] - 1 :: 8],
            "incomplete or changed full-suite membership",
        )
        require(
            gate.get("passed") is True
            and type(gate.get("tests")) is int
            and gate["tests"] > 0
            and all(
                type(gate.get(k)) is int and gate[k] == 0
                for k in ("failures", "errors", "skipped")
            ),
            "backend failed, skipped or unobserved",
        )
        source_proof(gate["source"], head, "full")
        action(gate["action"], head)
    require(
        seen == {(d, s) for d in ("mariadb", "postgresql") for s in range(1, 9)},
        "missing complete dual-SQL matrix",
    )
    seen = set()
    for gate in row["schema_gates"]:
        require(gate["dialect"] not in seen, "duplicate schema dialect")
        seen.add(gate["dialect"])
        require(
            gate.get("passed") is True
            and gate.get("steps") == SCHEMA_STEPS
            and type(gate.get("failures")) is int
            and gate["failures"] == 0
            and type(gate.get("skipped")) is int
            and gate["skipped"] == 0,
            "missing successful schema roundtrip",
        )
        source_proof(gate["source"], head, "schema")
    require(seen == {"mariadb", "mysql", "postgresql"}, "missing schema dialect")
    require(bool(row["actions"]), "missing current Actions")
    for run in row["actions"]:
        action(run, head)
    required_runs = {g["action"]["id"] for g in row["backend"]}
    require(
        required_runs.issubset({r["id"] for r in row["actions"]}),
        "matrix run absent from Actions inventory",
    )
    seen = set()
    for link in row["links"]:
        kind = link["kind"]
        require(kind in REQUIRED_LINKS and kind not in seen, "unknown/duplicate link")
        seen.add(kind)
        require(
            link.get("url") == REQUIRED_LINKS[kind]
            and link.get("final_url") == REQUIRED_LINKS[kind]
            and type(link.get("status")) is int
            and link["status"] == 200
            and link.get("classification") == "current",
            "unverified current link or redirect dependency",
        )
        source_proof(link["source"], head, "full")
    require(seen == set(REQUIRED_LINKS), "missing current link")
    require(
        set(row["limitations"]) == LIMITATIONS
        and all(
            isinstance(v, str) and bool(v.strip()) for v in row["limitations"].values()
        ),
        "external limitations must remain separately classified",
    )
    for change in row["later_ref_changes"]:
        require(
            set(change) == {"ref", "before", "after", "reason"},
            "invalid later ref-change receipt",
        )
        require(
            change["ref"].startswith("refs/heads/")
            and change["reason"] in ("feature-push", "metadata-push"),
            "unapproved later ref change",
        )
        if change["before"] is not None:
            revision(change["before"])
        revision(change["after"])
