---
phase: 24-v2-quality-stabilization-and-unified-library-operations
plan: 14
subsystem: backend-scan
tags:
  [scan, metadata-only, media-only, socketio, metadata, artwork, localization]
dependency_graph:
  requires: [mapped-scan-socket, provider-metadata-priority]
  provides:
    [
      explicit-scan-intents,
      metadata-only-scan-isolation,
      existing-rom-media-refresh,
    ]
  affects: [scan-socket, scan-handler, resource-path-persistence]
tech_stack:
  added: []
  patterns: [optional-bool-propagation, source-mocked-boundary-tests]
key_files:
  created: []
  modified:
    - backend/endpoints/sockets/scan.py
    - backend/handler/scan_handler.py
    - backend/tests/endpoints/sockets/test_scan.py
    - backend/tests/handler/test_scan_handler.py
    - backend/handler/metadata/rom_media.py
    - frontend/src/v2/data/operations.ts
    - frontend/src/v2/views/Scan.vue
decisions:
  - "Keep metadata_only false by default so existing scan behavior is unchanged."
  - "Preserve existing artwork URLs and persisted resource paths while allowing provider text metadata to refresh."
metrics:
  duration: "about 35 minutes"
  completed_date: "2026-10-06"
---

# Phase 24 Plan 14: Metadata-only scan isolation summary

Metadata-only scans now travel through the existing mapped socket scan lifecycle while refreshing provider text metadata without changing artwork, resource paths, owned media, or PC/DLC associations.

## Completed Task 1

Translated explicit operation intent through the existing frontend compatibility contract.

- Added optional `metadataOnly` and `mediaOnly` request flags and legacy payload fields.
- Rejects contradictory intents and invalid metadata/media policy combinations.
- Preserves deterministic operation item identities for library, platform, ROM, filesystem, and component scopes.
- Added preview diagnostics without introducing a second operation lifecycle.

## Completed Task 2

Task 2, Isolate backend metadata-only behavior.

- Added optional `metadata_only` propagation from the scan socket through mapping, platform, ROM identification, and `scan_rom`.
- Preserved artwork URLs and persisted resource paths during metadata-only scans, including complete scans.
- Skipped SGDB artwork lookup, resource downloads, provider-media persistence, Steam owned-media reconciliation, PC/DLC component synchronization and linking, and PC automation for metadata-only scans.
- Kept the normal path unchanged when `metadata_only` is false.
- Added source-mocked tests for socket forwarding, resource-path preservation, metadata text application, SGDB suppression, Steam media suppression, and component-link suppression.

## Verification

- `backend/endpoints/sockets/scan.py`, `backend/handler/scan_handler.py`, and both touched test files compile successfully with Python `compile(...)`.
- Source-mocked handler tests: 2 passed.
- Source-mocked socket tests: 2 passed.
- Normal MariaDB-backed pytest was not run because MariaDB is unavailable on the verified Linux VM, as requested.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking environment] Used the repository's existing `.venv/bin/pytest` because `uv` is not installed on the Linux VM.**

- **Impact:** No production behavior change.
- **Verification:** Isolated source-mocked tests passed.

**2. [Rule 3 - Test isolation] Added explicit mocks for existing database-backed lifecycle lookups in the new source-mocked tests.**

- **Impact:** Keeps the requested tests independent of MariaDB.
- **Files modified:** `backend/tests/handler/test_scan_handler.py`, `backend/tests/endpoints/sockets/test_scan.py`.

None - no architectural changes were needed.

## Known Stubs

None.

## Threat Flags

None. The change adds no endpoint, authentication, filesystem authority, or schema surface.

## Self-Check: PASSED

- Summary file exists.
- Task commit `11a5e632b` exists.
- The unrelated pre-existing mapping diff in `backend/endpoints/sockets/scan.py` remains outside the task commit.

## Final Reuse-First Audit

The final audit found no additional metadata-only or media-only behavior gap that can be fixed safely within this plan.

- Operation intents already translate through `OperationRequest`, the existing policy normalizer, and the single legacy scan adapter. Contradictory metadata-only/media-only policies are rejected, and component operations remain routed to the PC/DLC matcher authority.
- The scan socket already forwards both bounded flags through the mapped scan lifecycle. Media-only loads existing ROM rows only, filters requested ROM IDs against those rows, and never performs filesystem discovery, identification, or creation.
- ROM-only media refresh already reuses `POST /api/roms/{id}/media/refresh` through the shared `refresh_provider_owned_media` helper. Platform, library, and bulk media refresh remain on the existing socket lifecycle.
- Metadata-only preserves artwork and persisted resource paths, suppresses provider-media persistence and resource downloads, and preserves the existing Quick-task Steam DLC text refresh for already-linked components. That Quick-task authority was intentionally not reverted.
- `Scan.vue`, `ScanPlatformDialog.vue`, and `RefreshMetadataDialog.vue` expose the same translated metadata/media intent taxonomy, with scope-specific execution only.

