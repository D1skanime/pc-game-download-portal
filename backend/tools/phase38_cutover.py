#!/usr/bin/env python3
"""Read-only same-repository rename and final acceptance verifier.

Only known own-repository URL fields may change automatically. Historical bodies,
release assets and discussion identities remain exact. This command never writes
Git, GitHub, backup files or service state.
"""

import argparse
import hashlib
import json
import platform
import re
import subprocess  # nosec B404, fixed read-only Git argv
from pathlib import Path

from phase38_cutover_source import require, revision
from phase38_cutover_validation import validate

ROOT = Path("/home/d1sk/pc-game-download-portal")
BACKUP_ROOT = Path("/home/d1sk/za-backups/phase38-cutover")
OLD = "pc-game-download-portal"
NEW = "zockarchive"
OWNER = "D1skanime"
REPOSITORY_ID = 1415481891
NODE_ID = "R_kgDOVF6KIw"
URL_KEYS = {
    "url",
    "html_url",
    "assets_url",
    "upload_url",
    "tarball_url",
    "zipball_url",
    "browser_download_url",
    "comments_url",
    "issue_url",
    "diff_url",
    "patch_url",
    "commits_url",
    "review_comments_url",
    "review_comment_url",
    "statuses_url",
    "pull_request_url",
}
PREFIXES = (
    ("https://github.com/D1skanime/" + OLD, "https://github.com/D1skanime/" + NEW),
    (
        "https://api.github.com/repos/D1skanime/" + OLD,
        "https://api.github.com/repos/D1skanime/" + NEW,
    ),
    (
        "https://uploads.github.com/repos/D1skanime/" + OLD,
        "https://uploads.github.com/repos/D1skanime/" + NEW,
    ),
)


def git(*args):
    # trunk-ignore(bandit/B603): Fixed read-only verbs and validated external paths.
    return subprocess.check_output(  # nosec B603,B607
        ["git", *args],
        cwd=ROOT,
        text=True,
        stderr=subprocess.PIPE,
        timeout=60,
    )


def parse_refs(text):
    return sorted(
        [[ref, oid] for oid, ref in (line.split() for line in text.splitlines())]
    )


def refs(value, advertised=False):
    require(isinstance(value, list) and bool(value), "missing refs")
    require(all(isinstance(r, list) and len(r) == 2 for r in value), "invalid refs")
    require(
        value == sorted(value) and len({r[0] for r in value}) == len(value),
        "refs must be sorted and unique",
    )
    for ref, oid in value:
        revision(oid)
        require(
            isinstance(ref, str)
            and bool(re.fullmatch(r"(HEAD|refs/[A-Za-z0-9_./-]+(?:\^\{\})?)", ref)),
            "invalid ref",
        )
        if advertised:
            require(
                ref.startswith(("refs/heads/", "refs/tags/")), "foreign ref namespace"
            )
        if ref.endswith("^{}"):
            require(
                ref.startswith("refs/tags/") and ref[:-3] in {r[0] for r in value},
                "orphan peeled tag",
            )
    return value


def backup_path(value):
    path = Path(value)
    require(path.is_absolute() and not path.is_symlink(), "unsafe backup path")
    require(path.exists(), "missing backup path")
    resolved = path.resolve(strict=True)
    require(
        resolved.is_relative_to(BACKUP_ROOT.resolve()) and resolved != BACKUP_ROOT,
        "backup is outside dedicated external directory",
    )
    return resolved


def verify_bundle(row, source):
    path = backup_path(row["path"])
    require(path.is_file(), "missing backup file")
    require(
        row.get("sha256") == hashlib.sha256(path.read_bytes()).hexdigest(),
        "backup digest mismatch",
    )
    with path.open("rb") as stream:
        header = stream.readline()
        require(
            header in (b"# v2 git bundle\n", b"# v3 git bundle\n"),
            "invalid bundle header",
        )
        for _ in range(100000):
            line = stream.readline()
            require(not line.startswith(b"-"), "backup bundle has prerequisites")
            if line == b"\n":
                break
            require(bool(line), "truncated bundle header")
        else:
            raise ValueError("oversized bundle header")
    git("bundle", "verify", str(path))
    actual = parse_refs(git("bundle", "list-heads", str(path)))
    require(actual == refs(row["refs"]), "bundle ref coverage mismatch")
    source = revision(source)
    require(any(oid == source for _, oid in actual), "source not advertised in backup")


