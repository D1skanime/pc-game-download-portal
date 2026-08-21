---
phase: 06-safe-lifecycle-and-legacy-migration
plan: 37
subsystem: storage
tags: [python, migration, sha256, privacy, pytest, tdd]
requires:
  - phase: 06-03
    provides: bounded canonical legacy detection and domain-separated source fingerprint
provides:
  - private immutable exact membership evidence for source-observed regular files
  - canonical source-relative identity digest helper for Plans 42 and 44
  - adversarial membership, bounds, normalization, and privacy regression coverage
affects: [06-42, 06-44, legacy-detection, migration-impact]
tech-stack:
  added: []
  patterns:
    - versioned domain-separated length-delimited identity hashing
    - bounded digest-only evidence at a private detector boundary
key-files:
  created: []
  modified:
    - backend/handler/storage/legacy_migration.py
    - backend/tests/handler/storage/test_legacy_migration.py
key-decisions:
  - "Source membership keys use strict canonical relative POSIX text hashed as a length-delimited UTF-8 record under a versioned purpose tag."
  - "Identity evidence remains a sorted immutable bytes tuple excluded from repr and every public detection surface."
patterns-established:
  - "Collect private membership evidence only after a regular file passes the existing bounded hash walk."
  - "Reject ambiguous source identities with one static path-free exception."
requirements-completed: [MIG-01, MIG-03]
duration: 25min
completed: 2026-08-21
---

# Phase 6 Plan 37: Private Source Identity Evidence Summary

**Legacy detection now emits bounded exact digest membership for source-observed regular files while preserving the existing content fingerprint and public response contract.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-21T11:38:25Z
- **Completed:** 2026-08-21T12:03:16Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added one deterministic SHA-256 digest per successfully observed regular source identity using strict relative POSIX normalization, a versioned purpose tag, and length-delimited UTF-8.
- Stored evidence as a sorted immutable bytes tuple with an explicit count, including bounded partial observations, while excluding fingerprints and identity digests from dataclass repr.
- Preserved source fingerprint semantics, detection thresholds, permission and symlink denial, public schemas, progress metadata, and response behavior.
- Added exact regular-file membership, catalog-only absence, Unicode, symlink exclusion, content independence, bounds, ambiguity, token, path, log, repr, progress, and OpenAPI privacy coverage.

## TDD Gate Compliance

- **RED:** `9581dc588` ran only `test_detection_records_private_exact_source_identity_set` in a fresh isolated lifecycle and exited 1 at `exact private source identity evidence is missing`. Collection, database, runner, and other infrastructure failures were explicitly rejected.
- **GREEN:** `54bdb4e7c` passed the complete migration-handler module with 42 tests on fresh isolated database and runner resources.
- **Privacy follow-up:** `b54864b5e` added the real bearer token to forbidden diagnostic surfaces; the final independent module gate again passed all 42 tests.
- **Independent gate:** Fresh `p0637_pv` nonce `f9b3eaaefa9dcd4f72778728265a0e6d` passed 42 tests, complete tracked-backend manifest equality, exact cleanup, and normal application database continuity.

## Task Commits

1. **Task 1 RED: Specify exact private observed-identity evidence** - `9581dc588` (test)
2. **Task 2 GREEN: Derive domain-separated bounded identity digests** - `54bdb4e7c` (feat)
3. **Task 2 privacy follow-up: Cover the actual bearer token surface** - `b54864b5e` (test)

## Files Created/Modified

- `backend/handler/storage/legacy_migration.py` - strict identity normalization, digest derivation, bounded collection, immutable private outcome evidence, and repr privacy.
- `backend/tests/handler/storage/test_legacy_migration.py` - exact membership and complete private-surface regression coverage.

## Decisions Made

- Used one private pure helper as the normalization and digest contract so later catalog selection can compare exact membership without duplicating path rules.
- Kept the existing source fingerprint separate as the content-and-metadata restart confirmation value.
- Treated a normalized digest collision as unsafe and asserted evidence cardinality equals the successfully observed regular-file count.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used an owned disposable test runner**

