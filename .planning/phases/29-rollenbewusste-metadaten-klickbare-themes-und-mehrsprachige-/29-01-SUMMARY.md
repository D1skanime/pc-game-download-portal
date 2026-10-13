---
phase: 29-rollenbewusste-metadaten-klickbare-themes-und-mehrsprachige
plan: 01
subsystem: backend-metadata
tags: [igdb, metadata, facets, filters, pydantic, pc]
requires:
  - phase: 28-youtube-vorschau-steam-app-id-und-pc-save-medienverwaltung
    provides: Existing PC metadata persistence and component response contracts
provides:
  - Explicit IGDB company role records with developer, publisher, porting, and supporting evidence
  - Provider-qualified genre/theme identities with source labels and legacy compatibility arrays
  - Additive typed response schemas and canonical PC-aware facet query/sidecar support
affects: [phase-29-02, v2-game-details, gallery-filters]
tech-stack:
  added: []
  patterns:
    - Additive JSON metadata contract with legacy label arrays retained
    - Provider-qualified facet IDs separated from display labels
    - Canonical facet filters with legacy-value fallback
key-files:
  created: []
  modified:
    - backend/adapters/services/igdb_types.py
    - backend/handler/metadata/igdb_handler.py
    - backend/models/rom.py
    - backend/endpoints/responses/rom.py
    - backend/handler/database/roms_handler.py
    - backend/tests/handler/metadata/test_igdb_handler.py
    - backend/tests/models/test_pc_igdb_metadata.py
key-decisions:
  - "Preserve legacy genre/theme/company arrays and add canonical IDs, option records, and explicit company role records."
  - "Accept only positive integer IGDB entity IDs when constructing igdb:<numeric> identities."
  - "Canonical facet queries use provider IDs while legacy label filters remain readable for old metadata."
patterns-established:
  - "Role evidence is copied only from explicit IGDB booleans; roleless companies remain neutral."
  - "Facet sidecars expose additive canonical ID arrays while retaining existing display-label arrays."
requirements-completed: [PH29-ROLE, PH29-FILTER]
duration: 35min
completed: 2026-10-13
---

# Phase 29 Plan 01: Backend role-aware metadata and stable facet contract

**IGDB metadata now preserves explicit company roles and provider-qualified genre/theme identities while keeping legacy PC metadata readable and filterable.**

## Performance

- **Duration:** approximately 35 minutes
- **Started:** 2026-10-13
- **Completed:** 2026-10-13
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Added typed IGDB company and theme structures and normalized explicit developer, publisher, porting, and supporting evidence without inferring roles.
- Added additive company_roles, genre_ids, theme_ids, genre_options, and theme_options metadata fields using igdb:<numeric> IDs.
- Added Pydantic response contracts and canonical genre/theme filtering with legacy label fallback and additive sidecar IDs.
- Preserved existing legacy arrays, PC scope, and provider raw JSON ownership.

## Task Commits

1. **Task 1: Normalize explicit roles and stable facets** - d63d84ff1 (feat)
2. **Task 2: Persist and serialize the additive contract** - 826e2406d (feat)
3. **Task 3: Enforce canonical facet queries and PC scope** - fbdb483b0 (feat), follow-up wiring fix 1588f534a (fix)

**Plan metadata:** pending

## Files Created/Modified

- backend/adapters/services/igdb_types.py - Typed involved-company and theme provider records.
- backend/handler/metadata/igdb_handler.py - Explicit role and canonical facet normalization.
- backend/models/rom.py - Documents raw JSON ownership for canonical identities without migration.
- backend/endpoints/responses/rom.py - Additive typed role/facet response records.
- backend/handler/database/roms_handler.py - Canonical facet predicates and sidecar ID extraction.
- backend/tests/handler/metadata/test_igdb_handler.py - Role, duplicate, absent-role, and malformed-ID coverage.
- backend/tests/models/test_pc_igdb_metadata.py - Additive response round-trip coverage.

## Decisions Made

- Canonical identities are igdb:<positive numeric ID> and are never derived from translated labels.
- Existing label arrays remain available for legacy records and generated metadata views.
- Roleless companies are returned as neutral records with no guessed role.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing theme filter handler wiring**

- **Found during:** Task 3 verification
- **Issue:** The new theme predicate was referenced without a handler parameter and caused NameError.
- **Fix:** Added themes and themes_logic parameters and forwarded them through query construction.
- **Files modified:** backend/handler/database/roms_handler.py
- **Verification:** PC metadata endpoint focused tests passed.
- **Committed in:** 1588f534a

**2. [Rule 3 - Blocking] Used container runtime for unavailable host tooling**

- **Found during:** Task 1 test execution
- **Issue:** Host gsd-sdk and uv were unavailable; the verified romm-dev container provided the project runtime.
- **Fix:** Ran tests and scoped patch application through romm-dev without adding packages.
- **Verification:** Focused pytest suites passed in the container.
- **Committed in:** task commits above

**Total deviations:** 2 auto-fixed
**Impact on plan:** No product scope expansion; changes remain additive and backend-owned.

## Issues Encountered

- Host gsd-sdk and uv are unavailable. Manual GSD artifact updates and containerized test execution were used.
- npm run generate could not reach the configured OpenAPI endpoint at 127.0.0.1:3344; no generated files were changed. Backend response schemas remain the source contract.

## User Setup Required

None - no external service configuration required.

## Verification Evidence

- test_igdb_handler.py: 32 passed in isolated metadata execution.
- test_pc_igdb_metadata.py and test_generated_metadata.py: 18 passed.
- test_generated_metadata.py and test_rom_facets.py: 14 passed.
- test_pc_metadata.py -k get_roms: 2 passed.
- Python compile checks passed for modified backend modules.
- Commit hooks ran Trunk checks on each committed task file.

## Known Stubs

None.

## Threat Flags

| Flag                          | File                                     | Description                                                                                                  |
| ----------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| threat_flag: input-validation | backend/handler/metadata/igdb_handler.py | Provider IDs and filter IDs are explicitly constrained to positive integer-backed igdb:<numeric> identities. |

## Self-Check: PASSED

- Summary path exists.
- Task commits d63d84ff1, 826e2406d, fbdb483b0, and 1588f534a exist.
- Pre-existing .planning/STATE.md modification was not staged or overwritten.
