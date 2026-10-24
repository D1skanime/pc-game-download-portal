"""Actual isolated application/browser proof using existing lifecycle fixtures."""

import json
import shutil

from ci_target import CIRun
from phase34_faults import build_browser, remove_image, start_application
from phase35_browser import browser_config
from phase38_authority import PHASE, protected


def execute(gate, dialect, identity):
    if gate != "browser":
        raise RuntimeError("invalid browser gate")
    before = protected()
    run = CIRun(dialect)
    image = None
    receipt = {"identity": identity, "gate": gate, "passed": False}
    try:
        image = build_browser(run)
        run.image = image
        run.start()
        receipt["source_code_sha256"] = json.loads(
            (run.evidence / "code-before.json").read_text()
        )["sha256"]
        start_application(run)
        config = browser_config()
        config["testMatch"] = [
            "setup-recovery.spec.ts",
            "scan-lifecycle.spec.ts",
            "zockarchive-brand.spec.ts",
        ]
        config["timeout"] = 240000
        config["use"]["trace"] = "off"
        target = run.root / "checkout/frontend/playwright.phase38.config.ts"
        target.write_text("export default " + json.dumps(config) + ";\n")
        run.exec(
            [
                "npx",
                "--no-install",
                "playwright",
                "test",
                "--config",
                "playwright.phase38.config.ts",
            ],
            frontend=True,
            timeout=1200,
            extra={
                "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
                "PHASE34_BASE_URL": "http://127.0.0.1:3345",
                "PHASE34_TEST_PASSWORD": run.token,
                "PHASE34_TEST_USERNAME": "phase34-admin",
                "PHASE34_EVIDENCE_DIR": "/phase34/evidence",
            },
        )
        report = json.loads((run.evidence / "browser-report.json").read_text())
        if report["stats"]["unexpected"] or not report["stats"]["expected"]:
            raise RuntimeError("actual browser cases incomplete")
        receipt["stats"] = report["stats"]
        receipt["passed"] = True
    finally:
        try:
            run.close()
            if image:
                remove_image(run, image)
        finally:
            receipt["protected_unchanged"] = protected() == before
            cleanup = run.evidence / "cleanup.json"
            receipt["cleanup"] = (
                json.loads(cleanup.read_text()) if cleanup.exists() else None
            )
            destination = PHASE / "evidence/browser" / run.project
            destination.mkdir(parents=True, exist_ok=True)
            for source in run.evidence.iterdir():
                if source.is_file() and source.name != "code-before.json":
                    shutil.copy2(source, destination / source.name)
            (destination / "result.json").write_text(json.dumps(receipt, indent=2))
            print("PHASE38_BROWSER_EVIDENCE", destination, flush=True)
    return receipt
