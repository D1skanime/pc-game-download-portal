---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 04
subsystem: setup
tags: [frontend, setup, storage-mapping, pgdp]
requires: [33-02]
provides: [inline-folder-assignment, setup-folder-discovery-client, setup-assignment-save-flow]
affects: [phase-33-07, first-run-setup]
tech-stack:
  added: []
  patterns: [typed-server-slugs, wizard-owned-draft, server-readiness-gate]
key-files:
  created: [frontend/src/v2/components/Auth/SetupStepPlatforms.test.ts]
  modified: [frontend/src/services/api/setup.ts, frontend/src/v2/components/Auth/SetupStepPlatforms.vue, frontend/src/v2/views/Auth/Setup.vue, frontend/src/v2/views/Auth/Setup.test.ts, frontend/src/v2/sourceMutationControls.test.ts]
key-decisions:
  - Keep setup draft keyed by server folder names and submit only server platform slugs.
  - Authenticate before assignment mutation and continue only when the server response reports ready.
  - Keep the existing empty-home legacy read client compatible while the first-run flow uses the new folder contract.
metrics:
  duration: 22m
  completed: 2026-10-16
---

# Phase 33 Plan 04: First-run folder assignment summary

First-run setup now discovers direct Games folders, shows every folder in an accessible inline assignment table, preserves unknown folders as explicit unassigned rows, and saves assignments only after authentication and server readiness validation.

## Tasks

| Task | Result | Commit |
|---|---|---|
| 1. Implement inline assignment component | PASS, RED/GREEN/refactor gates | e05605291, c459ea90, cdf2c634a |
| 2. Make Setup own discovery, save, retry, continuation | PASS, RED/GREEN gates | 5d33e7433, 00ef219a3 |

## Verification

- compose frontend tests through pgdp-dev: PASS, 20 tests.
- compose frontend typecheck: PASS.
- Forbidden-copy scan for changed setup sources: PASS. No RomM branding, roms/{platform}, Storage Administration, PLATFORM_STORAGE_MAPPING, or LIBRARY_MANAGEMENT.
- Production file sizes: setup API 58 lines, assignment component 156 lines, Setup view 303 lines. All are under the 500-line gate.
- Protected dirty files remain untouched: docker-compose.override.yml, docker-compose.yml, and backend/pgdp_test/.

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 3 - Blocking tooling] Used the existing Compose service name**
   - Found during: Task 1 verification.
   - Issue: The plan's romm-dev service does not exist in this checkout.
   - Fix: Ran the same frontend test commands through the existing pgdp-dev service.
   - Verification: Component, setup, source-mutation tests and typecheck passed.

2. **[Rule 1 - Bug] Added the missing all-assignment guard**
   - Found during: Task 2 GREEN verification.
   - Issue: Finishing from a later wizard step could bypass the step-one assignment completeness check.
   - Fix: finishWizard returns before authentication or mutation unless every discovered folder has a platform slug.
   - Verification: Setup tests pass, including incomplete draft behavior.

3. **[Rule 3 - Blocking compatibility] Updated the affected existing component contract test**
   - Found during: frontend typecheck.
   - Issue: sourceMutationControls.test.ts still constructed the removed libraryInfo prop.
   - Fix: Updated that test to use the typed discovery/draft props.
   - Verification: Source-mutation test suite passes.

### Intentional compatibility

The shared setup client retains a typed getLibraryInfo read method for the existing empty-home consumer. The first-run Setup view does not call it and does not route through legacy Storage Administration. This avoids duplicating discovery logic while allowing the dependent home surface to migrate separately.

## Known Stubs

None.

## Authentication Gates

None.

## Threat Flags

None beyond the planned setup endpoints. The client submits server-provided folder names and platform slugs only; the backend remains authoritative for validation and readiness.

## Self-Check: PASSED

- Summary file exists.
- All production and test commits are present in Git history.
- Verification commands above passed on the verified Linux checkout.
