---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 33
subsystem: owned-storage-integrity
tags: [filesystem, descriptors, durable-publication, atomic-write, tdd]
requires:
  - phase: 02-read-only-policy-boundary
    provides: descriptor-relative operation-bound owned storage capabilities
  - phase: 06-31
    provides: complete retrying writes and failure-atomic owned mutation foundations
provides:
  - complete-durable-content-or-no-final owned create contract
  - atomic no-replace publication with explicit parent-durability reconciliation
  - staged inherited-descriptor output for the real ROM patcher consumer
affects: [phase6-final-verification, manual-primary-replacement, owned-asset-writes]
tech-stack:
  added: []
  patterns:
    - cryptographically unique same-parent staging under descriptor authority
    - fsync file, close, hard-link no-replace, unlink staging, fsync parent
    - durable rollback or bounded indeterminate state after post-publication failure
key-files:
  created: []
  modified:
    - backend/handler/filesystem/storage_access.py
    - backend/utils/rom_patcher/patcher.py
    - backend/tests/handler/filesystem/test_storage_access.py
    - backend/tests/utils/test_rom_patcher.py
key-decisions:
  - "OwnedCreate create, binary_file, and subprocess_file share one descriptor-relative staged-publication state machine."
  - "Atomic hard-link publication provides Linux no-replace semantics without widening authority beyond the owned parent descriptor."
  - "A failed post-publication parent fsync triggers exact-name rollback and a second parent fsync; uncertain rollback raises a bounded indeterminate-publication error."
patterns-established:
  - "Owned publication: complete and fsync content before the final directory entry exists."
  - "Consumer success boundary: subprocess validation must complete inside the output capability context before publication."
requirements-completed: [CAT-02]
duration: 24min
completed: 2026-08-21
---

# Phase 6 Plan 33: Crash-Safe Owned Publication Summary

**Owned creates now expose a final name only after complete file durability, atomic no-replace publication, and parent-directory durability.**

## Performance

- **Duration:** 24 minutes
- **Started:** 2026-08-21T09:42:01Z
- **Completed:** 2026-08-21T10:06:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Routed byte creates, binary streams, and subprocess writers through one unique same-directory staging primitive.
- Made acknowledged success require file fsync, descriptor close, atomic hard-link no-replace publication, exact staging unlink, and parent-directory fsync.
- Added exact final-name rollback plus a bounded indeterminate state when post-publication durability cannot be reconciled.
- Kept failed, timed-out, killed, colliding, and finalization-failing ROM patcher output unpublished.
- Added process-death, collision, close/fsync, order, reconciliation, concurrency, cleanup, and real-consumer regressions.

## TDD Evidence

- **RED:** With nonce `ebeacffff85aca68dba2fcaf62d8d763`, the exact killed subprocess writer test collected one item and exited 1 at `assert not target.exists()` because the partial final name was visible. Collection and infrastructure were healthy.
- **GREEN:** With nonce `2ec8e6f28fa37a2a0a694879c74260d4`, both task modules collected 68 tests and passed 68 with exit 0.
- **Plan verification:** With independent nonce `16bc9002ec67edf656ac84f9e55ba5e8`, all four required modules collected 343 tests and passed 343 with exit 0.
- **REFACTOR:** Scoped Trunk formatted and checked all four touched files with no issues; no separate refactor commit was required.

## Exact Verification Commands and Exits

- **RED command inside the disposable Linux runner:** `/app/.venv/bin/pytest -p no:env -p no:cacheprovider --basetemp /tmp/romm-p0633-t1-ebeacffff85aca68dba2fcaf62d8d763 tests/handler/filesystem/test_storage_access.py::test_owned_create_subprocess_killed_writer_never_publishes_final -x` - exit 1 for the intended behavioral assertion.
- **GREEN command inside the disposable Linux runner:** `/app/.venv/bin/pytest -p no:env -p no:cacheprovider --basetemp /tmp/romm-p0633-t2-2ec8e6f28fa37a2a0a694879c74260d4 tests/handler/filesystem/test_storage_access.py tests/utils/test_rom_patcher.py -x` - exit 0, 68 passed.
- **Plan verification command inside the disposable Linux runner:** `/app/.venv/bin/pytest -p no:env -p no:cacheprovider --basetemp /tmp/romm-p0633-pv-16bc9002ec67edf656ac84f9e55ba5e8 tests/handler/filesystem/test_storage_access.py tests/utils/test_rom_patcher.py tests/handler/filesystem/test_storage_policy.py tests/handler/filesystem/test_storage_inventory.py -x` - exit 0, 343 passed.
- **Static gate:** `trunk fmt` and `trunk check` scoped to the four touched files - exit 0 with no issues.
- **Whitespace gate:** `git diff --check` - exit 0.
- **Commit hooks:** Both task commits ran normally without bypass and passed.

