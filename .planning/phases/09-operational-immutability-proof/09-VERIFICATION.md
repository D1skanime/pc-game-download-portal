---
phase: 09-operational-immutability-proof
verified: 2026-08-28T15:01:12Z
status: gaps_found
score: 5/11 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Integration evidence covers read-only mounting, multiple mappings, mapping changes, scanning, streaming, downloading, restart persistence, legacy migration, nginx, and worker paths."
    status: failed
    reason: "The Phase 9 harness never starts Docker services, never hits nginx, never queues worker jobs, and never consumes browser proof artifacts. It generates witness data in-process."
    artifacts:
      - path: "backend/tools/verify_operational_immutability.py"
        issue: "execute_workflows() only runs preflight, copies fixtures, builds manifests, and writes JSON; there is no docker, nginx, worker, or Playwright execution."
      - path: "frontend/e2e/operational-immutability.spec.ts"
        issue: "Browser proof exists, but the final harness does not invoke it or read its browser artifacts."
    missing:
      - "Start and verify the isolated Compose stack during proof runs."
      - "Drive the real nginx-backed browser matrix as part of the final phase gate."
      - "Collect witnesses from actual nginx and worker execution instead of synthetic markers."
  - truth: "Before/after evidence shows source content, names, structure, sizes, hashes, and non-access timestamps unchanged across every supported workflow."
    status: failed
    reason: "Per-workflow before/after manifests are created without performing the named workflow. The same copied fixture is hashed before and after, so the proof does not cover real scan, metadata, mapping, download, or removal effects."
    artifacts:
      - path: "backend/tools/verify_operational_immutability.py"
        issue: "execute_workflow() captures before and after from the same fixture_root without any workflow-specific mutation attempt or external service interaction."
    missing:
      - "Bracket each real workflow with manifest capture around the actual action under test."
      - "Bind diff evidence to the real workflow outcome and service path used."
  - truth: "Browser proof runs against the real nginx-backed RomM stack and existing v2 surfaces, never a proof-only dashboard or v1 fallback."
    status: failed
    reason: "The Playwright suite is only list-verified. The final `--all` gate does not run it, and the generated artifact set contains no `browser.json` files."
    artifacts:
      - path: "backend/tools/verify_operational_immutability.py"
        issue: "No code reads `PHASE9_BROWSER_ARTIFACTS_DIR`, launches Playwright, or validates browser outputs."
      - path: "frontend/e2e/fixtures/operational-proof.ts"
        issue: "Browser artifact writing is optional on an env var and remains orphaned from the backend aggregate flow."
    missing:
      - "Execute Playwright against the nginx-backed stack in the final gate."
      - "Require and validate per-workflow browser artifacts in aggregate evidence."
---

# Phase 9: Operational Immutability Proof Verification Report

