---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 46
subsystem: backend-storage
tags: [python, alembic, mariadb, mysql, postgresql, privacy, tdd]
requires:
  - phase: 06-42
    provides: revision 0114 private source identity schema and invalidation
  - phase: 06-44
    provides: exact source-bound ROM and RomFile reconnection
provides:
  - authoritative 0114 lifecycle verification on all supported database dialects
  - restart-safe private evidence and exact handler selection proof
  - redacted failures with labeled exact container and volume cleanup
affects: [06-47, migration-verification, legacy-migration]
tech-stack:
  added: []
  patterns:
    - synthetic digest-only migration probes
    - labeled nonce-owned database containers and named data volumes
    - refreshed published-port propagation after database restart
key-files:
  created: []
  modified:
    - backend/tools/verify_storage_migrations.py
    - backend/tests/tools/test_verify_storage_migrations.py
key-decisions:
  - Every verifier database uses a proven labeled named volume removed after its exact container.
  - Every random published database port is refreshed and propagated after restart.
  - Subprocess failures expose bounded exit and selector evidence only.
requirements-completed: [MIG-02, MIG-04, MIG-05]
metrics:
  duration: 53m
  completed: 2026-08-21
---

# Phase 6 Plan 46: Private Identity Migration Authority Summary

Revision 0114 now has real pristine, seeded, restart, downgrade, re-upgrade, privacy, exact-handler, and cleanup authority on MariaDB, MySQL, and PostgreSQL.

## Performance

- Duration: 53 min
- Started: 2026-08-21T15:57:02Z
- Completed: 2026-08-21T16:49:35Z
- Tasks: 2
- Files modified: 2

## Accomplishments

- Added pristine 0114 schema checks and seeded 0113 invalidation for evidence-less selectable results on all three dialects.
- Added synthetic sorted unique evidence probes, duplicate and malformed rejection, restart persistence, downgrade invalidation, and re-upgrade unselectability.
- Added exact source-observed ROM and child-file handler selection to MariaDB and PostgreSQL authority while retaining only the declared MySQL 0107 handler exception.
- Added privacy checks and redacted failed subprocess commands, output, credentials, and identity values.
- Replaced implicit database storage with labeled nonce-owned named volumes, exact identity proof, and ownership-gated cleanup.

## TDD Gate Compliance

- RED: Fresh isolated p0646_t1 collected exactly test_verifier_requires_0114_source_identity_round_trip and exited 1 only because the verifier lacked the 0114 marker.
- GREEN: Fresh isolated p0646_t2 passed all 23 verifier tests.
- Independent verification: Fresh isolated p0646_pv passed all 23 verifier tests after formatting.
- Ordering: fccf95d19 precedes GREEN commit 30482acfd.

## Authoritative Dialect Evidence

| Dialect    | Image         | 0114 lifecycle                                                              | Handler                                 | Cleanup                                   | Exit |
| ---------- | ------------- | --------------------------------------------------------------------------- | --------------------------------------- | ----------------------------------------- | ---- |
| MariaDB    | mariadb:10.11 | pristine, seeded 0113, constraints, restart, downgrade, re-upgrade, privacy | exact ROM and child selection passed    | labeled container and named volume absent | 0    |
| MySQL      | mysql:8.4     | pristine, seeded 0113, constraints, restart, downgrade, re-upgrade, privacy | declared minimal 0107 handler skip only | labeled container and named volume absent | 0    |
| PostgreSQL | postgres:15   | pristine, seeded 0113, constraints, restart, downgrade, re-upgrade, privacy | exact ROM and child selection passed    | labeled container and named volume absent | 0    |

The real host verifier used a fresh disposable runner supplied by --runner-container, --handler-tests, and one repetition. No persistent application service was started or restarted.

## Verification

- Verifier unit lifecycle: 23 passed in Task 2 and 23 passed independently.
- Handler-only diagnostic authority: 61 passed on fresh MariaDB head.
- Scoped Trunk formatting and checking passed for both modified files.
- git diff --check passed.
- Normal application database SELECT 1 passed before and after every lifecycle.
- Exact verifier container, named volume, runner, database, principal, and basetemp absence checks passed.
- romm-dev remained stopped and no deployment occurred.
- The exact 28-entry baseline remained at SHA-256 4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1.

## Task Commits

1. Task 1 RED, specify 0114 verifier lifecycle and privacy probes: fccf95d19
2. Task 2 GREEN, run authoritative 0114 lifecycle on all three dialects: 30482acfd

## Decisions Made

- Used only synthetic lowercase hexadecimal digests in verifier data probes.
- Created one exact labeled named data volume per database container.
- Propagated the remapped random host port after every database restart.
- Classified expected constraint and guarded downgrade failures only after a healthy SELECT 1.
- Kept handler diagnostics bounded to exit codes, safe categories, and test node IDs.

## Deviations from Plan

### Auto-fixed Issues

1. Rule 3, blocking: Used nonce-owned disposable runners because romm-dev was stopped and restart was prohibited. RED, GREEN, independent, handler, and dialect runs proved exact cleanup and application continuity.

2. Rule 2, missing critical functionality: Made verifier data volumes explicit and owned. Database images could otherwise create anonymous volumes without independently provable identity. Added labeled named volumes and exact removal. Committed in 30482acfd.

3. Rule 1, bug: Propagated the refreshed random published port. Later cleanup and handler probes had retained the stale caller port after restart. Committed in 30482acfd.

4. Rule 3, blocking: Cleared only exact 0114 probe identity and result IDs before handler tests to avoid fixture contamination. Committed in 30482acfd.

## Issues Encountered

- The first RED harness grant statement was rejected because of shell quoting. Ownership-gated cleanup completed before the accepted RED rerun.
- A redundant broad post-roundtrip clear exposed the stale published-port bug and was removed.
- The host PATH omitted Trunk; the approved launcher at /home/d1sk/.local/bin/trunk completed scoped checks.

## Known Stubs

None.

## Threat Flags

None. The plan threat model covers dialect authority, private evidence, redacted diagnostics, bounded execution, and exact cleanup. No product endpoint, authentication, schema, or source-file surface was added.

## Cleanup and Continuity

- No romm.verifier.plan=06-46 container or volume remains.
- No p0646 runner, database, principal, basetemp, environment file, log file, PID file, or process remains.
- Normal application database access remained healthy.
- No tracked file was deleted.
- No service was deployed, started, or restarted.

## Next Phase Readiness

Plan 06-47 can consume real three-dialect 0114 authority with no remaining MIG-02, MIG-04, or MIG-05 verifier blocker.

## Self-Check: PASSED

---

Phase: 06-safe-lifecycle-and-legacy-migration
Completed: 2026-08-21
