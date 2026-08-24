---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 52
subsystem: owned-storage-integrity
tags: [python, filesystem, descriptors, durable-publication, pytest, tdd]
requires:
  - phase: 06-33
    provides: shared descriptor-relative staged publication for OwnedCreate paths
  - phase: 06-review
    provides: WR-01 descriptor-number reuse finding
provides:
  - single-consumption close semantics for staged publication descriptors
  - reused-descriptor sentinel regression for binary_file and subprocess_file paths
  - exact cleanup and original-error preservation after consumed close failures
affects: [phase-06-verification, plan-06-53, owned-asset-publication]
tech-stack:
  added: []
  patterns:
    - clear descriptor ownership before one close attempt
    - continue exact staging-name cleanup without replaying a consumed descriptor number
key-files:
  created: []
  modified:
    - backend/handler/filesystem/storage_access.py
    - backend/tests/handler/filesystem/test_storage_access.py
key-decisions:
  - "A staged descriptor number is consumed after the first os.close call regardless of its result."
  - "Abort swallows one cleanup close error, then continues exact staging unlink and parent fsync without retrying the number."
  - "Plan 53 binds the adversarial regression through explicit binary_file and subprocess_file pytest IDs."
patterns-established:
  - "Descriptor ownership: clear before close and never retry a possibly reused integer."
  - "Close-error cleanup: preserve the original bounded cause while continuing exact namespace cleanup."
requirements-completed: [CAT-02]
duration: 48min
completed: 2026-08-24
---

# Phase 6 Plan 52: Single-Consumption Staged Descriptor Summary

**Owned staged publication now closes each descriptor number at most once, preserving reused files or sockets while exact failure cleanup continues.**

## Performance

- **Duration:** 48 min
- **Started:** 2026-08-24T14:59:54Z
- **Completed:** 2026-08-24T15:47:24Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Removed both staged-publication close retry blocks while retaining clear-before-close ownership transfer.
- Preserved the original close error as the bounded publication cause and continued exact staging unlink plus parent fsync.
- Added a real Linux descriptor-reuse sentinel that proves later cleanup cannot close the reused integer.
- Added stable Plan 53 selector IDs `[binary_file]` and `[subprocess_file]`, plus abort close-once coverage.

## TDD Gate Compliance

- **RED:** Commit `18dd9f726` preceded all production edits. Nonce `6f5cdabf909d80117b9da2b5b36f0279` collected two cases and failed `[binary_file]` with `EBADF` because the unsafe second `os.close` had closed the sentinel.
- **GREEN targeted:** Nonce `5a30f5c25210d78f361f9116c3bcd33d` passed both explicit reuse IDs and the abort close-once case, 3 passed.
- **GREEN module:** Nonce `221a00048df0db9f3d32ec65b6d7beaf` passed all 64 storage-access tests.
- **Final after static correction:** Nonce `b453805b0ce699f94b21e06b9baad47a` again passed all 64 storage-access tests.
- **Static gate:** Scoped Trunk format and check passed both touched files with no issues; `git diff --check` passed.
- **Ordering:** `test(06-52)` commit `18dd9f726` precedes `feat(06-52)` commit `3efe4b417`.

## Task Commits

1. **Task 1: RED prove a consumed descriptor number is never retried** - `18dd9f726` (test)
2. **Task 2: GREEN consume descriptor ownership after one close attempt** - `3efe4b417` (feat)

## Files Created/Modified

- `backend/handler/filesystem/storage_access.py` - Removes retry-after-error close calls from publication and abort while preserving exact cleanup.
- `backend/tests/handler/filesystem/test_storage_access.py` - Proves real descriptor reuse survival, exact staging cleanup, original cause retention, explicit Plan 53 IDs, and one-close abort behavior.

## Decisions Made

