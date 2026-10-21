"""Exact isolated frontend schema, test, build and locale quality commands."""

import time

from phase34_fixtures import frontend_command
from phase35_contracts import GENERATED, confirm_run, generated_manifest


def execute_quality(run):
    confirm_run(run)
    baseline = generated_manifest(run.root / "checkout" / GENERATED)
    checks = []
    for argv in (
        ["npm", "run", "generate"],
        ["npm", "run", "typecheck"],
        frontend_command([]),
        ["npm", "run", "build"],
        ["python3", "src/locales/check_i18n_locales.py"],
        ["python3", "src/locales/check_i18n_sorted.py"],
        ["npm", "run", "v2:maintainability"],
    ):
        start = time.monotonic()
        result = run.exec(argv, frontend=True, timeout=900)
        checks.append(
            {
                "command": argv,
                "exit": result.returncode,
                "seconds": round(time.monotonic() - start, 3),
            }
        )
        print("PASS quality", argv, checks[-1]["seconds"], flush=True)
        if (
            argv == ["npm", "run", "generate"]
            and generated_manifest(run.root / "checkout" / GENERATED) != baseline
        ):
            raise RuntimeError("generated API contracts drift from final source")
    return checks
