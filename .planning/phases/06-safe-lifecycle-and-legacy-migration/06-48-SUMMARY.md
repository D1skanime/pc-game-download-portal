---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 48
subsystem: backend-storage
tags:
  [python, sqlalchemy, legacy-migration, sha256, folder-roms, rollback, pytest]
requires:
  - phase: 06-44
    provides: private exact source identity evidence and explicit catalog selection
  - phase: 06-47
    provides: isolated acceptance runners and the confirmed folder-ROM gap
provides:
  - exact child-to-parent selection for unique directory-backed ROMs
  - independent exact-digest selection for every RomFile
  - restart-safe migration and exact rollback lineage for folder ROMs
affects: [phase-06-verification, legacy-migration, impact-preview, rollback]
tech-stack:
  added: []
  patterns:
    - exact slash-boundary ancestry from observed child identities
    - one shared deterministic selection for preview and migration
key-files:
  created: []
  modified:
    - backend/handler/database/legacy_migration_handler.py
    - backend/tests/handler/storage/test_legacy_migration.py
    - backend/tests/integration/test_legacy_migration.py
key-decisions:
  - "A unique directory-backed ROM may derive parent authority only from an exact observed child strictly below its canonical identity plus a slash."
  - "Every RomFile remains independently selected by its own exact persisted digest; parent selection never bulk-selects children."
patterns-established:
  - "Canonicalize every ROM and RomFile once, then derive selection from the exact observed file rows."
  - "Sibling prefixes, basename similarity, unsafe identities, and ambiguous catalog identities cannot confer parent authority."
requirements-completed: [MIG-01, MIG-04]
duration: 43min
completed: 2026-08-24
---

# Phase 6 Plan 48: Exact Folder ROM Reconnection Summary

**Directory-backed ROM parents now reconnect from exact observed child files while every child row still requires its own persisted digest.**

## Performance

- **Duration:** 43 min
- **Started:** 2026-08-24T13:10:00Z
- **Completed:** 2026-08-24T13:53:03Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Refactored catalog selection so a unique folder parent qualifies from at least one exact observed owned child below the canonical parent slash boundary.
- Preserved direct digest selection for flat ROMs and independent exact digest membership for every RomFile, including absent sidecars that remain unreachable.
- Added boundary, ambiguity, unsafe text, basename similarity, restart, migration, rollback lineage, privacy, and source-manifest regressions.

## TDD Gate Compliance

- **RED:** `62e72dba4` ran the exact named integration selector in a nonce-owned disposable lifecycle. It failed on the current zero reconnectable folder-parent behavior, with normal collection, database setup, execution, and exact cleanup.
- **GREEN:** `f4423f0e9` passed the full changed modules after the minimal `_select_catalog` change.
- **Independent verification:** fresh final lifecycles passed 44 handler tests and 37 integration tests, followed by scoped Trunk, cleanup, continuity, stopped-service, and baseline gates.

## Task Commits

1. **Task 1: RED prove folder-parent and independent child selection** - `62e72dba4` (test)
2. **Task 2: GREEN derive the unique parent boundary without weakening child evidence** - `f4423f0e9` (feat)

## Files Created/Modified

- `backend/handler/database/legacy_migration_handler.py` - canonicalizes catalog rows once, computes exact observed child rows, derives unique parents with a strict slash boundary, and preserves exact child membership.
- `backend/tests/handler/storage/test_legacy_migration.py` - covers flat and folder selection, absent and out-of-boundary children, duplicate identities, unsafe text, basename similarity, and sibling prefixes.
- `backend/tests/integration/test_legacy_migration.py` - proves real nested detection, preview, migration, fresh-handler restart, exact lineage, rollback, privacy, and source immutability.

## Decisions Made

- Parent derivation uses only an exact canonical child identity beginning with `parent_identity + "/"`; unbounded string prefixes and aliases remain forbidden.
- Observed RomFile rows are computed by exact digest membership before parent selection. A selected parent cannot make an absent child reachable.
- Preview and migration continue to share the same locked selection object, so confirmation counts and changed IDs remain deterministic across restart.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used valid two-digit disposable runner indexes**

- **Found during:** Task 1 RED verification
- **Issue:** The plan's literal `ResourceIdentity.create(4801)` conflicts with the checked-in acceptance harness, which validates exactly a two-digit index suffix and rejected the identity before creating any resource.
- **Fix:** Used nonce-owned indexes 48 through 53 under the existing harness contract. The initially rejected invocation created no database, principal, basetemp, volume, or container.
- **Files modified:** None.
- **Verification:** Every accepted lifecycle cleaned its exact resources; final labeled container and volume counts were zero.
- **Committed in:** Not applicable.

**2. [Rule 1 - Bug] Corrected the pure selection test's declared types**

- **Found during:** Task 2 scoped Trunk verification
- **Issue:** The first RED unit matrix used `SimpleNamespace`, while `_select_catalog` deliberately accepts `Rom` and `RomFile`; mypy rejected the mismatch.
- **Fix:** Replaced stand-ins with real unsaved ORM rows without changing test behavior or production scope.
- **Files modified:** `backend/tests/handler/storage/test_legacy_migration.py`.
- **Verification:** Scoped Trunk passed, then the full 44-test handler module and 37-test integration module passed twice in fresh lifecycles.
- **Committed in:** `f4423f0e9`.

---

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 3).
**Impact on plan:** Both fixes preserved the planned behavior and safety boundary; no product scope, schema, API, or source authority was added.

## Issues Encountered

- The RED runner index from the plan was incompatible with the stricter checked-in harness grammar. The failure occurred before resource creation and the valid existing two-digit contract was used instead.
- The first scoped static pass caught test-only type stand-ins. Real ORM instances restored type fidelity without weakening the RED or GREEN evidence.

## Verification and Cleanup

- Final disposable handler lifecycle: 44 passed, 0 skipped.
- Final disposable integration lifecycle: 37 passed, 0 skipped.
- Scoped Trunk passed all three touched files; `git diff --check` passed.
- Integration tests preserved path, kind, mode, size, digest, and symlink source manifests across migration and rollback.
- Exact nonce-owned cleanup left zero labeled containers and zero labeled volumes; task databases and principals were removed by each lifecycle.
- Normal application database `SELECT 1` passed before and after final verification.
- `romm-dev` remained `romm-romm-dev:exited`; no service was started, restarted, deployed, or given a published port.
- The original 28-entry status remained byte-exact at `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1` after task commits.

## Known Stubs

None. No goal-blocking placeholder, TODO, FIXME, hardcoded empty rendering path, or unwired data source was introduced.

## Threat Review

No unplanned network endpoint, authentication path, schema change, file access pattern, or source mutation authority was introduced. Exact child ancestry, independent child membership, digest privacy, and runner isolation are covered by the Plan 48 threat register.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CR-01 and verification must-have 14 are closed for flat, folder, and multi-file catalog identities.
- Plans 06-49 through 06-54 can close the remaining independent Phase 6 gaps. Plan 48 has no blocker for them.

## Self-Check: PASSED

- All three modified product/test files exist.
- Commits `62e72dba4` and `f4423f0e9` resolve in repository history.
- RED then GREEN ordering, fresh tests, static checks, exact cleanup, DB continuity, stopped service, and the 28-entry baseline were verified.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-24_
