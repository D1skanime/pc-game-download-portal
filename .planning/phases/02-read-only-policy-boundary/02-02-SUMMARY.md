---
phase: 02-read-only-policy-boundary
plan: 02
subsystem: filesystem-security
tags: [python, openat, file-descriptors, nofollow, capabilities]
requires:
  - phase: 02-read-only-policy-boundary
    provides: closed storage operation policy and trusted descriptors
provides:
  - Descriptor-relative no-follow traversal below trusted external roots
  - Eight operation-specific, context-managed read capabilities
  - Adversarial symlink, race, lifecycle, and immutability evidence
affects: [external-read-consumers, storage-inventory, downloads, scans]
tech-stack:
  added: []
  patterns: [descriptor-owning capabilities, per-component openat traversal]
key-files:
  created:
    - backend/handler/filesystem/storage_access.py
    - backend/tests/handler/filesystem/test_storage_access.py
  modified:
    - backend/handler/filesystem/__init__.py
key-decisions:
  - "External access authorizes before opening the root and retains an already-open target descriptor."
  - "Every approved operation has a separate public capability type with no raw path or generic open surface."
patterns-established:
  - "Descriptor walk: open every component relative to its parent with O_NOFOLLOW and close intermediates immediately."
  - "Capability lifetime: context managers own exactly one target descriptor and reject use after close."
requirements-completed: [SAFE-01, SAFE-06, TEST-03]
duration: 7min
completed: 2026-08-09
---

# Phase 2 Plan 2: Descriptor-Bound External Access Summary

**Race-resistant external reads with per-component no-follow traversal and eight narrow FD-owning capabilities**

## Performance

- **Duration:** 7 min
- **Started:** 2026-08-09T22:12:30Z
- **Completed:** 2026-08-09T22:19:31Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Bound authorization to descriptor-relative access without returning reusable paths.
- Added separate RESOLVE, LIST, STAT, READ, SCAN, HASH, STREAM, and DOWNLOAD capability surfaces.
- Proved symlink rejection, name-swap containment, deterministic closure, partial-open cleanup, and unchanged source manifests.

## Task Commits

Each task was committed atomically:

1. **Task 02-02-01: Specify capability surfaces and adversarial descriptor behavior** - `a93c9e2d1` (test)
2. **Task 02-02-02: Implement operation-bound descriptor capabilities** - `a6327744d` (feat)

## Files Created/Modified

- `backend/handler/filesystem/storage_access.py` - Descriptor walker and eight operation-specific capabilities.
- `backend/handler/filesystem/__init__.py` - Public exports for the access boundary.
- `backend/tests/handler/filesystem/test_storage_access.py` - Surface, symlink, race, FD lifetime, kind, Unicode, and manifest evidence.

## Decisions Made

- Authorization uses the trusted external descriptor before any filesystem open.
- Directory traversal uses `dir_fd`, `O_NOFOLLOW`, `O_DIRECTORY`, `O_RDONLY`, and `O_CLOEXEC`; capabilities retain only the final descriptor.
- Resolve returns descriptor metadata, not a path, preserving the no-ambient-authority contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Normalized legacy SDK progress output**

- **Found during:** Plan metadata update
- **Issue:** The legacy state and roadmap writer reported 56 percent but left stale progress text and emitted a malformed roadmap table row.
- **Fix:** Synchronized the displayed progress and restored valid table alignment without changing plan counts.
- **Files modified:** `.planning/STATE.md`, `.planning/ROADMAP.md`
- **Verification:** State reports 9 of 16 completed plans and the roadmap reports 2 of 9 Phase 2 plans.

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Metadata only; implementation scope is unchanged.

## Issues Encountered

- The host does not expose `uv`; verification ran in the existing `romm-dev` container against the canonical bind-mounted checkout.
- The legacy state updater required a formatting correction after reporting the correct calculated progress.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. Empty chunk/result lists are internal accumulators and do not flow to a placeholder UI or incomplete behavior.

## Verification

- `uv run pytest tests/handler/filesystem/test_storage_policy.py tests/handler/filesystem/test_storage_access.py -x`: 277 passed.
- Commit hooks formatted and checked every task file without bypasses.

## Self-Check: PASSED

- Created files exist in the canonical Linux checkout.
- Task commits `a93c9e2d1` and `a6327744d` exist in repository history.
- No tracked file deletions occurred.

## Next Phase Readiness

- Descriptor-bound external capabilities are ready for the owned-storage separation work in Plan 02-03 and later consumer cutover.
- No blockers remain.

---

_Phase: 02-read-only-policy-boundary_
_Completed: 2026-08-09_
