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
| Trunk format/check | trunk fmt --all --ci && trunk check | Plan 04; required gate auto-trunk |
| Frontend production build | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/frontend && npm run build' | Plan 04; required gate auto-frontend-build |
| Repository hygiene | git diff --check and scoped git status --short from the canonical checkout | Plan 04 |

All project tooling runs in romm-dev. Host Node/npm/uv are not accepted substitutes. [VERIFIED: Phase 32 validation and repository package scripts]

## Disposable browser UAT command and harness

The browser gate uses the existing Playwright dependency and reporter from frontend/package.json, but creates dedicated temporary phase33-playwright.config.ts and phase33-first-run.spec.ts. The dedicated config has one chromium project and no auth.setup import/project/dependency or storageState; the spec explicitly performs first-admin setup against the empty database before asserting mapping. The browser spec is temporary UAT input under a disposable mktemp directory, not product code. [VERIFIED: repository inspection]

Preparation creates a synthetic text fixture and a unique Compose project with empty database/queue volumes, configured root Games, read-only bind mount, and two distinct probed disposable host ports. The wrapper performs Linux/canonical-root/branch/remote/planning-state preflight first, then creates manifest.py, phase33.env, and phase33.override.yml before any command that references them, installs its EXIT trap before Compose, and sets VALIDATED_PROJECT before up so cleanup runs on every later failure. The exact command sequence is:
The temporary UAT_ROOT/manifest.py helper must be created in the disposable directory from the Phase 22 manifest snippet, and it must emit relative path, type, size, non-access timestamps, and SHA-256 for every fixture entry; it is not a repository or product file.

