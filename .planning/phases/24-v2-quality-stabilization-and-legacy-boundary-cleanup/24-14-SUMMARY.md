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
