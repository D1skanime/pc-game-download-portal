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
COMPOSE_PROJECT_NAME=pgdp-phase33-browser-$(date +%s)-$RANDOM
EVIDENCE_DIR="$PWD/.planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/evidence/$COMPOSE_PROJECT_NAME"
PHASE33_PORT="$(shuf -i 18080-18999 -n 1)"
mkdir -p "$UAT_ROOT/fixture/Games/pc" "$UAT_ROOT/artifacts" "$EVIDENCE_DIR"
printf 'phase33 synthetic pc fixture
' > "$UAT_ROOT/fixture/Games/pc/Phase33-Synthetic.exe"
python3 "$UAT_ROOT/manifest.py" "$UAT_ROOT/fixture/Games" > "$UAT_ROOT/artifacts/before.json"
docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f docker-compose.override.yml -f "$UAT_ROOT/phase33.override.yml" --env-file "$UAT_ROOT/phase33.env" config > "$UAT_ROOT/artifacts/compose-config.yml"
docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f docker-compose.override.yml -f "$UAT_ROOT/phase33.override.yml" --env-file "$UAT_ROOT/phase33.env" up -d
PHASE33_PORT="$(docker compose -p "$COMPOSE_PROJECT_NAME" port romm-dev 3000 | awk -F: '{print $NF}')"
docker compose -p "$COMPOSE_PROJECT_NAME" ps -a > "$UAT_ROOT/artifacts/compose-ps.txt"
docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f docker-compose.override.yml -f "$UAT_ROOT/phase33.override.yml" --env-file "$UAT_ROOT/phase33.env" run --rm --no-deps -v "$UAT_ROOT:/uat" -e E2E_BASE_URL="http://host.docker.internal:$PHASE33_PORT" romm-dev bash -lc 'cd /app/frontend && npx playwright test /uat/phase33-first-run.spec.ts --config=playwright.config.ts --project=chromium --trace=on --reporter=line,junit=/uat/artifacts/playwright.xml' > "$UAT_ROOT/artifacts/playwright-command.log" 2>&1
python3 "$UAT_ROOT/manifest.py" "$UAT_ROOT/fixture/Games" > "$UAT_ROOT/artifacts/after.json"
cmp "$UAT_ROOT/artifacts/before.json" "$UAT_ROOT/artifacts/after.json"
docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f docker-compose.override.yml -f "$UAT_ROOT/phase33.override.yml" --env-file "$UAT_ROOT/phase33.env" down --volumes --remove-orphans > "$UAT_ROOT/artifacts/compose-cleanup.txt" 2>&1
cp -a "$UAT_ROOT/artifacts/." "$EVIDENCE_DIR/"
test -s "$EVIDENCE_DIR/playwright.xml"
test -s "$EVIDENCE_DIR/before.json"
test -s "$EVIDENCE_DIR/after.json"
test -s "$EVIDENCE_DIR/compose-cleanup.txt"
test -s "$EVIDENCE_DIR/compose-ps.txt"
# Leave UAT_ROOT until the structured validator passes; retain EVIDENCE_DIR.
~~~

The existing disposable Compose definition is selected by the implementation environment, not a production stack or live service. The harness fails closed if project name, target volume labels, source mount, or port is not unique and disposable. Cleanup saves output, uses only the exact project ID, and removes only UAT_ROOT after the retained-evidence validator passes. [VERIFIED: Phase 22 UAT, Phase 27 UAT, Phase 32 validation patterns]

Plan 04 Task 2 must also create phase33.env, phase33.override.yml, and state.json, verify the rendered override has the synthetic Games bind read-only and no container_name entries, and leave UAT_ROOT until the state-backed Task 3 validator passes. The temporary phase33-first-run.spec.ts must use the existing Playwright config and attach concrete files for each matrix entry:

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
{"automated_gates":[{"id":"auto-naming","status":"PASS","command":"...","exit_code":0,"artifacts":["<EVIDENCE_DIR>/naming.txt"],"result":"..."}],"scenarios":[{"id":"fresh-ordering","status":"PASS","command":"...","exit_code":0,"artifacts":["<EVIDENCE_DIR>/ordering.png"],"result":"..."},{"id":"input-gamepad","status":"BLOCKED","command":"...","exit_code":127,"artifacts":[],"result":"...","blocked_reason":"..."}]}
<!-- phase33-evidence-manifest:end -->
~~~

