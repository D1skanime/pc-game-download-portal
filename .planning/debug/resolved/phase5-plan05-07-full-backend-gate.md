---
slug: phase5-plan05-07-full-backend-gate
status: resolved
trigger: "Phase 5 Plan 05-07 full backend gate reported 3151 collected, 3035 passed, 10 skipped, 24 failed, and 82 errors after exact changed suites passed."
goal: find_and_fix
created: 2026-08-12
---

# Phase 5 Plan 05-07 Full Backend Gate

## Symptoms

- Exact changed suites passed before the complete backend gate.
- Complete backend gate reported 3151 collected, 3035 passed, 10 skipped, 24 failed, and 82 errors.
- Reproduction must use a fresh unique database plus isolated `/romm-library` and `/romm-resources` mounts with disposable MariaDB and Valkey services.

## Current Focus

**Hypothesis:** The original 24 failures and 82 errors are resolved, but 32 separately surfaced failures span stale Phase 2-5 contract tests and unrelated pre-existing metadata/task behavior changes outside the authorized Phase 5 Plan 05-07 remediation.

**Test:** Fresh fully populated isolated full backend gate with unique MariaDB schema `romm_test_phase5final_1786539190`, disposable Valkey, repository Docker/frontend inspection mounts, and JUnit `/tmp/romm-phase5-final-cSc2L5/reports/full.xml`.

**Expecting:** User decision is required before broadening into the 32 newly surfaced failures.

**Next action:** Choose whether to open a separate broad regression effort for all 32 failures or accept the scoped original-cluster remediation and record the remaining baseline debt.

- hypothesis: Docker environment variables alone select the unique pytest database.
  evidence: pytest-env forcibly replaced them from ackend/pytest.ini; MariaDB observed
  omm_test, not the supplied unique credentials.
  timestamp: 2026-08-12T00:35:00+02:00

## Evidence

- timestamp: 2026-08-12T00:00:00+02:00
  observation: Canonical host is Linux, repository root is `/home/d1sk/romm`, branch is `codex/pc-module-analysis`, and unrelated untracked files are present and must be preserved.
- timestamp: 2026-08-12T00:15:00+02:00
  observation: Environment preflight confirmed Linux, canonical root /home/d1sk/romm, branch codex/pc-module-analysis, origin https://github.com/rommapp/romm.git, and Phase 5 planning state for RomM PC Library. Repository and debugger rules were loaded from the canonical checkout.

- timestamp: 2026-08-12T00:25:00+02:00
  observation: Started disposable MariaDB
  omm-phase5gate-1786537912-db with unique schema
  omm_test_phase5gate_1786537912 and Valkey
  omm-phase5gate-1786537912-valkey sharing its isolated network namespace. Fresh mount root is /tmp/romm-phase5-gate-noFgyy; existing application services were untouched.

- timestamp: 2026-08-12T00:35:00+02:00
  observation: Initial isolated run produced setup errors from the first test. MariaDB logged Access denied for user romm_test; ackend/pytest.ini force-overwrites DB_NAME, DB_USER, and DB_PASSWD, so Docker -e values did not reach application imports. This run is invalid product evidence and identifies an environment invocation defect.

- timestamp: 2026-08-12T00:42:00+02:00
  observation: A one-test counterfactual using a multiline pytest env override connected to the unique schema and passed. The corrected complete gate is running as
  omm-phase5gate-1786537912-pytest2 with JUnit /tmp/romm-phase5-gate-noFgyy/reports/full.xml.

easoning_checkpoint:
hypothesis: The 82 setup errors are caused solely by stale test fixtures constructing owned-storage handlers without the required descriptor introduced by the storage policy cutover.
confirming_evidence: - All 21 asset errors end at FSAssetsHandler() with the same missing storage TypeError. - All 61 resource errors end at FSResourcesHandler() with the same missing storage TypeError.
falsification_test: Supplying the canonical owned ASSETS and RESOURCES descriptors will fail to collect or will expose production behavior errors in those same tests.
fix_rationale: Updating test construction to the production dependency contract restores coverage without weakening policy or adding fallback behavior.
blind_spots: Individual legacy assertions may encode direct-path behavior incompatible with descriptor-backed access.

- timestamp: 2026-08-12T01:05:00+02:00
  observation: After populating isolated mounts from canonical ackend/romm_test fixtures, the original cluster subset became 82 errors, 16 failures, and 63 passes. Heartbeat environment failures dropped from nine to one. The 82 constructor errors were fixed by binding canonical owned descriptors; both handler suites now pass 112 tests. Commit: 6bda68d4c.
- timestamp: 2026-08-12T01:06:00+02:00
  observation: Remaining original failures split into nine obsolete writable-library conversion expectations (all correctly denied 403), six hidden-ROM routes where policy denial 403 occurs before visibility masking 404, and one metadata heartbeat state expectation affected by shared external metadata state.

- timestamp: 2026-08-12T01:35:00+02:00
  observation: Authorization-order fix moved immutable policy denial after ROM lookup and visibility masking in six child mutation routes. Visibility suite: 25 passed. Commit `01430b68c`.
