---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 47
subsystem: acceptance
tags: [python, pytest, docker, mariadb, mysql, postgresql, vue, evidence]
requires:
  - 06-33
  - 06-34
  - 06-35
  - 06-36
  - 06-37
  - 06-38
  - 06-39
  - 06-40
  - 06-41
  - 06-42
  - 06-43
  - 06-44
  - 06-45
  - 06-46
provides:
  - Deterministic complete Phase 6 acceptance command
  - Digest-bound acceptance, validation, and exact source coverage evidence
  - Isolated per-module database, principal, basetemp, and container lifecycle
affects: [phase-06-verification, generated-contracts, frontend-verification]
tech-stack:
  added: []
  patterns:
    - nonce-owned disposable verification resources
    - canonical JSON digest binding
    - exact-set Markdown coverage parsing
key-files:
  created:
    - backend/tools/verify_phase6_acceptance.py
    - .planning/phases/06-safe-lifecycle-and-legacy-migration/06-47-ACCEPTANCE.json
  modified:
    - backend/tests/tools/test_verify_phase6_acceptance.py
    - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Input.ts
    - frontend/src/__generated__/models/LegacyImpactConfirmationSchema_Output.ts
    - frontend/src/__generated__/models/LegacyMigrationResultSchema.ts
    - .planning/phases/06-safe-lifecycle-and-legacy-migration/06-47-PLAN.md
    - .planning/phases/06-safe-lifecycle-and-legacy-migration/06-VALIDATION.md
    - .planning/phases/06-safe-lifecycle-and-legacy-migration/06-SOURCE-AUDIT.md
key-decisions:
  - "Bind the prior contract to the reproducible fresh total of 843 outcomes; retain 939 only as unsupported historical narrative."
  - "Keep romm-dev stopped and run every backend, dialect, contract, and frontend gate through disposable runners."
  - "Reuse Plan 45 UI evidence only where relevant files did not drift and mark it as not freshly run."
  - "Commit the exact generated terminal-newline output so controlled generation is byte-stable."
requirements-completed:
  [CAT-01, CAT-02, CAT-03, CAT-04, MIG-01, MIG-02, MIG-03, MIG-04, MIG-05]
metrics:
  duration: 8h54m
  completed: 2026-08-24
---

# Phase 6 Plan 47: Complete Acceptance Closure Summary

A checked-in, digest-bound Phase 6 acceptance harness now proves isolated backend regressions, three-dialect migration authority, generated-contract stability, frontend quality gates, immutable source manifests, exact cleanup, and complete source coverage without starting the application service.

## Performance

- **Duration:** 8h54m
- **Started:** 2026-08-23T23:33:51Z
- **Completed:** 2026-08-24
- **Tasks:** 3
- **Files changed:** 10

## Accomplishments

- Added a 1,530-line acceptance harness with exact 29-module prior inventory, deduplicated Phase 6 inventory, nonce-owned lifecycle cleanup, redaction, atomic evidence publication, and deterministic evidence verification.
- Published acceptance run `0525ee9a9a51ae4fad34e5791398cd40` with digest `f4b45a758dd5950caaee1f479220cb617aab1a053d7e5fa052ec0c72a47d94ff`.
- Passed 836 prior tests plus 7 skips, 403 deduplicated Phase 6 tests, MariaDB/MySQL/PostgreSQL lifecycle authority, generated contracts, focused/full frontend tests, typecheck, build, locales, and static checks.
- Bound validation to the successful structured run and replaced the source audit with exactly 88 unique current IDs.
- Preserved the exact 28-entry user-owned untracked baseline and kept `romm-dev` stopped.

## Task Commits

1. **Task 1 RED contract:** `9211264c0` (`test(06-47): specify complete phase acceptance gate`)
2. **Generated contract synchronization:** `22b983dcb` (`fix(06-47): synchronize generated contract output`)
3. **Task 2 complete gate:** `b15097dd0` (`feat(06-47): implement complete phase acceptance gate`)
4. **Task 3 evidence binding:** `57792b07f` (`docs(06-47): bind final validation and source coverage`)
5. **Formatted audit parser fix:** `765f79389` (`fix(06-47): accept formatted audit separators`)

## Verification Results

