---
phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup
plan: 13
subsystem: frontend-operations-and-metadata
tags:
  [vue, typescript, vitest, locale, metadata-fallback, scan, retry, diagnostics]

# Dependency graph
requires:
  - phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup
    provides: shared operation contracts, provider resolution, lifecycle orchestration, and compatibility scan adapter
  - phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup
    provides: operation entry-point migration and specialized PC/DLC ownership boundaries
provides:
  - requested metadata-locale propagation through the legacy scan compatibility payload
  - actual provider-locale and fallback preservation for Steam metadata
  - deterministic scope-derived operation item identities and explicit preview diagnostics
  - documented capability matrix, blockers, and deferred human verification
affects:
  [
    phase-24-final-verification,
    frontend-scan-entry-points,
    metadata-provider-integration,
  ]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - reuse the shared OperationRequest and legacy scan adapter for generic operations
    - keep PC parent, DLC, and component matcher APIs as the specialized authority
    - separate requested metadata locale from actual provider locale and fallback values
    - derive retry item identity from sorted scope values

key-files:
  created:
    - .planning/phases/24-v2-quality-stabilization-and-legacy-boundary-cleanup/24-13-SUMMARY.md
  modified:
    - frontend/src/v2/data/contracts.ts
    - frontend/src/v2/data/operations.ts
    - frontend/src/v2/composables/useLibraryOperation.ts
    - backend/endpoints/sockets/scan.py
    - backend/handler/scan_handler.py
    - backend/handler/metadata/steam_handler.py
    - backend/handler/metadata/pc_steam_enrichment.py

key-decisions:
  - "Generic scan and metadata entry points continue through the shared operation request and existing legacy adapter."
  - "PC parent, DLC, and component matching remain on their existing specialized endpoints; no generic component scan path was added."
  - "Requested metadata locale, actual provider locale, and fallback metadata remain separate and loss-resistant."
  - "Preview completion is represented as a non-mutating result with an explicit preview diagnostic."
  - "Phase 24 remains open until automated infrastructure and final human verification gates are complete."

patterns-established:
  - "operationItemIds(request) returns deterministic scope-kind-prefixed identities with sorted, deduplicated IDs or slugs."
  - "Operation results retain stable item identity for retry context without introducing a second lifecycle."

requirements-completed: [QA-01, QA-03, QA-05, QA-06, QA-07, QA-08]

# Metrics
duration: documentation follow-up
completed: 2026-10-06
---

# Phase 24 Plan 13: Locale propagation and operation parity summary

**Unified scan requests now preserve requested metadata locale, provider fallback provenance, deterministic retry identity, and explicit preview diagnostics while retaining the existing PC/DLC adapter boundary.**

## Performance

- **Duration:** Documentation follow-up
- **Completed:** 2026-10-06
- **Tasks:** 3 plan tasks recorded
- **Implementation commits:** 3
- **Documentation files created:** 1

## Capability Matrix

| Capability                                        | Generic authority                                                                                                          | Evidence                                                         | Status                           |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | -------------------------------- |
| Classic ROM, platform, and metadata refresh scans | Shared OperationRequest, normalization, and legacy scan adapter/socket                                                     | `db76deb71`; focused operations and socket tests                 | Implemented                      |
| Requested metadata locale                         | `metadataLocale` is normalized and carried as `metadata_locale` through the compatibility payload                          | `db76deb71`; frontend operations tests and backend scan tests    | Implemented                      |
| Actual provider locale                            | Provider response locale is recorded separately from the requested locale                                                  | `7a6e009fd`; Steam handler tests                                 | Implemented                      |
| Fallback metadata                                 | Fallback values remain distinct from requested-locale values and preserve the existing Steam `text_variants` storage shape | `7a6e009fd`; Steam handler tests                                 | Implemented                      |
| Generic operation item identity and retry context | `operationItemIds(request)` derives sorted, deduplicated scope-kind-prefixed identities                                    | `9ad38dbd2`; 6 operations tests and 3 operation-composable tests | Implemented                      |
| Preview                                           | Shared operation result reports `preview` with a non-retryable diagnostic and no mutation                                  | `9ad38dbd2`; focused Vitest and typecheck                        | Implemented                      |
| Permission diagnostics                            | Existing shared operation result reports explicit `permission-denied` diagnostics                                          | Shared `useLibraryOperation` path and contracts                  | Implemented                      |
| PC parent, DLC, and component matching            | Existing specialized PC/DLC matcher API                                                                                    | Match dialog parity tests and 24-10 migration evidence           | Preserved                        |
| Generic component scan                            | None. Component scopes remain rejected by the legacy scan translation boundary                                             | Existing operation translation guard                             | Intentionally deferred/protected |
| Media ownership and storage mapping               | Existing media/storage authorities                                                                                         | No new model introduced by 24-13                                 | Preserved                        |

