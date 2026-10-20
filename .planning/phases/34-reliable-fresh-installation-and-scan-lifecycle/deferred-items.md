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

## Historical frontend quality gaps

Resolved on 2026-10-19 by the authorized Wave 2 remediation, commit `15ed063ac`.
The full isolated retained-contract typecheck now exits 0. Provider tests remain
intact and four mapping behavior tests were added. See `34-WAVE2-QA.md` for actual
reproduction, final gates, remaining suite failures and teardown evidence.

Before remediation, the isolated npm run typecheck exited 2 with five diagnostics:

- frontend/src/v2/components/MatchRom/types.test.ts:52, TS2352.
- frontend/src/v2/components/Settings/pgdpFolderMappings.ts:32, TS2322.
- The same file:33, TS2677, and :34, two TS18047 diagnostics.

An exploratory full API regeneration also exposed existing schema/store drift at frontend/src/stores/roms.ts:212-213, two TS2322 diagnostics. Unrelated generated outputs were not applied. The four operation types were generated from the isolated backend and checked on the existing frontend baseline; no operation-type diagnostic remains. This does not establish a green global regeneration or frontend quality gate.

## Remaining phase gates

34-02 does not repair the RQ callable-recognition or Vue listener-ownership defects reproduced by 34-01. Dispatcher/worker integration, proven source recovery, frontend transport/lifecycle, production-like worker/Portainer faults and browser acceptance remain with their owning plans. Phase 33 acceptance remains open.

Existing Alembic configuration and SQLAlchemy relationship warnings were observed in successful pytest runs and remain out of scope.

## Historical setup regression exposed during 34-05 closeout (2026-10-19)

Resolved by the authorized Wave 2 remediation in `15ed063ac`: the fixture is
declared and every assertion remains. The combined adjacent/recovery rerun passes
all 39 cases, including the original 12. The following is historical evidence,
not the current result. See `34-WAVE2-QA.md`.

The original guarded adjacent regression ran 12 cases: 11 passed and one failed.
backend/tests/handler/test_setup_folder_handler.py:77 references tmp_path without
declaring its fixture in test_resolve_platform_bootstraps_missing_supported_platform.
The file is byte-identical to the pre-34-05 revision f7b40a7c1^, last changed in
65166f410. It remains outside this plan's implementation scope and was not fixed.

Actual failed evidence: /tmp/pgdp34-9ec96abf216d41c2acc694a79d0a26f3-yhozqb_d/evidence.
Cleanup and source immutability both passed. The exact 34-05 task suites passed
9/9 handler and 18/18 endpoint cases. The global typecheck still reports the five
known diagnostics above; neither failed gate is relabeled green.

## Wave 2 remaining frontend verification gaps (2026-10-19)

The full isolated frontend suite exits 1: 1009 passed, four failed, zero
skipped/errors. Three are the planned lifecycle behavioral REDs (P34_REMOUNT,
P34_OWNERS and P34_DEBOUNCE), still owned by their phase plans.

The additional failure is sourceMutationInventory.test.ts, "inventories every
production v2 module and reachable API service": existing services/api/setup.ts
assignFolders:api.post uses POST /setup/folders/assign without an authority
classification (payload=none operation=UNKNOWN storage=unknown). A separate
disposable snapshot with all three remediation diffs reversed reproduces the same
failure: 19 passed, one failed. No inventory rule, API or assertion was relaxed.
This requires an owning-plan follow-up outside the bounded three-file repair.

The production build exits 0 with CSS :deep minifier, vue3-pdf-app dependency eval
and large-chunk warnings. These warnings are outside this repair's scope.
The retained-contract full typecheck and 15 focused frontend tests pass.

Exact Linux evidence roots and clean teardown receipts for all five runs are in
34-WAVE2-QA.md. Full-phase acceptance remains open.