| Gate                                                 | Result                                                                                 |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------- |
| RED absent-harness contract                          | Expected named failure, exit 1; no collection, Docker, or DB error                     |
| Pure harness contract                                | 10 passed; one inherited unknown-config warning                                        |
| Harness self-test                                    | 10 passed                                                                              |
| Isolated scan regression after runner initialization | 76 passed                                                                              |
| Prior backend contract                               | 29 modules; 836 passed, 7 skipped; 843 outcomes                                        |
| Deduplicated Phase 6 backend                         | 14 modules; 403 passed                                                                 |
| Dialect lifecycle authority                          | MariaDB, MySQL, PostgreSQL complete; exits 0                                           |
| Contract/generated gate                              | 257 files, identical digest before/after                                               |
| Frontend                                             | Focused, full, typecheck, build, locales, static all exit 0                            |
| Source manifests                                     | 2,746 entries, identical digest before/after                                           |
| Evidence parser                                      | Digest, validation binding, and exact 88-ID coverage passed                            |
| Cleanup audit                                        | All owned resource counts zero; normal DB `SELECT 1` before/after                      |
| Baseline                                             | 28 entries; SHA-256 `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1` |

## Decisions Made

- Replaced the unsupported 939-outcome minimum with the user-approved fresh exact result of 843. No stored historical raw evidence exists for the 96-outcome difference, so this is documented as an evidence-count correction and not a functional-regression claim.
- Kept all verification in disposable runners because `romm-dev` was intentionally stopped and deployment/restart was outside scope.
- Recorded Plan 45 UI coverage as `previously_validated_no_drift` with `fresh_run=false`.
- Left STATE, ROADMAP, and REQUIREMENTS unchanged because Plan 47 explicitly prohibits those tracking mutations; the plan file itself records the approved threshold decision.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Initialized the isolated library root**

- **Found during:** Task 2 complete Phase 6 module execution
- **Issue:** The disposable runner created `romm_test` but not `romm_test/library`, causing the scan module to fail with `MissingStorageRootError`.
- **Fix:** Added a RED command-contract assertion, initialized the owned library directory before privilege drop, and verified the formerly failing module at 76 passed.
- **Files modified:** `backend/tools/verify_phase6_acceptance.py`, `backend/tests/tools/test_verify_phase6_acceptance.py`
- **Commit:** `b15097dd0`

**2. [Rule 1 - Bug] Synchronized controlled generated output**

- **Found during:** Task 2 generated-contract verification
- **Issue:** The controlled generator added a terminal blank line to three generated legacy models, so byte manifests differed despite unchanged schema semantics.
- **Fix:** Committed the exact generator output. The final run then produced identical 257-file manifests.
- **Files modified:** Three generated legacy model files
- **Commit:** `22b983dcb`

**3. [User-approved evidence correction] Bound the fresh 843-outcome result**

- **Found during:** Task 2 prior contract execution
- **Issue:** The locked 939 minimum could not be substantiated by stored raw evidence; the exact current 29 modules reproducibly produced 836 passed and 7 skipped.
- **Fix:** Updated the plan, harness, tests, command identity, validation, and summary to the approved exact result.
- **Files modified:** Plan, harness, tests, validation
- **Commit:** `b15097dd0`, `57792b07f`

**4. [Rule 1 - Bug] Accepted formatter-expanded Markdown separators**

- **Found during:** Final evidence verification after documentation hooks
- **Issue:** Markdown formatting widened `---` separator cells, while the exact-set parser skipped only the three-character form and rejected the structural row as an unknown ID.
- **Fix:** Added a RED formatted-table regression and accepted any separator-only cell of at least three hyphens without weakening ID or status validation.
- **Files modified:** `backend/tools/verify_phase6_acceptance.py`, `backend/tests/tools/test_verify_phase6_acceptance.py`
- **Commit:** `765f79389`

## Infrastructure Notes

The prior Wave 4 diagnostic exit 137 during global DB/Alembic setup remains an infrastructure-only warning. It was not rerun and is not represented as fresh Plan 47 evidence. All Plan 47 controlled gates completed successfully.

## Known Stubs

None. Stub-pattern scans found no goal-blocking placeholder, TODO, FIXME, or unwired empty-data path in Plan 47 files.

## Threat Review

No unplanned network endpoint, authentication path, schema trust boundary, or persistent file-access surface was introduced. Docker, database, generated-contract, manifest, and evidence-writer boundaries are covered by the Plan 47 threat model.

## Self-Check: PASSED

All created artifacts exist, all five implementation/evidence commits resolve, the acceptance record validates, and no required file or commit is absent.
