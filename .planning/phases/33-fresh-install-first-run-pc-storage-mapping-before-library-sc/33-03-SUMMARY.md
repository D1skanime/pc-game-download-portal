---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 03
subsystem: ui
tags: [vue, vitest, storage-mapping, scan-gating]

requires:
  - phase: 33-01
    provides: GET-only server-backed mapping readiness contract
  - phase: 33-02
    provides: first-run route into the PC/Windows mapping workflow
provides:
  - Empty Home state gated by active reachable readable non-writable Windows mapping
  - Direct Scan route gated by the same GET-only readiness authority
  - Focused no-mutation contract coverage for Home and Scan
affects: [phase-33-04, frontend-v2, storage-mapping, library-scan]

tech-stack:
  added: []
  patterns:
    - Views consume the shared storage readiness API and never bootstrap or mutate mappings.
    - Scan controls and lifecycle are mounted only after readiness succeeds.

key-files:
  created:
    - frontend/src/v2/views/Home.test.ts
    - frontend/src/v2/views/Scan.test.ts
  modified:
    - frontend/src/v2/views/Home.vue
    - frontend/src/v2/views/Scan.vue

key-decisions:
  - "Use the canonical server platform identity win to resolve readiness, never infer readiness from local filesystem state."
  - "Keep the existing scan lifecycle unchanged behind a readiness gate and add a direct scan() guard."

requirements-completed: [PGDP-33-01]

duration: 28 min
completed: 2026-10-15
---

# Phase 33 Plan 03: Gate Home and Scan on mapping readiness

**Empty Home and direct Scan navigation now expose scanning only after the server confirms a healthy read-only PC/Windows mapping.**

## Performance

- **Duration:** 28 min
- **Started:** 2026-10-15T15:16:00Z
- **Completed:** 2026-10-15T15:44:38Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Home resolves the canonical `win` platform and consumes `getMappingReadiness` before rendering the empty-library Scan CTA.
- Scan shows mapping guidance and recovery while readiness is missing, unhealthy, loading, or errored, and loads filesystem scan options only after readiness.
- Readiness checks remain GET-only, with direct scan invocation guarded even if UI controls are bypassed.
- Added focused Home and Scan tests covering gating, readiness recovery, and absence of mutation calls.

## Task Commits

1. **Task 1: Gate empty Home on read-only mapping readiness** - `d27c2932f`
2. **Task 2: Gate Scan controls on the same read-only readiness** - `aa4024474`

## Files Created/Modified

- `frontend/src/v2/views/Home.vue` - Adds mapping readiness state, mapping guidance, retry handling, and conditional Scan CTA rendering.
- `frontend/src/v2/views/Home.test.ts` - Verifies Home readiness gate and mutation-free contract.
- `frontend/src/v2/views/Scan.vue` - Adds the shared readiness gate, recovery path, and direct operation guard.
- `frontend/src/v2/views/Scan.test.ts` - Verifies Scan readiness gating and lifecycle protection.

## Decisions Made

- Reused Plan 01's shared GET-only readiness helper rather than introducing a second client-side predicate.
- Used the persisted `win` platform ID for mapping lookup, while routing to library management if the platform is not yet available.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test harness] Fixed Vitest source-path resolution**
- **Found during:** Task 1 focused verification
- **Issue:** `import.meta.url` was transformed to a non-file URL by the containerized Vitest runner, so the new focused tests failed before executing.
- **Fix:** Read the planned sibling view sources from the frontend test working directory.
- **Files modified:** `frontend/src/v2/views/Home.test.ts`, `frontend/src/v2/views/Scan.test.ts`
- **Verification:** Both focused files pass, 6 tests total.
- **Committed in:** `d27c2932f`, `aa4024474`

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** No product-scope change; the verification harness now runs in the repository's containerized Vitest environment.

## Issues Encountered

- The canonical Linux host does not expose `gsd-sdk` or a host Node runtime, so the prescribed SDK state handlers were unavailable. State and roadmap close-out edits were applied manually with narrow, exact replacements, preserving the pre-existing unrelated `.planning/STATE.md` changes.
- The focused container checks passed: Home and Scan tests 6/6, targeted Prettier formatting, and `vue-tsc --noEmit` produced no diagnostics.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 33 Plan 03 is complete. Plan 04 can run its bounded validation matrix and Linux/browser UAT against the now-gated Home and Scan entry points.

## Self-Check: PASSED

- `33-03-SUMMARY.md` exists.
- Task commits `d27c2932f` and `aa4024474` exist in Git history.
- Planned files are present and no unexpected deletions were introduced.

---
*Phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc*
*Completed: 2026-10-15*
