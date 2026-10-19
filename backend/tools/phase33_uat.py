#!/usr/bin/env python3
"""Run Phase 33 acceptance against generated, isolated synthetic resources."""

import argparse
import hashlib
import json
import shutil
import subprocess  # nosec B404, fixed local validator argv
import tempfile
import threading
import time
import xml.etree.ElementTree as ET  # nosec B405, repository-owned pytest receipt
from pathlib import Path
from typing import Any

import phase34
from phase34_faults import build_browser, remove_image, start_application
from phase34_fixtures import (
    backend_command,
)
from phase34_fixtures import prepare as original_prepare
from phase34_fixtures import (
    source_manifest,
)

REPO = Path(__file__).resolve().parents[2]
PHASE = (
    REPO
    / ".planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc"
)


def prepare(root, repo):
    games, checkout = original_prepare(root, repo)
    shutil.rmtree(games)
    fixture = root / "fixture/Games"
    for name in ("pc", "My Games"):
        folder = fixture / name
        folder.mkdir(parents=True)
        (folder / ("Synthetic.exe" if name == "pc" else "Synthetic.sfc")).write_bytes(
            b"phase33 synthetic fixture\n"
        )
    for name in ("Belmonts.Curse", "Lords.of.Shadow2"):
        folder = fixture / "pc/Castlevania" / name
        folder.mkdir(parents=True)
        for part in ("01", "02"):
            (folder / ("game.part" + part + ".rar")).write_bytes(
                b"synthetic split archive part"
            )
    games.symlink_to(fixture, target_is_directory=True)
    return games, checkout


