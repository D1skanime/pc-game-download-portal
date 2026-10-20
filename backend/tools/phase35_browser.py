#!/usr/bin/env python3
"""Actual isolated Phase 35 browser and final quality gates."""

import argparse
import json

import phase34
import phase35_incremental_scan_probe as probe
from phase34_faults import build_browser, remove_image, start_process, wait_http
from phase35_browser_receipts import assert_receipts, retain, validate_browser
from phase35_incremental_scan_fixture import prepare as fixture_prepare


def browser_config(url="http://127.0.0.1:3345", presentation=False):
    if url != "http://127.0.0.1:3345":
        raise RuntimeError("browser target must be isolated loopback")
    return {
        "testDir": "./e2e",
        "testMatch": (
            "phase35-presentation-smoke.spec.ts"
            if presentation
            else "phase35-incremental-scan.spec.ts"
        ),
        "workers": 1,
        "retries": 0,
        "timeout": 600000,
        "expect": {"timeout": 20000},
        "outputDir": "/phase34/evidence/browser-results",
        "reporter": [
            ["line"],
            ["json", {"outputFile": "/phase34/evidence/browser-report.json"}],
        ],
        "use": {
            "baseURL": url,
            "trace": "on",
            "serviceWorkers": "block",
            "hasTouch": True,
            "actionTimeout": 20000,
            "navigationTimeout": 60000,
        },
        "projects": [{"name": "chromium", "use": {"browserName": "chromium"}}],
    }


def prepare(root, repo):
    games, checkout = fixture_prepare(root, repo)
    # Real item paging must exceed the server's fixed 100-item cap.
    for index in range(46):
        folder = root / "fixture/Games/pc" / ("Paged.Unknown." + str(index)) / "Base"
        folder.mkdir(parents=True)
        (folder / "game.bin").write_bytes(("synthetic paged " + str(index)).encode())
    return games, checkout


def execute(dialect, quality=False, presentation=False):
    probe.preflight()
    phase34.prepare = fixture_prepare if presentation else prepare
    phase34.COMPOSE = (
        phase34.REPO
        / ".planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-uat-compose.yml"
    )
    run = phase34.Run(dialect)
    run.env["P33_GAMES"] = str(run.root / "fixture/Games")
    image = None
    result = {
        "kind": (
            "presentation-smoke"
            if presentation
            else ("quality" if quality else "browser")
        ),
        "debug_only": presentation,
        "dialect": dialect,
        "passed": False,
    }
    try:
        if not quality:
            image = build_browser(run)
            run.image = image
        run.start()
        (run.evidence / "observations.jsonl").touch()
        probe.start(run, initialize=True)
        if quality:
            from phase35_browser_quality import execute_quality

            result["checks"] = execute_quality(run)
        else:
            probe.call(run, "setup", "setup")
            target = run.root / "checkout/frontend/playwright.phase35.config.ts"
            target.write_text(
                "export default "
                + json.dumps(browser_config(presentation=presentation))
                + ";\n"
            )
            start_process(
                run,
                "vite",
                [
                    "/app/frontend/node_modules/.bin/vite",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "3345",
                    "--strictPort",
                ],
                extra={
                    "DEV_PORT": "3344",
                    "DEV_HTTPS": "false",
                    "CHOKIDAR_USEPOLLING": "true",
                },
            )
            wait_http(run, "http://127.0.0.1:3345/", seconds=60)
            run.exec(
                [
                    "npx",
                    "--no-install",
                    "playwright",
                    "test",
                    "--config",
                    "playwright.phase35.config.ts",
                ],
                frontend=True,
                timeout=900,
                extra={
                    "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
                    "PHASE34_BASE_URL": "http://127.0.0.1:3345",
                    "PHASE34_TEST_PASSWORD": run.token,
                    "PHASE34_TEST_USERNAME": "phase35-admin",
                },
            )
            if presentation:
                result["smoke"] = json.loads(
                    (run.evidence / "presentation-smoke.json").read_text()
                )
                if result["smoke"].get("passed") is not True:
                    raise RuntimeError("presentation smoke failed")
            else:
                result["browser"] = json.loads(
                    (run.evidence / "browser.json").read_text()
                )
                validate_browser(result["browser"])
        result["passed"] = True
    except BaseException as error:
        result["error"] = str(error)
        raise
    finally:
        try:
            run.close()
            if image:
                remove_image(run, image)
        finally:
            retain(run, result)
    return run.evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dialect", choices=("mariadb", "postgresql"), default="mariadb"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify", action="store_true")
    group.add_argument("--quality", action="store_true")
    group.add_argument("--presentation-smoke", action="store_true")
    group.add_argument("--assert-receipts", action="store_true")
    args = parser.parse_args()
    if args.assert_receipts:
        probe.preflight()
        assert_receipts()
    else:
        print(
            "PHASE35_BROWSER_EVIDENCE",
            execute(args.dialect, args.quality, args.presentation_smoke),
            flush=True,
        )


if __name__ == "__main__":
    main()
