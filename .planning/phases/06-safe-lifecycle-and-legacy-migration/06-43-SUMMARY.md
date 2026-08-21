---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 43
subsystem: backend
tags: [manuals, owned-storage, compare-and-swap, concurrency]
requires:
  - phase: 06-33
    provides: crash-safe OwnedCreate publication
provides:
  - Failure-atomic primary-manual replacement
  - Locked expected-path compare-and-swap
  - Bounded concurrent replacement conflicts
affects: [manual-upload, resources-storage, catalog-lifecycle]
tech-stack:
  added: []
  patterns:
    [staged owned publication, database compare-and-swap, delete-after-commit]
key-files:
  created:
    - backend/handler/database/manual_handler.py
  modified:
    - backend/endpoints/roms/manual.py
    - backend/handler/database/__init__.py
    - backend/tests/endpoints/roms/test_manual.py
key-decisions:
  - "Primary manuals use opaque unique server names and never overwrite during receive."
  - "The database path changes only through a locked expected-path compare-and-swap."
  - "Superseded owned bytes are deleted only after the new path commits."
metrics:
  duration: 18m
  completed: 2026-08-21
---

# Phase 6 Plan 43: Failure-Atomic Primary Manual Replacement Summary

**Crash-safe unique manual publication followed by locked path compare-and-swap and post-commit retirement of superseded owned bytes.**

## Performance

- **Duration:** 18m
- **Tasks:** 2
- **Files changed:** 4
- **Tests:** 64 passed

## Accomplishments

- Replaced fixed-name destructive uploads with Plan 33's crash-safe typed `OwnedCreate.binary_file` publication.
- Added a dedicated handler that locks the exact ROM row and changes `path_manual` only when the pre-request path remains current.
- Added a barrier-driven two-client endpoint regression proving one concurrent winner, one bounded conflict, complete winner bytes, and exact loser cleanup.
- Preserved the prior authoritative file through publication and database commit, then removed only its exact owned path.

## Task Commits

1. **Task 1 RED: Concurrent replacement contract** - `9f7eda6cf`
2. **Task 2 GREEN: Atomic owned publication and CAS** - `ce60c5fcd`

## Decisions Made

- Client filenames validate the extension and multipart field only; storage authority comes from a cryptographically opaque server-generated basename.
- Publication precedes database CAS, and stale or failed requests clean only their own new artifact.
- Failure to retire an already-superseded owned file is logged with a static path-free message and does not misreport the committed replacement.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used an owned disposable test runner**

- **Found during:** Task 1 RED lifecycle
- **Issue:** The shared `romm-dev` service was stopped and restarting it was prohibited.
- **Fix:** Used nonce-owned disposable runners from `romm-romm-dev` on `romm_default`, with canonical backend bind, explicit DB/Redis/auth environment, task-only tmpfs, and ownership-gated cleanup.
- **Verification:** Normal application `SELECT 1` succeeded before and after, and disposable runners, databases, principals, and temporary files were absent after each accepted lifecycle.
- **Commit:** Not applicable.

**2. [Rule 3 - Blocking] Corrected disposable basetemp topology**

- **Found during:** Task 2 verification
- **Issue:** Mounting tmpfs at the exact basetemp pre-created the directory that pytest requires to create.
- **Fix:** Mounted disposable `/tmp` and passed the exact absent basetemp beneath it.
- **Verification:** The repeated isolated suite passed 64 tests and cleanup completed.
- **Commit:** Not applicable.

## Issues Encountered

- One early disposable GRANT command was rejected because shell quoting interpreted identifier backticks. Its owned database and principal were removed before retry.
- A shared `TestClient` serialized concurrent calls; independent clients against the same app allowed both requests to reach the deterministic barrier.
- Pytest reported inherited `pytest-env`, Alembic, and fork warnings; selected tests passed.

## Known Stubs

None.

## Threat Flags

None. The plan threat model covers the new owned-resource publication, database locking, conflict response, and exact-path cleanup surfaces.

## Verification

- Genuine RED: concurrent endpoint calls returned two `201` responses instead of one `201` and one `409`.
- GREEN: `tests/endpoints/roms/test_manual.py tests/handler/filesystem/test_storage_access.py -x`, 64 passed.
- Scoped Trunk format, ruff, and mypy checks passed all four changed files.
- No tracked files were deleted.
- The 28-entry pre-existing untracked baseline retained SHA-256 `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1`.

## User Setup Required

None.

## Self-Check: PASSED

The summary target, all four key files, and commits `9f7eda6cf` and `ce60c5fcd` exist. The isolated resources were removed, the shared app service was not restarted, and the exact 28-entry baseline was preserved.
