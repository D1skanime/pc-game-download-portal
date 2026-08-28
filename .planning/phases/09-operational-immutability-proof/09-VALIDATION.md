---
phase: 09
slug: operational-immutability-proof
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-27
---

# Phase 09 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| **Framework**          | pytest 9.x and Playwright 1.61.1                                                                  |
| **Config file**        | `backend/pyproject.toml`, `backend/tests/conftest.py`, `frontend/playwright.config.ts`            |
| **Quick run command**  | `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -x -q`           |
| **Full suite command** | `python3 backend/tools/verify_operational_immutability.py --all --artifacts "$PHASE09_ARTIFACTS"` |
| **Estimated runtime**  | Quick run under 30 seconds; full production-like lifecycle measured during Wave 0                 |

---

## Sampling Rate

- **After every task commit:** Run the scoped unit test or preflight command assigned in the plan, with the quick run as the default harness check.
- **After every plan wave:** Run all workflows introduced by that wave, tier-sharing regressions, Compose preflight, and `git diff --check`.
- **Before `/gsd:verify-work`:** Run one clean full harness lifecycle, affected backend tests, nginx-backed Playwright, frontend verification when touched, scoped Trunk checks, artifact validation, and exact cleanup verification.
- **Max feedback latency:** 30 seconds for unit and static topology feedback. Production workflow gates run at wave boundaries.

---

## Per-Task Verification Map

| Task ID  | Plan         | Wave | Requirement                                       | Threat Ref       | Secure Behavior                                                                                                                               | Test Type              | Automated Command                                                                                                                                                                                                                                                                                   | File Exists                                                                | Status     |
| -------- | ------------ | ---- | ------------------------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | ---------- |
| 09-W1-01 | 09-01 Task 1 | 1    | TEST-05                                           | T-09-01          | Manifest capture rejects incomplete, unsorted, duplicate, unsafe, or raced source evidence before workflow proofs build on it                 | unit                   | `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -x -q`                                                                                                                                                                                                             | No, Wave 1                                                                 | pending    |
| 09-W1-02 | 09-01 Task 2 | 1    | TEST-04                                           | T-09-02          | The isolated stack attests a read-only source mount, separate owned writable targets, and ownership-safe cleanup before startup               | static integration     | `python3 backend/tools/verify_operational_immutability.py --preflight-only`                                                                                                                                                                                                                         | No, Wave 1                                                                 | pending    |
| 09-W2-01 | 09-02 Task 1 | 2    | TEST-04, TEST-05                                  | T-09-05          | Every locked workflow and restart proof emits its own exact before and after manifest pair plus bounded result envelope                       | integration            | `cd backend && uv run pytest tests/integration/test_operational_immutability.py tests/integration/test_scan_source_immutability.py -x -q && python3 backend/tools/verify_operational_immutability.py --workflow restart-persistence --artifacts /tmp/phase9-artifacts`                              | No, Wave 2                                                                 | pending    |
| 09-W2-02 | 09-02 Task 2 | 2    | TEST-06                                           | T-09-04, T-09-06 | Authorized delivery stays bound to database identity, nginx internal redirects, worker execution, and masked direct-path denials              | production integration | `cd backend && uv run pytest tests/integration/test_operational_immutability.py tests/endpoints/test_streaming.py tests/endpoints/roms/test_files.py -x -q && python3 backend/tools/verify_operational_immutability.py --requirement TEST-06 --artifacts /tmp/phase9-artifacts && git diff --check` | No, Wave 2                                                                 | pending    |
| 09-W2-03 | 09-03 Task 1 | 2    | TEST-04, TEST-06                                  | T-09-08          | Browser proof helpers reuse the real auth and hydration flow, target nginx, and avoid any proof-only or v1 route                              | browser harness        | `cd frontend && npm run test:e2e -- --list`                                                                                                                                                                                                                                                         | No, Wave 2                                                                 | pending    |
| 09-W2-04 | 09-03 Task 2 | 2    | TEST-04, TEST-06                                  | T-09-07, T-09-09 | The browser matrix drives real v2 browse, mapping, scan, play, download, migration, and removal flows serially against the shared proof stack | production browser     | `cd frontend && E2E_BASE_URL=http://127.0.0.1:3000 npx playwright test e2e/operational-immutability.spec.ts --project=chromium --workers=1 --list && git diff --check`                                                                                                                              | No, Wave 2                                                                 | pending    |
| 09-W3-01 | 09-04 Task 1 | 3    | DOC-01, DOC-02, DOC-03                            | T-09-10, T-09-11 | The operator guide stays aligned with the tested deployment and rejects unsafe Team4s, NAS, and host-path guidance                            | docs contract          | `python3 backend/tools/verify_operational_immutability.py --check-docs DOC-01 && python3 backend/tools/verify_operational_immutability.py --check-docs DOC-02 && python3 backend/tools/verify_operational_immutability.py --check-docs DOC-03 && rg -n "^\\                                         | 09-W" .planning/phases/09-operational-immutability-proof/09-VALIDATION.md` | No, Wave 3 | pending |
| 09-W3-02 | 09-04 Task 2 | 3    | TEST-04, TEST-05, TEST-06, DOC-01, DOC-02, DOC-03 | T-09-12          | The final synthetic phase gate emits complete aggregate coverage, safe cleanup evidence, and one result per required workflow slug            | full acceptance        | `cd backend && uv run pytest tests/tools/test_verify_operational_immutability.py -x -q && python3 backend/tools/verify_operational_immutability.py --all --artifacts /tmp/phase9-artifacts && git diff --check`                                                                                     | No, Wave 3                                                                 | pending    |

