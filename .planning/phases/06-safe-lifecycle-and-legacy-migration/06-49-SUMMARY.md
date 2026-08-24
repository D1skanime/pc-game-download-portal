---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 49
subsystem: backend-storage
tags: [python, fastapi, sqlalchemy, manuals, cas, owned-storage, pytest]
requires:
  - phase: 06-43
    provides: durable OwnedCreate publication and exact expected-path CAS
  - phase: 06-47
    provides: isolated acceptance runners and the confirmed primary-manual gap
provides:
  - validated token-path primary-manual discovery and exact deletion
  - shared unique-candidate CAS publication for upload and redownload
  - immutable local-file redownload inputs with loser and superseded cleanup
affects: [phase-06-verification, primary-manuals, resource-storage]
tech-stack:
  added: []
  patterns:
    - persisted exact-path authority with bounded fixed-name compatibility
    - complete owned candidate publication before locked expected-path CAS
key-files:
  created: []
  modified:
    - backend/endpoints/roms/manual.py
    - backend/handler/database/manual_handler.py
    - backend/handler/filesystem/resources_handler.py
    - backend/tests/endpoints/roms/test_manual.py
    - backend/tests/handler/filesystem/test_resources_handler.py
key-decisions:
  - "A non-empty path_manual is authoritative only when it is one direct PDF or Markdown child of the exact ROM resources/manual directory."
  - "Upload and redownload publish unique candidates before one expected-path CAS; only the loser candidate or validated superseded generation is cleaned."
  - "DELETE removes one validated owned path and clears path_manual plus url_manual only while the locked expected path still matches."
patterns-established:
  - "A missing valid authoritative file is clearable without widening discovery to sibling or legacy names."
  - "Local metadata-provider manuals are copied as read-only inputs into the same owned staging contract as HTTP bytes."
requirements-completed: [CAT-02]
duration: 28min
completed: 2026-08-24
---

# Phase 6 Plan 49: Primary Manual Path Authority Summary

**Token-named PDF and Markdown manuals now remain discoverable across restart and share one exact, failure-atomic CAS lifecycle across upload, redownload, and deletion.**

## Performance

- **Duration:** 28 min
- **Started:** 2026-08-24T13:59:56Z
- **Completed:** 2026-08-24T14:27:29Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Made a validated persisted `path_manual` the primary discovery authority while retaining only bounded `{rom.id}.pdf` and `{rom.id}.md` compatibility for empty legacy rows.
- Unified upload and HTTP/local redownload behind unique `OwnedCreate` candidates, locked expected-path CAS, loser cleanup, and validated superseded-generation cleanup.
- Replaced directory-wide primary deletion with exact owned-file deletion and one locked operation that conditionally clears `path_manual` and `url_manual`, including an already-absent valid file.
- Added stable Plan 53 evidence selectors for restart, exact deletion, CAS failures, both race orderings, and `file` plus `launchbox-file` source preservation.

## TDD Gate Compliance

- **RED:** `c4d5eaac2` ran `test_uploaded_token_manual_survives_restart_and_deletes_exactly` in a nonce-owned disposable lifecycle. Upload succeeded, then fresh-handler discovery failed at the intended fixed-name authority gap with normal collection, setup, execution, and exact cleanup.
- **GREEN:** `aa22e255b` passed the exact formerly failing selector and both complete changed test modules after the minimal path, CAS, and conditional-clear implementation.
- **Independent verification:** fresh final lifecycles passed 13 endpoint tests and 100 resource-handler tests, followed by scoped Trunk and `git diff --check`.

## Task Commits

1. **Task 1: RED specify token-path deletion and upload-redownload serialization** - `c4d5eaac2` (test)
2. **Task 2: GREEN share staged publication and expected-path CAS** - `aa22e255b` (feat)

## Files Created/Modified

