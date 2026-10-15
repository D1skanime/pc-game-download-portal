# Phase 33 Validation Architecture

## Scope and authority

Phase 33 proves that a fresh installation enters the existing PC/Windows mapping workflow before the empty-library screen. The canonical persisted representation is Storage root Games, mapping relative_path pc, effective source target Games/pc, and the canonical Windows platform returned by the server. Only authenticated setup completion may call mutating storage bootstrap. Home and Scan readiness are read-only and the backend scan command builder remains authoritative and fail-closed. [VERIFIED: Phase 33 research and plans]

## Automated command matrix

| Gate | Command | Owner |
|---|---|---|
| Naming and deployment render | bash scripts/verify-pgdp-naming.sh and docker compose --env-file examples/portainer.env.example -f examples/portainer-stack.yml config | Plan 04 |
| Storage bootstrap and exact pair | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/backend && uv run pytest tests/endpoints/storage/test_legacy_bootstrap_paths.py tests/endpoints/test_storage.py -q' | Plan 01 |
| Readiness helper | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/frontend && npm run test -- src/services/api/storage.test.ts' | Plan 01 |
| Setup handoff | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/frontend && npm run test -- src/v2/views/Auth/Setup.test.ts' | Plan 02 |
| Empty Home and Scan gates | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/frontend && npm run test -- src/v2/views/Home.test.ts src/v2/views/Scan.test.ts' | Plan 03 |
| Frontend integration | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/frontend && npm run typecheck && npm run test' | Plan 04 |
| Backend integration | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/backend && uv run pytest tests --collect-only -q && uv run pytest tests/endpoints/storage/test_legacy_bootstrap_paths.py tests/endpoints/test_storage.py tests/endpoints/sockets/test_scan.py tests/integration/test_mapped_scan.py -q' | Plan 04 |
| Repository hygiene | git diff --check and scoped git status --short from the canonical checkout | Plan 04 |

All project tooling runs in romm-dev. Host Node/npm/uv are not accepted substitutes. [VERIFIED: Phase 32 validation and repository package scripts]

## Disposable browser UAT command and harness

The browser gate uses the existing Playwright dependency, config, fixtures, and reporter from frontend/package.json and frontend/playwright.config.ts. The browser spec is temporary UAT input under a disposable mktemp directory, not product code. [VERIFIED: repository inspection]

Preparation creates a synthetic text fixture and a unique Compose project with empty database/queue volumes, configured root Games, read-only bind mount, and a disposable host port. The exact command sequence is:
The temporary UAT_ROOT/manifest.py helper must be created in the disposable directory from the Phase 22 manifest snippet, and it must emit relative path, type, size, non-access timestamps, and SHA-256 for every fixture entry; it is not a repository or product file.

~~~bash
set -euo pipefail
UAT_ROOT=$(mktemp -d /tmp/pgdp-phase33-browser.XXXXXX)
COMPOSE_PROJECT_NAME=pgdp-phase33-browser-$(date +%s)
PHASE33_PORT="$(shuf -i 18080-18999 -n 1)"
mkdir -p "$UAT_ROOT/fixture/Games/pc" "$UAT_ROOT/artifacts"
printf 'phase33 synthetic pc fixture\n' > "$UAT_ROOT/fixture/Games/pc/Phase33-Synthetic.exe"
printf 'phase33 synthetic manifest\n' > "$UAT_ROOT/fixture/Games/pc/Phase33-Synthetic.txt"
python3 "$UAT_ROOT/manifest.py" "$UAT_ROOT/fixture/Games" > "$UAT_ROOT/artifacts/before.json"
docker compose -p "$COMPOSE_PROJECT_NAME" -f backend/docker-compose.pc-integration-test.yml --env-file "$UAT_ROOT/uat.env" up -d
docker compose -p "$COMPOSE_PROJECT_NAME" ps --format json > "$UAT_ROOT/artifacts/compose-before.json"
docker compose -p "$COMPOSE_PROJECT_NAME" port app 3000
docker compose -p "$COMPOSE_PROJECT_NAME" run --rm --no-deps -v "$UAT_ROOT:/uat" -e E2E_BASE_URL="http://host.docker.internal:$PHASE33_PORT" romm-dev bash -lc 'cd /app/frontend && npx playwright test /uat/phase33-first-run.spec.ts --config=playwright.config.ts --project=chromium --reporter=line,junit=/uat/artifacts/playwright.xml' > "$UAT_ROOT/artifacts/playwright-command.log" 2>&1
python3 "$UAT_ROOT/manifest.py" "$UAT_ROOT/fixture/Games" > "$UAT_ROOT/artifacts/after.json"
cmp "$UAT_ROOT/artifacts/before.json" "$UAT_ROOT/artifacts/after.json"
docker compose -p "$COMPOSE_PROJECT_NAME" ps -a > "$UAT_ROOT/artifacts/compose-after.txt"
docker compose -p "$COMPOSE_PROJECT_NAME" down --volumes --remove-orphans > "$UAT_ROOT/artifacts/cleanup.txt" 2>&1
test -s "$UAT_ROOT/artifacts/playwright.xml"
test -s "$UAT_ROOT/artifacts/before.json"
test -s "$UAT_ROOT/artifacts/after.json"
~~~

The existing disposable Compose definition is selected by the implementation environment, not a production stack or live service. The harness fails closed if project name, target volume labels, source mount, or port is not unique and disposable. Cleanup saves output, uses only the exact project ID, then removes only UAT_ROOT. [VERIFIED: Phase 22 UAT, Phase 27 UAT, Phase 32 validation patterns]

The temporary phase33-first-run.spec.ts must use the existing Playwright config and attach concrete files for each matrix entry:

