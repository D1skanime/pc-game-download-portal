---
phase: 05-preview-and-read-path-cutover
plan: 01
subsystem: planning
tags: [storage, mapping, integration, security]
requires:
  - phase: 03-mapping-administration-contracts
    provides: Versioned mapping administration, safe resolution, health, and bounded errors
  - phase: 02-read-only-policy-boundary
    provides: Operation-bound external read capabilities
provides:
  - Exact Phase 3 identifier binding for all Phase 5 read workflows
  - Mandatory Plan 05-04 durable preview persistence fallback
affects: [05-02, 05-03, 05-04, 05-05, 05-06, 05-07, 05-08]
tech-stack:
  added: []
  patterns: [exact-name integration gate, operation-specific capability binding]
key-files:
  created:
    - .planning/phases/05-preview-and-read-path-cutover/05-INTEGRATION-CONTRACT.md
  modified: []
key-decisions:
  - "Mapping revision is PlatformStorageMapping.version, serialized as an integer with mapping ID, not a parallel revision type."
  - "Plan 05-04 owns durable preview persistence through the explicit 0110 fallback because Phase 3 landed no persistence extension."
requirements-completed: [SCAN-01, SCAN-02, SCAN-03, SCAN-04, SCAN-05, SCAN-06]
duration: 10min
completed: 2026-08-11
---

# Phase 5 Plan 1: Phase 3 Integration Gate Summary

Exact-name binding to the landed mapping repository, integer revision, lifecycle state, safe resolver, live health snapshot, bounded errors, and operation-specific read capabilities.

## Performance

- Duration: 10 min
- Completed: 2026-08-11
- Tasks: 2
- Files modified: 1

## Accomplishments

- Recorded every mandatory Phase 3 contract with exact module paths and identifiers.
- Bound mapping identity to PlatformStorageMapping.id plus PlatformStorageMapping.version without inventing a parallel revision type.
- Bound Phase 5 filesystem work to StoragePolicy authorization and operation-specific capabilities returned by open_storage_access.
- Selected the mandatory Plan 05-04 durable preview-result persistence fallback at Alembic revision 0110.
- Approved the contract after the no-blocker verification passed.

## Task Commits

1. Task 1: Record the landed Phase 3 contract - 960679d72
2. Task 2: Approve the Phase 3 integration binding - a5077022f

## Files Created/Modified

- .planning/phases/05-preview-and-read-path-cutover/05-INTEGRATION-CONTRACT.md - Exact landed identifiers, persistence selection, evidence, and approval signal.

## Decisions Made

- Phase 3 represents the immutable mapping revision as the positive integer PlatformStorageMapping.version.
- Removed and disabled mappings are inactive rows distinguished by immutable StorageMappingAuditAction history; replacement uses an old inactive versioned row plus a new active row.
- Mapping-ID reads must extend DBStorageHandler with a public read-only method rather than create a repository beside it.
- Durable preview results will use the assigned Plan 05-04 model, handler, 0110 migration, and migration test.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The remote host does not provide ripgrep, so repository searches used grep as the documented fallback.
- Phase 5 planning files were already unrelated untracked files in the remote working tree. Only the integration contract and this summary were staged.

## User Setup Required

None.

## Known Stubs

None.

## Next Phase Readiness

- Plan 05-02 can consume the approved exact-name contract.
- Plan 05-04 must implement the recorded durable preview persistence fallback.
- No integration blockers remain.

## Self-Check: PASSED

- The integration contract exists in the authoritative Linux repository.
- Task commits 960679d72 and a5077022f exist.
- Required contract headings and identifiers are present.
- The contract contains no blocked row and records Resume signal: approved.
- No backend runtime file was created or modified.

---

Phase: 05-preview-and-read-path-cutover
Completed: 2026-08-11
