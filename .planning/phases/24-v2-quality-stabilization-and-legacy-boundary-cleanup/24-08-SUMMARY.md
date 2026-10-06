---
phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup
plan: 08
subsystem: frontend-operations
tags: [vue, typescript, vitest, provider-resolution, locale, lifecycle, scan]
requires:
  - phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup
    provides: normalized storage-aware operation contracts and legacy scan translation from plan 24-07
provides:
  - shared field-, locale-, and region-aware provider resolution
  - lifecycle orchestrator wrapping the existing useScanLifecycle socket ownership
  - bounded concurrency, retry backoff, cancellation/resume, idempotency, diagnostics, and impact summaries
affects: [24-09 metadata-media-ownership, 24-10 operation-entry-point-migration]
tech-stack:
  added: []
  patterns:
    [
      single provider resolver,
      observer-backed lifecycle wrapper,
      stable job/item correlation,
      explicit partial/retryable outcomes,
    ]
key-files:
  created:
    - frontend/src/v2/composables/useProviderResolution.ts
    - frontend/src/v2/composables/useProviderResolution.test.ts
    - frontend/src/v2/composables/useLibraryOperation.ts
    - frontend/src/v2/composables/useLibraryOperation.test.ts
    - frontend/src/v2/components/Scan/OperationSummary.vue
  modified:
    - frontend/src/v2/data/contracts.ts
    - frontend/src/v2/data/operations.ts
    - frontend/src/v2/composables/useScanLifecycle/index.ts
key-decisions:
  - "Keep useScanLifecycle as the only socket subscriber and expose typed lifecycle observers to the orchestrator."
  - "Expand All provider selections into concrete enabled providers before legacy translation, with matcher gates represented separately."
  - "Normalize requested locales but record the actual provider response locale in provenance."
  - "Clamp concurrency to a bounded 1-16 range and make retries, cancellation, resume, and idempotency explicit in operation state."
patterns-established:
  - "Provider resolution is pure and reusable across full scan, platform scan, ROM refresh, and bulk refresh callers."
  - "Operation results retain operationId, jobId, item IDs, outcomes, diagnostics, and impact without using arrival order."
requirements-completed: [QA-02, QA-05, QA-06, QA-08]
duration: 10min
completed: 2026-10-06
---

# Phase 24 Plan 08: Shared provider resolution and lifecycle orchestration summary

**Shared locale-aware provider/policy resolution and an operational library lifecycle wrapper now sit above the existing normalized scan contract and socket lifecycle.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-10-06T12:15:00Z
- **Completed:** 2026-10-06T12:24:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Centralized concrete provider expansion, All-mode behavior, hash matcher gates, provider grouping, locale normalization, region propagation, and actual-locale provenance.
- Added a lifecycle orchestrator that wraps existing Pinia/socket ownership and provides stable correlation, idempotency, cancellation, resumability, bounded concurrency, rate-limit/backoff handling, structured diagnostics, retryable outcomes, and read-only impact summaries.
- Added a summary component for scope/provider/locale/region/policy impact and focused tests covering provider equivalence, IGDB-English plus Steam-localized planning, concurrency, and retry backoff.
- Preserved plan 24-07 at `5303ca6ea` and left unrelated dirty files unstaged.

## Task Commits

1. **Task 1: Centralize field- and locale-aware provider resolution** - `74104f198`
2. **Task 2: Centralize lifecycle and impact summary** - `f3d174abc`

## Files Created/Modified

- `frontend/src/v2/composables/useProviderResolution.ts` - Pure provider expansion, gating, locale, region, and provenance helpers.
- `frontend/src/v2/composables/useProviderResolution.test.ts` - Provider equivalence and locale/provenance tests.
- `frontend/src/v2/composables/useLibraryOperation.ts` - Operation state machine, bounded executor, backoff, cancellation, resume, retry, idempotency, diagnostics, and impact.
- `frontend/src/v2/composables/useLibraryOperation.test.ts` - Concurrency and retry/backoff tests.
- `frontend/src/v2/composables/useScanLifecycle/index.ts` - Existing lifecycle now exposes typed observers without adding another socket subscriber.
- `frontend/src/v2/components/Scan/OperationSummary.vue` - Read-only operation impact summary.
- `frontend/src/v2/data/contracts.ts` - Region, lifecycle status, diagnostic, attempt, and impact vocabulary.
- `frontend/src/v2/data/operations.ts` - Locale normalization, region normalization, and bounded execution normalization.

## Decisions Made

- Reused the existing scan socket adapter and Pinia lifecycle as the single event/state authority.
- Kept provider resolution independent of translated labels and preserved actual provider-returned locales.
- Represented partial/retryable behavior in typed operation outcomes rather than hiding it in global success/failure state.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The non-login SSH shell did not expose Node/npm on PATH. Verification was rerun successfully with the installed Node 24 path explicitly prepended; no repository change was required.
- Commit hooks formatted only the staged 24-08 files and reported no issues.

## Verification

- `npm run test -- src/v2/composables/useProviderResolution.test.ts src/v2/composables/useLibraryOperation.test.ts src/v2/data/operations.test.ts`
- Result: 3 files passed, 10 tests passed.
- `npm run typecheck`
- Result: passed with zero diagnostics.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 24-09 can consume the shared resolver and operation result/diagnostic vocabulary to add metadata/media ownership and per-item ledger behavior. Existing UI callers remain compatible and can migrate entry point by entry point in plan 24-10.

---

_Phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup_
_Completed: 2026-10-06_

## Self-Check: PASSED

- Summary exists.
- Task commits 74104f198 and f3d174abc exist.
- Plan 24-07 commit 5303ca6ea remains present.
