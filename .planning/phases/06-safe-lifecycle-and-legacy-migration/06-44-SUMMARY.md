---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 44
subsystem: backend-storage
tags: [python, sqlalchemy, migration, sha256, privacy, pytest, tdd]
requires:
  - phase: 06-37
    provides: private source-observed identity digest derivation
  - phase: 06-42
    provides: durable private source identity rows
provides:
  - exact persisted source and catalog identity intersection
  - explicit ROM and RomFile reconnection under deterministic locks
  - restart-safe exact membership and rollback lineage verification
affects: [06-46, 06-47, legacy-migration, rollback]
tech-stack:
  added: []
  patterns:
    - private digest-only authority persisted with its detection result
    - one shared catalog selection for preview and migration
key-files:
  created: []
  modified:
    - backend/handler/database/legacy_migration_handler.py
    - backend/handler/database/roms_handler.py
    - backend/tests/handler/storage/test_legacy_migration.py
    - backend/tests/integration/test_legacy_migration.py
    - backend/tests/handler/database/test_storage_lifecycle.py
key-decisions:
  - "Catalog identities must start with the exact platform fs_slug segment and remain canonical before domain-separated hashing."
  - "Migration passes explicit locked ROM and RomFile ID sets to the database handler, and child files never inherit reachability from the parent alone."
patterns-established:
  - "Selectable detection evidence is nonempty, sorted, unique, exact-length, and committed atomically with its result."
  - "Fresh migration observation requires both aggregate fingerprint and exact digest tuple equality."
requirements-completed: [MIG-01, MIG-02, MIG-03, MIG-04, MIG-05]
duration: 18min
completed: 2026-08-21
---

# Phase 6 Plan 44: Exact Source-Bound Legacy Reconnection Summary

**Legacy migration now reconnects only unique ROM identities and independently observed child files proven present by private persisted source digests.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-08-21T14:50:26Z
- **Completed:** 2026-08-21T15:08:39Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Persisted exact digest-only source identity rows in the same transaction as selectable detection results, with strict cardinality, ordering, uniqueness, and digest validation.
- Replaced catalog-only preview counts with an exact source and catalog intersection that rejects wrong-prefix, empty, unsafe, alias, ambiguous, case-distinct, and Unicode-distinct identities without case folding.
- Reconnected only explicit locked ROM IDs and independently observed RomFile IDs, while absent ROMs and sidecars remain missing through migration, restart, and rollback.
- Required fresh aggregate source fingerprint, exact source identity tuple, and catalog fingerprint equality before any owned mapping or catalog write.
- Limited rollback lineage to rows actually changed and preserved every public result, response, repr, and log boundary without private identities.

## TDD Gate Compliance

- **RED:** `9906d38e7` ran only `test_migration_reconnects_only_source_observed_rom_and_sidecar`; pytest exited 1 because the current catalog-only preview reported 4 reconnectable ROMs instead of the exact observed count of 1. Collection, setup, database, runner, and cleanup failures were rejected.
- **GREEN:** `8c27cc0dd` passed all 111 legacy handler, integration, and storage-lifecycle tests in a fresh Task 2 lifecycle.
- **Independent verification:** a fresh `p0644_pv` lifecycle passed the same 111 tests, scoped Trunk, `git diff --check`, manifest equality, exact resource cleanup, and normal application database continuity.

## Task Commits

1. **Task 1 RED: Prove source-absent ROMs and sidecars remain unreachable** - `9906d38e7` (test)
2. **Task 2 GREEN: Persist, lock, intersect, and update exact identities atomically** - `8c27cc0dd` (feat)

## Files Created/Modified