**Phase Goal:** Operators have production-like evidence and guidance showing that supported NAS workflows preserve the archive and do not disrupt Team4s.
**Verified:** 2026-08-28T15:01:12Z
**Status:** gaps_found
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                                                                                | Status       | Evidence                                                                                                                                                                                                                                          |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Integration evidence covers read-only mounting, multiple mappings, mapping changes, scanning, streaming, downloading, restart persistence, legacy migration, nginx, and worker paths.                | ✗ FAILED     | `backend/tools/verify_operational_immutability.py:802-909` never starts services or calls browser tests. `_service_witness()` at `:681-722` fabricates nginx/worker/restart witnesses.                                                            |
| 2   | Before/after evidence shows source content, names, structure, sizes, hashes, and non-access timestamps unchanged across every supported workflow.                                                    | ✗ FAILED     | `execute_workflow()` at `backend/tools/verify_operational_immutability.py:764-799` hashes the same copied fixture before and after, with no workflow action in between.                                                                           |
| 3   | An operator can deploy one `:ro` root with separate writable storage and follow documented mapping, browsing, migration, catalog-removal, security, troubleshooting, limitation, and atime guidance. | ✓ VERIFIED   | Operator guide covers mount topology, writable separation, browse/mapping flow, migration/removal, troubleshooting, noatime guidance, limitations, and safety boundaries in `docs/external-read-only-library-operations.md:9-81`.                 |
| 4   | Operational instructions require an approved maintenance window for a real NAS mount and prohibit Team4s source, service, restart, or active-encode changes.                                         | ✓ VERIFIED   | Maintenance-window and Team4s prohibitions are explicit in `docs/external-read-only-library-operations.md:57-77`. `python3 backend/tools/verify_operational_immutability.py --check-docs DOC-03` passed on 2026-08-28.                            |
| 5   | Every Phase 9 workflow proof starts from one canonical manifest format that captures names, structure, type, size, hash, and non-access timestamps without mutating the source fixture.              | ✓ VERIFIED   | Manifest capture and validation exist in `backend/tools/verify_operational_immutability.py:194-265` and `:367-466`; tool tests passed with `12 passed`.                                                                                           |
| 6   | The isolated stack models a read-only external library and separate RomM-owned writable paths before any browser or backend workflow runs.                                                           | ✓ VERIFIED   | Compose contract and preflight enforcement exist in `backend/docker-compose.immutability-test.yml` and `backend/tools/verify_operational_immutability.py:490-639`. `--preflight-only` passed.                                                     |
| 7   | Cleanup and artifact ownership stay bounded to the Phase 9 harness, never Team4s, a real NAS mount, or unrelated containers.                                                                         | ⚠️ UNCERTAIN | Label validation exists in `backend/tools/verify_operational_immutability.py:476-546`, but cleanup evidence is synthesized from compose model service names in `:824-838`, not from live owned resources.                                         |
| 8   | Every D-07 workflow gets its own before/after manifest pair, exact diff, and result envelope instead of one suite-level aggregate.                                                                   | ✓ VERIFIED   | Independent workflow directories were emitted under `/tmp/phase9-verify-subagent/workflows/*/{before.json,after.json,diff.json,result.json}`.                                                                                                     |
| 9   | Production-like proof uses the real worker queue and nginx-backed file delivery paths rather than inline or API-only substitutes.                                                                    | ✗ FAILED     | `_workflow_http_probes()` and `_service_witness()` at `backend/tools/verify_operational_immutability.py:667-722` hardcode `200`/`404` statuses and `observed` worker state; there is no real queue or nginx interaction.                          |
| 10  | Browser proof runs against the real nginx-backed RomM stack and existing v2 surfaces, never a proof-only dashboard or v1 fallback.                                                                   | ✗ FAILED     | The Playwright suite is authored against v2 surfaces in `frontend/e2e/operational-immutability.spec.ts:16-250`, but the final harness never invokes it and `/tmp/phase9-verify-subagent` contains no `browser.json` outputs.                      |
| 11  | Documentation and aggregate evidence explicitly distinguish content immutability from optional access-time invariance under documented noatime equivalents.                                          | ✓ VERIFIED   | The guide distinguishes atime variance from content immutability at `docs/external-read-only-library-operations.md:39-43`, and manifest comparison excludes atime unless requested in `backend/tools/verify_operational_immutability.py:265-319`. |

**Score:** 5/11 truths verified

### Required Artifacts

