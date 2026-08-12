---
phase: 05-preview-and-read-path-cutover
plan: 07
subsystem: backend-read-delivery
tags: [mapping, download, zip-cache, openapi, nginx]
requires:
  - phase: 05-03
    provides: MappingReadContext and stable mapped-read failures
  - phase: 05-06
    provides: Descriptor-bound direct delivery
provides:
  - Atomic all-member DOWNLOAD preflight before response construction
  - Descriptor-bound single-file transfer and RomM-owned generated ZIP delivery
  - Complete fixed-layout read-authority inventory and generated frontend contract
affects: [phase-05-verification, phase-09-production-validation]
tech-stack:
  added: []
  patterns:
    [
      all-members-before-output,
      descriptor-bound-zip-inputs,
      owned-cache-redirects,
    ]
key-files:
  created: []
  modified:
    - backend/endpoints/roms/__init__.py
    - backend/utils/nginx.py
    - backend/utils/zip_cache.py
    - backend/handler/filesystem/roms_handler.py
    - frontend/src/__generated__/
    - .planning/phases/05-preview-and-read-path-cutover/05-VALIDATION.md
key-decisions:
  - "External mapped downloads never hand raw source paths to Nginx; only completed RomM-owned cache archives use internal redirects."
  - "ZIP cache identity contains bounded mapping ID, revision, logical path, member name, size, and timestamp rather than host paths."
requirements-completed: [SCAN-01, SCAN-02, SCAN-06]
duration: 5h
completed: 2026-08-12
---

# Phase 5 Plan 7: Atomic Multi-file Delivery Cutover Summary

Mapped downloads now authorize every required member before response construction, bind transfers to authorized descriptors, and redirect only to complete RomM-owned generated archives.

## Performance

- **Duration:** 5h across execution and two debug continuations
- **Completed:** 2026-08-12
- **Tasks:** 3
- **Task commits:** 5, plus 11 authorized full-gate remediation commits

## Accomplishments

- Preflights every single, multi-part, and bulk-download source for the active mapping revision before headers or output.
- Streams single files from one already-open descriptor with GET, HEAD, and Range parity.
- Generates ZIPs only from authorized descriptor snapshots into the RomM-owned cache.
- Removed the last unused fixed-layout import and obsolete mod_zip raw-path response classes.
- Regenerated frontend storage contracts, passed frontend typecheck, and completed the Phase 5 validation sign-off.

## Task Commits

1. Task 1 RED: `4dc6828cd`
2. Task 1 GREEN: `df45c0a99`
3. Task 2 RED: `2e71afd8a`
4. Task 2 GREEN: `bd287636f`
5. Task 3: `5f3b7ffb0`

Full-suite remediation commits: `6bda68d4c`, `01430b68c`, `f2579d268`, `5ee37ef46`, `b379b67db`, `97747767a`, `8c95869e2`, `3fb691917`, `231bbd791`, `ff9baf2e1`, and `0a3204c6c`.

## Verification

- Task 1 exact suite: 114 passed, 7 skipped, exit 0.
- Task 2 exact suite: 6 passed, exit 0.
- Fresh isolated full backend gate: 3,141 passed, 10 skipped, zero failures or errors, exit 0.
- Controlled checkout-bound OpenAPI generation: exit 0.
- Frontend typecheck: exit 0.
- Exact Phase 5 legacy read inventory: no findings, exit 0.
- Scoped non-mutating Trunk format gate: 6 applicable files checked, exit 0.
- Scoped Trunk check gate: 6 applicable files checked, exit 0.
- Repository commit hook checked all 24 Task 3 files with no issues.

## Decisions Made

- External mapped sources remain application-controlled descriptors for direct transfer.
- Nginx receives only paths for immutable RomM-owned completed cache files.
- Generated archive identity excludes absolute host paths and includes mapping revision.
- The user-approved scoped Trunk gate covered every applicable 05-07 file; 17 generated files were ignored by the repository's existing Trunk configuration.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Repaired full-suite fixture and contract regressions**

- **Found during:** Task 3 full backend gate.
- **Issue:** Stale capability fixtures, mutation expectations, session decoration, provider state, and scheduled scan mocks produced 24 failures and 82 errors.
- **Fix:** The authorized debug session repaired the original cluster and the subsequently exposed stale contracts in 11 atomic commits.
- **Verification:** Fresh isolated full backend gate passed 3,141 tests with 10 skips.
- **Commits:** `6bda68d4c` through `0a3204c6c`, as listed above.

**2. [Rule 3 - Blocking] Recovered the Trunk toolchain from disk exhaustion**

- **Found during:** Task 3 Trunk verification.
- **Issue:** A full root filesystem corrupted hermetic tool installation and caused a stalled Trunk daemon.
- **Fix:** User-authorized Docker image pruning recovered 3.108 GB while preserving all containers, followed by clean scoped formatter and linter runs.
- **Verification:** Both scoped Trunk commands exit 0.

**3. [Rule 2 - Missing Critical] Removed final dead read-authority remnants**

- **Found during:** Task 3 exact legacy inventory.
- **Issue:** An unused fixed-layout configuration import and obsolete mod_zip response classes retained legacy authority forms.
- **Fix:** Removed both without changing active consumers.
- **Verification:** Exact runtime inventory and focused suites pass.
- **Commit:** `5f3b7ffb0`.

**4. [AGENTS.md] Replaced the Windows-only generation recipe with controlled Linux containers**

- **Found during:** Task 3 contract generation.
- **Issue:** The plan's PowerShell and `Scripts/python.exe` recipe conflicts with the canonical Linux-only execution boundary.
- **Fix:** Used a uniquely named backend container, bounded readiness checks, exact cleanup, and a checkout-mounted Node container.
- **Verification:** Generation and typecheck exit 0.

**Total deviations:** 4 resolved deviations. All were required for correctness, verification, or repository policy compliance.

## Issues Encountered

- Initial full-suite runs used insufficiently isolated storage/database environments and were invalid evidence. The resolved debug workflow established a fresh schema and isolated mounts.
- Trunk 1.25.0 does not support `fmt --check`; its supported non-mutating equivalent is `fmt --no-fix --ci --no-progress`.

## User Setup Required

None.

## Known Stubs

None.

## Threat Flags

None. The change removes raw external handoff surfaces and adds no new network endpoint, authentication path, schema boundary, or source write.

## Next Phase Readiness

- Phase 5 read consumers are mapping-aware and source-immutable.
- Production-like Nginx and NAS behavior remains the planned Phase 9 validation boundary.

## Self-Check: PASSED

- All created and modified files exist.
- All Task 1, Task 2, Task 3, and debug remediation commits exist.
- Focused, full-backend, generation, typecheck, inventory, and scoped Trunk gates passed.
- No unrelated untracked file was staged.

---

_Phase: 05-preview-and-read-path-cutover_
_Completed: 2026-08-12_
