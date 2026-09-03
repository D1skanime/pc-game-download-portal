---
phase: 12
slug: dlc-detail-pages-for-local-pc-components
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-03
---

# Phase 12: DLC detail pages for local PC components - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property               | Value                                                                                                                                                 |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Frontend framework** | Vitest with Vue Test Utils (`frontend/vitest.config.ts`)                                                                                              |
| **Backend framework**  | pytest (`backend/tests/endpoints/roms/test_pc_metadata.py`)                                                                                           |
| **Quick frontend run** | `cd frontend && npm run test -- src/v2/components/GameDetails src/v2/components/Dialogs src/v2/components/MatchRom src/v2/views/PcDlcDetails.test.ts` |
| **Quick backend run**  | `cd backend && uv run pytest tests/endpoints/roms/test_pc_metadata.py tests/handler/metadata/test_pc_match_handler.py -q`                             |
| **Static checks**      | `cd frontend && npm run typecheck`; `trunk fmt --no-fix` and `trunk check --no-fix` for touched files                                                 |

## Sampling Rate

- **After every task commit:** Run the task's focused frontend or backend
  command plus its static check.
- **After every plan wave:** Run both quick commands and frontend typecheck.
- **Before `/gsd:verify-work`:** When models change, run migration upgrade and
  downgrade checks, regenerate OpenAPI frontend types, then run full typecheck,
  test suite, and build.
- **Max feedback latency:** 60 seconds for focused checks, excluding migration
  and type generation.

## Per-Task Verification Map

| Work area                              | Requirement                   | Secure behavior                                                                                                                           | Test type                  | Required proof                                                                                                                       | File Exists | Status     |
| -------------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------- | ---------- |
| Shared parent/component matcher target | D-07, D-08, D-09              | A component match never calls generic `updateRom`; confirmation targets only the nested component API.                                    | Vue unit                   | Parent and DLC entries mount the same matcher with different typed targets; component confirmation calls only the component adapter. | ❌ W0       | ⬜ pending |
| Candidate search and confirmation      | D-07, D-09, D-10              | Server recomputes candidate data from the explicit request and accepts only selected candidate/media references belonging to that result. | pytest endpoint/handler    | Query/selection mismatch is rejected; cancel and preview leave metadata/media unchanged.                                             | ❌ W0       | ⬜ pending |
| Owned component media                  | D-04, D-05, D-10, D-11        | Uploads and provider-media imports enter only RomM-owned storage; parent, sibling, and source tree remain unchanged.                      | pytest endpoint + Vue unit | MIME, size, ownership, and containment tests pass; source mutation inventory stays clean.                                            | ❌ W0       | ⬜ pending |
| Component-scoped notes                 | D-03, D-06                    | A DLC note is visible and mutable only for that component under normal permission rules.                                                  | pytest endpoint + Vue unit | Parent and sibling notes never appear; unauthorised or foreign-component writes fail.                                                | ❌ W0       | ⬜ pending |
| DLC detail tabs and actions            | D-01 through D-06, D-11, D-12 | Route renders Overview, Files, Media, Notes only. It exposes no DLC save-data tab, parent media, or parent downloads.                     | Vue unit                   | Invalid/stale/foreign/non-DLC routes have only an escape state; tabs and overflow actions are component-bounded.                     | ❌ W0       | ⬜ pending |
| Component files and downloads          | D-04, D-11, D-12              | Downloads resolve only a selected component manifest member through authorised endpoints.                                                 | Vue unit + endpoint        | Parent files and raw paths cannot be requested; rendered hash/size evidence matches the selected component.                          | ❌ W0       | ⬜ pending |
| Locale and generated contracts         | D-03, D-08, D-11              | All copy is translated and API schemas/types agree.                                                                                       | static                     | Locale parity/sort, OpenAPI generation, and typecheck exit zero.                                                                     | ❌ W0       | ⬜ pending |

_Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky_

## Wave 0 Requirements

- [ ] Add or extend tests for the typed shared matcher, `PcComponents`, DLC
      overflow action, and four-tab DLC page.
- [ ] Add endpoint and handler tests for explicit component matching,
      media-reference confirmation, owned-media containment, notes, and bounded
      file downloads.
- [ ] Add migration tests when component-owned media or notes require models.
- [ ] Extend `frontend/src/v2/sourceMutationControls.test.ts` for all new
      matching, upload, import, note, and download seams.

## Manual-Only Verifications

| Behavior                                                                                                     | Requirement             | Why manual                                                            | Test instructions                                                                                                                                                            |
| ------------------------------------------------------------------------------------------------------------ | ----------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The same `ROM zuordnen` dialog appears from PC-parent search, PC-component search, and DLC overflow actions. | D-07, D-08              | Interaction equivalence and visual hierarchy need browser inspection. | In light and dark themes, open every entry point, change provider filters, choose grid/list, inspect description and cover selection, then cancel and confirm independently. |
| DLC tabs work at xs, sm, md, and xl with every input mode.                                                   | D-03 through D-06, D-11 | Responsive composition and gamepad focus require a running app.       | Use mouse, touch, keyboard, and gamepad through tab changes, overflow menu, uploads, notes, and owned-media deletion confirmation.                                           |
| Explicit confirmation is required before provider-media import.                                              | D-10                    | Browser flow proves no side effect while browsing/cancelling.         | Compare media before opening, filtering, previewing, and cancelling the matcher, then confirm and verify only that DLC changes.                                              |

## Database and Type Generation Gate

If models or endpoint schemas change, run migration upgrade and downgrade checks
for MariaDB and PostgreSQL, regenerate `frontend/src/__generated__/` from
OpenAPI, then run frontend typecheck. Pre-generated types alone cannot pass
this phase.

## Validation Sign-Off

- [ ] All planned tasks have focused automated verification or Wave 0 tests.
- [ ] Sampling continuity has no three consecutive tasks without automated checks.
- [ ] Wave 0 covers every missing test seam above.
- [ ] No watch-mode flags are used.
- [ ] Feedback latency is below 60 seconds for focused checks.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** pending
