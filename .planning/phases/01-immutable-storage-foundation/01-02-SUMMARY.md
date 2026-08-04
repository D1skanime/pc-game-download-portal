---
phase: 01-immutable-storage-foundation
plan: 02
subsystem: filesystem
tags: [pathlib, hypothesis, normalization, path-security, immutable-storage]
requires:
  - phase: 01-immutable-storage-foundation
    provides: Immutable storage root and platform mapping identities from plan 01-01
provides:
  - Pure lexical normalization for logical relative storage paths
  - Bounded typed storage resolution error taxonomy
  - Adversarial POSIX, Windows, control-character, and Unicode test matrix
affects: [01-03, 01-04, 01-05, storage-resolver, platform-mapping]
tech-stack:
  added: []
  patterns: [raw-text validation before path composition, bounded domain errors, exact Unicode preservation]
key-files:
  created:
    - backend/exceptions/storage_exceptions.py
    - backend/handler/filesystem/storage_resolver.py
    - backend/tests/handler/filesystem/test_storage_resolver.py
  modified: []
key-decisions:
  - "Empty paths are accepted only through the explicit allow_root internal contract; mappings remain non-empty."
  - "Normalization preserves valid text byte-for-byte and rejects controls, ambiguous separators, dot segments, traversal, and absolute Windows or POSIX forms."
patterns-established:
  - "Lexical validation is pure and independent from the mutating FSHandler hierarchy."
  - "Storage resolution failures expose bounded domain messages without operating-system paths."
requirements-completed: [PATH-01, PATH-04]
duration: 6min
completed: 2026-08-04
---

# Phase 1 Plan 2: Pure Lexical Normalization and Bounded Errors Summary

**Pure, non-mutating relative-path validation with exact Unicode preservation and a bounded storage resolution error taxonomy**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-04T20:50:05Z
- **Completed:** 2026-08-04T20:56:05Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Rejects empty mapping paths, POSIX absolute paths, Windows drive, UNC and device forms, backslashes, ambiguous separators, dot segments, traversal, NUL, C0, and DEL before filesystem composition.
- Preserves spaces, dots, hyphens, nested directories, case, umlauts, composed and decomposed Unicode, and 255-character components exactly.
- Defines typed errors for invalid input, missing or inactive roots, missing, non-directory, or unreadable targets, symlinks, escapes, and writable-root safety observations.
- Keeps normalization independent from `FSHandler` and performs no filesystem access or mutation.

## Task Commits

1. **Task 1 RED: Lexical normalization matrix** - `ac0160129` (test)
2. **Task 2 GREEN: Normalization and exception contracts** - `2a543ca11` (feat)

## Files Created/Modified

- `backend/exceptions/storage_exceptions.py` - Bounded storage resolution exception hierarchy.
- `backend/handler/filesystem/storage_resolver.py` - Pure logical relative-path normalizer.
- `backend/tests/handler/filesystem/test_storage_resolver.py` - Parameterized and property-based lexical security coverage.

## Decisions Made

- Empty text represents the root only when `allow_root=True`; the default mapping contract rejects it.
- Valid logical names are returned unchanged. The normalizer does not case-fold, Unicode-normalize, URL-decode, resolve, or touch the filesystem.
- Invalid raw values use one bounded message rather than echoing attacker-controlled text or deployment paths.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Repaired Unicode fixtures corrupted by the remote patch transport**
- **Found during:** Task 2 GREEN verification
- **Issue:** Non-ASCII test literals arrived as question marks, invalidating composed and decomposed Unicode evidence.
- **Fix:** Expressed Unicode fixtures with Python Unicode escapes so source transport is ASCII-safe while runtime values remain exact Unicode.
- **Files modified:** `backend/tests/handler/filesystem/test_storage_resolver.py`
- **Verification:** All 28 lexical and property tests pass, including distinct NFC and NFD values.
- **Committed in:** `2a543ca11`

---

**Total deviations:** 1 auto-fixed bug
**Impact on plan:** The fix restores the planned Unicode proof without expanding runtime scope.

## Issues Encountered

- The host user cannot execute the root-owned `uv` environment. Verification ran inside the existing RomM development container against an isolated MariaDB test database without restarting any service.
- Trunk and Ruff were unavailable in the host and container environments. Git hooks were not bypassed, Python compilation passed, and targeted tests passed.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None. This plan adds no endpoint, authentication path, schema change, external file access, or consumer integration beyond its declared lexical trust boundary.

## Next Phase Readiness

- Plan 01-03 can compose this lexical boundary with strict, non-mutating canonical containment and symlink rejection.
- No NAS activation, external-root access, API cutover, or consumer wiring occurred.

## Self-Check: PASSED

- All three planned files exist.
- Commits `ac0160129` and `2a543ca11` exist in repository history.
- All 28 focused tests pass and the resolver has no mutating-handler dependency or filesystem operation.

---
*Phase: 01-immutable-storage-foundation*
*Completed: 2026-08-04*