## Locale and Fallback Semantics

- UI locale and requested metadata locale are independent operation inputs.
- The requested metadata locale is normalized before legacy translation and provider execution.
- A provider response is not relabeled to match the request. The actual locale is retained as provider provenance.
- Steam localized values and English fallback values remain separate in the existing `text_variants` shape.
- Fallback behavior does not introduce a second provider resolver, metadata model, or ownership policy.

## Adapter and Ownership Boundaries

- Generic scan and metadata operations use the existing `useLibraryOperation` lifecycle wrapper and legacy scan adapter.
- The existing socket lifecycle remains the event authority.
- Manual classic ROM matching and cover search retain their dialog context on failure.
- PC parent, DLC, and component matching continue through their specialized endpoints. No generic component scan path was introduced.
- No storage mapping, media ownership, source mutation, or PC component ownership model was duplicated.

## Verification Evidence

Passed on the canonical Linux checkout with Node 24 explicitly added to PATH:

- `npm run test -- --run src/v2/data/operations.test.ts src/v2/composables/useLibraryOperation.test.ts`
  - 2 files passed, 9 tests passed.
- `npm run typecheck`
  - Passed with zero diagnostics.
- The operation parity commit was formatted and checked by the repository hook with no issues.

The locale/provider implementation commits also include focused frontend and backend tests for requested locale propagation, actual Steam locale recording, and fallback behavior.

## Infrastructure Blockers and Limits

- Backend integration verification remains blocked when MariaDB is unavailable at `127.0.0.1:3306`; this is recorded in the preceding Phase 24 validation summaries.
- The non-login SSH environment does not expose Node/npm by default. The focused frontend verification required `/home/d1sk/.nvm/versions/node/v24.19.0/bin` to be prepended to PATH.
- A full production build was not claimed as evidence for this documentation task. Existing Phase 24 records note third-party chunk-size and CSS pseudo-selector build warnings. Those warnings remain infrastructure/noise items and were not changed here.
- No `24-VALIDATION.md` existed when this documentation task ran, so no validation file was created.

## Deferred Final Human Verification

Phase 24 is not complete. The following remain explicitly deferred to the final human and end-to-end verification checkpoint:

- Verify classic ROM scans, platform scans, metadata refresh, and locale selection in the browser.
- Verify German or other requested metadata, actual provider locale, and English fallback display without relabeling or overwriting.
- Verify PC nested parent, DLC, and component matching through the specialized endpoints.
- Verify media search and selection, including failed-dialog context preservation.
- Verify preview and permission diagnostics in the UI.
- Verify retry and resume behavior with stable item identity after partial or retryable failures.
- Sweep both v2 themes, responsive breakpoints, mouse, touch, keyboard, and gamepad input.
- Re-run backend integration tests and the production build when MariaDB and the required build infrastructure are available.

## Task Commits

1. **Task 1: Propagate requested metadata locale** - `db76deb71` and `7a6e009fd`
2. **Task 2: Close operation parity gaps** - `9ad38dbd2`
3. **Task 3: Document final capability matrix** - this documentation commit

## Deviations from Plan

The implementation tasks were completed in their own commits before this documentation task. The planned `24-VALIDATION.md` artifact was absent, so it was not created. No implementation deviation was introduced by this documentation task.

## Next Phase Readiness

The shared operation and locale semantics are documented for final verification. Phase 24 remains open until the deferred human checks, backend infrastructure checks, and any remaining automated/build gates are completed.

---

_Phase: 24-v2-quality-stabilization-and-legacy-boundary-cleanup_
_Plan: 13_
_Documentation completed: 2026-10-06_
