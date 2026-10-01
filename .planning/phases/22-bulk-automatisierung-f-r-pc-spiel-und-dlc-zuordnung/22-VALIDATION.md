---
phase: 22
slug: bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-01
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for scheduled PC matching, protected metadata
> application, and administrator review.

---

## Test Infrastructure

| Property               | Value                                                                                                                                                                                         |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Framework**          | pytest with pytest-asyncio and Vitest                                                                                                                                                         |
| **Config file**        | `backend/pytest.ini`, `frontend/vitest.config.ts`                                                                                                                                             |
| **Quick run command**  | `cd backend && uv run pytest tests/handler/metadata/test_pc_match_handler.py tests/handler/test_scan_handler.py tests/tasks/test_scan_library.py tests/endpoints/roms/test_pc_metadata.py -q` |
| **Full suite command** | `trunk fmt && trunk check && cd frontend && npm run typecheck && npm run test`                                                                                                                |
| **Estimated runtime**  | ~120 seconds for focused tests, environment dependent                                                                                                                                         |

---

## Sampling Rate

- **After every task commit:** Run the relevant focused pytest or Vitest command.
- **After every plan wave:** Run the full targeted backend and frontend suites.
- **Before `/gsd:verify-work`:** Run `trunk fmt && trunk check`, the focused
  suites, frontend typecheck, and isolated browser UAT.
- **Max feedback latency:** 120 seconds.

---

## Per-Task Verification Map

| Task ID  | Plan | Wave | Requirement            | Threat Ref | Secure Behavior                                                                                        | Test Type      | Automated Command                                                                                     | File Exists | Status     |
| -------- | ---- | ---- | ---------------------- | ---------- | ------------------------------------------------------------------------------------------------------ | -------------- | ----------------------------------------------------------------------------------------------------- | ----------- | ---------- |
| 22-01-01 | 01   | 1    | D-01, D-02, D-03, D-04 | T-22-01    | Only one valid parent or parent-listed DLC candidate applies; ties queue without mutation.             | unit/handler   | `uv run pytest tests/handler/metadata/test_pc_match_handler.py tests/handler/test_scan_handler.py -q` | ❌ W0       | ⬜ pending |
| 22-01-02 | 01   | 1    | D-02, D-04, D-05       | T-22-02    | Queue upsert is target-version-bound, idempotent, and cannot overwrite manual data.                    | model/database | `uv run pytest tests/handler/database/test_pc_automation.py -q`                                       | ❌ W0       | ⬜ pending |
| 22-02-01 | 02   | 2    | D-07, D-08             | T-22-03    | Scheduled scan includes Steam, production uses 15 minutes, and 10-second override is development-only. | task/config    | `uv run pytest tests/tasks/test_scan_library.py -q`                                                   | ✅          | ⬜ pending |
| 22-02-02 | 02   | 2    | D-05, D-06             | T-22-04    | List, accept, correct, skip, and batch reload server-side state and reject stale or mixed actions.     | endpoint       | `uv run pytest tests/endpoints/roms/test_pc_automation.py -q`                                         | ❌ W0       | ⬜ pending |
| 22-03-01 | 03   | 3    | D-05, D-06, D-08       | T-22-04    | v2 queue handles progress, empty/loading/error, paging, correction, and batch actions accessibly.      | Vitest         | `npm run test -- --run src/v2/components/Settings/PcAutomationQueue.test.ts`                          | ❌ W0       | ⬜ pending |
| 22-03-02 | 03   | 3    | D-08                   | T-22-03    | Source fixture digest remains unchanged after automatic scan and queue review.                         | integration    | `uv run pytest tests/integration/test_scan_source_immutability.py -q`                                 | ✅          | ⬜ pending |

_Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky_

---

## Wave 0 Requirements

- [ ] `backend/tests/handler/database/test_pc_automation.py` — durable queue
      fixtures for parent and component targets.
- [ ] `backend/tests/endpoints/roms/test_pc_automation.py` — protected queue
      list and mutation endpoint fixtures.
- [ ] `frontend/src/v2/components/Settings/PcAutomationQueue.test.ts` — queue
      loading, error, keyboard, correction, and batch behavior.

---

## Manual-Only Verifications

| Behavior                | Requirement | Why Manual                                                               | Test Instructions                                                                                                                                                                              |
| ----------------------- | ----------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 10-second UAT discovery | D-07        | Requires an isolated running scheduler and fixture library.              | Configure the development-only 10-second override, add a new named PC fixture and DLC, wait for processing, then confirm automatic enrichment or one queue entry and unchanged source digests. |
| Review queue workflow   | D-05, D-06  | Requires browser confirmation of candidate context and bulk interaction. | In the isolated UAT app, accept one safe item, correct one through MatchRomDialog, skip one item, and confirm a mixed/stale batch is rejected.                                                 |

---

## Validation Sign-Off

- [ ] All tasks have automated verification or explicit Wave 0 dependencies.
- [ ] Sampling continuity has no three consecutive tasks without automated verification.
- [ ] Wave 0 covers all missing test references.
- [ ] No watch-mode flags are used in CI verification.
- [ ] Focused feedback latency is at most 120 seconds where infrastructure is available.
- [ ] `nyquist_compliant: true` set after Wave 0 is complete.

**Approval:** pending