def verify_backup(before):
    backup = before["backup"]
    source = revision(backup["source"])
    local = backup["local"]
    remote = backup["remote"]
    verify_bundle(local, source)
    verify_bundle(remote, before["repository_head"])
    require(local["refs"] == refs(backup["local_refs"]), "missing local refs")
    require(
        backup["local_refs"] == refs(before["local_refs"]),
        "backup differs from captured local ref inventory",
    )
    remote_refs = [
        [r, oid] for r, oid in refs(before["refs"], True) if not r.endswith("^{}")
    ]
    require(remote["refs"] == remote_refs, "remote bundle omits advertised refs")
    mirror = backup_path(backup["mirror"])
    require(
        mirror.is_dir()
        and git("--git-dir=" + str(mirror), "rev-parse", "--is-bare-repository").strip()
        == "true",
        "missing bare mirror",
    )
    observed = parse_refs(git("--git-dir=" + str(mirror), "show-ref", "--dereference"))
    require(observed == before["refs"], "mirror refs or peeled tags differ")
    for _, oid in observed:
        git("--git-dir=" + str(mirror), "cat-file", "-e", revision(oid))
    git("--git-dir=" + str(mirror), "fsck", "--full", "--no-reflogs")
    require(
        any(oid == source for _, oid in local["refs"]), "unpublished source omitted"
    )


def rewrite(value, key=""):
    if isinstance(value, dict):
        return {k: rewrite(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [rewrite(v, key) for v in value]
    if isinstance(value, str) and key in URL_KEYS:
        for old, new in PREFIXES:
            if value == old or value.startswith((old + "/", old + "?", old + "{")):
                return new + value[len(old) :]
    return value


def records(rows, kind):
    require(isinstance(rows, list), "missing " + kind)
    ids = []
    for row in rows:
        required = {"id", "node_id"}
        if kind == "releases":
            required |= {
                "tag_name",
                "name",
                "body",
                "draft",
                "prerelease",
                "target_commitish",
                "assets",
                "html_url",
            }
            records(row["assets"], "assets")
        elif kind == "assets":
            required |= {"name", "size", "digest", "browser_download_url"}
            require(
                type(row.get("size")) is int and row["size"] >= 0, "invalid asset size"
            )
            require(
                isinstance(row.get("digest"), str)
                and re.fullmatch(r"sha256:[0-9a-f]{64}", row["digest"]),
                "asset content digest unavailable",
            )
        else:
            required |= {"number", "title", "body", "html_url"}
        require(required.issubset(row), "incomplete " + kind + " metadata")
        require(
            type(row.get("id")) is int
            and row["id"] > 0
            and isinstance(row.get("node_id"), str)
            and bool(row["node_id"]),
            "invalid content identity",
        )
        ids.append(row["id"])
    require(
        ids == sorted(ids) and len(set(ids)) == len(ids), "unsorted/duplicate content"
    )


def continuity(before, after):
    for row, name in ((before, OLD), (after, NEW)):
        require(row.get("schema") == 1, "unsupported snapshot schema")
        repo = row["repository"]
        require(
            repo.get("id") == REPOSITORY_ID and repo.get("node_id") == NODE_ID,
            "foreign repository identity",
        )
        require(
            repo.get("owner") == OWNER and repo.get("name") == name,
            "wrong repository owner/name",
        )
        require(
            {"default_branch", "visibility", "description", "homepage"}.issubset(repo),
            "incomplete repository metadata",
        )
        require(
            repo["default_branch"] == "main" and repo["visibility"] == "public",
            "unexpected default branch/visibility",
        )
        expected = "https://github.com/" + OWNER + "/" + name + ".git"
        require(
            row.get("origins") == {"fetch": expected, "push": expected},
            "actual fetch/push origin mismatch",
        )
        refs(row.get("refs"), True)
        for kind in ("releases", "issues", "pull_requests"):
            records(row.get(kind), kind)
    require(before["refs"] == after["refs"], "refs changed during continuity window")
    left = dict(before["repository"])
    right = dict(after["repository"])
    left["name"] = NEW
    edits = after["metadata_edits"]
    require(
        set(edits).issubset({"description", "homepage"}), "unapproved metadata edit"
    )
    for key, pair in edits.items():
        require(pair == [left[key], right[key]], "About edit does not match capture")
        left[key] = right[key]
    require(left == right, "repository metadata changed")
    for kind in ("releases", "issues", "pull_requests"):
        require(
            rewrite(before[kind]) == after[kind], "historical content changed: " + kind
        )
    verify_backup(before)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("before", "after", "validation"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        require(
            platform.system() == "Linux" and Path.cwd().resolve() == ROOT,
            "requires canonical Linux checkout",
        )
        require(
            git("rev-parse", "--show-toplevel").strip() == str(ROOT), "wrong Git root"
        )
        values = [
            json.loads(p.read_text())
            for p in (args.before, args.after, args.validation)
        ]
        continuity(values[0], values[1])
        validate(values[2])
    except (
        ValueError,
        KeyError,
        TypeError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        parser.exit(1, "FAIL cutover evidence: " + type(exc).__name__ + "\n")
    print("PASS same-ID continuity, verified backup and final-source acceptance")


if __name__ == "__main__":
    main()
