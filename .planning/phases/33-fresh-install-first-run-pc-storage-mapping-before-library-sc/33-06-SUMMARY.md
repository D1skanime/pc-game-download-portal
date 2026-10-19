---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 06
subsystem: testing
tags: [uat, setup, storage, collections, browser]
status: awaiting-human-verification
requires:
  - phase: 33-10
    provides: Explicit collection promotion and safe owned-media retirement
provides:
  - Guarded fresh Linux setup and real-worker browser acceptance evidence
  - Exact source and cleanup validation with retained provenance
affects: [phase-33-acceptance]
tech-stack:
  added: []
  patterns: [guarded-disposable-runner, read-only-synthetic-source]
key-files:
  created:
    - backend/tools/phase33_uat.py
    - backend/tools/phase33_collection_fixture.py
    - backend/tools/phase33_worker_probe.py
    - backend/tools/tests/test_phase33_uat.py
  modified:
    - .planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-UAT.md
    - .planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-VALIDATION.md
key-decisions:
  - Reuse the existing authoritative disposable runner and immutable source guard.
  - Require executed browser evidence and exact frontend source equality before receipt reuse.
  - Preserve live Dev data and treat human collection acceptance as a separate checkpoint.
metrics:
  duration: resumed acceptance across corrective implementation
  completed-date: 2026-10-19
  tasks-completed: 1
  tasks-total: 2
---

# Phase 33 Plan 06: Fresh setup and real collection scan acceptance

**Guarded Linux browser execution proves fresh mapping readiness, explicit
child promotion, safe media cleanup and normal/scheduled collection discovery.**

Task 1 is technically verified. Task 2, the mandatory human browser checkpoint,
remains pending. This summary does not close Phase 33 or approve a later phase.

## Task commits

| Commit | Work |
| --- | --- |
| db1a144ab | Use real authenticated Request fixtures and the fixture library boundary. |
| cd65f2382 | Record RED coverage for missing PC setup identity. |
| 3cf92caa0 | Reuse the existing canonical PC-to-Windows identity in setup discovery. |
| 10e07fd08 | Add the guarded executed browser/worker harness, exact mount validator and adversarial tests. |

## Verification

Final evidence is retained under
evidence/pgdp34-f4dd7651eda049868d9483e52118cfcb.
The full command exited zero. All 22 named browser checks passed on the final
retained-state reconnect policy. Current production hashes match that snapshot;
unchanged frontend hashes match the 64fa62f2 receipt with typecheck, 1,102 tests,
build and maintainability passing.

Actual worker totals/scanned counts were initial 3/3, selected child 1/1,
normal complete 4/4 and scheduled 6/6. The child detail contains both expected
archive parts. The parent disappeared, classification persisted, audit stayed
with the retained identity, exclusively owned media was removed and shared
media remained. Both later shared scan paths discovered host-added direct
children without parent resurrection. Source manifests matched in every
application segment and all generated resources were removed.

Focused setup/backend receipts contain 21 passing tests and 18 passing alias
regressions. Final retained-identity controls passed 9 cases on each of MariaDB
and PostgreSQL. Eight harness adversarial tests, shell syntax and scoped Trunk
passed. Fresh final MariaDB/MySQL/PostgreSQL schema cycles and parity passed
with 39/39/40 successful commands and verified cleanup. Their full source
manifests equal the final browser snapshot, including the final audit/cleanup
columns. The small receipt index records hashes and exact source coverage.

Mouse, keyboard focus, touch, theme classes/screenshots and 320px/1440px document
bounds were exercised. Next/Previous targets measured 48px. Physical gamepad
verification is BLOCKED because navigator.getGamepads() found no connected
device. Human visual and live collection acceptance remain pending.

## Deviations from Plan

