"""Bind disposable proofs to the canonical same-repository rename transition."""

import json
import os
import platform
import socket
import subprocess  # nosec B404, fixed read-only identity commands
from pathlib import Path

import phase34

ROOT = Path("/home/d1sk/pc-game-download-portal")
BRANCH = "codex/phase-38-zockarchive-rebranding"
PHASE = ROOT / ".planning/phases/38-zockarchive-product-and-repository-rebranding"
NAMES = ("D1skanime/pc-game-download-portal", "D1skanime/zockarchive")
OVERRIDES = {
    "DATABASE_URL",
    "COMPOSE_FILE",
    "COMPOSE_PROJECT_NAME",
    "PYTEST_ADDOPTS",
    "GITHUB_REPOSITORY",
    "GITHUB_ACTIONS",
}


def validate_identity(identity):
    """Accept only an exact live immutable-ID/name/origin pair."""
    if identity.get("overrides"):
        raise RuntimeError("refusing inherited target override")
    expected = {
        "system": "Linux",
        "host": "team4slinux",
        "root": str(ROOT),
        "workspace": str(ROOT),
        "branch": BRANCH,
    }
    if any(identity.get(key) != value for key, value in expected.items()):
        raise RuntimeError("proof execution identity mismatch")
    if any(
        marker not in identity.get(key, "")
        for key, marker in (
            ("project", "RomM PC Library"),
            ("state", "Phase38"),
            ("context", "ZA-BRAND-09"),
        )
    ):
        raise RuntimeError("proof planning identity mismatch")
    proof = identity.get("proof")
    if (
        not isinstance(proof, dict)
        or proof.get("id") != 1415481891
        or proof.get("node_id") != "R_kgDOVF6KIw"
        or proof.get("full_name") not in NAMES
        or identity.get("origin") != "https://github.com/" + proof["full_name"] + ".git"
    ):
        raise RuntimeError("proof live repository identity mismatch")
    return identity


def read_only(argv):
    # trunk-ignore(bandit/B603): Fixed Git/GitHub identity argv, no shell.
    return subprocess.check_output(argv, text=True, timeout=30).strip()


def preflight():
    """Verify source and reject inherited destinations before allocating resources."""
    phase34.host_preflight()
    overrides = {
        key: True
        for key, value in os.environ.items()
        if value
        and (key in OVERRIDES or key.startswith(("DB_", "REDIS_", "P34_", "PHASE34_")))
    }
    identity = {
        "system": platform.system(),
        "host": socket.gethostname(),
        "root": read_only(["git", "rev-parse", "--show-toplevel"]),
        "workspace": str(
            Path(os.environ.get("GITHUB_WORKSPACE", str(Path.cwd()))).resolve()
        ),
        "branch": read_only(["git", "branch", "--show-current"]),
        "origin": read_only(["git", "remote", "get-url", "origin"]),
        "project": (ROOT / ".planning/PROJECT.md").read_text(),
        "state": (ROOT / ".planning/STATE.md").read_text(),
        "context": (PHASE / "38-CONTEXT.md").read_text(),
        "overrides": overrides,
        "proof": None,
    }
    if overrides:
        raise RuntimeError("refusing inherited target override")
    identity["proof"] = json.loads(read_only(["gh", "api", "repositories/1415481891"]))
    validate_identity(identity)
    return {
        "source": read_only(["git", "rev-parse", "HEAD"]),
        "branch": identity["branch"],
        "origin": identity["origin"],
        "repository": {
            key: identity["proof"][key] for key in ("id", "node_id", "full_name")
        },
    }


def protected():
    """Fingerprint only predeclared unrelated files and retained provenance."""
    import hashlib

    baseline = json.loads((PHASE / "38-PROTECTED-BASELINE.json").read_text())
    actual = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in baseline["hashes"]
    }
    if actual != baseline["hashes"]:
        raise RuntimeError("protected work fingerprint mismatch")
    return actual