- timestamp: 2026-08-12T01:40:00+02:00
  observation: Replaced nine obsolete writable-library success expectations with nine explicit 403 `external_storage_operation_denied` and byte-manifest no-mutation checks. Suite: 9 passed. Commit `f2579d268`.
- timestamp: 2026-08-12T01:45:00+02:00
  observation: Isolated LaunchBox heartbeat through the endpoint-bound handler mock; heartbeat suite: 15 passed. Commit `5ee37ef46`.
- timestamp: 2026-08-12T02:00:00+02:00
  observation: Fresh full gate collected 3153 tests and finished 3109 passed, 10 skipped, 32 failed, 0 errors, 2 subtests passed in 452.83s. JUnit: `/tmp/romm-phase5-final-cSc2L5/reports/full.xml`. The original 24 failures and 82 errors are absent.
- timestamp: 2026-08-12T02:02:00+02:00
  observation: Newly surfaced failures cluster as 1 Phase 3 storage-handler session-test defect, 4 stale Phase 2 consumer/inventory source-contract assertions, 1 Phase 3 resolver property edge case, 8 ScreenScraper metadata failures tied to later commit `3b3aebc64`, 2 stale Phase 5 scheduled-scan mocks after `c10ee471e`, 6 pre-existing RetroAchievements task expectations after `7146081d7`, 9 pre-existing LaunchBox task expectations after `8c12ac86a`, and 1 stale Phase 5 watcher file-location assertion despite implementation in `backend/watcher.py` commit `6de06a3ed`.

## Investigation Log

- timestamp: 2026-08-12T01:35:00+02:00
  observation: Authorization-order fix moved immutable policy denial after ROM lookup and visibility masking in six child mutation routes. Visibility suite: 25 passed. Commit `01430b68c`.
- timestamp: 2026-08-12T01:40:00+02:00
  observation: Replaced nine obsolete writable-library success expectations with nine explicit 403 `external_storage_operation_denied` and byte-manifest no-mutation checks. Suite: 9 passed. Commit `f2579d268`.
- timestamp: 2026-08-12T01:45:00+02:00
  observation: Isolated LaunchBox heartbeat through the endpoint-bound handler mock; heartbeat suite: 15 passed. Commit `5ee37ef46`.
- timestamp: 2026-08-12T02:00:00+02:00
  observation: Fresh full gate collected 3153 tests and finished 3109 passed, 10 skipped, 32 failed, 0 errors, 2 subtests passed in 452.83s. JUnit: `/tmp/romm-phase5-final-cSc2L5/reports/full.xml`. The original 24 failures and 82 errors are absent.
- timestamp: 2026-08-12T02:02:00+02:00
  observation: Newly surfaced failures cluster as 1 Phase 3 storage-handler session-test defect, 4 stale Phase 2 consumer/inventory source-contract assertions, 1 Phase 3 resolver property edge case, 8 ScreenScraper metadata failures tied to later commit `3b3aebc64`, 2 stale Phase 5 scheduled-scan mocks after `c10ee471e`, 6 pre-existing RetroAchievements task expectations after `7146081d7`, 9 pre-existing LaunchBox task expectations after `8c12ac86a`, and 1 stale Phase 5 watcher file-location assertion despite implementation in `backend/watcher.py` commit `6de06a3ed`.

## Resolution

verification: Fresh isolated gate using schema `romm_test_phase5green_1786540564` passed 3141 tests, skipped 10, failed 0, errored 0, with 2 subtests passed in 424.00 seconds. JUnit: `/tmp/romm-phase5-green-ZRr1kn/reports/full.xml`.
files_changed: [backend/handler/database/storage_handler.py, backend/endpoints/roms/screenshot.py, backend/endpoints/roms/soundtrack.py, backend/endpoints/roms/manual.py, backend/tests/handler/filesystem/test_assets_handler.py, backend/tests/handler/filesystem/test_resources_handler.py, backend/tests/endpoints/roms/test_convert_to_folder.py, backend/tests/endpoints/test_heartbeat.py, backend/tests/handler/filesystem/test_external_read_consumers.py, backend/tests/handler/filesystem/test_storage_inventory.py, backend/tests/handler/filesystem/test_storage_resolver.py, backend/tests/handler/metadata/test_ss_handler.py, backend/tests/tasks/test_scan_library.py, backend/tests/test_watcher.py, backend/tests/tasks/test_sync_retroachievements_progress.py, backend/tests/tasks/test_update_launchbox_metadata.py]

root_cause: The gate combined stale capability-bound test fixtures, obsolete immutable-library mutation expectations, authorization ordering, one misplaced database session decorator, stale mapped-read source contracts, unsafe Hypothesis input generation, provider-gating fixtures, and stale scheduled/watcher scan mocks.
fix: Bound test fixtures to owned capabilities and explicit provider states, preserved visibility masking and immutable mutation denials, restored database session decoration, aligned tests with mapping-bound reads and scan commands, and corrected safe path generation.
investigation_cycles: 3
fix_cycles: 12
