---
phase: 02-read-only-policy-boundary
plan: 08
subsystem: filesystem-security
tags: [ast, inventory, storage-policy, capabilities, pytest]
requires:
  - phase: 02-05
    provides: endpoint mutation policy gates
  - phase: 02-06
    provides: capability-only transformation seams
  - phase: 02-07
    provides: owned sync, cleanup, and terminal job denials
provides:
  - Closed symbol-level registry for external reads, mutations, and migration exclusions
  - AST equality gate for sensitive mutation seams and enforcement links
  - Runnable evidence linkage for every classified row
affects: [02-09, phase-verification, storage-policy]
tech-stack:
  added: []
  patterns:
    [
      closed enforcement inventory,
      independent AST discovery,
      runnable evidence links,
    ]
key-files:
  created:
    - backend/handler/filesystem/storage_inventory.py
    - backend/tests/handler/filesystem/test_storage_inventory.py
  modified: []
key-decisions:
  - "Boundary-only policy guards remain explicit inventory rows even when their guarded function contains no direct filesystem call."
  - "Historical migrations are explicit non-runtime exclusions with import isolation evidence."
patterns-established:
  - "Every inventory row names one module and symbol, exact storage classes and operations, one disposition, a resolvable enforcement symbol, and a real pytest test."
requirements-completed: [SAFE-01, SAFE-02, SAFE-04, SAFE-06, TEST-03]
duration: 16min
completed: 2026-08-10
---

# Phase 2 Plan 8: Closed Storage Enforcement Inventory Summary

**A closed symbol-level storage registry now pairs every classified read and mutation seam with exact authority, enforcement, and runnable evidence, backed by an independent AST gate**

## Performance

- **Duration:** 16 min
- **Started:** 2026-08-10T10:03:00Z
- **Completed:** 2026-08-10T10:19:24Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Registered external reads across composition, firmware, platform, heartbeat, config, scan, socket, watcher, ROM, hash, streaming, direct download, and ZIP surfaces.
- Registered governed and structurally owned-only mutations across endpoints, archives, ZIP, patching, export, audio, sync, watcher, bootstrap, cleanup, and tasks.
- Added AST equality checks that fail on unknown sensitive mutation symbols, unresolved enforcement links, duplicate rows, missing evidence, and raw direct-download response adapters.
- Classified migrations 0019 and 0040 as explicit non-runtime exclusions and proved runtime code does not import them.

## Task Commits

1. **Task 1 RED: Specify complete enforcement evidence** - `72386183b`
2. **Task 1 GREEN: Register complete enforcement evidence** - `401a86b5b`
3. **Task 2 RED: Specify closed seam discovery** - `10b84a1cb`
4. **Task 2 GREEN: Fail closed on unknown seams and adapters** - `6d22cbbb4`

## Files Created/Modified

- `backend/handler/filesystem/storage_inventory.py` - Immutable row model and closed post-enforcement registry.
- `backend/tests/handler/filesystem/test_storage_inventory.py` - Inventory schema, evidence, AST equality, adapter, exclusion, and enforcement gates.

## Decisions Made

- Boundary-only guards remain registered even if their functions delegate I/O or deny before a literal mutation call.
- AST discovery is independent of the registry's symbol list and normalizes class-owned filesystem seams to their registered class authority.
- Evidence references must resolve to an actual pytest test function, and enforcement links must resolve to actual Python symbols.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ran verification in the canonical development image**

- **Found during:** Task 1 verification
- **Issue:** The Linux host does not provide `uv` or `trunk`, and the long-running development container cannot reach pytest's loopback database.
- **Fix:** Ran pytest in a disposable `romm-romm-dev` container sharing the MariaDB container network and bind-mounting the canonical backend checkout. Repository commit hooks formatted and checked both task files without bypass.
- **Files modified:** None
- **Verification:** 6 inventory tests pass; both task commits passed repository hooks.
- **Committed in:** Not applicable, environment-only deviation.

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** Verification used the repository's canonical image and isolated test schema without changing implementation scope.

## Issues Encountered

- The plan's host command was unavailable because `uv` is not installed on the Linux host. The equivalent repository image command passed.
- Pytest reports one existing Alembic `path_separator` deprecation warning.
- The canonical host has no gsd-sdk executable, so its documented state and roadmap mutations were applied directly and limited to Plan 02-08.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None. The inventory and static gate cover the plan's declared runtime-caller-to-storage-authority boundary and introduce no new network, authentication, schema, or filesystem access surface.

## Verification

- `test_storage_inventory.py`: 6 passed, 1 existing Alembic warning.
- Python compilation passed for both created files using an isolated bytecode cache.
- Repository commit hooks formatted and checked both task files without bypass.
- `git diff --check` passed.
- Stub scan found no TODO, FIXME, placeholder, coming-soon, or not-available markers.

## Next Phase Readiness

- Plan 02-09 can run the full Phase 2 regression and dual-fixture verification gates against this closed inventory.
- No blockers remain.

## Self-Check: PASSED

- Both created key files exist in the canonical Linux checkout.
- Task commits `72386183b`, `401a86b5b`, `10b84a1cb`, and `6d22cbbb4` exist on `codex/pc-module-analysis`.
- The focused inventory suite passes after commit-hook formatting.
- No tracked deletions or unintended untracked files were introduced.

---

_Phase: 02-read-only-policy-boundary_
_Completed: 2026-08-10_
