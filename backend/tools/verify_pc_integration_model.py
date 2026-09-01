#!/usr/bin/env python3
"""Run the Phase 10 PC browser flow against an isolated fixture library."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
import tempfile
import time
import uuid
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "backend" / "docker-compose.pc-integration-test.yml"
SOURCE_LIBRARY_ROOT = (
    REPO_ROOT / "tests" / "fixtures" / "pc-integration-model" / "source-library"
)
PC_E2E_SEEDER = Path("/workspace/backend/tools/seed_phase10_pc_fixture.py")
E2E_USER_SEEDER = Path("/workspace/.github/scripts/seed_e2e_users.py")


def fixture_tree_digest(root: Path) -> str:
    """Return a stable digest of every relative path and file payload."""
    lines: list[str] = []
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative_path = path.relative_to(root).as_posix()
        if path.is_dir():
            lines.append(f"directory:{relative_path}")
        elif path.is_file():
            lines.append(
                f"file:{relative_path}:{path.stat().st_size}:"
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}"
            )
        else:
            raise ValueError(f"unsupported fixture entry: {relative_path}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def prepare_fixture_copy(source_root: Path, run_root: Path) -> Path:
    """Copy the checked-in source below the Structure A Windows platform path."""
    fixture_root = run_root / "library"
    destination = fixture_root / "roms" / "win"
    destination.mkdir(parents=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file():
            continue
        relative_path = source_path.relative_to(source_root)
        target_path = destination / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
    return fixture_root


def phase10_environment(
    *, fixture_root: Path, artifacts_root: Path, compose_project: str
) -> dict[str, str]:
    environment = dict(os.environ)
    environment.update(
        {
            "PHASE10_REPO_ROOT": str(REPO_ROOT),
            "PHASE10_FIXTURE_SOURCE": str(fixture_root),
            "PHASE10_ARTIFACTS": str(artifacts_root),
            "COMPOSE_PROJECT_NAME": compose_project,
        }
    )
    environment.pop("PHASE9_FIXTURE_SOURCE", None)
    return environment


def _run(
    command: list[str], *, cwd: Path = REPO_ROOT, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _compose(*args: str) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *args]


def _base_url(environment: dict[str, str]) -> str:
    completed = _run(_compose("port", "nginx", "80"), env=environment)
    host, _, port = completed.stdout.strip().splitlines()[-1].rpartition(":")
    return f"http://{('127.0.0.1' if host == '0.0.0.0' else host)}:{port}"  # nosec B104


def _wait_for_stack(base_url: str, timeout_seconds: int = 90) -> None:
    deadline = time.monotonic() + timeout_seconds
    heartbeat_url = f"{base_url}/api/heartbeat"
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib_request.urlopen(  # nosec B310
                heartbeat_url, timeout=2
            ) as response:
                if response.status < 500:
                    return
        except (OSError, TimeoutError, urllib_error.URLError) as error:
            last_error = error
        time.sleep(1)
    raise RuntimeError(
        f"Phase 10 stack did not become ready: {heartbeat_url}"
    ) from last_error


def _compose_exec(environment: dict[str, str], script: Path) -> str:
    completed = _run(
        _compose("exec", "-T", "app", "uv", "run", "python", str(script)),
        env=environment,
    )
    return completed.stdout


def _run_browser(*, base_url: str, fixture_root: Path, rom_id: int) -> None:
    environment = dict(os.environ)
    environment.update(
        {
            "E2E_BASE_URL": base_url,
            "PC_E2E_ROM_ID": str(rom_id),
            "PC_E2E_FIXTURE_ROOT": str(fixture_root),
        }
    )
    _run(
        [
            "npx",
            "playwright",
            "test",
            "e2e/pc-integration-model.spec.ts",
            "--project=chromium",
            "--workers=1",
        ],
        cwd=REPO_ROOT / "frontend",
        env=environment,
    )


def _cleanup(environment: dict[str, str]) -> None:
    _run(_compose("down", "-v", "--remove-orphans"), env=environment)


def run() -> dict[str, str | int]:
    source_digest = fixture_tree_digest(SOURCE_LIBRARY_ROOT)
    with tempfile.TemporaryDirectory(prefix="phase10-pc-") as temp_dir:
        run_root = Path(temp_dir)
        fixture_root = prepare_fixture_copy(SOURCE_LIBRARY_ROOT, run_root)
        before_digest = fixture_tree_digest(fixture_root)
        artifacts_root = run_root / "artifacts"
        artifacts_root.mkdir()
        environment = phase10_environment(
            fixture_root=fixture_root,
            artifacts_root=artifacts_root,
            compose_project=f"phase10-pc-{uuid.uuid4().hex[:12]}",
        )
        try:
            _run(
                _compose("up", "-d", "database", "queue", "app", "nginx"),
                env=environment,
            )
            base_url = _base_url(environment)
            _wait_for_stack(base_url)
            _compose_exec(environment, E2E_USER_SEEDER)
            seed_output = _compose_exec(environment, PC_E2E_SEEDER)
            rom_id = int(json.loads(seed_output.strip().splitlines()[-1])["rom_id"])
            _run_browser(base_url=base_url, fixture_root=fixture_root, rom_id=rom_id)
            after_digest = fixture_tree_digest(fixture_root)
            if after_digest != before_digest:
                raise RuntimeError("PC fixture changed during the browser flow")
            if fixture_tree_digest(SOURCE_LIBRARY_ROOT) != source_digest:
                raise RuntimeError(
                    "checked-in PC fixture changed during the browser flow"
                )
            return {
                "base_url": base_url,
                "rom_id": rom_id,
                "fixture_digest": after_digest,
            }
        finally:
            _cleanup(environment)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(run(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