~~~bash
set -euo pipefail
test "$(uname -s)" = "Linux"
REPO_ROOT="$(git rev-parse --show-toplevel)"
test "$REPO_ROOT" = "/home/d1sk/pc-game-download-portal"
test -n "$(git -C "$REPO_ROOT" branch --show-current)"
git -C "$REPO_ROOT" remote get-url origin >/dev/null
test -f "$REPO_ROOT/.planning/ROADMAP.md" && test -f "$REPO_ROOT/.planning/STATE.md" && test -d "$REPO_ROOT/.planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc"
cd "$REPO_ROOT"
UAT_ROOT=$(mktemp -d /tmp/pgdp-phase33-browser.XXXXXX)
COMPOSE_PROJECT_NAME=pgdp-phase33-browser-$(date +%s)-$RANDOM
EVIDENCE_DIR="$PWD/.planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/evidence/$COMPOSE_PROJECT_NAME"
mkdir -p "$UAT_ROOT/fixture/Games/pc" "$UAT_ROOT/artifacts" "$EVIDENCE_DIR"
: > "$UAT_ROOT/manifest.py"
: > "$UAT_ROOT/phase33.env"
: > "$UAT_ROOT/phase33.override.yml"
VALIDATED_PROJECT=""
CLEANUP_DONE=0
cleanup() { set +e; rc=0; if [ "$CLEANUP_DONE" -eq 0 ] && [ -n "$VALIDATED_PROJECT" ] && [ "$COMPOSE_PROJECT_NAME" = "$VALIDATED_PROJECT" ]; then docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f docker-compose.override.yml -f "$UAT_ROOT/phase33.override.yml" --env-file "$UAT_ROOT/phase33.env" down --volumes --remove-orphans > "$UAT_ROOT/artifacts/compose-cleanup.txt" 2>&1; rc="$?"; printf "%s\n" "$rc" > "$UAT_ROOT/artifacts/teardown-status.txt"; CLEANUP_DONE=1; fi; return "$rc"; }
trap cleanup EXIT
pick_free_port() { for attempt in $(seq 1 20); do candidate="$(shuf -i 18080-19999 -n 1)"; if ! ss -Hln "( sport = :$candidate )" 2>/dev/null | grep -q . && ! lsof -nP -iTCP:"$candidate" -sTCP:LISTEN -t 2>/dev/null | grep -q .; then printf "%s" "$candidate"; return 0; fi; done; return 1; }
PHASE33_HTTP_PORT="$(pick_free_port)"; PHASE33_API_PORT="$(pick_free_port)"; [ "$PHASE33_HTTP_PORT" != "$PHASE33_API_PORT" ]
PHASE33_PORT="$PHASE33_HTTP_PORT"
printf "%s\n" "PHASE33_FIXTURE_ROOT=$UAT_ROOT/fixture" "ROMS_FOLDER_NAME=Games" "PHASE33_HTTP_PORT=$PHASE33_HTTP_PORT" "PHASE33_API_PORT=$PHASE33_API_PORT" > "$UAT_ROOT/phase33.env"
printf "%s\n" "services:" "  romm-dev:" "    environment:" "      ROMS_FOLDER_NAME: Games" "    volumes:" "      - $UAT_ROOT/fixture:/app/romm/library:ro" > "$UAT_ROOT/phase33.override.yml"
printf "%s\n" "#!/usr/bin/env python3" "# Phase 22 manifest helper implementation is created here." > "$UAT_ROOT/manifest.py"
printf 'phase33 synthetic pc fixture
' > "$UAT_ROOT/fixture/Games/pc/Phase33-Synthetic.exe"
python3 "$UAT_ROOT/manifest.py" "$UAT_ROOT/fixture/Games" > "$UAT_ROOT/artifacts/before.json"
docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f docker-compose.override.yml -f "$UAT_ROOT/phase33.override.yml" --env-file "$UAT_ROOT/phase33.env" config > "$UAT_ROOT/artifacts/compose-config.yml"
grep -F "/app/romm/library" "$UAT_ROOT/artifacts/compose-config.yml" >/dev/null
grep -F "Games" "$UAT_ROOT/artifacts/compose-config.yml" >/dev/null
grep -F "/app/romm/library" "$UAT_ROOT/artifacts/compose-config.yml" >/dev/null
grep -F "pc" "$UAT_ROOT/artifacts/compose-config.yml" >/dev/null
VALIDATED_PROJECT="$COMPOSE_PROJECT_NAME"
docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f docker-compose.override.yml -f "$UAT_ROOT/phase33.override.yml" --env-file "$UAT_ROOT/phase33.env" up -d
PHASE33_PORT="$(docker compose -p "$COMPOSE_PROJECT_NAME" port romm-dev 3000 | awk -F: '{print $NF}')"
docker compose -p "$COMPOSE_PROJECT_NAME" ps -a > "$UAT_ROOT/artifacts/compose-ps.txt"
set +e
docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f docker-compose.override.yml -f "$UAT_ROOT/phase33.override.yml" --env-file "$UAT_ROOT/phase33.env" run --rm --no-deps --entrypoint bash --add-host host.docker.internal:host-gateway -v "$UAT_ROOT:/uat" -e E2E_BASE_URL="http://host.docker.internal:$PHASE33_PORT" romm-dev -lc 'test -n "$E2E_BASE_URL" && curl --fail --silent --show-error "$E2E_BASE_URL/health" >/dev/null && cd /app/frontend && npx playwright test /uat/phase33-first-run.spec.ts --config=/uat/phase33-playwright.config.ts --project=chromium --trace=on --reporter=line,junit=/uat/artifacts/playwright.xml' > "$UAT_ROOT/artifacts/playwright-command.log" 2>&1
PLAYWRIGHT_EXIT="$?"
set -e
printf "%s\n" "$PLAYWRIGHT_EXIT" > "$UAT_ROOT/artifacts/playwright-exit-status.txt"
python3 "$UAT_ROOT/manifest.py" "$UAT_ROOT/fixture/Games" > "$UAT_ROOT/artifacts/after.json"
set +e
cmp "$UAT_ROOT/artifacts/before.json" "$UAT_ROOT/artifacts/after.json"
CMP_EXIT="$?"
set -e
printf "%s\n" "$CMP_EXIT" > "$UAT_ROOT/artifacts/cmp-exit-status.txt"
cleanup
docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f docker-compose.override.yml -f "$UAT_ROOT/phase33.override.yml" --env-file "$UAT_ROOT/phase33.env" ps -a --format "{{.Name}}" > "$UAT_ROOT/artifacts/post-down-ps.txt"
docker ps -a --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" --format "{{.Names}}" > "$UAT_ROOT/artifacts/post-down-services.txt"
docker volume ls --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" --format "{{.Name}}" > "$UAT_ROOT/artifacts/post-down-volumes.txt"
cp -a "$UAT_ROOT/artifacts/." "$EVIDENCE_DIR/"
cp "$UAT_ROOT/artifacts/playwright.xml" "$EVIDENCE_DIR/playwright-report.xml"
cp "$UAT_ROOT/artifacts/compose-volume-labels.txt" "$EVIDENCE_DIR/compose-volume-labels.txt"
test -s "$EVIDENCE_DIR/playwright.xml"
test -s "$EVIDENCE_DIR/before.json"
test -s "$EVIDENCE_DIR/after.json"
test -s "$EVIDENCE_DIR/compose-cleanup.txt"
test -s "$EVIDENCE_DIR/compose-ps.txt"
# Leave UAT_ROOT until the structured validator passes; retain EVIDENCE_DIR.
~~~

The existing disposable Compose definition is selected by the implementation environment, not a production stack or live service. The harness fails closed if project name, target volume labels, source mount, or port is not unique and disposable. Cleanup saves output, uses only the exact project ID, and removes only UAT_ROOT after the retained-evidence validator passes. [VERIFIED: Phase 22 UAT, Phase 27 UAT, Phase 32 validation patterns]

