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

| Task ID  | Plan | Wave | Requirements           | Threat Ref                         | Secure Behavior                                                                                                                         | Test Type            | Automated Command                                                                                                                                                                                            | File Exists | Status     |
| -------- | ---- | ---- | ---------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------- | ---------- |
| 22-01-01 | 01   | 1    | D-02, D-04, D-05       | T-22-01, T-22-03                   | Defines idempotent parent/component queue transitions, stale detection, and manual-protection refusal before implementation.            | database TDD         | `cd backend && uv run pytest tests/handler/database/test_pc_automation.py -q`                                                                                                                                | ❌ W0       | ⬜ pending |
| 22-01-02 | 01   | 1    | D-02, D-04, D-05       | T-22-01, T-22-02                   | Migration stores only bounded provider evidence with unique target identity and no source-path or secret data.                          | migration/model      | `cd backend && uv run pytest tests/handler/database/test_pc_automation.py -q && uv run alembic upgrade head && uv run alembic downgrade -1`                                                                  | ❌ W0       | ⬜ pending |
| 22-01-03 | 01   | 1    | D-02, D-04, D-05       | T-22-01, T-22-03                   | Guarded queue CRUD requires current queue/target versions and terminal skip only for the same incarnation and fingerprint.              | database             | `cd backend && uv run pytest tests/handler/database/test_pc_automation.py -q`                                                                                                                                | ❌ W0       | ⬜ pending |
| 22-02-01 | 02   | 2    | D-01, D-02, D-03, D-04 | T-22-04, T-22-05                   | Tests exact-one parent/DLC decisions, ties, failures, and preserved manual/provider-protected data.                                     | handler TDD          | `cd backend && uv run pytest tests/handler/metadata/test_pc_automation.py tests/handler/metadata/test_pc_match_handler.py -q`                                                                                | ❌ W0       | ⬜ pending |
| 22-02-02 | 02   | 2    | D-01, D-02, D-03, D-04 | T-22-04, T-22-05                   | Reconstructs queued candidates server-side, recomputes fingerprint/cardinality, then applies only canonical guarded persistence.        | handler/scan         | `cd backend && uv run pytest tests/handler/metadata/test_pc_automation.py tests/handler/metadata/test_pc_match_handler.py tests/handler/test_scan_handler.py -q`                                             | ❌ W0       | ⬜ pending |
| 22-02-03 | 02   | 2    | D-07, D-08             | T-22-03, T-22-06                   | Mapped scan includes enabled Steam, uses 15-minute production cron, and permits only guarded DEV_MODE 10-second RQ interval scheduling. | task/config          | `cd backend && uv run pytest tests/tasks/test_scan_library.py -q`                                                                                                                                            | ✅          | ⬜ pending |
| 22-03-01 | 03   | 3    | D-05, D-06             | T-22-07, T-22-08, T-22-09          | Endpoint tests require authorization, visibility, server-side candidate reconstruction, and all-or-nothing batch prevalidation.         | endpoint TDD         | `cd backend && uv run pytest tests/endpoints/roms/test_pc_automation.py -q`                                                                                                                                  | ❌ W0       | ⬜ pending |
| 22-03-02 | 03   | 3    | D-05, D-06             | T-22-07, T-22-08, T-22-09, T-22-10 | Protected endpoints use ROMS_READ/ROMS_WRITE and reject forged, mixed, stale, invisible, or protected target actions.                   | endpoint             | `cd backend && uv run pytest tests/endpoints/roms/test_pc_automation.py -q`                                                                                                                                  | ❌ W0       | ⬜ pending |
| 22-03-03 | 03   | 3    | D-05, D-06             | T-22-07                            | Generated frontend contracts replace hand-authored API types after schema verification.                                                 | OpenAPI/typecheck    | `cd frontend && npm run generate && npm run typecheck`                                                                                                                                                       | ✅          | ⬜ pending |
| 22-04-01 | 04   | 4    | D-05, D-06             | T-22-11, T-22-12, T-22-13, T-22-14 | UI tests cover loading, error, paging, keyboard actions, existing-dialog correction, and rejected batch feedback.                       | Vitest TDD           | `cd frontend && npm run test -- --run src/v2/components/Settings/PcAutomationQueue.test.ts`                                                                                                                  | ❌ W0       | ⬜ pending |
| 22-04-02 | 04   | 4    | D-05, D-06, D-08       | T-22-11, T-22-12, T-22-13, T-22-14 | Paginated v2 queue keeps selection local, applies no optimistic metadata write, and uses server validation.                             | Vitest/typecheck     | `cd frontend && npm run test -- --run src/v2/components/Settings/PcAutomationQueue.test.ts && npm run typecheck`                                                                                             | ❌ W0       | ⬜ pending |
| 22-04-03 | 04   | 4    | D-05, D-06, D-08       | T-22-11, T-22-12                   | Scope-gated administration tab preserves permission and route-query isolation without editing locale files.                             | Vitest/typecheck     | `cd frontend && npm run test -- --run src/v2/components/Settings/PcAutomationQueue.test.ts && npm run typecheck`                                                                                             | ❌ W0       | ⬜ pending |
| 22-05-01 | 05   | 5    | D-05, D-06, D-08       | T-22-18, T-22-19                   | English settings keys cover every queue label, action, safety state, and failure outcome.                                               | i18n source          | `cd frontend && python3 src/locales/check_i18n_sorted.py`                                                                                                                                                    | ✅          | ⬜ pending |
| 22-05-02 | 05   | 5    | D-05, D-06, D-08       | T-22-18, T-22-19                   | All 17 non-English locale files receive the complete translated queue key set with no placeholders.                                     | i18n translation     | `cd frontend && python3 src/locales/check_i18n_locales.py && python3 src/locales/check_i18n_sorted.py`                                                                                                       | ✅          | ⬜ pending |
| 22-05-03 | 05   | 5    | D-05, D-06, D-08       | T-22-18, T-22-19                   | Parity, key ordering, and frontend compilation prove the localized queue contract is consumable.                                        | i18n/typecheck       | `cd frontend && python3 src/locales/check_i18n_locales.py && python3 src/locales/check_i18n_sorted.py && npm run typecheck`                                                                                  | ✅          | ⬜ pending |
| 22-06-01 | 06   | 6    | D-07, D-08             | T-22-15                            | Isolated mapped fixture preserves digest, names, sizes, structure, and timestamps through interval automation and review outcomes.      | integration          | `cd backend && uv run pytest tests/integration/test_scan_source_immutability.py tests/tasks/test_scan_library.py tests/handler/metadata/test_pc_automation.py tests/endpoints/roms/test_pc_automation.py -q` | ✅          | ⬜ pending |
| 22-06-02 | 06   | 6    | D-07, D-08             | T-22-16, T-22-17                   | UAT record fixes the development-only ten-second configuration and records reproducible isolated evidence.                              | integration evidence | `cd backend && uv run pytest tests/integration/test_scan_source_immutability.py -q`                                                                                                                          | ✅          | ⬜ pending |
| 22-06-03 | 06   | 6    | D-07, D-08             | T-22-15, T-22-16, T-22-17          | Browser UAT verifies queue progress, valid and rejected review actions, and unchanged isolated source evidence.                         | integration + human  | `cd backend && uv run pytest tests/integration/test_scan_source_immutability.py tests/tasks/test_scan_library.py tests/handler/metadata/test_pc_automation.py tests/endpoints/roms/test_pc_automation.py -q` | ✅          | ⬜ pending |

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
