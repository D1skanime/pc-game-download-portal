#!/usr/bin/env python3
"""Run connected localized-description acceptance on token-owned resources."""

import argparse
import json

import phase34
import phase36_description_probe as probe
from phase34_evidence import read_json
from phase34_faults import build_browser, remove_image, start_process, wait_http
from phase35_browser import browser_config as previous_config
from phase35_incremental_scan_probe import observations
from phase36_description_fixture import prepare


def browser_config(url="http://127.0.0.1:3345"):
    config = previous_config(url)
    config["testMatch"] = "phase36-descriptions.spec.ts"
    config["timeout"] = 900000
    return config


def execute(dialect, quality=False):
    probe.preflight()
    phase34.prepare = prepare
    phase34.COMPOSE = (
        phase34.REPO
        / ".planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-uat-compose.yml"
    )
    run = phase34.Run(dialect)
    run.env["P33_GAMES"] = str(run.root / "Games")
    run.env["PLAYMATCH_API_URL"] = "http://127.0.0.1:3346"
    image = None
    result = {
        "phase": 36,
        "kind": "quality" if quality else "browser",
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
        probe.call(run, "setup", "setup")
        if quality:
            from phase36_quality import execute_quality

            result["checks"] = execute_quality(run)
        else:
            probe.stage(run, "cold")
            probe.call(run, "seed", "browser-seed")
            probe.stage(run, "adopt", action="adopt")
            target = run.root / "checkout/frontend/playwright.phase36.config.ts"
            target.write_text("export default " + json.dumps(browser_config()) + ";\n")
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
            wait_http(run, "http://127.0.0.1:3345/", seconds=90)
            run.exec(
                [
                    "npx",
                    "--no-install",
                    "playwright",
                    "test",
                    "--config",
                    "playwright.phase36.config.ts",
                ],
                frontend=True,
                timeout=1200,
                extra={
                    "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
                    "PHASE34_BASE_URL": "http://127.0.0.1:3345",
                    "PHASE34_TEST_PASSWORD": run.token,
                    "PHASE34_TEST_USERNAME": "phase35-admin",
                },
            )
            result["browser"] = read_json(run.evidence / "browser.json")
            if result["browser"].get("passed") is not True:
                raise RuntimeError("connected browser scenarios incomplete")
        result["wire_requests"] = [
            row for row in observations(run) if row["kind"] == "provider_http"
        ]
        result["observed_worker"] = any(
            row["kind"] == "description_worker_boot" for row in observations(run)
        )
        result["source_hashes"] = read_json(run.evidence / "code-before.json")
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
            result["cleanup"] = read_json(run.evidence / "cleanup.json")
            (run.evidence / "phase36-browser-result.json").write_text(
                json.dumps(result, indent=2)
            )
            from phase36_receipts import sanitize

            sanitize(run.evidence, run.token)
            print("PHASE36_BROWSER_EVIDENCE", run.evidence, flush=True)
    return run.evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dialect", choices=("mariadb", "postgresql"), default="mariadb"
    )
    parser.add_argument("--receipt-index")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify", action="store_true")
    group.add_argument("--quality", action="store_true")
    group.add_argument("--assert-receipts", action="store_true")
    args = parser.parse_args()
    if args.assert_receipts:
        from phase36_receipts import assert_receipts

        probe.preflight()
        assert_receipts(args.receipt_index)
    else:
        execute(args.dialect, args.quality)


if __name__ == "__main__":
    main()