### Verification evidence

- Python compilation passed for the touched scan and owned-media production modules.
- Targeted `git diff --check` passed for the plan's frontend, backend, test, and locale files.
- Frontend focused tests and typecheck were attempted but blocked by `npm: command not found` on `team4s-linux`.
- Backend focused tests were attempted but blocked by `No module named pytest`; `backend/.venv/bin/pytest` is also unavailable.
- No MariaDB-backed test was run, and no service, Docker workload, or Phase 25 file was changed.

## Completed Task 3

Media-only is now a bounded compatibility mode on the existing mapped scan lifecycle.

- Added media_only propagation from the scan socket through mapping execution to scan_platforms.
- The media-only path loads only existing database ROMs and never calls filesystem platform discovery, _identify_platform, or _identify_rom; it cannot create or identify ROMs.
- Optional ROM selection is filtered against already-loaded existing ROM IDs; platform/library scopes remain database-backed.
- Provider media refresh is shared with the existing POST /api/roms/{id}/media/refresh authority by extracting the existing download/reconciliation routine into handler.metadata.rom_media.
- Media-only updates only owned provider media; it does not write metadata fields, provider IDs, source paths, PC/DLC associations, or metadata priority results.
- Contradictory metadata_only plus media_only requests are rejected at the socket boundary.
- Added source-mocked socket tests for existing-ROM-only behavior and ROM-ID filtering.

## Task 3 Verification

- Python compile(...) passed for the three production modules and the socket test module.
- Targeted git diff --check passed for all Task 3 files.
- Targeted pytest was attempted with .venv/bin/pytest -k media_only; collection setup was blocked before test execution because MariaDB is unavailable at 127.0.0.1:3306.
- No frontend change was needed for the single-ROM path: the existing frontend refreshOwnedMedia API already targets the existing REST authority.
- The pre-existing mapping_scan_commands dirty change in backend/endpoints/sockets/scan.py was not staged or reverted.

---

## Task 4: Unified scan intents

# Phase 24-14 Task 4 Summary

## Outcome

Unified the scan controls in the existing frontend architecture around explicit operation intent:

- `Metadaten aktualisieren` / `Update metadata` sends `metadataOnly` and leaves media policies disabled.
- `Medien aktualisieren` / `Update media` sends `mediaOnly` and is explicitly limited to existing ROMs.
- A single-ROM media refresh reuses the existing `romApi.refreshOwnedMedia` REST authority.
- Platform and library/bulk media refresh continue through the existing socket and operation lifecycle.
- Quick, unmatched, hashes, complete, and new-platform scans remain available in the scopes where they are supported.
- German and English labels/descriptions now use the same intent vocabulary and state the non-mutating boundaries.

## Files

- `frontend/src/v2/views/Scan.vue`
- `frontend/src/v2/components/Gallery/ScanPlatformDialog.vue`
- `frontend/src/v2/components/Dialogs/RefreshMetadataDialog.vue`
- `frontend/src/v2/data/contracts.ts`
- `frontend/src/locales/en_US/{scan,rom}.json`
- `frontend/src/locales/de_DE/{scan,rom}.json`

## Verification

- `npx vitest run src/v2/data/operations.test.ts src/v2/sourceMutationControls.test.ts`: 25 tests passed.
- `npm run typecheck`: passed.
- `git diff --check` on all Task 4 files: passed.
- MariaDB-backed backend tests remain environment-blocked at `127.0.0.1:3306`; Task 3 contains source-mocked coverage for socket media-only behavior.

## Boundary check

No second scan lifecycle, provider resolver, storage mapping, or media reconciliation implementation was introduced. Existing REST and socket authorities remain the only execution paths.

## Phase-wide verification

- Frontend full suite: 105 files, 899 tests passed.
- Frontend typecheck and V2 maintainability gate passed (465 production files).
- Focused operation-contract tests passed (12 tests).
- Backend source compilation and `git diff --check` passed for touched Task 3 modules.
- Backend MariaDB-backed pytest remains blocked because MariaDB is unavailable at `127.0.0.1:3306`.
- Frontend production build reached asset transformation but remains environment-blocked by permission denied on root-owned `frontend/dist/sw.js`; no TypeScript/build transform error was reported.
- Human E2E checkpoint remains required before marking Phase 24 complete.
