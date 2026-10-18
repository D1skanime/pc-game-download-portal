# Phase 34 Deferred Items

## Resolved: 34-02 historical migration portability (2026-10-18)

The user explicitly authorized bounded historical MariaDB/MySQL/PostgreSQL portability repairs before resuming 34-02. These are no longer blockers.

- MySQL 8.4 conditional index/column DDL now uses online catalog checks through the Alembic MySQL implementation. Original failure: 0001_initial_models.py, CREATE UNIQUE INDEX IF NOT EXISTS. Original evidence: /tmp/pgdp34-3c3748d9193041349ae6a421f1dc4b3b-67w7shzt/evidence.
- Migration 0057 uses an expression default for the empty text value, preserving its value on all three dialects.
- The disposable MySQL server explicitly permits its existing trigger migrations with binary logging enabled. No application server settings changed.
- PostgreSQL 0134 preserves fractional timestamps and database update behavior with its native type and update trigger.
- PostgreSQL 0138 replaces the metadata view transactionally because its changed column ordering cannot use CREATE OR REPLACE VIEW.
- Operation migration 0139 explicitly disables singleton auto-increment and preserves microseconds in dispatch, lease and audit timestamps. Real MySQL tests reproduced rounding that otherwise delayed immediate dispatch and changed replay snapshots.

Repair commits: 285833fb7 and d0851b51d. Baseline and final schema matrices passed independently on MariaDB 10.11, MySQL 8.4 and PostgreSQL 15. No stamping past failures, SQLite substitution or dialect omission occurred. See 34-02-SUMMARY.md for the exact evidence and task commits.

## Existing frontend quality gaps

The final tree's isolated npm run typecheck still exits 2 with five existing diagnostics:

- frontend/src/v2/components/MatchRom/types.test.ts:52, TS2352.
- frontend/src/v2/components/Settings/pgdpFolderMappings.ts:32, TS2322.
- The same file:33, TS2677, and :34, two TS18047 diagnostics.

An exploratory full API regeneration also exposed existing schema/store drift at frontend/src/stores/roms.ts:212-213, two TS2322 diagnostics. Unrelated generated outputs were not applied. The four operation types were generated from the isolated backend and checked on the existing frontend baseline; no operation-type diagnostic remains. This does not establish a green global regeneration or frontend quality gate.

## Remaining phase gates

34-02 does not repair the RQ callable-recognition or Vue listener-ownership defects reproduced by 34-01. Dispatcher/worker integration, proven source recovery, frontend transport/lifecycle, production-like worker/Portainer faults and browser acceptance remain with their owning plans. Phase 33 acceptance remains open.

Existing Alembic configuration and SQLAlchemy relationship warnings were observed in successful pytest runs and remain out of scope.
