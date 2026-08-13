---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 24
subsystem: firmware-lifecycle-and-storage-policy
tags: [authorization, firmware, storage-policy, tdd, vue]
requires:
  - phase: 06-09
    provides: closed typed storage policy descriptors
  - phase: 06-15
    provides: catalog-only lifecycle precedent
provides:
  - firmware read, download, and catalog-only removal without client source mutation authority
  - pre-mutation denial coverage for external storage operation families
  - exact typed ASSETS and RESOURCES guards for owned screenshot and manual deletion
affects:
  [
    firmware-ui,
    legacy-firmware-ui,
    storage-policy,
    screenshot-delete,
    manual-delete,
  ]
tech-stack:
  added: []
  patterns:
    - authorize non-empty external intent before lookup or mutation
    - authorize exact typed owned descriptor immediately before owned handler I/O
key-files:
  created: []
  modified:
    - frontend/src/v2/components/Gallery/FirmwareTab.vue
    - frontend/src/v2/components/Gallery/DeleteFirmwareDialog.vue
    - frontend/src/services/api/firmware.ts
    - frontend/src/v2/components/Gallery/FirmwareTab.test.ts
    - frontend/src/components/Gallery/AppBar/Platform/FirmwareDrawer.vue
    - frontend/src/components/common/Platform/Dialog/DeleteFirmware.vue
    - frontend/src/components/common/Platform/Dialog/UploadFirmware.vue
    - backend/endpoints/firmware.py
    - backend/endpoints/screenshots.py
    - backend/endpoints/roms/manual.py
    - backend/tests/endpoints/test_storage_policy_denials.py
key-decisions:
  - "Allow firmware catalog removal only when no external delete intent is supplied; deny non-empty delete_from_fs before lookup or mutation."
  - "Authorize personal screenshot and primary manual deletion with exact typed ASSETS and RESOURCES descriptors immediately before owned I/O."
patterns-established:
  - "Shared mutation clients must remain source-neutral across active and retired UI callers."
requirements-completed: [CAT-01, CAT-04]
duration: 33m
completed: 2026-08-13
---

# Phase 6 Plan 24: Firmware External Mutation Closure Summary

**Firmware remains readable, downloadable, and catalog-removable while client source mutation is absent and crafted external mutation is denied before any filesystem or database change.**

## Performance

- **Duration:** 33 minutes 18 seconds
- **Started:** 2026-08-13T17:52:48Z
- **Completed:** 2026-08-13T18:26:06Z
- **Tasks:** 1
- **Files modified:** 11

## Accomplishments

- Removed firmware upload dropzones, buttons, pending-file state, upload client export, source-delete selection, and `delete_from_fs` payload expression.
- Preserved firmware reads, downloads, and catalog-only deletion while denying any crafted non-empty external delete request before lookup, filesystem I/O, or database mutation.
- Locked the enumerated external UPLOAD, SIDECAR_WRITE, COVER_WRITE, DELETE, EXTRACT, and MKDIR operation and descriptor pairs with direct policy, route-source, replay, redaction, and immutable-manifest assertions.
- Added exact typed ASSETS and RESOURCES authorization immediately before personal screenshot and primary manual owned deletion.
- Removed the retired legacy drawer upload entry and converted its shared firmware delete flow to catalog-only behavior so the source-neutral client contract typechecks across the complete frontend.

## TDD Evidence

- **RED:** `12be4bbe2` added the firmware UI/service regression and backend authority matrix. The frontend gate had 2 passing tests and 1 intended failure because upload and source-delete expression remained. The backend gate reached 13 passing selected cases before the intended missing owned screenshot guard failure.
- **GREEN:** `b0f31a12e` passed all 3 focused frontend tests, all 29 selected backend policy cases, and the 64-test broader endpoint suite.
- **REFACTOR:** No separate behavior refactor commit was required; mandatory hooks formatted and rechecked the GREEN files.

## Task Commits

1. **Task 1 RED: Close firmware and external authority** - `12be4bbe2` (test)
2. **Task 1 GREEN: Remove firmware external mutation** - `b0f31a12e` (fix)

## Files Created/Modified

- `frontend/src/v2/components/Gallery/FirmwareTab.vue` - Removes upload expression and performs catalog-only deletion.
- `frontend/src/v2/components/Gallery/DeleteFirmwareDialog.vue` - Confirms catalog removal without filesystem selection or destructive source copy.
- `frontend/src/services/api/firmware.ts` - Exposes read and catalog-only delete methods with no upload export or source-delete payload.
- `frontend/src/v2/components/Gallery/FirmwareTab.test.ts` - Locks maximum-grant source-neutral firmware behavior and preserved hash presentation.
- `frontend/src/components/Gallery/AppBar/Platform/FirmwareDrawer.vue` - Removes the retired upload entry point.
- `frontend/src/components/common/Platform/Dialog/DeleteFirmware.vue` - Keeps retired shared deletion catalog-only.
- `frontend/src/components/common/Platform/Dialog/UploadFirmware.vue` - Retires the unreferenced mutation component without adding a replacement client.
- `backend/endpoints/firmware.py` - Allows catalog-only removal and denies non-empty external deletion intent before mutation.
- `backend/endpoints/screenshots.py` - Authorizes exact typed ASSETS deletion immediately before personal screenshot I/O.
- `backend/endpoints/roms/manual.py` - Authorizes exact typed RESOURCES deletion immediately before primary manual I/O.
- `backend/tests/endpoints/test_storage_policy_denials.py` - Covers external authority families, owned guards, catalog neutrality, replay, redaction, and source immutability.