Plan 04 Task 2 must also create phase33.env, phase33.override.yml, and state.json, verify the rendered override has the synthetic Games bind read-only, no container_name entries, only unique generated host ports (no fixed 3100), and DB_HOST=romm-db-dev plus REDIS_HOST=romm-valkey-dev, and leave UAT_ROOT until the state-backed Task 3 validator passes. The temporary phase33-first-run.spec.ts must use the existing Playwright config and attach concrete files for each matrix entry:

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

Task 1 must run docker compose --env-file examples/portainer.env.example -f examples/portainer-stack.yml config > .planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/evidence/phase33-deployment-render.yml, assert that file is non-empty, and record canonical Linux git status --short -- .planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc.

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

Critical browser scenarios fresh-ordering, exact-games-pc, readonly-source, and cleanup must be PASS. BLOCKED is valid only for a genuinely unavailable optional input modality (input-touch, input-keyboard, or input-gamepad) with an attempted command and reason; all ordering, mapping, persistence, readonly, cleanup, theme, layout, and Compose-isolation scenarios must PASS. Implementation failures, assertion failures, mapping/persistence failures, source mutation, and Compose isolation failures are invalid BLOCKED results and fail validation.

The allowed automated gate IDs are exactly: auto-naming, auto-frontend, auto-backend, auto-repository, auto-trunk, auto-frontend-build. The allowed browser scenario IDs are exactly: fresh-ordering, exact-games-pc, reload-persistence, readonly-source, theme-dark, theme-light, layout-desktop, layout-narrow, input-mouse, input-touch, input-keyboard, input-gamepad, cleanup.

Every entry in both arrays requires id, status, command, exit_code, artifacts, and result. PASS requires exit code 0, a non-empty executed command, a non-empty artifact array whose files exist under retained EVIDENCE_DIR, and a result. BLOCKED requires the attempted command and a non-empty blocked_reason; any listed artifact must also exist under retained EVIDENCE_DIR. Duplicate, missing, or extra IDs fail validation. Artifact references may not point to /uat or UAT_ROOT. Keyword presence in prose does not satisfy the gate. The wrapper uses set -euo pipefail and an EXIT trap keyed to the exact validated project; it always runs down --volumes --remove-orphans and captures teardown status. Before removing UAT_ROOT, the validator requires teardown status 0 plus empty post-down project, service, and volume artifacts, and refuses cleanup otherwise. EVIDENCE_DIR and cleanup output remain retained.

The validator requires all six gate IDs, a retained state_file under EVIDENCE_DIR, cmp_exit_status=0, mandatory scenarios PASS, and the Playwright exit rules before cleanup. It reads artifacts.playwright_report and artifacts.compose_volume_labels from state.json. A nonzero Playwright exit never automatically becomes BLOCKED: it fails validation unless the manifest proves that only optional input-touch, input-keyboard, or input-gamepad is unavailable while all required scenarios and assertions PASS. Evidence collection still continues so failures are retained.

Run the structured validator from the canonical checkout:

~~~bash
python3 - .planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-UAT.md <<'PY'
import json, os, pathlib, re, shutil, sys
uat = pathlib.Path(sys.argv[1])
text = uat.read_text()
start = "<!-- phase33-evidence-manifest:start -->"
end = "<!-- phase33-evidence-manifest:end -->"
if text.count(start) != 1 or text.count(end) != 1:
    raise SystemExit("missing or duplicate structured evidence markers")
data = json.loads(text.split(start, 1)[1].split(end, 1)[0].strip())
state = json.loads(pathlib.Path(data["state_file"]).read_text())
evidence = pathlib.Path(state["EVIDENCE_DIR"]).resolve()
if evidence not in state_file.parents: raise SystemExit("state_file must be retained under EVIDENCE_DIR")
uat_root = pathlib.Path(state["UAT_ROOT"]).resolve()
if not re.fullmatch(r"/tmp/pgdp-phase33-browser\.[A-Za-z0-9]{6}", str(uat_root)) or not uat_root.is_dir():
    raise SystemExit("refusing cleanup: UAT_ROOT is not an expected disposable directory")
repo = pathlib.Path.cwd().resolve()
if uat_root == repo or repo in uat_root.parents or uat_root in evidence.parents or evidence in uat_root.parents:
    raise SystemExit("refusing cleanup: UAT_ROOT is not distinct from repo/evidence")
if os.stat(uat_root).st_uid != os.getuid() or not re.fullmatch(r"pgdp-phase33-[0-9]+-[0-9]+", state["COMPOSE_PROJECT_NAME"]) or state["COMPOSE_PROJECT_NAME"] not in evidence.name:
    raise SystemExit("refusing cleanup: ownership or expected project identity failed")