The allowed automated gate IDs are exactly: auto-naming, auto-frontend, auto-backend, auto-repository. The allowed browser scenario IDs are exactly: fresh-ordering, exact-games-pc, reload-persistence, readonly-source, theme-dark, theme-light, layout-desktop, layout-narrow, input-mouse, input-touch, input-keyboard, input-gamepad, cleanup.

Every entry in both arrays requires id, status, command, exit_code, artifacts, and result. PASS requires exit code 0, a non-empty executed command, a non-empty artifact array whose files exist under retained EVIDENCE_DIR, and a result. BLOCKED requires the attempted command and a non-empty blocked_reason; any listed artifact must also exist under retained EVIDENCE_DIR. Duplicate, missing, or extra IDs fail validation. Artifact references may not point to /uat or UAT_ROOT. Keyword presence in prose does not satisfy the gate. Remove UAT_ROOT only after this validator passes; EVIDENCE_DIR and its cleanup output remain retained.

Run the structured validator from the canonical checkout:

~~~bash
python3 - .planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-UAT.md "$EVIDENCE_DIR" "$UAT_ROOT" <<'PY'
import json, pathlib, sys
text = pathlib.Path(sys.argv[1]).read_text()
evidence = pathlib.Path(sys.argv[2]).resolve()
uat_root = pathlib.Path(sys.argv[3]).resolve()
start = "<!-- phase33-evidence-manifest:start -->"
end = "<!-- phase33-evidence-manifest:end -->"
if text.count(start) != 1 or text.count(end) != 1:
    raise SystemExit("missing or duplicate structured evidence markers")
data = json.loads(text.split(start, 1)[1].split(end, 1)[0].strip())
required_gates = {"auto-naming", "auto-frontend", "auto-backend", "auto-repository"}
required_scenarios = {"fresh-ordering", "exact-games-pc", "reload-persistence", "readonly-source", "theme-dark", "theme-light", "layout-desktop", "layout-narrow", "input-mouse", "input-touch", "input-keyboard", "input-gamepad", "cleanup"}
def check(entries, required, label):
    if not isinstance(entries, list) or len(entries) != len(required) or {e.get("id") for e in entries} != required:
        raise SystemExit(label + " IDs are missing, duplicated, or unexpected")
    for e in entries:
        if e.get("status") not in {"PASS", "BLOCKED"} or not isinstance(e.get("command"), str) or not e["command"].strip():
            raise SystemExit(e.get("id", label) + ": missing executed command or invalid status")
        artifacts = e.get("artifacts")
        if not isinstance(artifacts, list):
            raise SystemExit(e["id"] + ": artifacts must be an array")
        for raw in artifacts:
            path = pathlib.Path(raw).resolve()
            if evidence not in path.parents or uat_root in path.parents or not path.is_file():
                raise SystemExit(e["id"] + ": artifact is not a retained existing file")
        if e["status"] == "PASS" and (e.get("exit_code") != 0 or not artifacts or not e.get("result")):
            raise SystemExit(e["id"] + ": PASS requires exit_code 0, artifacts, and result")
        if e["status"] == "BLOCKED" and not isinstance(e.get("blocked_reason"), str):
            raise SystemExit(e["id"] + ": BLOCKED requires blocked_reason")
check(data.get("automated_gates"), required_gates, "automated gate")
check(data.get("scenarios"), required_scenarios, "browser scenario")
print("structured Phase 33 UAT evidence: PASS")
PY
test -d "$EVIDENCE_DIR"
rm -rf -- "$UAT_ROOT"
~~~
