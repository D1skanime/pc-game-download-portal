---
phase: 15-direct-resumable-transfer
plan: 01
subsystem: database
tags: [sqlalchemy, download-manifest, authorization, lifecycle]
requires:
  - phase: 14-immutable-download-manifests
    provides: Opaque member identities, durable component topology, and lifecycle state
provides:
  - Owner-scoped transfer member lookup by manifest ID and opaque public member ID
  - Lifecycle-preserving transfer candidate for later verification and streaming plans
affects: [15-02, 15-03, direct-transfer]
tech-stack:
  added: []
  patterns:
    [owner-scoped member query, transfer lookup without light revalidation]
key-files:
  created: []
  modified:
    - backend/handler/database/download_manifests_handler.py
    - backend/tests/handler/database/test_download_manifests_handler.py
key-decisions:
  - "Transfer lookup starts at the opaque persisted member and scopes it by manifest and owner."
  - "Transfer lookup only performs expiry transition; source validation remains the strong per-member check in Plan 15-02."
patterns-established:
  - "Transfer authorization resolves a member through its persisted manifest component relation, never from a path or internal member identifier."
requirements-completed: [XFER-01, XFER-03]
duration: 2min
completed: 2026-09-16
---

# Phase 15 Plan 01: Owner-Scoped Transfer Member Lookup Summary

**An opaque, owner-scoped manifest-member query now returns the trusted manifest, component, ROM, and source-member relations without filesystem revalidation or path exposure.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-09-16T21:09:00Z
- **Completed:** 2026-09-16T21:11:33Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Added a single member lookup constrained by manifest ID, authenticated user ID, and member public UUID.
- Eagerly loads the trusted persisted aggregate, selected component, ROM, and source-member relations for the later transfer layers.
- Preserves `REVOKED` and `SOURCE_CHANGED`, transitions elapsed `VALID` manifests to `EXPIRED`, and never invokes Phase 14 light revalidation.

## Task Commits

1. **Task 1: Specify and implement owner-scoped transfer-member lookup** - `a7a431590` (test), `77c43cbdd` (feat)

## Files Created/Modified

- `backend/handler/database/download_manifests_handler.py` - Adds the owner-scoped, lifecycle-aware transfer member resolver.
- `backend/tests/handler/database/test_download_manifests_handler.py` - Covers owner, manifest, opaque member, lifecycle, and no-light-revalidation behavior.

## Decisions Made

- The resolver returns the persisted `DownloadManifestMember`, letting the route inspect the owning aggregate lifecycle while obtaining the exact authorized member relation.
- Source hashing and source-change detection are deliberately deferred to Plan 15-02, immediately before transfer.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pytest emitted pre-existing cache permission warnings for `backend/.pytest_cache`; test execution completed successfully.

## Verification

- `cd backend && uv run pytest tests/handler/database/test_download_manifests_handler.py -k 'transfer_manifest_member or download_manifest' -q` - 8 passed.
- `trunk check backend/handler/database/download_manifests_handler.py backend/tests/handler/database/test_download_manifests_handler.py` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 15-02 can use the returned trusted relations to perform its fresh HASH-backed source verification before opening a transfer stream.

## Self-Check: PASSED

- Confirmed both task commits exist and both owned implementation/test files are present.

---

_Phase: 15-direct-resumable-transfer_
_Completed: 2026-09-16_
