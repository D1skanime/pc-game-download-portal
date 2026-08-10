---
phase: 02-read-only-policy-boundary
plan: 10
subsystem: filesystem-security
tags: [trusted-descriptors, ast-inventory, tdd, read-only-policy]
requires:
  - phase: 02-09
    provides: full Phase 2 regression and dual-mount evidence
provides:
  - Composition-only external descriptor authority
  - Descriptor-only external access with pre-I/O raw model rejection
  - Independent fail-closed AST discovery for authority seams
affects: [phase-03, phase-05, phase-verification]
tech-stack:
  added: []
  patterns:
    [token-gated descriptor authority, syntax-derived authority allowlist]
key-files:
  created: []
  modified:
    - backend/handler/filesystem/storage_policy.py
    - backend/handler/filesystem/storage_access.py
    - backend/handler/filesystem/storage_inventory.py
    - backend/tests/handler/filesystem/test_storage_policy.py
    - backend/tests/handler/filesystem/test_storage_access.py
    - backend/tests/handler/filesystem/test_storage_inventory.py
key-decisions:
  - "Only build_storage_composition may construct runtime external descriptors."
  - "open_storage_access rejects raw StorageRoot input before authorization, normalization, or I/O."
  - "The independent AST gate excludes tests, tools, migrations, and non-authority Phase 1 resolver functions."
requirements-completed: [SAFE-01, SAFE-04, TEST-03]
duration: 18min
completed: 2026-08-10
---

# Phase 2 Plan 10: External Authority Closure Summary

**External reads now require composition-bound descriptors, with independent AST enforcement preventing caller-forgeable factories and raw StorageRoot access seams**

## Performance

- **Duration:** 18 min
- **Completed:** 2026-08-10
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Removed the public StorageRoot-to-descriptor factory and its model/path trust boundary.
- Narrowed external access and descriptor-relative open helpers to bound descriptors only, rejecting raw models before authorization, normalization, or filesystem observation.
- Added syntax-derived runtime discovery that permits only the composition provider and proves seeded factory and raw-root mutants are rejected.
- Re-ran focused, full Phase 2, ROM patcher, dual-mount, Trunk, and final inventory evidence.

## Task Commits

1. **Task 02-10-01 RED: Prove authority cannot be forged or hidden** - `480642c0a`
2. **Task 02-10-02 GREEN: Make trusted descriptors the sole authority** - `d7bd7250c`
3. **Task 02-10-03: Re-run complete Phase 2 and dual-mount evidence** - `bf3585975`

## Decisions Made

- Runtime external authority is created only by `build_storage_composition` through the private token-gated constructor.
- The dual-mount verifier retains its isolated private identity under `backend/tools`, outside runtime discovery.
- Phase 1 health and containment resolution remain non-authority operations; no Phase 3 mapping API or Phase 5 lookup was introduced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Kept scoped Trunk verification clean**

- **Found during:** Task 02-10-03
- **Issue:** Scoped Trunk surfaced existing static typing ambiguity in the now-touched capability tests and one invalid-operation authorization argument.
- **Fix:** Preserved runtime behavior with precise test-only typing suppressions, file-local inventory lint configuration, and authorization against the validated owned descriptor.
- **Files modified:** `backend/handler/filesystem/storage_access.py`, the three focused test files
- **Verification:** Scoped Trunk reports no issues; focused authority suite passes 297 tests.
- **Commit:** `bf3585975`

**Total deviations:** 1 auto-fixed blocking issue. **Impact:** Verification quality improved without changing product scope or authority semantics.

## Issues Encountered

- Pytest reports one existing Alembic `path_separator` deprecation warning.
- The canonical host uses the repository development image because host `uv` is unavailable.

## User Setup Required

None.

## Known Stubs

None.

## Threat Flags

None. This plan removes an authority surface and adds no endpoint, schema, authentication, or new filesystem trust boundary.

## Verification

- RED gate: expected failure on the public `create_external_descriptor` surface after 255 passing tests.
- Focused authority and inventory gate: 297 passed.
- Full Phase 2 suite: 865 passed, 8 skipped, including `tests/utils/test_rom_patcher.py`.
- Dual-mount verifier: PASS for identical writable and `:ro` denials, unchanged manifests, and writable owned output.
- Scoped Trunk launcher: no issues across all six plan files.
- Seeded alternative factory and raw StorageRoot mutants: rejected by AST discovery.
- Repository commit hooks passed without bypass.

## Next Phase Readiness

- Phase 2 is complete with both verification gaps closed.
- Phase 3 may build mapping administration contracts; Phase 5 retains database-backed mapping lookup and consumer cutover.

## Self-Check: PASSED

- All six modified key files exist in the canonical Linux checkout.
- Task commits `480642c0a`, `d7bd7250c`, and `bf3585975` exist on `codex/pc-module-analysis`.
- TDD RED precedes GREEN, all final gates pass, and no tracked files were deleted.
- Unrelated untracked files remain untouched.

---

_Phase: 02-read-only-policy-boundary_
_Completed: 2026-08-10_