| Scenario | Required assertions/artifacts |
|---|---|
| fresh-ordering | Mapping route appears before Home/Scan, screenshot and trace |
| exact-games-pc | root Games, relative_path pc, effective Games/pc, screenshot and response artifact |
| reload-persistence | page.reload preserves mapping, screenshot and trace |
| readonly-source | unavailable/unreadable/writable recovery hides Scan, healthy read-only state exposes it, before/after manifests |
| theme-dark, theme-light | golden path at each theme, screenshots and traces |
| layout-desktop, layout-narrow | 1440x900 and 390x844 remain usable, screenshots |
| input-mouse, input-touch | same mapping and scan gating, screenshots/traces |
| input-keyboard | keyboard focus order, visible focus, activation, screenshot/trace |
| input-gamepad | universal input navigation/activation preserves readiness, screenshot/trace or explicit BLOCKED result |
| cleanup | exact project ID, ps -a, cleanup output, no live target |

The spec must assert observable routes, labels/API payloads, state transitions, and artifact attachment. Container health alone is not browser evidence. [VERIFIED: Phase 33 plan and repository Playwright config]

## Sampling cadence

- Per task: focused changed-contract command.
- Per wave: Plan 01 backend/frontend gates, Plan 02 setup tests, Plan 03 Home/Scan tests, and frontend typecheck.
- Phase gate: deployment render/naming, full frontend suite, backend collection/focused integration, disposable browser UAT, and structured evidence validation before verification.
- Browser sampling: v2-dark and v2-light, desktop and narrow, mouse, touch, keyboard, and gamepad. Repeat no-mapping, unhealthy-root, and reload cases once each.

## Wave 0 gaps and closure

| Gap | Closure | Evidence |
|---|---|---|
| Setup view/router test | Plan 02 Task 1 | Setup.test.ts and setup completion route assertion |
| Home empty-state mapping-vs-scan test | Plan 03 Task 1 | Home.test.ts and CTA absence/presence |
| Fresh backend fixture for exact Games/pc + Windows identity + persistence | Plan 01 Task 1 | bootstrap endpoint tests and exact root/path assertions |
| Disposable first-run browser matrix | Plan 04 Task 2 | temporary Playwright spec command plus artifacts |
| Readiness mutates storage during Home/Scan | Plan 01 Task 2 and Plan 03 Task 1 | GET-only API mocks and zero POST assertions |
| Input-modality coverage | Plan 04 Task 2 | Playwright screenshots/traces or explicit blocked entries |

## Structured evidence rules

Task 3 inserts exactly one JSON block into 33-UAT.md:

~~~text
<!-- phase33-evidence-manifest:start -->
{"scenarios":[{"id":"fresh-ordering","status":"PASS","command":"...","exit_code":0,"artifacts":["/tmp/.../ordering.png"],"result":"..."},{"id":"input-gamepad","status":"BLOCKED","command":"...","exit_code":127,"artifacts":[],"result":"...","blocked_reason":"..."}]}
<!-- phase33-evidence-manifest:end -->
~~~

Required IDs are exactly: fresh-ordering, exact-games-pc, reload-persistence, readonly-source, theme-dark, theme-light, layout-desktop, layout-narrow, input-mouse, input-touch, input-keyboard, input-gamepad, cleanup.

Every entry requires status, command, exit_code, artifacts, and result. PASS requires exit code 0 and at least one existing concrete artifact path. BLOCKED requires the attempted command and a non-empty blocked_reason. Duplicate, missing, or extra IDs fail validation. Keyword presence in prose does not satisfy the gate.

Run this validator from the canonical checkout:

~~~bash
python3 - .planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-UAT.md <<'PY'
import json, pathlib, sys
text = pathlib.Path(sys.argv[1]).read_text()
start = "<!-- phase33-evidence-manifest:start -->"
end = "<!-- phase33-evidence-manifest:end -->"
if text.count(start) != 1 or text.count(end) != 1:
    raise SystemExit("missing or duplicate structured evidence markers")
data = json.loads(text.split(start, 1)[1].split(end, 1)[0].strip())
required = {"fresh-ordering", "exact-games-pc", "reload-persistence", "readonly-source", "theme-dark", "theme-light", "layout-desktop", "layout-narrow", "input-mouse", "input-touch", "input-keyboard", "input-gamepad", "cleanup"}
entries = data.get("scenarios")
if not isinstance(entries, list) or len(entries) != len(required) or {e.get("id") for e in entries} != required:
    raise SystemExit("scenario IDs are missing, duplicated, or unexpected")
for entry in entries:
    if not isinstance(entry.get("command"), str) or not entry["command"].strip():
        raise SystemExit(f"{entry.get('id')}: missing executed command")
    if entry.get("status") not in {"PASS", "BLOCKED"}:
        raise SystemExit(f"{entry['id']}: invalid status")
    if entry["status"] == "PASS":
        if entry.get("exit_code") != 0:
            raise SystemExit(f"{entry['id']}: PASS requires exit_code 0")
        artifacts = entry.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts or any(not pathlib.Path(p).is_file() for p in artifacts):
            raise SystemExit(f"{entry['id']}: PASS requires existing concrete artifacts")
    elif not isinstance(entry.get("blocked_reason"), str) or not entry["blocked_reason"].strip():
        raise SystemExit(f"{entry['id']}: BLOCKED requires blocked_reason")
print(f"validated {len(entries)} structured Phase 33 UAT scenarios")
PY
~~~

The validator is structural and artifact-backed. [VERIFIED: requested checker blocker]

## Evidence rules

Use disposable state only. Record exact Compose project ID, container image, synthetic credentials policy, fixture manifest before/after, browser URL, viewport/theme/input modality, screenshots or traces, test output, structured scenario command/exit code, and cleanup result. Do not inspect or alter live NAS mounts, Team4s, existing volumes, or production credentials.