- `backend/handler/database/legacy_migration_handler.py` - atomic evidence persistence, deterministic evidence and catalog locks, shared exact selection, fresh set equality, and exact rollback lineage.
- `backend/handler/database/roms_handler.py` - validated explicit ROM and RomFile reconnection updates.
- `backend/tests/handler/storage/test_legacy_migration.py` - exact evidence fixtures and same-count identity membership drift coverage.
- `backend/tests/integration/test_legacy_migration.py` - present ROM/file, absent ROM/sidecar, ambiguity, unsafe identity, restart, rollback, and privacy regression.
- `backend/tests/handler/database/test_storage_lifecycle.py` - direct-insert transaction fixture with exact private evidence rows.

## Decisions Made

- Catalog membership is derived only from a canonical full catalog identity whose first segment exactly equals `Platform.fs_slug`; exactly that segment is removed before Plan 37 hashing.
- ROM uniqueness is evaluated on the exact mapping-relative identity before digest membership, while each child file requires its own digest and a selected parent.
- The private selection object carries locked rows and IDs only inside the transaction so public impact and migration dataclasses remain unchanged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used nonce-owned disposable test runners**

- **Found during:** Task 1 RED lifecycle
- **Issue:** The plan names `romm-dev`, but it was stopped and service restart was prohibited.
- **Fix:** Used fresh nonce-owned containers from `romm-romm-dev`, mounted the canonical backend read-only, prepared only the runner-local Python traversal permission, and ran pytest as UID 1000.
- **Files modified:** None.
- **Verification:** Accepted RED, GREEN, and independent lifecycles proved runner, database, principal, and basetemp absence plus normal application `SELECT 1` before and after.
- **Committed in:** Not applicable.

**2. [Rule 3 - Blocking] Added private evidence to the direct-insert lifecycle fixture**

- **Found during:** Task 2 GREEN verification
- **Issue:** The storage-lifecycle transaction test bypasses `save_detection_result` and inserted a selectable result without the newly required private evidence rows.
- **Fix:** Populated its result-owned identity rows from the real detector outcome.
- **Files modified:** `backend/tests/handler/database/test_storage_lifecycle.py`.
- **Verification:** The full 111-test Task 2 and independent gates passed.
- **Committed in:** `8c27cc0dd`.

---

**Total deviations:** 2 auto-fixed (2 Rule 3).
**Impact on plan:** Both deviations were required to exercise the planned behavior safely; product scope did not expand.

## Issues Encountered

- The first disposable runner could not traverse the image-owned Python path as UID 1000. The run was rejected as RED, then runner-local `/root` traversal was enabled before executing pytest as UID 1000.
- Two early RED fixtures collided with MariaDB's unique, case-insensitive `(platform_id, fs_name)` index. Both were rejected before behavioral evidence; the final fixture used distinct stored names that still model exact logical ambiguity and case/Unicode controls.

## Verification and Cleanup

- RED command: isolated `p0644_t1` named selector, pytest exit 1 at exact preview count; lifecycle wrapper exit 0 after validating the expected failure and cleanup.
- GREEN command: isolated `p0644_t2` three-module selector, exit 0 with 111 passed and 3 inherited warnings.
- Independent command: isolated `p0644_pv` three-module selector, exit 0 with 111 passed and 3 inherited warnings.
- Scoped Trunk check passed for all five affected files; `git diff --check` passed.
- Tracked backend manifest remained `c55424945a925020ac0712c1e59e79ba939672f1cf798aa3267877822c269745` before and after verification.
- The 28-entry baseline remained at `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1`.
- No service was started or restarted, nothing was deployed, and all temporary patch and runner resources were removed.

## Known Stubs

None.

## Threat Flags

None. Exact private evidence, catalog authority, explicit updates, and privacy boundaries were all registered in the plan threat model; no new endpoint, schema, network, authentication, or file-access surface was introduced.

## User Setup Required

None.

## Next Phase Readiness

Plan 06-46 can verify the already portable selection and revision authority across MariaDB, MySQL, and PostgreSQL. No blockers remain.

## Self-Check: PASSED

- All five modified files and commits `9906d38e7` then `8c27cc0dd` exist.
- RED and GREEN ordering, independent tests, static checks, privacy, manifest, cleanup, continuity, and the exact 28-entry baseline passed.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-21_
