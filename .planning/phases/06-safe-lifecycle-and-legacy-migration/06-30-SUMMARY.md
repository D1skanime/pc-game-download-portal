---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 30
subsystem: legacy-migration-observation
tags: [python, pytest, sqlalchemy, fastapi, resource-budgets]
requires:
  - phase: 06-20
    provides: aggregate-aware descriptor hash budgets and persisted detection results
provides:
  - truthful lower-bound metadata for every partial legacy observation
  - persisted and public lower-bound propagation without path disclosure
affects: [MIG-03, MIG-05, legacy-detection, storage-administration]
tech-stack:
  added: []
  patterns:
    [
      keyword-only partial budget observations,
      explicit descriptor deadline classification,
    ]
key-files:
  created: []
  modified:
    - backend/handler/storage/legacy_migration.py
    - backend/tests/handler/storage/test_legacy_migration.py
key-decisions:
  - "Treat every budget-limited prefix as a lower bound while exact and non-budget outcomes retain their existing semantics."
  - "Classify descriptor hash deadlines as time_budget before generic hash failures."
requirements-completed: [MIG-03, MIG-05]
duration: 17min
completed: 2026-08-20
---

# Phase 6 Plan 30: Truthful Detection Lower Bounds Summary

Every budget-limited legacy observation now reports its measured prefix as a lower bound while remaining unselectable, fingerprint-free, and path-safe through persistence and the public schema.

## Performance

- **Duration:** 17 min
- **Started:** 2026-08-20T12:34:34Z
- **Completed:** 2026-08-20T12:51:01Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Unified all entry, time, per-file, aggregate, descriptor-byte, deadline, and returned-byte budget exits behind a truthful lower-bound observation helper.
- Classified descriptor hash deadlines explicitly as bounded `time_budget` outcomes before generic hash failures.
- Added behavioral coverage for observed prefixes, exact and non-budget controls, persistence, public serialization, and path-free diagnostics.
- Preserved the exact two accepted legacy grammars, source immutability, null fingerprints, and unselectable partial results.

## TDD Gate Compliance

- RED commit `b0f242b41` produced the exact named lower-bound assertion failure; the expanded matrix exposed ten behavioral failures while exact controls remained green.
- GREEN commit `b7dba5718` passed the focused 14-case matrix and all 105 related handler, task, and endpoint tests.
- Commit order is RED before GREEN.

## Task Commits

1. **Behavioral RED coverage:** `b0f242b41`
2. **Truthful partial observations:** `b7dba5718`

## Files Created/Modified

- `backend/handler/storage/legacy_migration.py` - keyword-only partial observation construction and explicit descriptor deadline classification.
- `backend/tests/handler/storage/test_legacy_migration.py` - complete budget matrix, negative controls, and persistence/schema round trip.

## Decisions Made

- Every budget-limited prefix is partial even when its observed count is zero.
- Exact completion, empty, missing, unsafe, unreadable, concurrent-change, and generic hash-failure outcomes retain their prior lower-bound semantics.
- Public partial diagnostics expose only bounded reason codes and counters, never paths, filenames, raw exceptions, or fingerprints.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provisioned a task-only database principal**

- **Found during:** Task 1 RED
- **Issue:** The normal application database user could not create the prescribed isolated database, so the first infrastructure attempt was rejected rather than counted as RED.
- **Fix:** Created scoped user `p0630` with rights only for `romm_test_0630`, then reran and accepted only the exact behavioral failure.
- **Files modified:** None; the database and user were removed during cleanup.

**2. [Rule 3 - Blocking] Typed dynamic budget-case arguments**

- **Found during:** Task 2 GREEN static verification
- **Issue:** Scoped mypy analysis rejected the deliberately heterogeneous parameter dictionary without an explicit value type.
- **Fix:** Annotated the test arguments as `dict[str, Any]`.
- **Files modified:** `backend/tests/handler/storage/test_legacy_migration.py`
- **Commit:** `b7dba5718`

**3. [Rule 1 - Bug] Reconciled stale completion tracking**

- **Found during:** Final tracking
- **Issue:** The checked-in GSD progress handler counted 65 completed plans but wrote 56% in frontmatter, left the visible bar at 96%, and collapsed roadmap table spacing.
- **Fix:** Reconciled both progress representations to 65/67 (97%) and normalized the Phase 6 roadmap row after running the required handlers.
- **Files modified:** `.planning/STATE.md`, `.planning/ROADMAP.md`

**4. [Rule 3 - Blocking] Used the canonical host identity for the metadata commit**

- **Found during:** Final commit
- **Issue:** The checked-in Docker GSD CLI staged the exact metadata files but its disposable Node container had no Git author identity.
- **Fix:** Preserved the exact staging set and committed it from the verified Linux checkout with normal hooks and the repository-configured identity.
- **Files modified:** None beyond the prescribed metadata set.

## Issues Encountered

- One repeated test command initially omitted `-p no:env`, so pytest-env replaced the isolated credentials and caused a connection error. The result was rejected as infrastructure noise; the prescribed isolated command then passed.
- Pytest reported the inherited unknown `env` option warning when that plugin was disabled and the inherited Alembic path-separator deprecation warning.

## Verification

- Exact RED gate: status 1 with only `test_entry_budget_reports_observed_lower_bound` failing on `lower_bound is True`.
- Expanded RED matrix: 10 expected failures and 2 exact/non-budget controls passed.
- Focused GREEN matrix: 14 passed, 26 deselected.
- Full related backend suite: 105 passed.
- Scoped Trunk: 2 files checked, no issues.
- Python AST parsing: 2 files passed.
- `git diff --check`: passed.
- Source manifest: only the two plan-owned files changed from the Plan 06-29 baseline; no legacy source file was modified.
- Runtime continuity: normal application `SELECT 1` returned `1` after cleanup.

## Known Stubs

None.

## Threat Flags

None. The planned observation boundary was hardened without adding endpoints, file-access authority, authentication paths, or schemas.

## User Setup Required

None.

## Cleanup

- Database `romm_test_0630` and user `p0630` were dropped; exact absence checks both returned zero.
- No task-owned container, volume, temporary file, restart, or deployment remains.
- The existing `romm-dev` service remained running and unchanged.
- All 28 baseline untracked paths were preserved.

## Next Phase Readiness

Plan 06-31 can proceed against truthful lower-bound detection metadata. No blockers remain.

## Self-Check: PASSED

The summary, both modified files, and both TDD task commits exist; all prescribed gates and cleanup assertions passed.
