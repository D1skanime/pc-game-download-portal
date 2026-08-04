---
phase: 01-immutable-storage-foundation
plan: 05
subsystem: testing
tags: [pytest, alembic, mariadb, mysql, postgresql, immutability]
requires:
  - phase: 01-immutable-storage-foundation
    provides: Immutable storage schema, lexical normalization, canonical resolver, and atomic mapping persistence
provides:
  - Complete TEST-01 adversarial and non-mutation evidence
  - Independent three-dialect migration cycles in local verification and CI
  - Pinned MariaDB 10.11, MySQL 8.4, and PostgreSQL 15 portability gates
affects: [phase-02-storage-policy, storage-security, migrations, ci]
tech-stack:
  added: []
  patterns:
    [
      filesystem manifest evidence,
      mutation tripwires,
      three-step migration cycles,
    ]
key-files:
  created: []
  modified:
    - backend/tests/handler/database/test_storage_handler.py
    - .github/workflows/migrations.yml
key-decisions:
  - "CI treats MariaDB, MySQL, and PostgreSQL as independent migration authorities rather than inferring compatibility between dialects."
  - "MySQL starts from a clean 0107-compatible baseline because pre-0108 historical DDL is not MySQL 8 compatible."
patterns-established:
  - "Source immutability evidence snapshots names, kinds, sizes, modes, mtimes, and symlink targets while excluding atime."
  - "Migration portability requires upgrade head, downgrade to 0107, and re-upgrade on every supported dialect."
requirements-completed: [TEST-01]
duration: 11min
completed: 2026-08-04
---

# Phase 1 Plan 5: Adversarial and Cross-Dialect Evidence Summary

Exhaustive immutable-storage threat evidence with source manifests, mutation tripwires, and repeatable three-dialect migration cycles.

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-04T21:27:06Z
- **Completed:** 2026-08-04T21:38:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Closed TEST-01 with named coverage for lexical rejection, Unicode and long names, root and target state, symlink variants, sibling containment, overlap serialization, bounded errors, and immutable source manifests.
- Added persistence-level mutation tripwires for directory creation, deletion, rename, replacement, copy, move, and temporary-file creation.
- Proved revision 0108 upgrade, downgrade to 0107, and re-upgrade independently on MariaDB 10.11, MySQL 8.4, and PostgreSQL 15.
- Extended the authoritative migration workflow with pinned `migrate-mariadb`, `migrate-mysql`, and `migrate-postgres` jobs.

## Task Commits

1. **Task 1: Complete the adversarial matrix** - `2e5a61f80` (test)
2. **Task 2: Run final portability and quality gates** - `489279504` (ci)

## Files Created/Modified

- `backend/tests/handler/database/test_storage_handler.py` - Persistence manifest and source-mutation tripwire evidence.
- `.github/workflows/migrations.yml` - Pinned three-dialect upgrade, downgrade, and re-upgrade CI jobs.

## Decisions Made

- MariaDB, MySQL, and PostgreSQL each remain an independent portability authority.
- MySQL uses the established clean 0107-compatible baseline because historical migrations before 0108 are not MySQL 8 compatible.
- Atime remains excluded from Phase 1 manifests per D-32; production mount-level atime proof remains Phase 9.

## Verification Evidence

- `cd backend && python3 tools/verify_storage_migrations.py --dialects mariadb mysql postgresql`: MariaDB 10.11, MySQL 8.4, and PostgreSQL 15 each passed upgrade, downgrade to 0107, and re-upgrade.
- `uv run pytest tests/handler/filesystem/test_storage_resolver.py tests/handler/database/test_storage_handler.py -x`: 56 passed.
- `uv run pytest tests/models/test_storage.py -x`: 8 passed.
- `trunk fmt .github/workflows/migrations.yml backend/tests/handler/database/test_storage_handler.py`: passed.
- `trunk check .github/workflows/migrations.yml backend/tests/handler/database/test_storage_handler.py`: no issues.
- Before and after manifests remained identical for registration, health, resolution, and mapping validation, excluding atime.

## Deviations from Plan

None - plan scope and security boundaries were followed exactly.

## Issues Encountered

- The repository verifier must run on the Docker host because the application container intentionally has no Docker CLI or socket. It completed from the host while running Alembic inside the existing development container.
- The isolated `romm_test` schema had been dropped by the model-suite teardown. It was recreated from the 0107 migration boundary before verification, without touching application data.
- A repository-wide Trunk invocation included pre-existing untracked `.codex` content and unrelated planning-format failures. All unrelated tracked formatting changes were restored individually, then Trunk passed against the two plan-owned files.

## User Setup Required

None. No external service configuration or real NAS activation is required.

## Known Stubs

None.

## Threat Flags

None. This plan adds test and CI evidence only, with no API, consumer, filesystem-write, or schema surface.

## Next Phase Readiness

- Phase 1's storage identity, resolution, persistence, immutability, and dialect evidence are complete.
- Phase 2 can add central operation-policy enforcement without assuming any API or consumer cutover occurred here.
- Real NAS activation, mount behavior, and atime evidence remain explicitly deferred to Phase 9.

## Self-Check: PASSED

- Both modified files exist.
- Task commits `2e5a61f80` and `489279504` exist.
- All 64 phase tests, three dialect cycles, and scoped Trunk gates pass.

---

_Phase: 01-immutable-storage-foundation_
_Completed: 2026-08-04_