- `backend/endpoints/roms/manual.py` - shares candidate publication and CAS cleanup across upload/redownload, copies local sources without mutation, and deletes exactly one authoritative owned file.
- `backend/handler/database/manual_handler.py` - locks and atomically clears both manual metadata fields only for the exact expected path.
- `backend/handler/filesystem/resources_handler.py` - validates persisted direct-child manual references, makes them authoritative, and bounds legacy fixed-name fallback.
- `backend/tests/endpoints/roms/test_manual.py` - covers restart, PDF/Markdown exact deletion, missing and invalid references, HTTP/write/CAS failure, both races, and stable local-URI IDs.
- `backend/tests/handler/filesystem/test_resources_handler.py` - covers token authority, unsafe references, missing authoritative files, and fixed PDF/Markdown compatibility.

## Decisions Made

- A non-empty invalid or missing persisted reference never falls back to another filename. Missing valid references remain eligible for exact conditional metadata clearing.
- Cleanup of a superseded DB reference is attempted only when that old value independently validates for the same ROM manual directory; invalid persisted text never becomes deletion authority.
- LaunchBox URI resolution uses its configured root plus lexical and resolved containment rather than constructing the stale mutation-capable handler; the source is opened read-only and copied.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used valid two-digit disposable runner indexes**

- **Found during:** Task 1 RED and Task 2 GREEN verification
- **Issue:** The plan's literal indexes `4901` and `4910+i` conflict with the checked-in acceptance harness, which accepts exactly a two-digit index and otherwise fails before creating resources.
- **Fix:** Used nonce-owned two-digit indexes 49 through 55 under the existing runner contract.
- **Files modified:** None.
- **Verification:** Every accepted lifecycle reported its module result and completed exact owned cleanup.
- **Committed in:** Not applicable.

**2. [Rule 3 - Blocking] Repaired LaunchBox local-URI resolution after descriptor hardening**

- **Found during:** Task 2 full endpoint-module GREEN verification
- **Issue:** `_resolve_local_file_uri` constructed `FSLaunchboxHandler`, whose stale constructor no longer supplies the storage descriptor now required by `FSHandler`, so the required `launchbox-file` case returned 500 before reading the source.
- **Fix:** Resolve the relative LaunchBox URI directly under the configured LaunchBox root with absolute, parent-traversal, and resolved-containment rejection. No mutation authority was added.
- **Files modified:** `backend/handler/filesystem/resources_handler.py`.
- **Verification:** The exact `[launchbox-file]` selector passed, followed by the full 13-test endpoint module and 100-test resource module.
- **Committed in:** `aa22e255b`.

---

**Total deviations:** 2 auto-fixed (2 Rule 3).
**Impact on plan:** Both fixes preserved the specified trust boundaries and test topology without adding schema, endpoint, deployment, or source-mutation scope.

## Verification and Cleanup

- Exact GREEN restart/deletion selector: 1 passed, 0 skipped.
- Exact LaunchBox local-source selector: 1 passed, 0 skipped.
- Final disposable endpoint lifecycle: 13 passed, 0 skipped.
- Final disposable resource-handler lifecycle: 100 passed, 0 skipped.
- Scoped Trunk passed all five touched files; `git diff --check` passed.
- Race and failure tests prove one referenced winner and no partial, loser, superseded, or staging orphan; local source mode, size, mtime, and SHA-256 remain unchanged.
- Each disposable lifecycle performed exact database, principal, basetemp, container, and volume cleanup.
- `romm-dev` remained `romm-romm-dev:exited`; no service was started, restarted, deployed, or given a public port.
- The original 28-entry untracked baseline remained byte-exact at `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1` after both task commits.

## Known Stubs

None. No goal-blocking placeholder, TODO, FIXME, hardcoded empty rendering path, or unwired data source was introduced.

## Threat Review

No unplanned endpoint, authentication path, schema change, or external mutation authority was introduced. Exact ROM-directory containment, allowed extensions, complete owned publication, locked CAS, single-path deletion, bounded errors, and immutable local inputs cover the Plan 49 threat register.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CR-02, CR-03, and verification must-have 29 now have deterministic token-path, race, failure, restart, and source-preservation coverage.
- Plan 53 can bind its required source rows to the exact stable pytest IDs, including `[file]` and `[launchbox-file]`.

## Self-Check: PASSED

- All five modified product/test files exist.
- Commits `c4d5eaac2` and `aa22e255b` resolve in repository history.
- RED then GREEN ordering, disposable tests, scoped static checks, cleanup, continuity, stopped-service, and baseline gates were verified.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-24_
