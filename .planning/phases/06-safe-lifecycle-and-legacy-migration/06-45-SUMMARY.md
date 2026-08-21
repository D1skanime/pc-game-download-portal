---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 45
subsystem: frontend
tags: [manuals, single-upload, accessibility, concurrency, v2]
requires:
  - phase: 06-40
    provides: singular primary-manual upload service and stable progress identity
  - phase: 06-41
    provides: mutation-disabled stable manual viewers
  - phase: 06-43
    provides: failure-atomic backend replacement and bounded conflict
provides:
  - Visible single-operation primary-manual upload and replacement state machine
  - Same-ROM authoritative refresh before truthful success
  - Active-v2 fan-out coordinator removal with frozen v1 compatibility
affects: [manual-upload, game-details, upload-progress, phase-8-v1-removal]
tech-stack:
  added: []
  patterns:
    [
      feature-owned pending state,
      single-file validation,
      identity-guarded refresh,
    ]
key-files:
  created:
    - frontend/src/v2/components/GameDetails/ManualSubtab.test.ts
  modified:
    - frontend/src/v2/components/GameDetails/ManualSubtab.vue
    - frontend/src/v2/components/Dialogs/GlobalDialogs.vue
    - frontend/src/v2/sourceMutationControls.test.ts
  deleted:
    - frontend/src/v2/components/Dialogs/ManualUploadTargetDialog.vue
key-decisions:
  - "ManualSubtab owns exactly one singular primary-manual request and blocks every local mutation entry point through refresh."
  - "The existing viewer remains authoritative until same-ROM refresh, and currentRom changes only when its identity still matches."
  - "Only the active-v2 coordinator is removed; frozen v1 plural service, emitter, consumers, and progress host remain intact."
metrics:
  duration: 28m
  completed: 2026-08-21
---

# Phase 6 Plan 45: Single Primary Manual Interaction Summary

**One-file primary-manual uploads with a stable viewer, visible accessible pending state, guarded authoritative refresh, and truthful terminal notifications.**

## Performance

- **Duration:** 28m
- **Tasks:** 2
- **Files changed:** 5
- **Tests:** 672 full-suite tests passed

## Accomplishments

- Replaced the active-v2 plural emitter handoff with one direct `romApi.uploadManual` request bound to the initiating ROM and exact File.
- Kept the current PDF or Markdown viewer mounted while upload and refresh are pending, with `aria-busy`, one polite status, loading semantics, and disabled drop/delete/re-download controls.
- Added exact validation, duplicate-gesture blocking, safe pre-commit failure copy, bounded conflict copy, post-commit refresh warning, retry behavior, and navigation-safe current-ROM updates.
- Removed only the v2 coordinator import, mount, and file while preserving the plural service/emitter and every frozen v1 consumer.
- Added a behavior-first feature regression spanning empty, replacement, pending, success, failure, conflict, refresh failure, permission, native-input, responsive-structure, and compatibility contracts.

## Task Commits

1. **Task 1 RED: Complete visible manual state-machine contract** - `f18913f3c`
2. **Task 2 GREEN: Singular active-v2 manual interaction** - `364bb2764`

## Decisions Made

- File validation requires exactly one `.pdf` or `.md` file with a compatible empty, PDF, Markdown, or plain-text MIME.
- Upload and authoritative refresh share one local pending boundary, so no second gesture or viewer mutation can race either phase.
- Refresh updates the ROM collection, but replaces `currentRom` only when the user is still viewing the initiating ROM.
- API errors use approved localized safety copy only; a successful save followed by refresh failure uses only the reload warning.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated the retained source-control assertion for approved replacement copy**

- **Found during:** Task 2 focused GREEN verification
- **Issue:** `sourceMutationControls.test.ts` still expected the superseded `common.upload` label even though the approved UI contract requires `rom.replace-manual`.
- **Fix:** Updated only the manual resources-only assertion; unrelated source-mutation assertions remain unchanged.
- **Files modified:** `frontend/src/v2/sourceMutationControls.test.ts`
- **Commit:** `364bb2764`

**2. [Rule 3 - Blocking] Supplied the source inventory's checked-in backend fixture read**

- **Found during:** Task 2 focused GREEN verification
- **Issue:** The pinned frontend-only bind made the selected source-mutation test resolve its required `../backend/endpoints/roms/patch.py` fixture as missing.
- **Fix:** Repeated the exact owned Node 24 lifecycle with an additional read-only canonical backend bind at `/backend`; source content and test behavior were unchanged.
- **Verification:** Four focused files passed 17 tests, typecheck passed, and the exact owned volume was removed and proved absent.
- **Commit:** Not applicable.

## Issues Encountered

- The first GREEN lifecycle failed only on the stale label assertion and missing read-only backend fixture bind; its exact owned volume was still removed before retry.
- Existing suite warnings from Vue Router, Storybook accessibility TODOs, Browserslist age, chunk sizing, and the third-party PDF package remained non-fatal and outside this plan.
- No development service was started, restarted, or deployed. The interaction matrix is covered by component/state assertions and preserved responsive structure; no live deployed manual UI was claimed.

## Known Stubs

None.

## Threat Flags

None. The plan threat model covers file selection, duplicate gestures, permission gating, bounded notifications, frozen-v1 compatibility, and same-ROM refresh identity.

## Verification

- Deterministic RED: Vitest exited 1 and the pinned JSON parser accepted exactly the named behavioral failure with the compatibility assertion passing; task-owned result and volume cleanup passed.
- Focused GREEN: `rom.test.ts`, `ManualViewerControls.test.ts`, `ManualSubtab.test.ts`, and `sourceMutationControls.test.ts` passed 17 tests; `vue-tsc --noEmit` passed.
- Full frontend: 58 files and 672 tests passed under Node 24; typecheck passed.
- Production build passed to trapped `/tmp/romm-p0645-build.*` output, which was removed with the disposable runner.
- Locale parity passed across all 18 locales and every `rom.json` key order was sorted.
- Hooked scoped Trunk checks passed all modified production/test files; `git diff --check` passed.
- Static gates proved active-v2 contains no plural call, `Promise.allSettled`, coordinator event, coordinator mount, or coordinator file.
- Frozen v1 consumers, plural service/emitter contracts, upload store, and UploadProgressToast are byte-unchanged from the RED commit.
- All exact task/plan-owned Node volumes and reporter/build artifacts were removed and proved absent.
- The 28-entry pre-existing untracked baseline retained SHA-256 `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1`.

## User Setup Required

None.

## Self-Check: PASSED

The summary target, all key files, the intentional coordinator deletion, and commits `f18913f3c` and `364bb2764` exist. Focused/full gates passed, disposable resources are absent, tracked status is clean, and the exact 28-entry baseline is preserved.