---

## Wave 0 Requirements

- [ ] `backend/tools/verify_operational_immutability.py` (`09-01 Task 2`, `09-W1-02`) - bounded orchestration, canonical manifest, deterministic artifacts, topology attestation, and ownership-safe cleanup.
- [ ] `backend/tests/tools/test_verify_operational_immutability.py` (`09-01 Task 1`, `09-W1-01`) - manifest schema, mutation, Compose topology, artifact, and cleanup tests.
- [ ] `backend/docker-compose.immutability-test.yml` - isolated production-like stack with app, worker, nginx, database, queue, read-only fixtures, and separate writable storage.
- [ ] `frontend/e2e/operational-immutability.spec.ts` - nginx-backed v2 browser workflow matrix.
- [ ] `frontend/e2e/fixtures/operational-proof.ts` - workflow checkpoints, manifest finalization, and infrastructure witnesses.
- [ ] Repository-controlled deterministic fixture with multiple mappings, nested and Unicode paths, empty and zero-byte entries, multi-file content, and path-safety cases.
- [ ] CI artifact upload with redaction and always-run ownership-safe cleanup.
- [ ] Executable DOC-01 through DOC-03 contract checks.

No framework installation is required.

---

## Manual-Only Verifications

| Behavior                              | Requirement            | Why Manual                                                                | Test Instructions                                                                                                                                         |
| ------------------------------------- | ---------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Operator guide sequencing and clarity | DOC-01, DOC-02, DOC-03 | Section checks cannot prove operational clarity                           | Review authorization, backup and recovery readiness, workload review, mount validation, rollback, and post-window confirmation as one complete procedure. |
| Vendor-specific noatime equivalent    | DOC-02                 | Phase 9 is prohibited from probing a real NAS                             | During a later separately authorized deployment review, verify the NAS-specific setting and retain its attestation.                                       |
| Team4s and encode isolation           | DOC-03                 | Synthetic evidence cannot inspect real operational workloads              | Before any later authorized maintenance window, confirm Team4s paths, containers, services, and active encodes are outside the approved target.           |
| Emulator visual and audio sanity      | TEST-04                | Human perception may supplement automated v2 route and network assertions | Use only the isolated synthetic stack and record the result alongside automated immutability evidence.                                                    |

---

## Exhaustive Phase Gate

The final run must produce an independent before and after manifest pair for mapping creation, mapping change, mapping removal, folder browsing and mapping tests, preview, scan and hashing, metadata matching, streaming and browser play, single-file and multi-file download, restart persistence, legacy migration and supported rollback, game catalog removal, and platform mapping removal.

Required artifacts are `run.json`, resolved topology and mount attestations, per-workflow `before.json`, `after.json`, `diff.json`, and `result.json`, browser evidence, app/worker/nginx witnesses, `aggregate.json`, and `cleanup.json`. Missing or malformed evidence, source deltas, absent service witnesses, unsafe paths, secrets, or cleanup residue are hard failures.

---

## Validation Sign-Off

- [x] All tasks have an automated verification command or Wave 0 dependency.
- [x] Sampling continuity has no three consecutive tasks without automated verification.
- [x] Wave 0 covers every missing test and harness reference.
- [x] No watch-mode flags are used.
- [x] Quick feedback latency remains under 30 seconds.
- [x] Every TEST-04, TEST-05, TEST-06, DOC-01, DOC-02, and DOC-03 obligation is assigned to a plan and final gate.
- [x] Full execution uses only synthetic or repository-controlled fixtures.
- [x] No real NAS, Team4s service, Team4s data, host restart, or active encode workload is accessed or altered.

**Approval:** complete, 2026-08-27
