# Phase 9 Live Operational Proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Phase 9 gate produce and validate real isolated-stack evidence for every supported immutable-library workflow.

**Architecture:** The Python harness owns one uniquely named labeled Compose project and captures evidence around actions executed against that project. Playwright writes run-bound browser results under the harness artifact root, while the harness validates them and persists real nginx, worker, and restart evidence before bounded cleanup.

**Tech Stack:** Python 3.13, pytest, Docker Compose, MariaDB, Redis/RQ, nginx, Playwright, Vue v2 surfaces.

**Spec:** `docs/superpowers/specs/2026-08-30-phase9-live-operational-proof-design.md`

## Global Constraints

- Use only copies of `tests/fixtures/operational-immutability`; never access a NAS mount or Team4s.
- Compose cleanup must use the generated project name and validate both Phase 9 labels before removal.
- The `/romm/library` bind stays read-only and all owned paths remain distinct writable volumes.
- Every production-code behavior starts with a failing test.
- No witness may contain fabricated HTTP status, job outcome, marker, or service log.

---

### Task 1: Fail closed on synthetic and unbound evidence

**Files:**

- Modify: `backend/tests/tools/test_verify_operational_immutability.py`
- Modify: `backend/tools/verify_operational_immutability.py`

**Interfaces:**

- Consumes: `WorkflowSpec`, `validate_workflow_result()`, `validate_browser_artifacts()`.
- Produces: `WorkflowExecutionContext`, `validate_live_witnesses(result, context)`, and a browser artifact contract bound to `run_id` and `base_url`.

- [ ] **Step 1: Write the failing unit tests**

Add tests that pass a delivery result with only `authorized_status: 200` and no request URL, response headers, or nginx-log reference; a worker result with only a marker and no job ID/log reference; and a `browser.json` whose `run_id` differs from the run or whose `final_url` is outside the resolved nginx base URL. Each test must expect `ValueError`.

- [ ] **Step 2: Run the focused tests to verify RED**

Run: `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -q -k 'synthetic or browser'`

Expected: FAIL because the current validators accept generated markers and do not bind browser output to a run or base URL.

- [ ] **Step 3: Implement the minimal live-evidence schema**

Add a `WorkflowExecutionContext` dataclass containing `run_id`, `compose_project`, `base_url`, `fixture_root`, and `artifacts_root`. Replace `_workflow_http_probes()` and `_service_witness()` with validators that require: actual command/HTTP evidence for each action, actual nginx/worker log artifact paths, and a result whose values match the execution context. Extend `validate_browser_artifacts()` to require `run_id`, canonical workflow slug, passed status, and a `final_url` with the resolved nginx origin.

- [ ] **Step 4: Run the focused tests to verify GREEN**

Run: `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -q -k 'synthetic or browser'`

Expected: PASS, with all malformed or unbound witnesses rejected.

- [ ] **Step 5: Commit**

Run: `git add backend/tools/verify_operational_immutability.py backend/tests/tools/test_verify_operational_immutability.py && git commit -m "test: reject synthetic phase 9 evidence"`

### Task 2: Execute and attest the isolated live stack

**Files:**

- Modify: `backend/tools/verify_operational_immutability.py`
- Modify: `backend/docker-compose.immutability-test.yml`
- Modify: `backend/tools/seed_phase9_database_platforms.py`
- Modify: `backend/tests/integration/test_operational_immutability.py`

**Interfaces:**

- Consumes: `WorkflowExecutionContext` from Task 1 and the seeded isolated app/worker/nginx stack.
- Produces: `execute_live_workflow(spec, context) -> dict[str, Any]`, per-workflow before/after/diff/result artifacts, and real service-log files.

- [ ] **Step 1: Write the failing integration tests**

Create a narrow live-stack test marked for Docker that runs `--workflow scan-hash` against a temporary artifact directory. Require a changed test double only at the action boundary, then assert that the result contains a real queue job ID and a worker-log line reference, that `before.json` is written before the action and `after.json` after it, and that `cleanup.json` records the generated Compose project. Add a delivery test that requires the actual nginx URL, response statuses, headers, and nginx-log reference rather than fixed values.

- [ ] **Step 2: Run the integration tests to verify RED**

Run: `cd backend && uv run pytest tests/integration/test_operational_immutability.py -q -k 'live or delivery'`

Expected: FAIL because `execute_workflow()` currently takes both manifests with no action between them and builds witness values in process.

- [ ] **Step 3: Implement bounded live orchestration**

Make `execute_workflows()` start the generated Compose project, resolve and wait for nginx, seed the database, and create one `WorkflowExecutionContext`. Implement action adapters for mapping, browse, preview, scan/hash, metadata, delivery, lifecycle, and restart. Each adapter must execute against the isolated app, worker, or nginx and return its raw response or command identity. Capture before/after manifests around that adapter only. Collect logs with `docker compose logs`, search them for the returned request or job identity, and persist the matching lines and relative log paths. Restart only the generated `app` service, then re-query isolated persisted state. Always collect available logs and write failed run/cleanup payloads before `down -v --remove-orphans`.

- [ ] **Step 4: Run the integration tests to verify GREEN**

Run: `cd backend && uv run pytest tests/integration/test_operational_immutability.py -q -k 'live or delivery'`

