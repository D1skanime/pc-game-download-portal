---
quick_task: 261010-wq3
slug: fix-pc-match-dialog-so-successful-game-c
title: Close PC MatchRomDialog after successful assignment
status: planned
created: 2026-10-11
---

# Plan: Close PC MatchRomDialog after successful assignment

## Objective

Fix the v2 PC `MatchRomDialog` so a successful game or component metadata assignment closes as soon as the assignment API resolves successfully. Keep the post-assignment refresh as a best-effort UI update whose failure cannot reopen or keep the dialog visible, and add regression coverage for both parent-game and component assignment paths where applicable. Do not change backend contracts, refresh ownership, unrelated classic matching behavior, or deployment state.

## Current findings

- `frontend/src/v2/components/Dialogs/MatchRomDialog.vue` performs the PC assignment through `selectPcMetadataCandidate` for a parent game or `selectPcComponentMetadataCandidate` for a component.
- The same `try` block currently awaits `pcRefresh.value?.()` before showing success and calling `closeDialog()`. A refresh rejection is therefore reported as `rom.update-failed` and leaves the dialog open even though assignment already succeeded.
- The classic non-PC branch already closes after its assignment API succeeds and should remain behaviorally unchanged.
- `frontend/src/v2/components/Dialogs/MatchRomDialog.test.ts` currently verifies PC target classification and source-level operation guards, so the regression can extend this focused suite without introducing broad unrelated component coverage.
- The PC refresh callback is supplied by `PcComponents.vue` or `PcDlcDetail.vue` and is allowed to be asynchronous. The fix must not make those callers responsible for dialog lifecycle.

## Tasks

### 1. Separate PC assignment success from post-assignment refresh

Files:

- `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`

Plan:

- Keep both existing PC assignment API selections, payload construction, expected-version guard, loading state, success snackbar, and assignment-error snackbar intact.
- Treat resolution of the selected parent-game or component assignment API as the success boundary: clear the matching state and call `closeDialog()` immediately after that API succeeds, before awaiting any refresh callback.
- Invoke `pcRefresh.value?.()` only after the dialog has been closed, in a separate best-effort error boundary. A rejected refresh must not enter the assignment `catch`, must not show `rom.update-failed`, and must not leave `show` true. Report the refresh failure only through an existing non-blocking error mechanism if one is already appropriate, without adding a new locale contract.
- Preserve the existing behavior when the assignment API itself rejects: keep the dialog open, clear the loading state, and show the assignment failure snackbar. Do not alter the classic ROM matching branch.

Verify: `cd frontend && npm run typecheck`

### 2. Add focused regression coverage for close timing and refresh failures

Files:

- `frontend/src/v2/components/Dialogs/MatchRomDialog.test.ts`

Plan:

- Extend the existing focused MatchRomDialog regression suite with assertions that the PC success path closes immediately after `selectPcMetadataCandidate` or `selectPcComponentMetadataCandidate` resolves, rather than waiting for `pcRefresh`.
- Cover a refresh callback that rejects after assignment success and assert that the dialog-close path remains unconditional, the assignment failure message is not used for the refresh rejection, and both parent-game and component endpoint guards remain present.
- Retain or strengthen the API-failure case so an assignment rejection still keeps the dialog open and uses the update-failure path. Keep tests limited to this dialog's lifecycle and do not duplicate unrelated MatchRom body or provider-filter tests.

Verify: `cd frontend && npm run test -- --run src/v2/components/Dialogs/MatchRomDialog.test.ts`; `cd frontend && npm run typecheck`

## Expected files

- `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`
- `frontend/src/v2/components/Dialogs/MatchRomDialog.test.ts`

## Dependency order

Task 1 precedes Task 2 because the regression tests must exercise and guard the final close-before-refresh control flow. No backend, generated type, locale, or API service changes are expected.

## Acceptance criteria

- A successful PC parent-game assignment closes `MatchRomDialog` immediately after the assignment API resolves.
- A successful PC component assignment closes `MatchRomDialog` immediately after the assignment API resolves.
- A refresh callback that rejects after assignment success cannot keep the dialog open and is not reported as an assignment failure.
- An assignment API rejection still keeps the dialog open and reports the existing update failure.
- Existing expected-version, selected-media, endpoint, success, loading, and classic matching behavior remain intact.
- Focused Vitest coverage and frontend typecheck pass.
- No source implementation or commit is made as part of this planning-only task.

## Source audit

| Source   | Item                                                                                                                     | Coverage                      |
| -------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------- |
| GOAL     | Close PC MatchRomDialog after successful game/component assignment and isolate refresh errors                            | Tasks 1-2                     |
| REQ      | No phase requirement IDs supplied for this quick task                                                                    | N/A                           |
| RESEARCH | No separate research artifact; existing code and project skills provide the relevant constraints                         | Covered by findings/tasks     |
| CONTEXT  | No CONTEXT.md decisions supplied; user explicitly requires Linux-only planning, no source edits, and regression coverage | Scope and acceptance criteria |

## Verification

- `cd frontend && npm run test -- --run src/v2/components/Dialogs/MatchRomDialog.test.ts`
- `cd frontend && npm run typecheck`
- `git diff --check`
- Confirm `git status --short` shows only the requested quick `PLAN.md` artifact changed by this planning task.

## Out of scope

- No backend changes, API contract changes, generated types, translations, refresh-caller redesign, or visual redesign.
- No deployment, service restart, source implementation, or commit in this planning-only task.
