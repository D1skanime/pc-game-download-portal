---
phase: 12-dlc-detail-pages-for-local-pc-components
plan: 10
subsystem: frontend
tags: [vue, typescript, openapi, pc-components, metadata-matching]
requires:
  - phase: 12-08
    provides: target-aware parent and component metadata APIs
  - phase: 12-09
    provides: component-owned resource contracts
provides:
  - One typed matcher shell for PC parents and classified components
  - Generated PC matcher API contracts and target-contained confirmation
affects: [game-details, pc-components, match-rom-dialog]
tech-stack:
  added: []
  patterns: [discriminated matcher targets, nested component confirmation]
key-files:
  created:
    - frontend/src/v2/components/Dialogs/MatchRomDialog.test.ts
  modified:
    - frontend/package.json
    - frontend/src/services/api/rom.ts
    - frontend/src/v2/components/MatchRom/types.ts
    - frontend/src/v2/components/Dialogs/MatchRomDialog.vue
    - frontend/src/v2/components/GameDetails/PcComponents.vue
    - frontend/src/v2/views/GameDetails.vue
  deleted:
    - frontend/src/v2/components/GameDetails/PcMetadataReview.vue
key-decisions:
  - "PC targets are discriminated by parent ROM versus concrete classified component identity."
  - "Component confirmation uses only nested component selection routes and refreshes the containing detail state."
  - "Unresolved components expose no authoritative metadata matcher launcher."
duration: 10min
completed: 2026-09-03
---

# Phase 12 Plan 10: Shared PC Matcher Summary

**PC parent games and every classified PC component now use the established polished matcher, while component confirmations remain contained to their nested target.**

## Accomplishments

- Regenerated the OpenAPI client from the verified local API contract and added typed, normalized PC matcher adapters.
- Added an explicit discriminated target contract for PC parents and classified base, update, DLC, hotfix, language-pack, and extra components.
- Reused the existing grid/list matcher shell, provider filtering, cover picker, and confirmation flow without allowing component selection to call the generic parent update route.
- Replaced the simplified PC metadata review UI with shared parent and component matcher launchers. Unresolved components intentionally have no launcher.

## Task Commits

1. **Task 1: Regenerate and expose target-specific PC matcher service contracts**
   - `17188b4ec` `feat(12-10): generate PC matcher client contracts`
2. **Task 2: Extract the shared matcher shell behind an explicit target adapter**
   - `f8abaa466` `feat(12-10): share matcher shell with PC targets`
3. **Task 3: Replace PC metadata-review entry points only after shared matcher parity**
   - `78abf3691` `feat(12-10): route PC metadata actions through shared matcher`

## Verification

- `cd frontend && npm run generate` passed against `http://127.0.0.1:3344/openapi.json`.
- `cd frontend && npm run typecheck` passed.
- `cd frontend && npm run test -- src/v2/components/Dialogs/MatchRomDialog.test.ts src/v2/components/GameDetails/PcComponents.test.ts` passed, 4 tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking configuration] Corrected the local OpenAPI generator endpoint**

- **Found during:** Task 1
- **Issue:** The generator hardcoded port 3000, where an unrelated service returned HTTP 404. The verified RomM OpenAPI endpoint is port 3344.
- **Fix:** Updated the repository generator script to use `http://127.0.0.1:3344/openapi.json`, then regenerated the client through the project generator.
- **Files modified:** `frontend/package.json`, `frontend/src/__generated__/`
- **Verification:** Generation and typecheck pass.
- **Commit:** `17188b4ec`

**Total deviations:** 1 auto-fixed (Rule 3).

## Known Stubs

None.

## Self-Check: PASSED

- All listed created and modified files exist, and the planned review component was intentionally removed.
- All three Plan 12-10 task commits exist in Git history.