1. **[Rule 3 - Blocking harness]** The old shell runner could manufacture PASS
   without a browser, used an unsuitable Playwright configuration, mounted
   canonical frontend files writable and could mask the original failure during
   teardown. The replacement delegates private target authority, source copying,
   startup and cleanup to the tested guarded runner. It never touches live Dev.
2. **[Rule 1 - Stale test fixture]** Legacy bootstrap tests passed SimpleNamespace
   instead of an authenticated Starlette Request and depended on an implicit
   library path/fallback. Fixtures were corrected without weakening security.
   Commit db1a144ab; reachable MariaDB GREEN 21.
3. **[Rule 1 - Setup identity]** Actual fresh discovery did not recognize pc.
   The existing endpoint's identity helper was extracted and shared rather than
   duplicated. RED and GREEN commits cd65f2382 and 3cf92caa0; GREEN 18.
4. **[Rule 1 - Fixture boundary]** An in-container symlink conflicted with the
   existing no-follow source boundary. Both aliases now bind the identical
   generated Games source directly and read-only.
5. **[Rule 1 - Real UAT findings]** Actual 40px navigation and worker session,
   publication lock order, cold import and inventory-count defects were reported
   to their owning production workers and corrected with focused regressions.
   The final browser exercises their real UI/API/RQ behavior. Their production
   commits and plan 33-10 details are recorded by the parent executor.
6. **[Rule 1 - Harness corrections]** Direct API writes now send the actual CSRF
   cookie header. File assertions use DetailedRomSchema instead of the gallery
   response that intentionally omits files. Compose source normalization requires
   authoritative exact Docker source/RW evidence. Historical failed receipts are
   retained; the final full run passes without post-hoc repair.
7. **[Authorized scope extension]** The user required explicit collection
   retirement, retained parent context and later full/scheduled child discovery.
   Approved plan 33-10 supplies that behavior. Synthetic fixtures test it through
   public endpoints and registered tasks, without parallel business logic.
8. **[Repository boundary]** Standalone adapters and fixtures live under
   backend/tools. Runtime state, raw logs, screenshots and traces stay retained
   locally under ignored evidence paths; only receipt hashes are committed.

## Safety and remaining checkpoint

The harness resets only its strongly identified synthetic database. Primary and
guarded library mounts resolve to the same owned read-only fixture. No source
Games files, live database, Redis or live Media were reset by this executor.
The operator's separately authorized 15-minute Dev autoscan activation has its
own sanitized receipt and was verified by the parent.

There are no unfinished production stubs in the owned changes. The optional
physical input limitation and mandatory human checkpoint are explicit, rather
than represented by synthetic success. The parent owns global STATE/ROADMAP
and plan 33-10 status; no global phase-completion update is made here.

## Self-Check: PASSED

All named artifacts and task commits exist. Final browser state, exact production
proof, all 22 browser checks, three exact-source schema runs, frontend receipt
compatibility and cleanup receipts were inspected. Global state changes remain
owned by the parent. Task 2 remains awaiting human verification.

## Historical setup-root fallback evidence

The preceding summary recorded this earlier deviation and focused proof. It is
retained here as historical context; the final browser evidence above supersedes
its pending acceptance position.


## Deviation

Fresh UAT exposed that `GET /api/setup/folders` returned HTTP 409 on an empty
database even when the configured library bind was present. The regression test
now proves that `SetupFolderHandler.root()` registers the configured library
root through `db_storage_handler.register_root` when no active matching root
exists. The minimal fallback preserves the existing external read-only health
and policy checks and does not add a second mapping step.

## Verification

- RED: `test_root_registers_configured_library_when_database_is_empty` failed
  before the production change.
- GREEN: focused handler and endpoint tests passed, 10 passed.
- Live temporary UAT: `GET /api/setup/folders` returned HTTP 200 and discovered
  `My Games` and `pc`; the database contains one healthy external read-only
  root at `/app/romm/library`.
- In-memory Python compilation passed for both changed files.

Full Phase 33 browser UAT remains pending and is not marked complete here.