- **Found during:** Task 1 RED lifecycle
- **Issue:** The plan names the persistent `romm-dev` container, but it was stopped and service restart was prohibited.
- **Fix:** Used fresh nonce-named containers from the existing `romm-romm-dev` image with the backend bind mounted read-only and task-only tmpfs paths.
- **Files modified:** None.
- **Verification:** Every accepted lifecycle proved exact runner absence, database and principal absence, temp absence, application `SELECT 1`, and the 28-entry baseline.
- **Committed in:** Not applicable.

**2. [Rule 1 - Bug] Replaced a vacuous empty-string privacy assertion**

- **Found during:** Task 2 GREEN verification
- **Issue:** The initial exception test asserted that each rejected input was absent from the message, which can never hold for the empty string.
- **Fix:** Asserted one exact generic path-free exception message for every ambiguous input.
- **Files modified:** `backend/tests/handler/storage/test_legacy_migration.py`.
- **Verification:** The complete 42-test module and final independent lifecycle passed.
- **Committed in:** `54bdb4e7c`.

**3. [Rule 2 - Missing Critical] Checked the real request token on private surfaces**

- **Found during:** Final threat-surface scan
- **Issue:** The privacy fixture checked a token-like filename and host but did not explicitly include the actual bearer token in the forbidden values.
- **Fix:** Added the request fixture token to the repr, log, schema, progress metadata, and response surface scan.
- **Files modified:** `backend/tests/handler/storage/test_legacy_migration.py`.
- **Verification:** Scoped Trunk and the final 42-test independent lifecycle passed.
- **Committed in:** `b54864b5e`.

---

**Total deviations:** 3 auto-fixed (1 Rule 1, 1 Rule 2, 1 Rule 3).
**Impact on plan:** The changes close correctness, privacy, and isolated verification gaps without expanding product scope.

## Issues Encountered

- The first RED harness attempt failed in SQL shell quoting before pytest and was rejected as infrastructure evidence. It cleaned successfully, and a fresh lifecycle produced the required assertion-only RED.
- The first GREEN run found only the vacuous empty-string test assertion. Cleanup and database continuity still completed before the corrected fresh run.
- The canonical host has no remote `apply_patch` executable; checked, exact textual replacements were used only inside the verified Linux checkout.

## Verification

- RED: named test exited 1 only for the missing evidence contract.
- GREEN and independent plan gates: 42 tests passed with two pre-existing warnings.
- Scoped Trunk: two modified files checked with no issues.
- `git diff --check`: passed.
- Public OpenAPI and captured progress response surfaces contain no identity field, digest, raw name, absolute path, token, or host value.
- Complete tracked-backend manifest was identical before and after the final runner lifecycle: `98e09b7d29ef72127fb6a63aa411f486591307d1b9e65f028e47457b291d7f8b`.

## Cleanup and Continuity

- Accepted RED used nonce `e96473d05b1f91ea55e1023af6f18b1e`; GREEN used `1337e038f676dc06686813d550b46027`; final plan verification used `f9b3eaaefa9dcd4f72778728265a0e6d`.
- Every owned nonce database, 32-character principal, runner, and tmpfs basetemp was proven absent after use.
- Normal application `SELECT 1` passed before and after every accepted lifecycle.
- The persistent `romm-dev` container remained stopped; no service was started, restarted, or deployed.
- All 28 pre-existing untracked status entries were preserved.

## Known Stubs

None.

## Threat Flags

None. The private digest boundary and read-only source walk were explicitly covered by the plan threat model; no endpoint, schema, network, authentication, or new file-access authority was introduced.

## User Setup Required

None.

## Next Phase Readiness

- Plans 42 and 44 can consume `_source_identity_digest` and `source_identity_digests` for exact observed-source catalog membership.
- No blockers remain.

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Completed: 2026-08-21_

## Self-Check: PASSED

- Both modified files and commits `9581dc588`, `54bdb4e7c`, and `b54864b5e` exist.
- RED, GREEN, final module, Trunk, manifest, cleanup, continuity, and 28-entry baseline evidence passed.