gates = {"auto-naming", "auto-frontend", "auto-backend", "auto-repository", "auto-trunk", "auto-frontend-build"}
scenarios = {"fresh-ordering", "exact-games-pc", "reload-persistence", "readonly-source", "theme-dark", "theme-light", "layout-desktop", "layout-narrow", "input-mouse", "input-touch", "input-keyboard", "input-gamepad", "cleanup"}
media = {"theme-dark", "theme-light", "layout-desktop", "layout-narrow", "input-mouse", "input-touch", "input-keyboard", "input-gamepad"}
def check(entries, required, label):
    if not isinstance(entries, list) or len(entries) != len(required) or {e.get("id") for e in entries} != required:
        raise SystemExit(label + " IDs are missing, duplicated, or unexpected")
    for e in entries:
        if e.get("status") not in {"PASS", "BLOCKED"} or not e.get("command", "").strip():
            raise SystemExit(e.get("id", label) + ": missing command/status")
        paths = [pathlib.Path(x).resolve() for x in e.get("artifacts", [])]
        if e["status"] == "PASS" and (e.get("exit_code") != 0 or not paths or not e.get("result")):
            raise SystemExit(e["id"] + ": PASS requires exit_code, result, and artifacts")
        if e["status"] == "BLOCKED" and e["id"] not in {"input-touch", "input-keyboard", "input-gamepad"}: raise SystemExit(e["id"] + ": only optional input modalities may be BLOCKED")
        if e["status"] == "BLOCKED" and any(token in e.get("blocked_reason", "").lower() for token in ("assert", "implementation", "mapping", "persistence", "mutation", "isolation", "error", "failed")): raise SystemExit(e["id"] + ": implementation/assertion failures cannot be BLOCKED")
        if e["status"] == "BLOCKED" and not e.get("blocked_reason", "").strip():
            raise SystemExit(e["id"] + ": BLOCKED requires reason")
        for path in paths:
            if evidence not in path.parents or uat_root in path.parents or "/uat/" in str(path) or not path.is_file():
                raise SystemExit(e["id"] + ": artifact is not retained")
        if e["status"] == "PASS" and e["id"] in media:
            suffixes = {p.suffix.lower() for p in paths}
            if ".png" not in suffixes or not (".zip" in suffixes or ".trace" in suffixes):
                raise SystemExit(e["id"] + ": requires scenario screenshot and trace")
check(data["automated_gates"], gates, "automated gate")
check(data["scenarios"], scenarios, "browser scenario")
playwright_exit = int(pathlib.Path(state["artifacts"]["playwright_exit_status"]).read_text().strip())
if playwright_exit != 0:
    critical = {"fresh-ordering", "exact-games-pc", "readonly-source", "cleanup", "reload-persistence", "theme-dark", "theme-light", "layout-desktop", "layout-narrow", "input-mouse"}
    statuses = {entry["id"]: entry["status"] for entry in data["scenarios"]}
    if any(statuses.get(item) != "PASS" for item in critical):
        raise SystemExit("Playwright failure cannot be BLOCKED for required scenarios")
    if not any(statuses.get(item) == "BLOCKED" for item in {"input-touch", "input-keyboard", "input-gamepad"}):
        raise SystemExit("nonzero Playwright exit requires an explicitly unavailable optional modality")
for key in ("compose_project_labels", "compose_volume_names", "compose_volume_labels", "cmp_exit_status", "playwright_exit_status", "teardown_status", "post_down_ps", "post_down_services", "post_down_volumes"):
    path=pathlib.Path(state["artifacts"][key]).resolve()
    if evidence not in path.parents or not path.is_file(): raise SystemExit("missing isolation artifact: "+key)
if state["COMPOSE_PROJECT_NAME"] not in pathlib.Path(state["artifacts"]["compose_project_labels"]).read_text(): raise SystemExit("project label mismatch")
vols=[x.strip() for x in pathlib.Path(state["artifacts"]["compose_volume_names"]).read_text().splitlines() if x.strip()]
if not vols or len(vols)!=len(set(vols)) or any(state["COMPOSE_PROJECT_NAME"] not in x for x in vols): raise SystemExit("volume names are not unique/project-prefixed")
if pathlib.Path(state["artifacts"]["cmp_exit_status"]).read_text().strip()!="0": raise SystemExit("source fixture changed")
if pathlib.Path(state["artifacts"]["teardown_status"]).read_text().strip()!="0": raise SystemExit("teardown failed")
for key in ("post_down_ps","post_down_services","post_down_volumes"):
    if pathlib.Path(state["artifacts"][key]).read_text().strip(): raise SystemExit("resources remain: "+key)
shutil.rmtree(uat_root)
print("state-backed Phase 33 UAT evidence: PASS")
PY
~~~