| Artifact                                                              | Expected                                                     | Status      | Details                                                                                                                                |
| --------------------------------------------------------------------- | ------------------------------------------------------------ | ----------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/tools/verify_operational_immutability.py`                    | Bounded proof harness, docs contract, aggregate gate         | ⚠️ HOLLOW   | Substantive file, but workflow execution is synthetic. No Docker, Playwright, nginx, or worker invocation.                             |
| `backend/tests/tools/test_verify_operational_immutability.py`         | Harness contract coverage                                    | ✓ VERIFIED  | Substantive and passing, but it validates the synthetic harness contract rather than real production-path execution.                   |
| `backend/docker-compose.immutability-test.yml`                        | Read-only source mount plus separate writable owned storage  | ✓ VERIFIED  | Compose topology declares `read_only: true` source binds and separate writable targets.                                                |
| `backend/tests/integration/test_operational_immutability.py`          | Integration coverage for workflow envelopes and witnesses    | ⚠️ HOLLOW   | Runs the harness and asserts emitted JSON structure. It does not prove live nginx/worker/browser wiring.                               |
| `backend/tests/integration/test_scan_source_immutability.py`          | Manifest regression anchor                                   | ✓ VERIFIED  | Confirms manifest identity and hash stability for a controlled fixture.                                                                |
| `frontend/e2e/operational-immutability.spec.ts`                       | Browser workflow matrix on real v2 surfaces                  | ⚠️ ORPHANED | Substantive and v2-only, but not executed by the final Phase 9 gate.                                                                   |
| `frontend/e2e/fixtures/operational-proof.ts`                          | Authenticated proof helpers and browser artifact writing     | ⚠️ PARTIAL  | Correctly reuses `auth.ts`, but browser artifact output is optional and unconsumed by backend aggregate logic.                         |
| `docs/external-read-only-library-operations.md`                       | Operator guide for DOC-01..03 scope                          | ✓ VERIFIED  | Complete sections and safe guidance present.                                                                                           |
| `.planning/phases/09-operational-immutability-proof/09-VALIDATION.md` | Final validation map with exact commands and no placeholders | ⚠️ WARNING  | No `TBD`, but the verification rows remain `pending` after execution and overstate the final gate as a full production-like lifecycle. |

### Key Link Verification

| From                                                         | To                                                           | Via                                                              | Status      | Details                                                                                             |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ---------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------- |
| `backend/tools/verify_operational_immutability.py`           | `backend/tests/integration/test_scan_source_immutability.py` | Stable manifest ordering, relative identity, and sha256 evidence | ✓ WIRED     | Shared manifest logic is exercised by the regression test.                                          |
| `backend/docker-compose.immutability-test.yml`               | `backend/docker-compose.policy-test.yml`                     | Explicit read-only source bind and separate owned output bind    | ✓ WIRED     | Matching topology pattern exists.                                                                   |
| `backend/tools/verify_operational_immutability.py`           | `docker/nginx/templates/default.conf.template`               | nginx internal redirect and cache delivery witness expectations  | ⚠️ PARTIAL  | Pattern strings exist, but the harness never reads nginx config or exercises nginx.                 |
| `backend/tests/integration/test_operational_immutability.py` | `backend/tests/endpoints/test_streaming.py`                  | Server-side path derivation and hidden read-path assertions      | ✓ WIRED     | Endpoint regression coverage exists.                                                                |
| `frontend/e2e/operational-immutability.spec.ts`              | `09-UI-SPEC.md`                                              | Existing v2 surfaces, semantic selectors, no proof-only route    | ✓ WIRED     | The spec uses existing routes and semantic selectors.                                               |
| `frontend/e2e/fixtures/operational-proof.ts`                 | `frontend/e2e/fixtures/auth.ts`                              | Authenticated storage state and hydrated-shell waits             | ✓ WIRED     | Direct import and reuse at `frontend/e2e/fixtures/operational-proof.ts:4,147-150`.                  |
| `backend/tools/verify_operational_immutability.py`           | `frontend/e2e/operational-immutability.spec.ts`              | Stable workflow slugs and aggregate coverage matrix              | ✗ NOT_WIRED | Slug names align, but backend aggregate logic does not read browser artifacts or launch Playwright. |

### Data-Flow Trace (Level 4)

| Artifact                                           | Data Variable                  | Source                                             | Produces Real Data                                                                 | Status         |
| -------------------------------------------------- | ------------------------------ | -------------------------------------------------- | ---------------------------------------------------------------------------------- | -------------- |
| `backend/tools/verify_operational_immutability.py` | `service_witness`              | `_service_witness()` and `_workflow_http_probes()` | No, values are literal markers and hardcoded statuses at `:681-722`.               | ⚠️ STATIC      |
| `backend/tools/verify_operational_immutability.py` | `workflow_results`             | `execute_workflow()`                               | Partial, it produces real manifest snapshots but not from real workflow execution. | ⚠️ HOLLOW      |
| `frontend/e2e/operational-immutability.spec.ts`    | page/API state                 | `page.request`, `gotoHydrated`, visible routes     | Yes, if executed.                                                                  | ✓ FLOWING      |
| `frontend/e2e/fixtures/operational-proof.ts`       | `browser.json` artifact stream | `PHASE9_BROWSER_ARTIFACTS_DIR` gated writes        | No in final gate, because backend never supplies or consumes the artifact path.    | ✗ DISCONNECTED |

### Behavioral Spot-Checks

| Behavior                                          | Command                                                                                                  | Result                                                                                                                                                         | Status |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Compose preflight validates read-only topology    | `python3 backend/tools/verify_operational_immutability.py --preflight-only`                              | Returned `status: ok` with services `app,database,nginx,queue,worker`.                                                                                         | ✓ PASS |
| Tool contract suite passes                        | `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -x -q`                  | `12 passed, 1 warning in 0.09s`                                                                                                                                | ✓ PASS |
| DOC-03 safety contract is executable              | `python3 backend/tools/verify_operational_immutability.py --check-docs DOC-03`                           | Returned `status: passed`                                                                                                                                      | ✓ PASS |
| Full phase gate produces real full-stack evidence | `python3 backend/tools/verify_operational_immutability.py --all --artifacts /tmp/phase9-verify-subagent` | Exit 0, but artifacts contain no `browser.json`; service logs are one-line synthesized markers; workflow results are generated without real service execution. | ✗ FAIL |

### Probe Execution

| Probe                     | Command                                           | Result                      | Status    |
| ------------------------- | ------------------------------------------------- | --------------------------- | --------- |
| Conventional shell probes | `find scripts -path '*/tests/probe-*.sh' -type f` | `scripts/` directory absent | ? SKIPPED |

### Requirements Coverage

| Requirement | Source Plan                        | Description                                                                                                                                          | Status      | Evidence                                                                                                                     |
| ----------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `TEST-04`   | `09-01`, `09-02`, `09-03`, `09-04` | Integration tests prove read-only mounting, scanning, streaming, downloading, mappings, restart persistence, and legacy migration.                   | ✗ BLOCKED   | The harness proves static topology and artifact shape, but not real integration execution.                                   |
| `TEST-05`   | `09-01`, `09-02`, `09-04`          | Before/after evidence proves source content, names, structure, sizes, hashes, and non-access timestamps remain unchanged across supported workflows. | ✗ BLOCKED   | Before/after manifests are taken around no-op workflow bodies in `backend/tools/verify_operational_immutability.py:764-799`. |
| `TEST-06`   | `09-02`, `09-03`, `09-04`          | Production-like nginx and worker paths enforce the same authorized boundary as development paths.                                                    | ✗ BLOCKED   | nginx/worker evidence is synthetic and browser execution is not part of the final gate.                                      |
| `DOC-01`    | `09-04`                            | Documentation explains `:ro` mount, writable storage, mappings, browser flow, migration, catalog-only removal.                                       | ✓ SATISFIED | Sections present in `docs/external-read-only-library-operations.md:9-37`.                                                    |
| `DOC-02`    | `09-04`                            | Documentation explains defense in depth, path safety, troubleshooting, limitations, and noatime guidance.                                            | ✓ SATISFIED | Sections present in `docs/external-read-only-library-operations.md:39-55,79-81`.                                             |
| `DOC-03`    | `09-04`                            | Operational instructions require a safe maintenance window and prohibit Team4s changes during active encode work.                                    | ✓ SATISFIED | Explicit prohibitions in `docs/external-read-only-library-operations.md:57-77`; docs check passed.                           |

### Anti-Patterns Found

| File                                                                  | Line    | Pattern                                         | Severity   | Impact                                                                                         |
| --------------------------------------------------------------------- | ------- | ----------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------- |
| `backend/tools/verify_operational_immutability.py`                    | 174-187 | Synthesized service logs                        | 🛑 Blocker | `app.log`, `nginx.log`, `worker.log`, etc. are generated strings, not captured service output. |
| `backend/tools/verify_operational_immutability.py`                    | 681-722 | Hardcoded witness/status generation             | 🛑 Blocker | nginx, worker, and restart proof data is fabricated in-process.                                |
| `backend/tools/verify_operational_immutability.py`                    | 764-799 | No-op workflow proof                            | 🛑 Blocker | Workflow artifacts are emitted without executing the workflow they claim to prove.             |
| `backend/tools/verify_operational_immutability.py`                    | 802-909 | Final gate does not invoke Docker or Playwright | 🛑 Blocker | The supposed production-like full run is only local file generation plus docs checks.          |
| `.planning/phases/09-operational-immutability-proof/09-VALIDATION.md` | 41-48   | All task rows still `pending`                   | ⚠️ Warning | Validation contract was not updated to reflect actual execution state.                         |

### Human Verification Required

These checks remain necessary, but they do not change the current verdict because automated blockers already prevent phase acceptance.

### 1. Operator Guide Sequencing And Clarity

**Test:** Review authorization, backup readiness, workload review, mount validation, rollback, and post-window confirmation as one complete procedure.
**Expected:** The guide reads as a coherent operator runbook, not just section presence.
**Why human:** Section checks cannot prove operational clarity.

### 2. Vendor-Specific noatime Equivalent

**Test:** During a separately authorized deployment review, confirm the NAS-specific equivalent of `noatime`.
**Expected:** Access-time mitigation is documented and actually available on the target platform.
**Why human:** Phase 9 is prohibited from probing a real NAS.

### 3. Team4s And Encode Isolation

**Test:** Before any later authorized maintenance window, confirm Team4s paths, containers, services, and active encodes are outside scope.
**Expected:** No Team4s or active encode workload is touched by the approved procedure.
**Why human:** Synthetic evidence cannot inspect real operational workloads.

### 4. Emulator Visual And Audio Sanity

**Test:** On the isolated synthetic stack, validate visible emulator and audio behavior during stream/play.
**Expected:** User-visible playback works while source immutability evidence remains unchanged.
**Why human:** Human perception is needed for media playback quality.

### Gaps Summary

Phase 9 did not achieve its stated goal. The documentation half is real and auditable, but the proof half is not production-like. The final harness succeeds because it validates a synthetic contract of its own making: it copies a fixture, hashes it twice, fabricates nginx/worker/restart witnesses, writes one-line fake service logs, and never starts the Compose stack or executes the Playwright browser matrix. That leaves `TEST-04`, `TEST-05`, and `TEST-06` unfulfilled.

The fix path is narrow and concrete: make `--all` orchestrate the isolated stack, run the real browser matrix against nginx, capture actual worker/nginx evidence, and only then bracket each supported workflow with before/after manifests and aggregate reporting.

---

_Verified: 2026-08-28T15:01:12Z_
_Verifier: the agent (gsd-verifier)_
