---
status: in-progress
quick_task: 261002-hft
slug: seed-the-isolated-phase-22-uat-database
files_modified:
  - backend/tools/seed_phase22_uat_database.py
  - backend/tests/tools/test_seed_phase22_uat_database.py
  - .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md
---

# Seed the isolated Phase 22 UAT database

## Objective

Make the disposable Phase 22 UAT stack discover its read-only fake Windows
fixtures during a normal quick scan by seeding only its disposable database
with an external read-only storage root and an active `win` platform mapping.

The task must not alter application runtime behavior, production data, Docker
Compose source, NAS or Team4s paths, real libraries, or fixture files.

## Tasks

<task type="auto" tdd="true">
<name>Task 1: Add an idempotent isolated Phase 22 database seeder and its focused tests</name>
<files>backend/tools/seed_phase22_uat_database.py, backend/tests/tools/test_seed_phase22_uat_database.py</files>
<read_first>backend/tools/seed_phase10_pc_fixture.py, backend/tools/seed_phase9_database_platforms.py, backend/tests/tools/test_seed_phase9_database_platforms.py, backend/handler/database/storage_handler.py, backend/models/storage.py</read_first>
<behavior>
- Given the disposable app mount at `/romm/library/roms` and a readable, non-writable `win` directory, the seeder registers or reuses exactly one external-read-only root and ensures the Windows platform has one active mapping with relative path `win`.
- Given an existing correct root, platform, and active mapping, a second run succeeds without creating a duplicate root, platform, mapping, audit row, or scan job.
- Given a missing `e2e_admin`, missing `win` platform directory, writable/unreachable root, or an existing incompatible active mapping, the seeder fails loudly without replacing or deactivating data.
</behavior>
<action>Create `backend/tools/seed_phase22_uat_database.py`, following the Phase 9/10 in-container seeder pattern. Wait for the disposable database, locate or register only `/romm/library/roms` through `db_storage_handler.register_root` so the existing health checks enforce the external-read-only contract, discover/register the `win` platform from the mounted filesystem, and create a mapping only when no active mapping exists. Use the disposable `e2e_admin` only as the audit actor. Treat a pre-existing active mapping as success only when it targets the same root and normalized `win` path; otherwise raise a descriptive error. Do not call `scan_platforms`, mutate fixture files, open write capabilities, print credentials, or include any production-path fallback. Emit a small JSON summary containing non-secret root/platform/mapping ids and paths. Write focused db-free mock tests first, including idempotency and all refusal cases.</action>
<verify><automated>cd backend && uv run pytest tests/tools/test_seed_phase22_uat_database.py tests/tools/test_seed_phase9_database_platforms.py tests/integration/test_scan_source_immutability.py -q</automated></verify>
<done>The isolated seeder can be safely run twice against only the disposable stack, establishes the exact `external_read_only` root and `win` mapping required by a quick scan, and refuses unsafe or conflicting state without repairing it destructively.</done>
</task>

<task type="auto">
<name>Task 2: Record the reproducible seed, verification, and cleanup procedure in the Phase 22 UAT record</name>
<files>.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md</files>
<read_first>.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md, backend/docker-compose.pc-integration-test.yml, backend/tools/verify_pc_integration_model.py</read_first>
<action>Amend the existing UAT procedure with one pre-scan setup step that runs the new seeder inside the uniquely named, already healthy disposable app service before the browser user selects Quick Scan. Specify the expected JSON fields and an automated read-only verification that queries the disposable database or uses the seeder output to prove the active root path is `/romm/library/roms`, its mode is `external_read_only`, and the `win` mapping is active. Keep provider keys in the existing local backend environment and never document them. Preserve the existing source-digest evidence. State exact cleanup guarantees: run `docker compose down --volumes --remove-orphans` with the unique `COMPOSE_PROJECT_NAME`, remove only the known `mktemp -d` UAT directory after the post-run digest comparison, and never prune global Docker resources or touch real paths.</action>
<verify><automated>cd backend && uv run pytest tests/tools/test_seed_phase22_uat_database.py tests/integration/test_scan_source_immutability.py -q</automated></verify>
<done>The UAT record lets an executor seed the disposable database before Quick Scan, independently confirm the root and mapping contract, retain immutable-fixture evidence, and clean up only the uniquely named stack and temporary UAT directory.</done>
</task>

## Verification

1. Run the focused seeder and source-immutability tests.
2. In a fresh uniquely named UAT Compose project only, run the seeder twice in
   the disposable app container, then select Quick Scan in the browser. The
   scan must discover the fake `win` fixtures without manual storage setup.
3. Compare the pre/post source evidence before cleanup. It must be byte-for-byte
   identical, including names, types, sizes, timestamps, and hashes.
4. Tear down only the explicit UAT project and its explicitly created temporary
   root. Do not use global Docker prune commands.

## Cleanup Guarantees

- All database changes are contained in the uniquely named disposable Compose
  project and are removed with that project's volumes.
- The source fixture remains bind-mounted read-only and is never written,
  renamed, moved, or deleted.
- No NAS, Team4s, production database, real library, persistent application
  configuration, or Compose source is read or changed.
