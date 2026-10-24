"""Git-object evidence with fixed coverage for full suites and schema inputs.

Receipts carry complete path/blob maps. Equality is recomputed from Git objects,
never inferred from a caller's equivalence assertion or a partial manifest.
"""

import configparser
import hashlib
import json
import re
import subprocess  # nosec B404, fixed read-only Git argv
from pathlib import Path

from ci_test_profiles import classify_test_files, select_test_files

ROOT = Path("/home/d1sk/pc-game-download-portal")
SHA = re.compile(r"[0-9a-f]{40}")
SCHEMA_TOOLS = (
    "backend/tools/ci",
    "backend/tools/phase34",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def revision(value):
    require(isinstance(value, str) and SHA.fullmatch(value), "invalid Git commit")
    return value


def git(*args, binary=False, data=None):
    # trunk-ignore(bandit/B603): Read-only Git argv; validated commits and fixed verbs.
    return subprocess.check_output(  # nosec B603,B607
        ["git", *args],
        cwd=ROOT,
        text=not binary,
        stderr=subprocess.PIPE,
        timeout=60,
        input=data,
    )


def objects(commit):
    revision(commit)
    require(git("cat-file", "-t", commit).strip() == "commit", "source is not a commit")
    entries = {}
    for entry in git("ls-tree", "-rz", "--full-tree", commit).split("\0"):
        if not entry:
            continue
        metadata, name = entry.split("\t", 1)
        mode, kind, oid = metadata.split()
        if name.startswith(".planning/"):
            continue
        require(
            kind == "blob" and mode in ("100644", "100755", "120000"),
            "unsupported source object",
        )
        entries[name] = mode + ":" + oid
    require(bool(entries), "empty source coverage")
    return entries


def manifest(commit, domain):
    require(domain in ("full", "schema"), "invalid proof domain")
    files = objects(commit)
    if domain == "schema":
        files = {
            path: oid
            for path, oid in files.items()
            if (
                path.startswith("backend/")
                and not path.startswith(("backend/tests/", "backend/tools/"))
            )
            or path.startswith(SCHEMA_TOOLS)
            or path
            in (
                "pyproject.toml",
                "uv.lock",
                ".dockerignore",
                "docker/Dockerfile",
                ".github/workflows/migrations.yml",
            )
        }
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return {"files": files, "sha256": hashlib.sha256(encoded).hexdigest()}


def source_proof(row, head, domain):
    """Allow a CI merge checkout only with a direct head parent and equal inputs."""
    revision(head)
    commit = revision(row["commit"])
    actual = manifest(commit, domain)
    require(row.get("manifest") == actual, "source manifest coverage/digest mismatch")
    if domain == "schema":
        observed = row.get("observed_inputs")
        require(
            isinstance(observed, dict) and isinstance(observed.get("files"), dict),
            "missing observed runtime input manifest",
        )
        encoded = json.dumps(observed["files"], sort_keys=True).encode()
        require(
            observed.get("sha256") == hashlib.sha256(encoded).hexdigest(),
            "observed runtime manifest digest mismatch",
        )
        projected = {p: v for p, v in observed["files"].items() if schema_runtime(p)}
        require(
            projected == runtime_manifest(commit), "runtime snapshot differs from Git"
        )
    if commit != head:
        if domain == "full":
            parents = git("rev-list", "--parents", "-n", "1", commit).split()[1:]
            require(head in parents, "checkout is not final head or its CI merge")
        require(
            actual == manifest(head, domain), "tested inputs differ from final head"
        )
    return commit


def test_membership(commit):
    """Use exactly the existing CI pytest filename selection and shard ordering."""
    files = objects(commit)
    config = configparser.ConfigParser(interpolation=None)
    config.read_string(git("show", revision(commit) + ":backend/pytest.ini"))
    patterns = config.get(
        "pytest", "python_files", fallback="test_*.py *_test.py"
    ).split()
    return classify_test_files(select_test_files(files, patterns))


def schema_runtime(path):
    return (
        path.startswith("backend/")
        and not path.startswith(("backend/tests/", "backend/tools/"))
        or path in ("pyproject.toml", "uv.lock")
    )


def runtime_manifest(commit):
    """Hash actual Git blob bytes for the fixed schema-runtime coverage."""
    selected = {
        p: oid.split(":")[1] for p, oid in objects(commit).items() if schema_runtime(p)
    }
    require(bool(selected), "empty schema-runtime coverage")
    data = ("\n".join(selected.values()) + "\n").encode()
    output = git("cat-file", "--batch", binary=True, data=data)
    files = {}
    position = 0
    for name, oid in selected.items():
        end = output.index(b"\n", position)
        header = output[position:end].decode().split()
        require(header[:2] == [oid, "blob"], "invalid Git blob evidence")
        size = int(header[2])
        value = output[end + 1 : end + 1 + size]
        require(len(value) == size, "truncated Git blob")
        files[name] = hashlib.sha256(value).hexdigest()
        position = end + size + 2
    return files