Expected: PASS, showing real action outcomes between unchanged manifests and evidence from the live labeled project.

- [ ] **Step 5: Commit**

Run: `git add backend/tools/verify_operational_immutability.py backend/docker-compose.immutability-test.yml backend/tools/seed_phase9_database_platforms.py backend/tests/integration/test_operational_immutability.py && git commit -m "feat: run phase 9 proof against live stack"`

### Task 3: Bind the v2 browser matrix to the aggregate gate

**Files:**

- Modify: `frontend/e2e/fixtures/operational-proof.ts`
- Modify: `frontend/e2e/operational-immutability.spec.ts`
- Modify: `backend/tools/verify_operational_immutability.py`
- Modify: `backend/tests/tools/test_verify_operational_immutability.py`

**Interfaces:**

- Consumes: `PHASE9_RUN_ID`, `E2E_BASE_URL`, and `PHASE9_BROWSER_ARTIFACTS_DIR` supplied by the harness.
- Produces: one `workflows/<slug>/browser.json` containing `run_id`, `workflow`, `status`, timing, actual final URL, and observed action outcome.

- [ ] **Step 1: Write the failing browser-artifact tests**

Extend the Python unit suite so `validate_browser_artifacts()` rejects skipped, missing, non-nginx-origin, and wrong-run artifacts. Add a Playwright helper test for a completed artifact that lacks the harness run ID. Assert that the aggregate test fails if the browser command succeeds but any required artifact is absent.

- [ ] **Step 2: Run the focused tests to verify RED**

Run: `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -q -k browser`

Expected: FAIL because the existing browser payload has no run ID and the aggregate gate accepts optional artifact fields.

- [ ] **Step 3: Implement run-bound browser output and real actions**

Pass `PHASE9_RUN_ID` into `_run_browser_matrix()`. Require it in `beginWorkflow()` and `completeWorkflow()`. For each current v2 workflow, record the action's actual API response status or visible state in `browser.json`; remove assertions that only inspect static headings when an authenticated isolated action is available. Preserve serial execution, existing auth helpers, v2 routes, and no proof-only UI. Make the harness validate browser artifacts after Playwright and before reporting success.

- [ ] **Step 4: Run the browser and aggregate checks to verify GREEN**

Run: `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -q -k browser && python3 tools/verify_operational_immutability.py --all --artifacts "$(mktemp -d)"`

Expected: PASS, with every browser-covered workflow producing a run-bound artifact and the aggregate result validating it.

- [ ] **Step 5: Commit**

Run: `git add frontend/e2e/fixtures/operational-proof.ts frontend/e2e/operational-immutability.spec.ts backend/tools/verify_operational_immutability.py backend/tests/tools/test_verify_operational_immutability.py && git commit -m "feat: bind browser proof to phase 9 gate"`

### Task 4: Verify the complete Phase 9 acceptance surface

**Files:**

- Modify: `.planning/phases/09-operational-immutability-proof/09-VALIDATION.md`
- Modify: `.planning/phases/09-operational-immutability-proof/09-VERIFICATION.md`

**Interfaces:**

- Consumes: the full aggregate artifact set from Tasks 1 to 3.
- Produces: completed validation rows and a re-verification report based on live evidence.

- [ ] **Step 1: Write the failing validation assertions**

Add explicit assertions in `backend/tests/tools/test_verify_operational_immutability.py` that the validation contract requires live Compose, nginx, worker, and browser evidence, and that it no longer describes the gate as synthetic.

- [ ] **Step 2: Run the assertion to verify RED**

Run: `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -q -k validation`

Expected: FAIL while `09-VALIDATION.md` still names the synthetic final gate.

- [ ] **Step 3: Update the validation contract and rerun the independent verifier**

Replace synthetic-gate wording with the exact live full-stack command, mark only evidence actually executed as complete, then run `python3 backend/tools/verify_operational_immutability.py --all --artifacts "$(mktemp -d)"`. Update `09-VERIFICATION.md` only from that emitted evidence and its rerun results.

- [ ] **Step 4: Run full verification**

Run: `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py tests/integration/test_operational_immutability.py tests/integration/test_scan_source_immutability.py -x -q && cd .. && trunk fmt && trunk check && python3 backend/tools/verify_operational_immutability.py --all --artifacts "$(mktemp -d)" && git diff --check`

Expected: PASS, TEST-04 through TEST-06 have live evidence, and DOC-01 through DOC-03 remain passed.

- [ ] **Step 5: Commit**

Run: `git add .planning/phases/09-operational-immutability-proof/09-VALIDATION.md .planning/phases/09-operational-immutability-proof/09-VERIFICATION.md backend/tests/tools/test_verify_operational_immutability.py && git commit -m "docs: verify live phase 9 proof"`

---

## Plan Review

- Spec coverage: Tasks 1 through 3 implement live stack orchestration, real workflow bracketing, nginx/worker/restart witnesses, mandatory browser output, and bounded cleanup. Task 4 records independent live verification.
- Placeholder scan: no deferred implementation markers or unspecified error-handling steps remain.
- Interface consistency: all workflow action code receives `WorkflowExecutionContext`; browser artifacts consume the exact `PHASE9_RUN_ID` that the aggregate validator requires.