## Decisions Made

- Keep firmware catalog cleanup useful without granting external file mutation authority.
- Treat every non-empty `delete_from_fs` request as crafted external intent and reject it before lookup or partial selection.
- Keep typed-owned lifecycle useful through exact closed descriptors instead of weakening external guards.
- Retain the tracked legacy upload SFC as an unreferenced, non-rendering retired component rather than creating an alternate raw upload client or deleting unrelated history.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Bug] Bypassed the authentication decorator in direct endpoint body tests**

- **Found during:** Task 1 GREEN backend verification
- **Issue:** Direct calls reached the `protected_route` wrapper, which requires a real FastAPI request, instead of exercising the endpoint body under the test's controlled authorization and mutation spies.
- **Fix:** Used `inspect.unwrap` only in the two direct firmware endpoint-body tests.
- **Files modified:** `backend/tests/endpoints/test_storage_policy_denials.py`.
- **Verification:** The focused backend gate passed 29 tests and the broader endpoint gate passed 64 tests.
- **Committed in:** `b0f31a12e`.

**2. [Rule 3 - Blocking] Retired legacy callers of the removed shared firmware authority**

- **Found during:** Frontend typecheck
- **Issue:** Two retired legacy dialogs still referenced the removed shared upload method and source-delete parameter, causing three type errors.
- **Fix:** Removed the retired drawer upload entry, made its delete dialog catalog-only, and reduced the unreferenced upload SFC to a non-rendering retired component.
- **Files modified:** `frontend/src/components/Gallery/AppBar/Platform/FirmwareDrawer.vue`, `frontend/src/components/common/Platform/Dialog/DeleteFirmware.vue`, `frontend/src/components/common/Platform/Dialog/UploadFirmware.vue`.
- **Verification:** Frontend typecheck, production build, focused tests, installed ESLint, and commit hooks passed.
- **Committed in:** `b0f31a12e`.

**3. [Rule 3 - Blocking] Used the repository-installed ESLint after isolated Trunk resolution failed**

- **Found during:** Final scoped static verification
- **Issue:** Trunk's isolated ESLint 10 runner could not resolve the repository dependency `@eslint/js`, although formatting and backend Trunk checks were healthy.
- **Fix:** Ran the repository-installed ESLint inside the existing development container against every modified frontend source file.
- **Files modified:** None beyond formatter corrections in the planned GREEN commit.
- **Verification:** Installed ESLint exited zero with no errors or warnings; backend Trunk checked all four backend files with no issues.
- **Committed in:** Not applicable, verification environment only.

**4. [Rule 3 - Blocking] Completed the metadata commit with the verified host identity**

- **Found during:** Plan closeout
- **Issue:** The disposable Node GSD commit handler staged the exact tracking set but had no Git author identity.
- **Fix:** Committed the exact staged summary and tracking files from the verified Linux checkout with mandatory hooks.
- **Files modified:** None beyond the summary and approved tracking files.
- **Verification:** The final metadata commit contains only the summary, STATE, ROADMAP, and REQUIREMENTS files.
- **Committed in:** Final metadata commit.

---

**Total deviations:** 4 auto-fixed correctness or blocking issues.
**Impact on plan:** The fixes preserved the threat model, strengthened source neutrality across shared callers, and did not add endpoints, raw clients, storage authority, services, or dependencies.

## Issues Encountered

- Existing Vitest Cache API, router, and checkbox test warnings remained non-failing and unrelated to this plan.
- The production build retained existing dependency and bundle-size warnings; it completed successfully.
- The isolated test database required a task-only authentication secret because the existing development container did not carry one. The secret was supplied only to test processes and was not written to the repository.

## Verification

- Focused frontend firmware gate: 3 passed.
- Focused backend policy gate: 29 passed, 15 deselected.
- Complete policy plus related screenshot/manual endpoint suite: 64 passed.
- Frontend typecheck with 4096 MB Node memory: passed.
- Frontend production build with 4096 MB Node memory: passed.
- Frontend installed ESLint across six modified source files: passed with no errors or warnings.
- Scoped backend Trunk across four modified files: no issues.
- Static forbidden-expression scan across the v2 firmware tab, dialog, and service: no matches.
- `git diff --check`: passed.
- Commit hooks: passed without bypass for RED and GREEN commits.
- TDD sequence: `12be4bbe2` precedes `b0f31a12e`.
- Cleanup: `romm_test_0624` dropped and absence asserted; no service was restarted or deployed.

## Known Stubs

None. The retained legacy upload SFC is intentionally unreferenced and non-rendering after authority retirement; it does not flow empty or mock data to the UI.

## Threat Flags

None. All modified trust boundaries were enumerated by the plan threat model; no new endpoint, authentication path, filesystem access pattern, schema, raw client, or mutation authority was introduced.

## Next Phase Readiness

Firmware client authority is source-neutral, external operation families remain fail-closed, and typed-owned screenshot and manual deletion are ready for the adjacent setup and rename closure plans.

## Self-Check: PASSED

- Summary artifact exists at the required phase path.
- RED commit `12be4bbe2` and GREEN commit `b0f31a12e` exist.
- All eleven modified files exist and neither task commit deleted a tracked file.
- Stub scan found no unresolved TODO, FIXME, placeholder, coming-soon, or unavailable marker in modified implementation files.
- Exact task-owned database audit is empty.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-13_