def watch_fixture_additions(run, stop, errors):
    """Add only named synthetic fixtures between immutable application segments."""
    segments = []
    before_file = "before.json"
    for stage, name in (
        ("normal", "Newly.Added.Game"),
        ("scheduled", "Scheduled.New.Game"),
    ):
        request = run.evidence / ("add-" + stage + "-child.request")
        while not request.exists():
            if stop.wait(0.1):
                return
        observed = source_manifest(run.root / "Games")
        after_file = stage + "-source-before-addition.json"
        (run.evidence / after_file).write_text(json.dumps(observed, indent=2))
        if observed != run.before:
            errors.append("application mutated synthetic Games before " + stage)
            return
        folder = run.root / "fixture/Games/pc/Castlevania" / name
        if folder.exists() or folder.is_symlink():
            errors.append("synthetic addition target already exists")
            return
        folder.mkdir()
        for part in ("01", "02"):
            (folder / ("fixture.part" + part + ".rar")).write_bytes(
                b"synthetic addition outside application"
            )
        run.before = source_manifest(run.root / "Games")
        next_before = stage + "-source-after-addition.json"
        (run.evidence / next_before).write_text(json.dumps(run.before, indent=2))
        segments.append(
            {
                "before": before_file,
                "after": after_file,
                "added_fixture": "pc/Castlevania/" + name,
                "next_before": next_before,
            }
        )
        (run.evidence / "fixture-segments.json").write_text(
            json.dumps(segments, indent=2)
        )
        (run.evidence / "source-before.json").write_text(
            json.dumps(run.before, indent=2)
        )
        before_file = next_before
        (run.evidence / ("add-" + stage + "-child.ready")).write_text(
            "fixture addition complete"
        )
    while not stop.wait(0.1):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-receipt", type=Path)
    parser.add_argument("--frontend-receipt", type=Path)
    args = parser.parse_args()
    phase34.host_preflight()
    phase34.prepare = prepare
    phase34.COMPOSE = PHASE / "33-uat-compose.yml"
    run = phase34.Run()
    run.env["P33_GAMES"] = str(run.root / "fixture/Games")
    state: dict[str, Any] = {
        "compose_project": run.project,
        "uat_root": str(run.root),
        "compose_file": str(phase34.COMPOSE),
        "rendered_compose": str(run.evidence / "rendered.json"),
        "evidence_dir": str(run.evidence),
        "browser_exit": None,
        "backend_exit": None,
        "teardown_exit": None,
        "browser_command": "cd frontend && npx --no-install playwright test phase33.spec.ts --config playwright.phase33.config.ts --project=chromium --reporter=line",
    }
    image = None
    error = None
    fixture_stop = threading.Event()
    fixture_errors: list[str] = []
    fixture_thread = None
    try:
        image = build_browser(run)
        run.image = image
        run.start()
        rendered = run.compose("config", "--format", "json").stdout
        # Credentials and generated labels are not acceptance evidence.
        data = json.loads(rendered)
        for service in data["services"].values():
            service.pop("environment", None)
            service.pop("command", None)
            service.pop("labels", None)
        (run.evidence / "rendered.json").write_text(json.dumps(data, indent=2))
        state["disposable_volume"] = run.project + "_owned"
        (run.evidence / "before.json").write_text(
            json.dumps(source_manifest(run.root / "Games"), indent=2)
        )
        if args.backend_receipt:
            receipt = args.backend_receipt.resolve()
            if not receipt.is_relative_to(PHASE / "evidence"):
                raise RuntimeError("backend receipt must be retained locally")
            report = ET.parse(
                receipt
            ).getroot()  # nosec B314, validated retained pytest XML
            suites = [report] if report.tag == "testsuite" else list(report)
            if sum(int(s.get("tests", "0")) for s in suites) < 21 or any(
                int(s.get(k, "0"))
                for s in suites
                for k in ("failures", "errors", "skipped")
            ):
                raise RuntimeError("backend receipt is not a full passing focused run")
            shutil.copy2(receipt, run.evidence / "phase33-backend.xml")
            state["backend_exit"] = 0
            state["backend_receipt"] = {
                "source": str(receipt),
                "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
            }
        else:
            result = run.exec(
                backend_command(
                    [
                        "tests/endpoints/test_setup.py",
                        "tests/handler/test_setup_folder_handler.py",
                        "tests/endpoints/storage/test_legacy_bootstrap_paths.py",
                        "tests/integration/test_setup_folder_assignments.py",
                        "tests/integration/test_mapped_scan.py",
                        "-q",
                    ],
                    name="phase33-backend",
                ),
                timeout=600,
                check=False,
            )
            state["backend_exit"] = result.returncode
            if result.returncode:
                raise RuntimeError("focused backend gate failed")
        target = run.root / "checkout/frontend"
        shutil.copy2(PHASE / "33-browser-uat.spec.ts", target / "phase33.spec.ts")
        config = {
            "testDir": ".",
            "testMatch": "phase33.spec.ts",
            "workers": 1,
            "retries": 0,
            "timeout": 240000,
            "expect": {"timeout": 20000},
            "outputDir": "/phase34/evidence/browser-results",
            "reporter": [
                ["json", {"outputFile": "/phase34/evidence/browser-report.json"}],
                ["line"],
            ],
            "projects": [{"name": "chromium", "use": {"browserName": "chromium"}}],
            "use": {
                "baseURL": "http://127.0.0.1:3345",
                "trace": "on",
                "serviceWorkers": "block",
                "hasTouch": True,
            },
        }
        (target / "playwright.phase33.config.ts").write_text(
            "export default " + json.dumps(config) + ";\n"
        )
        start_application(run)
        fixture_thread = threading.Thread(
            target=watch_fixture_additions,
            args=(run, fixture_stop, fixture_errors),
            daemon=True,
        )
        fixture_thread.start()
        result = run.exec(
            [
                "npx",
                "--no-install",
                "playwright",
                "test",
                "phase33.spec.ts",
                "--config",
                "playwright.phase33.config.ts",
                "--project=chromium",
                "--reporter=line",
            ],
            frontend=True,
            extra={
                "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
                "PHASE34_TEST_PASSWORD": run.token,
            },
            timeout=600,
            check=False,
        )
        fixture_stop.set()
        fixture_thread.join(timeout=2)
        if fixture_errors:
            raise RuntimeError(fixture_errors[0])
        state["browser_exit"] = result.returncode
        if result.returncode:
            raise RuntimeError("browser acceptance failed")
        if args.frontend_receipt:
            receipt = args.frontend_receipt.resolve()
            if not receipt.is_relative_to(PHASE / "evidence"):
                raise RuntimeError("frontend receipt must be retained locally")
            quality_deadline = time.monotonic() + 360
            while (
                not receipt.is_file() or not (receipt.parent / "cleanup.json").is_file()
            ):
                if time.monotonic() >= quality_deadline:
                    raise RuntimeError(
                        "matching final frontend quality receipt deadline"
                    )
                time.sleep(0.2)
            proof = json.loads(receipt.read_text())
            command_rows = json.loads((receipt.parent / "commands.json").read_text())
            cleanup = json.loads((receipt.parent / "cleanup.json").read_text())
            report = ET.parse(
                receipt.parent / "frontend.xml"
            ).getroot()  # nosec B314, retained generated pytest-style XML
            suites = [report] if report.tag == "testsuite" else list(report)
            if (
                not command_rows
                or any(row["exit"] for row in command_rows)
                or cleanup.get("clean") is not True
            ):
                raise RuntimeError("frontend proof contains failed commands or cleanup")
            if sum(int(s.get("tests", "0")) for s in suites) < 1000 or any(
                int(s.get(k, "0"))
                for s in suites
                for k in ("failures", "errors", "skipped")
            ):
                raise RuntimeError(
                    "frontend proof does not contain the full passing test suite"
                )
            prior = json.loads((receipt.parent / "code-before.json").read_text())
            current = json.loads((run.evidence / "code-before.json").read_text())
            prior_frontend = {
                k: v for k, v in prior["files"].items() if k.startswith("frontend/")
            }
            current_frontend = {
                k: v for k, v in current["files"].items() if k.startswith("frontend/")
            }
            if (
                proof.get("passed") is not True
                or not prior_frontend
                or prior_frontend != current_frontend
            ):
                raise RuntimeError(
                    "frontend receipt does not prove the current frontend source"
                )
            state["frontend_exit"] = 0
            state["frontend_receipt"] = {
                "source": str(receipt),
                "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
            }
        else:
            quality = run.exec(
                [
                    "bash",
                    "-c",
                    "npm run typecheck && npm run test -- --run && npm run build",
                ],
                frontend=True,
                timeout=900,
                check=False,
            )
            state["frontend_exit"] = quality.returncode
            if quality.returncode:
                raise RuntimeError("latest frontend validation failed")
        (run.evidence / "after.json").write_text(
            json.dumps(source_manifest(run.root / "Games"), indent=2)
        )
        (PHASE / "state.json").write_text(json.dumps(state, indent=2) + "\n")
        run.command(
            [
                "python3",
                str(PHASE / "33-evidence-validate.py"),
                "--state",
                str(PHASE / "state.json"),
            ]
        )
    except BaseException as exc:
        error = exc
    finally:
        fixture_stop.set()
        if fixture_thread:
            fixture_thread.join(timeout=2)
        try:
            run.close()
            if image:
                remove_image(run, image)
            state["teardown_exit"] = 0
        except BaseException as exc:
            state["teardown_exit"] = 1
            error = error or exc
        archive = PHASE / "evidence" / run.project
        shutil.copytree(run.evidence, archive)
        state["evidence_dir"] = str(archive)
        state["rendered_compose"] = str(archive / "rendered.json")
        state["original_error"] = str(error) if error else None
        if (
            state["teardown_exit"] == 0
            and run.root.parent == Path(tempfile.gettempdir())
            and run.root.name.startswith(run.project + "-")
        ):
            shutil.rmtree(run.root)
        state["uat_root_removed"] = not run.root.exists()
        (PHASE / "state.json").write_text(json.dumps(state, indent=2) + "\n")
        (archive / "state.json").write_text(json.dumps(state, indent=2) + "\n")
    if error:
        raise error
    # trunk-ignore(bandit/B603): Fixed local validator argv in verified repository.
    run_result = subprocess.run(  # nosec B603,B607, fixed repository validator argv
        [
            "python3",
            str(PHASE / "33-evidence-validate.py"),
            "--state",
            str(PHASE / "state.json"),
            "--assert-cleanup",
        ],
        check=False,
    )
    return run_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