## Task Commits

1. **Task 1 RED: Specify crash-safe owned publication** - `609c15879` (test)
2. **Task 2 GREEN: Stage, fsync, publish no-replace, and fsync the parent** - `cafe39ad2` (feat)

## Files Created/Modified

- `backend/handler/filesystem/storage_access.py` - Adds the shared staged-publication state machine, streaming API, exact rollback, and bounded indeterminate state.
- `backend/utils/rom_patcher/patcher.py` - Keeps subprocess return-code validation inside the output context so failure aborts staging.
- `backend/tests/handler/filesystem/test_storage_access.py` - Proves process-death safety, ordering, cleanup, collisions, parent durability, binary streaming, and concurrent unique staging.
- `backend/tests/utils/test_rom_patcher.py` - Proves successful late publication and failed, timed-out, colliding, or finalization-failing consumer cleanup.

## Decisions Made

- Used a cryptographically random 128-bit staging suffix and bounded exclusive-create retries, avoiding predictable PID-only collisions.
- Used descriptor-relative `os.link` for atomic Linux no-replace publication, then removed only the exact staging name.
- Retained the original failure as the reported bounded error when cleanup is attempted; used the indeterminate class only when durable final-name rollback cannot be confirmed.
- Did not scan the directory or remove pattern-matched stale files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Kept ROM patcher failure detection inside staged output context**

- **Found during:** Task 2 implementation.
- **Issue:** The existing patcher checked the subprocess return code only after leaving `OwnedCreate.subprocess_file()`; the strengthened context would therefore publish failed patch output before the consumer raised.
- **Fix:** Moved bounded return-code parsing and failure raising inside the output context.
- **Files modified:** `backend/utils/rom_patcher/patcher.py`
- **Verification:** The real consumer failure, timeout, collision, and success tests passed within both the 68-test GREEN gate and the 343-test plan gate.
- **Committed in:** `cafe39ad2`

**2. [Rule 3 - Blocking] Corrected test typing surfaced by scoped Trunk**

- **Found during:** Task 2 static verification.
- **Issue:** Two test-only assignments were valid at runtime but failed mypy's precise callable and object narrowing checks.
- **Fix:** Added the exact assignment suppression for the deliberate fork-local write replacement and narrowed the inherited descriptor tuple before set conversion.
- **Files modified:** `backend/tests/handler/filesystem/test_storage_access.py`, `backend/tests/utils/test_rom_patcher.py`
- **Verification:** Scoped Trunk format and check passed all four touched files with no issues.
- **Committed in:** `cafe39ad2`

---

**Total deviations:** 2 auto-fixed (1 missing critical functionality, 1 blocking static-check issue).
**Impact on plan:** Both changes are required for the staged-publication contract and its prescribed quality gate; no unrelated behavior was added.

## Issues Encountered

- The project `romm-dev` service container was stopped and service restart was not authorized. Tests ran in nonce-named disposable containers from the existing development image, with only the repository backend, mock module, and exact `/tmp` path mounted.
- The image's generic Python symlink was stale. Each disposable runner created an ephemeral in-container compatibility symlink before pytest; no repository or service configuration changed.
- An initial RED attempt stopped on that runner setup problem and was rejected as infrastructure evidence. The accepted repeated RED failed only the intended behavioral assertion.
- An initial GREEN lifecycle stopped before pytest because shell quoting corrupted its grant statement. It was rejected, and its fresh database and principal were removed with cleanup PASS before the corrected independent run.
- Pytest emitted inherited warnings for the disabled pytest-env plugin configuration and Alembic path separator. They did not affect selected behavior.

## Known Stubs

None. Empty accumulators and the initially empty private staging-name field are internal state initialized before use, not UI or behavior placeholders.

## Threat Flags

None. The plan threat model covers owned descriptor authority, staging-to-final publication, kernel close/fsync/link failures, patcher inheritance, bounded errors, and isolated test resources. No endpoint, authentication path, schema, dependency, or external source mutation authority was introduced.

## User Setup Required

None.

## Cleanup

- Every accepted lifecycle proved its nonce database and principal absent with authoritative `0:0`, removed the exact basetemp and disposable runner, and reconfirmed normal application `SELECT 1`.
- No project service was started, restarted, stopped, or deployed.
- No tracked file was deleted.
- All 28 pre-existing untracked paths remain present and untouched.

## Next Phase Readiness

The CR-04 crash-safety gap is closed. The durable owned-create primitive is ready for the later primary-manual replacement flow and Phase 6 final verification.


## Self-Check: PASSED

The summary path, all four modified files, and task commits `609c15879` and `cafe39ad2` exist. All plan verification and acceptance gates passed, no tracked deletion occurred, no `p0633` runner, temporary directory, or database remains, and the 28 baseline untracked paths were preserved.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-21_
