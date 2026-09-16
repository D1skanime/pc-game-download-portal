---
phase: 14-immutable-download-manifests
plan: "04"
subsystem: database-api
tags: [sqlalchemy, alembic, fastapi, openapi, download-manifest]
requires:
  - phase: 14-03
    provides: immutable manifest creation and retrieval API
provides:
  - Opaque UUID member identities bound to strong snapshots and future URLs
  - Database-enforced selected-component/source-member topology
affects: [15-download-delivery]
tech-stack:
  added: []
  patterns:
    [composite ownership foreign keys, pre-capture public identity allocation]
key-files:
  created:
    - backend/alembic/versions/0121_download_manifest_member_identity_and_topology.py
  modified:
    - backend/models/download_manifest.py
    - backend/handler/database/download_manifests_handler.py
    - backend/handler/filesystem/roms_handler.py
    - backend/endpoints/download_manifests.py
key-decisions:
  - "Allocate a UUID before HASH capture and use it for persisted identity, snapshot input, JSON, and the future URL."
  - "Use paired component IDs with composite foreign keys so direct database writes cannot cross source components."
requirements-completed: [DLMT-02]
duration: 45min
completed: 2026-09-16
---

# Phase 14 Plan 04: Immutable Download Manifest Gap Closure Summary

**Opaque UUID manifest-member identities are captured before hashing and protected by durable composite ownership constraints.**

## Performance

- **Tasks:** 2/2
- **Files modified:** 11

## Accomplishments

- Added portable public member IDs and composite selected/source component foreign keys.
- Bound the exact UUID to the NUL-separated strong validator, persisted member, JSON `file_id`, and future relative URL.
- Preserved STAT-only normal GET behavior and generated the updated frontend contract.

## Task Commits

1. `3bfcdd8e9` - RED: manifest identity topology tests.
2. `a9072d5a5` - GREEN: durable topology and migration.
3. `db19c7038` - RED: public snapshot binding tests.
4. `105caa111` - GREEN: capture, serialization, URL, and generated contract binding.

## Verification

- `uv run pytest tests/models/test_download_manifest.py -vv` - 7 passed.
- Focused filesystem, database-handler, and endpoint manifest tests - 13 passed.
- pytest-managed local DB `upgrade head`, `downgrade -1`, `upgrade head` - passed.
- Scoped `trunk check` over all plan-owned backend files - passed.
- Loopback OpenAPI generation on task-owned port 3345 and frontend `npm run typecheck` - passed.
- Router transfer-surface scan produced no matches.

## Deviations from Plan

### Auto-fixed Issues

1. [Rule 3 - Blocking] Extended Alembic version metadata to 64 characters.

- The required revision identifier exceeds Alembic's default 32-character version column.
- The migration widens `alembic_version.version_num` before recording the approved revision, allowing the portable migration cycle to complete.

2. [Rule 3 - Blocking] Overrode the frontend generator input with the task-owned 3345 loopback URL.

- The repository script remains hard-coded to 3344, which belonged to a non-task listener.
- Generation retained the script invocation but supplied the 3345 input override after exact task-owned Uvicorn readiness; only the changed generated contract was committed.

## Next Phase Readiness

Phase 15 can resolve opaque member IDs and perform its required fresh strong check before any transfer. No delivery endpoint, streaming, range handling, archive work, or source writes were added.

## Self-Check: PASSED

- Created migration and summary exist.
- All four task commits exist in git history.
