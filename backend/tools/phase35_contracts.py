#!/usr/bin/env python3
"""Generate backend-owned frontend contracts in a token-bound disposable runtime."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from phase34 import REPO, Run, host_preflight
from phase34_faults import start_application

SCHEMA_URL = "http://127.0.0.1:3344/openapi.json"
GENERATED = Path("frontend/src/__generated__")


def validate_authority(run, url):
    """Accept only this run's exact isolated container-loopback schema."""
    if (
        url != SCHEMA_URL
        or not re.fullmatch(r"[a-f0-9]{32}", run.token)
        or run.project != "pgdp34-" + run.token
        or not run.manifest
        or run.manifest.get("token") != run.token
        or run.manifest.get("project") != run.project
    ):
        raise RuntimeError("unowned or unsafe contract generation target")


def generated_manifest(root):
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("generated directory must be a real directory")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("generated symlink rejected")
        if path.is_file():
            if path.suffix != ".ts":
                raise RuntimeError("unexpected generated artifact")
            result[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


def copy_generated(source, target, baseline):
    generated = generated_manifest(source)
    if not generated or "index.ts" not in generated:
        raise RuntimeError("partial generated contract")
    if generated_manifest(target) != baseline:
        raise RuntimeError("generated destination changed concurrently")
    removed = set(baseline) - set(generated)
    if removed:
        raise RuntimeError("generation unexpectedly removed existing contracts")
    changed = []
    for name, digest in generated.items():
        if baseline.get(name) == digest:
            continue
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, destination)
        changed.append(name)
    return changed


def confirm_run(run):
    validate_authority(run, SCHEMA_URL)
    owned = run.owned("container")
    if run.runner not in owned:
        # Docker may return short IDs, so compare the inspected immutable identity.
        if not any(
            run.inspect("container", item)["Id"] == run.runner for item in owned
        ):
            raise RuntimeError("runner ownership mismatch")
    run.exec(
        [
            "uv",
            "run",
            "python",
            "-c",
            "from tools.phase34_target_guard import validate_target; validate_target()",
        ]
    )


def generate(driver):
    host_preflight()
    baseline = generated_manifest(REPO / GENERATED)
    run = Run(driver)
    try:
        run.start()
        confirm_run(run)
        start_application(run)
        run.exec(
            [
                "uv",
                "run",
                "python",
                "-c",
                "import urllib.request; from pathlib import Path; "
                "from tools.phase34_target_guard import validate_target; validate_target(); "
                "Path('/phase34/evidence/openapi.json').write_bytes("
                "urllib.request.urlopen(" + repr(SCHEMA_URL) + ", timeout=10).read())",
            ]
        )
        run.exec(["npm", "run", "generate"], frontend=True)
        run.exec(["npm", "run", "typecheck"], frontend=True, timeout=300)
        confirm_run(run)
        snapshot = run.root / "checkout"
        recorded = json.loads((run.evidence / "code-before.json").read_text())
        backend = {
            name: digest
            for name, digest in recorded["files"].items()
            if name.startswith("backend/")
        }
        if any(
            hashlib.sha256((REPO / name).read_bytes()).hexdigest() != digest
            for name, digest in backend.items()
        ):
            raise RuntimeError("backend source changed during generation")
        generated = generated_manifest(snapshot / GENERATED)
        changed = copy_generated(snapshot / GENERATED, REPO / GENERATED, baseline)
        receipt = {
            "schema_sha256": hashlib.sha256(
                (run.evidence / "openapi.json").read_bytes()
            ).hexdigest(),
            "source_sha256": recorded["sha256"],
            "backend_source_hashes": backend,
            "generated_hashes": generated,
            "changed": changed,
            "dialect": driver,
            "schema_url": SCHEMA_URL,
        }
        (run.evidence / "contracts.json").write_text(json.dumps(receipt, indent=2))
        print(
            "PASS exact contracts:",
            json.dumps(
                {
                    key: receipt[key]
                    for key in ("schema_sha256", "source_sha256", "changed")
                }
            ),
            flush=True,
        )
    finally:
        run.close()
    return run.evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true", required=True)
    parser.add_argument(
        "--dialect", choices=("mariadb", "postgresql"), default="mariadb"
    )
    args = parser.parse_args()
    print("Contract receipts:", generate(args.dialect))


if __name__ == "__main__":
    main()