- Treat a close result as consuming the integer because Linux may release the descriptor before reporting an error.
- Keep the existing publication order, error taxonomy, exact-name authority, and parent durability behavior unchanged.
- Use `binary_file` and `subprocess_file` as explicit parameter IDs required by Plan 53; existing create-path close-failure tests remain in the complete module.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Prepared an accessible disposable Python runtime**

- **Found during:** Task 1 RED verification.
- **Issue:** The image venv points through a root-owned Python home that UID 1000 cannot read. Direct execution failed before collection.
- **Fix:** Extracted the exact image Python distribution into a nonce-owned host `/tmp` directory, mounted it read-only at `/opt/romm-python`, and ran the repository backend read-only as UID/GID 1000.
- **Files modified:** None.
- **Verification:** Accepted RED and all GREEN runners reported Python 3.13.12 and collected the intended tests.
- **Committed in:** Not applicable.

**2. [Rule 3 - Blocking] Supplied isolated configuration-only runner values**

- **Found during:** Task 1 RED verification.
- **Issue:** Conftest requires authentication, writable configuration, and database credential fields even though this module overrides database fixtures.
- **Fix:** Set `ROMM_BASE_PATH=/tmp/romm`, an explicitly disposable auth key, and disposable database field values inside the network-none container. No database connection or database creation occurred.
- **Files modified:** None.
- **Verification:** The accepted RED reached the intended behavioral assertion; every GREEN run collected and completed the filesystem-only module.
- **Committed in:** Not applicable.

**3. [Rule 3 - Blocking] Corrected a test-only mypy exception-target conflict**

- **Found during:** Task 2 scoped Trunk verification.
- **Issue:** Reusing `error` after an `except OSError as error` target violated mypy's exception-target lifetime rule.
- **Fix:** Used distinct `close_error` and `fstat_error` names without changing behavior.
- **Files modified:** `backend/tests/handler/filesystem/test_storage_access.py`.
- **Verification:** Scoped Trunk passed, followed by a fresh 64-test module pass.
- **Committed in:** `3efe4b417`.

---

**Total deviations:** 3 auto-fixed (3 Rule 3 blocking issues).
**Impact on plan:** All adaptations were required for isolated verification or static correctness. Product scope and descriptor authority remained exactly bounded to Plan 06-52.

## Issues Encountered

- Rejected pre-collection runner attempts exposed the image Python-home permission, required auth value, read-only default `/romm` path, and required database fields one at a time. Every rejected attempt cleaned its exact full container ID and nonce-owned Python directory.
- The accepted runner remained network-none, published no port, created no database, and mounted canonical backend source read-only.
- Pytest reported the inherited warning for the disabled pytest-env plugin configuration. It did not affect collection or behavior.

## Known Stubs

None. The private empty staging name and optional descriptor are initialized internal state, not placeholders or unwired behavior.

## Threat Review

No unplanned endpoint, authentication path, schema change, dependency, or new filesystem authority was introduced. The Plan 06-52 threat register covers descriptor reuse, close-error cleanup, bounded error chaining, and exact staging-name removal.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- WR-01 and must-have 31's descriptor-reuse warning are closed.
- Plan 06-53 can bind directly to `test_owned_create_close_error_never_closes_reused_descriptor[binary_file]` and `[subprocess_file]`.
- Plan 06-50 remains the true next incomplete plan and must stay the current GSD position.

## Cleanup

- Every runner and Python-source container was removed by its validated 64-hex ID.
- Every nonce-owned `/tmp/p0652-python-*` directory was removed.
- No database, principal, volume, port, or service lifecycle was used.
- `romm-dev` remained stopped.
- The original 28-entry untracked status baseline remained exact at `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1`.

## Self-Check: PASSED

- Both modified source/test files exist.
- Commits `18dd9f726` and `3efe4b417` resolve in repository history in RED then GREEN order.
- The summary exists at the required Plan 06-52 path.
- Fresh tests, scoped static checks, exact cleanup, stopped service, and baseline gates passed.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-24_
