---
phase: 12
slug: dlc-detail-pages-for-local-pc-components
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-02
---

# Phase 12: DLC detail pages for local PC components - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                                                                            |
| ---------------------- | ------------------------------------------------------------------------------------------------ |
| **Framework**          | Vitest with Vue Test Utils                                                                       |
| **Config file**        | `frontend/vitest.config.ts`                                                                      |
| **Quick run command**  | `cd frontend && npm run test -- src/v2/components/GameDetails src/v2/views/PcDlcDetails.test.ts` |
| **Full suite command** | `cd frontend && npm run typecheck && npm run test && npm run build`                              |
| **Estimated runtime**  | ~180 seconds                                                                                     |

---

## Sampling Rate

- **After every task commit:** Run the focused Vitest command and `cd frontend && npm run typecheck`.
- **After every plan wave:** Run `cd frontend && npm run test`.
- **Before `/gsd:verify-work`:** The full frontend typecheck, test suite, and build must be green.
- **Max feedback latency:** 60 seconds for focused tests, excluding typecheck.

---

## Per-Task Verification Map

| Task ID  | Plan | Wave | Requirement      | Threat Ref                | Secure Behavior                                                                                  | Test Type | Automated Command                                                                                                                                                                                                                                                                   | File Exists | Status     |
| -------- | ---- | ---- | ---------------- | ------------------------- | ------------------------------------------------------------------------------------------------ | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ---------- |
| 12-02-01 | 02   | 1    | D-01, D-02       | T-12-01                   | Strict scalar parsing resolves only a DLC contained by the fetched visible parent ROM.           | unit      | `cd frontend && npm run test -- src/v2/views/PcDlcDetails.test.ts src/v2/router/routeInventory.test.ts`                                                                                                                                                                             | ❌ W0       | ⬜ pending |
| 12-04-01 | 04   | 1    | D-03, D-04, D-05 | T-12-04                   | First locale batch supplies the DLC detail copy contract.                                        | locale    | `cd frontend && python3 src/locales/check_i18n_sorted.py`                                                                                                                                                                                                                           | ✅          | ✅ green   |
| 12-05-01 | 05   | 1    | D-03, D-04, D-05 | T-12-04                   | Second locale batch supplies its complete DLC detail copy contract.                              | locale    | `cd frontend && python3 src/locales/check_i18n_sorted.py`                                                                                                                                                                                                                           | ✅          | ✅ green   |
| 12-01-01 | 01   | 2    | D-01, D-02       | T-12-01                   | Both local-DLC entry points use the canonical nested parent-ROM route.                           | unit      | `cd frontend && npm run test -- src/v2/views/GameDetails.test.ts src/v2/components/GameDetails/OverviewTab.test.ts src/v2/components/GameDetails/RelatedGamesGrid.test.ts src/v2/components/GameDetails/RelatedGameCard.test.ts src/v2/components/GameDetails/PcComponents.test.ts` | ✅ / ❌ W0  | ⬜ pending |
| 12-03-01 | 03   | 2    | D-03, D-04, D-05 | T-12-02, T-12-03, T-12-04 | The page renders only selected component metadata, owned media, and immutable manifest evidence. | unit      | `cd frontend && npm run test -- src/v2/components/GameDetails/PcDlcDetail.test.ts src/v2/components/GameDetails/PcDlcFiles.test.ts src/v2/views/PcDlcDetails.test.ts`                                                                                                               | ❌ W0       | ⬜ pending |
| 12-06-01 | 06   | 3    | D-04             | T-12-03, T-12-04          | Loading or navigating to the page issues no provider, selection, or source-mutating request.     | unit      | `cd frontend && npm run test -- src/v2/sourceMutationControls.test.ts src/v2/views/PcDlcDetails.test.ts`                                                                                                                                                                            | ✅ / ❌ W0  | ✅ green   |
| 12-06-02 | 06   | 3    | D-03, D-04, D-05 | T-12-04                   | Both completed locale batches have a matching, sorted global DLC-detail key set.                 | locale    | `cd frontend && python3 src/locales/check_i18n_locales.py && python3 src/locales/check_i18n_sorted.py`                                                                                                                                                                              | ✅          | ✅ green   |
| 12-06-03 | 06   | 3    | D-02, D-03       | T-12-02, T-12-04          | Both entries meet the responsive, theme, and universal-input contract.                           | manual    | `cd frontend && npm run typecheck && npm run test && npm run build`                                                                                                                                                                                                                 | ✅          | ⬜ pending |

_Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky_

---

## Wave 0 Requirements

- [ ] `frontend/src/v2/views/PcDlcDetails.test.ts` — direct route, invalid identifier, stale component, and non-DLC rejection coverage.
- [ ] `frontend/src/v2/components/GameDetails/PcDlcDetail.test.ts` — component title, summary, owned-media isolation, and cover fallback coverage.
- [ ] `frontend/src/v2/components/GameDetails/PcDlcFiles.test.ts` — manifest member, byte-size, and SHA-256 rendering coverage if the plan creates a dedicated file composite.
- [ ] `frontend/src/v2/components/GameDetails/OverviewTab.test.ts` and `RelatedGamesGrid.test.ts` — parent-ROM ID propagation to the local DLC card.
- [ ] Route-inventory test update if `frontend/src/v2/router/routeInventory.ts` is covered by an existing test.

---

## Manual-Only Verifications

| Behavior                                                                                              | Requirement | Why Manual                                                      | Test Instructions                                                                                                                            |
| ----------------------------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| The DLC page remains legible at 320px through 4K in both themes.                                      | D-03        | Responsive visual composition needs browser inspection.         | Visit a DLC route at each viewport in light and dark themes, verify cover fallback, title, summary, media, manifest, and parent back action. |
| Mouse, touch, keyboard, and gamepad navigation reach both entry points and return to the parent page. | D-02        | Input modality behavior requires an interactive v2 environment. | Navigate from the overview card and PC Components list using each modality, then activate back navigation.                                   |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verification or Wave 0 dependencies.
- [ ] Sampling continuity: no 3 consecutive tasks without automated verification.
- [ ] Wave 0 covers all missing references.
- [ ] No watch-mode flags.
- [ ] Focused feedback latency is below 60 seconds.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending
