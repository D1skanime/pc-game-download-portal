---
title: Fix the Phase 22 isolated UAT scheduled scan and queue target visibility
type: quick
status: planned
quick_task: 261002-qut
slug: fix-the-phase-22-isolated-uat-scheduled-
files_modified:
  - backend/docker-compose.pc-integration-test.yml
  - backend/tasks/tasks.py
  - backend/tasks/scheduled/scan_library.py
  - backend/tests/tasks/test_scan_library.py
  - backend/endpoints/roms/pc_automation.py
  - backend/endpoints/responses/rom.py
  - backend/tests/endpoints/roms/test_pc_automation.py
  - frontend/src/v2/components/Settings/PcAutomationQueue.vue
  - frontend/src/__generated__/models/PcAutomationQueueItemSchema.ts
  - .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md
requirements: [D-05, D-07, D-08]
must_haves:
  truths:
    - "The disposable Phase 22 stack has a running RQ scheduler and worker, so the development-only 10-second interval scan is actually executed."
    - "A scheduled scan processes only active mapped platforms, stays recurring after a failed execution, and does not fail because another platform lacks a storage mapping."
    - "Each administration queue row identifies the real ROM or DLC component being reviewed, separately from any proposed provider candidate."
    - "A fresh synthetic Sekiro fixture is discovered automatically after one or more 10-second intervals, with the source fixture unchanged."
  artifacts:
    - path: backend/docker-compose.pc-integration-test.yml
      provides: "Disposable app, Redis, RQ scheduler, and worker topology"
    - path: backend/tasks/tasks.py
      provides: "Indefinitely recurring development interval task semantics"
    - path: backend/tasks/scheduled/scan_library.py
      provides: "Mapped-only scheduled scan execution"
    - path: backend/endpoints/responses/rom.py
      provides: "Queue contract with a server-derived target title"
    - path: frontend/src/v2/components/Settings/PcAutomationQueue.vue
      provides: "Visible reviewed target and distinct provider proposal"
    - path: .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md
      provides: "Repeatable disposable Sekiro interval-scan proof"
  key_links:
    - from: backend/docker-compose.pc-integration-test.yml
      to: tasks.scheduled.scan_library.pc_automation_uat_interval_task
      via: "RQ scheduler process and low-priority worker sharing the disposable Redis service"
      pattern: "rq (scheduler|worker)"
    - from: backend/tasks/scheduled/scan_library.py
      to: backend/endpoints/sockets/scan.py
      via: "mapping_scan_commands returns only active mapping commands before execute_mapping_scans"
      pattern: "mapping_scan_commands"
    - from: backend/endpoints/roms/pc_automation.py
      to: frontend/src/v2/components/Settings/PcAutomationQueue.vue
      via: "generated OpenAPI PcAutomationQueueItemSchema target title"
      pattern: "target_title"
---

# Fix the Phase 22 isolated UAT scheduled scan and queue target visibility

## Objective

Make the Phase 22 disposable UAT prove the promised automatic ten-second scan,
without changing its read-only source boundary or relying on a manually started
scan. Correct the queue so an operator sees the actual ROM/DLC target, not
only an optional provider proposal. This is a narrow UAT and scheduler fix,
not a change to real libraries, Team4s, NAS storage, credentials, or
production deployment.

Observed evidence to address:

- The disposable Compose environment starts Redis and the web process but no
  RQ scheduler/worker pair, so a stored interval job cannot run.
- `mapping_scan_commands([])` is designed to skip unmapped platforms, but the
  scheduled UAT must prove that behavior and must never let an unmapped
  platform prevent its mapped `win` fixture from scanning.
- The interval uses a one-off scheduler configuration, so a failed execution
  can consume its sole scheduled occurrence instead of running again.
- Queue cards show a provider candidate or normalized query, which makes a
  DLC already structurally attached to its parent look like a duplicate or an
  unnamed item.

Preserve all existing optimistic-lock review semantics, provider protections,
and external read-only restrictions. Do not use real game bytes or a
persistent database. Do not modify unrelated dirty files and do not commit
this planning artifact.

## Context

- `CLAUDE.md`
- `.planning/STATE.md`
- `.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md`
- `.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-02-SUMMARY.md`
- `.planning/quick/261002-lj2-fix-phase-22-scan-lifecycle-and-german-s/261002-lj2-PLAN.md`
- `backend/docker-compose.pc-integration-test.yml`
- `backend/tasks/tasks.py`
- `backend/tasks/scheduled/scan_library.py`
- `backend/endpoints/sockets/scan.py`
- `backend/endpoints/roms/pc_automation.py`
- `backend/endpoints/responses/rom.py`
- `frontend/src/v2/components/Settings/PcAutomationQueue.vue`

<interfaces>

From `backend/tasks/tasks.py`:

```python
class DevelopmentIntervalTask(PeriodicTask):
    def schedule(self) -> Job | None: ...
```

The interval runner is registered by the app startup path, then must remain a
standing RQ schedule entry. Its scheduler and worker must connect to the same
isolated Redis service and run `RomMWorker` with the repository's low-priority
queue configuration.

From `backend/endpoints/sockets/scan.py`:

```python
def mapping_scan_commands(platform_ids: list[int], *, trigger: ScanTrigger,
                          scope: ScanScope, scan_type: ScanType) -> list[MappedScanCommand]: ...
async def execute_mapping_scans(commands: list[MappedScanCommand], *,
                                metadata_sources: list[str], ...) -> ScanStats: ...
```

An empty platform id selection must resolve only active storage mappings. An
unmapped platform is not a valid scheduled scan command and must not cause the
mapped platform run to fail.

From `backend/endpoints/roms/pc_automation.py`:

```python
def _schema(item) -> PcAutomationQueueItemSchema: ...
```

The route must derive the display name from the authoritative ROM or scoped
component record. It must not accept a client-supplied title and must retain
the separate candidate evidence fields.
</interfaces>

## Tasks

<task type="auto" tdd="true">
<name>Task 1: Make the development interval a resilient mapped-only recurring scan</name>
<files>backend/tasks/tasks.py, backend/tasks/scheduled/scan_library.py, backend/tests/tasks/test_scan_library.py</files>
<read_first>backend/tasks/tasks.py, backend/tasks/scheduled/scan_library.py, backend/endpoints/sockets/scan.py, backend/tests/tasks/test_scan_library.py, backend/tests/integration/test_scan_source_immutability.py</read_first>
<behavior>
- With the exact development-only ten-second setting, the scheduler creates an indefinitely recurring interval entry, not a single occurrence; a failed scheduled invocation does not prevent its next interval execution.
- A scheduled run with one mapped platform and one unmapped platform produces and executes only the mapped command, does not raise `MissingPlatformStorageMappingError`, and retains the mapped scan's storage authorization path.
- Disabled scheduling and the production cron behavior retain their existing semantics.
</behavior>
<action>Write focused failing scheduler tests first. Verify the installed RQ scheduler API used by the repository and change `DevelopmentIntervalTask.schedule` to create a durable recurring interval entry using its documented infinite-repeat form, retaining existing de-duplication, timeout, task metadata, and the development-only ten-second gate. Do not introduce a retry loop that swallows scan errors, a direct scan fallback, or a second competing cron job. Then make `ScanLibraryTask.run` explicitly operate on the active commands returned by `mapping_scan_commands`, including an empty-command no-op, so unmapped platforms are skipped before `execute_mapping_scans` and cannot abort mapped UAT discovery. Add regression coverage for recurring scheduler arguments, a simulated failed job followed by a next scheduled execution, active-mapping-only command selection, and unchanged source authorization. Keep `mapping_scan_commands` as the sole scan-command factory.</action>
<verify><automated>cd backend && uv run pytest tests/tasks/test_scan_library.py tests/integration/test_scan_source_immutability.py -q</automated></verify>
<done>The ten-second development task remains scheduled across failures, and scheduled scans execute only active mapped platforms without weakening mapped scan authorization or production scheduling.</done>
</task>

<task type="auto" tdd="true">
<name>Task 2: Expose the authoritative reviewed target on queue cards</name>
<files>backend/endpoints/responses/rom.py, backend/endpoints/roms/pc_automation.py, backend/tests/endpoints/roms/test_pc_automation.py, frontend/src/__generated__/models/PcAutomationQueueItemSchema.ts, frontend/src/v2/components/Settings/PcAutomationQueue.vue</files>
<read_first>backend/models/rom.py, backend/handler/database/roms_handler.py, backend/endpoints/responses/rom.py, backend/endpoints/roms/pc_automation.py, backend/tests/endpoints/roms/test_pc_automation.py, frontend/src/v2/components/Settings/PcAutomationQueue.vue, frontend/src/stores/pcAutomation.ts</read_first>
<behavior>
- A parent queue item returns the current authoritative ROM name as `target_title`.
- A component queue item returns the authoritative component display name when present, otherwise its scoped relative path, and is still tied to its parent ROM id and component id.
- Candidate title, provider, and fingerprint stay distinct provider evidence; the browser shows the target being reviewed and labels a different candidate as a proposal rather than replacing the target name.
- Missing/removed targets do not disclose unrelated records and retain the existing visibility and conflict behavior.
</behavior>
<action>Start with endpoint and component tests that fail because the response lacks a server-derived target title. Extend `PcAutomationQueueItemSchema` and `_schema` with a bounded `target_title` resolved only from the visible queue item's ROM and its same-ROM component. For components prefer existing component metadata name, then the component relative path; for parent items prefer the current ROM name, then the stored normalized query. Do not persist a duplicate target name in `PcAutomationQueue`, add a migration, accept client display text, or change authorization/version tokens. Regenerate the OpenAPI TypeScript model through the repository generator, then update the v2 queue card so the primary label is `target_title`, the candidate title is rendered only as a clearly distinct proposal when it differs, and correction dialogs retain their existing canonical target binding. Add focused Vue tests if an existing queue-card test harness covers the component; otherwise run the component typecheck and retain generated-type consistency.</action>
<verify><automated>cd backend && uv run pytest tests/endpoints/roms/test_pc_automation.py -q && cd ../frontend && npm run generate && npm run typecheck</automated></verify>
<done>Administration makes it clear which real game or DLC will be changed, provider candidates remain separate evidence, and all review actions still use the original server-derived ids and versions.</done>
</task>

<task type="auto">
<name>Task 3: Run a fresh disposable scheduler-worker UAT with an automatically detected Sekiro fixture</name>
<files>backend/docker-compose.pc-integration-test.yml, .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md</files>
<read_first>backend/docker-compose.pc-integration-test.yml, backend/docker-compose.immutability-test.yml, backend/handler/rq_worker.py, backend/tools/seed_phase22_uat_database.py, backend/tools/verify_pc_integration_model.py, .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md</read_first>
<action>Add disposable `scheduler` and `worker` services to the Phase 22 test Compose definition. They must share the base app's read-only backend source mount, disposable Redis service, config volumes, environment, and unique Compose project, but neither may expose ports or mount a real library. Use the repository's established `rq scheduler` and `rq worker --worker-class handler.rq_worker.RomMWorker` invocation and low-priority queue name. Keep the fixture bind mounted read-only for every service that needs it. Update the UAT record with exact non-secret commands to: start app/Redis/database/scheduler/worker; seed only the temporary `win` mapping; record the standing interval job; add a new synthetic text-only `Sekiro Shadows Die Twice.iso` after the baseline UAT scan; wait two intervals; verify through the disposable API/database that its ROM was created or its one review item has authoritative `target_title` containing Sekiro; inspect worker logs only for the named project; compare full pre/post manifests; and clean only that project and `mktemp` root. Execute this proof in a new named disposable project, capture actual project-safe evidence in `22-UAT.md`, and leave the UAT unapproved if automatic Sekiro detection cannot be demonstrated.</action>
<verify><automated>cd backend && docker compose -f docker-compose.pc-integration-test.yml config >/dev/null && uv run pytest tests/tasks/test_scan_library.py tests/integration/test_scan_source_immutability.py -q</automated></verify>
<done>The documented and executed disposable stack has a scheduler and worker, a newly added synthetic Sekiro fixture appears without a browser-started scan, source evidence remains byte-identical, and cleanup is limited to the exact temporary UAT resources.</done>
</task>

## Verification

1. Run the focused backend scheduler, mapped-scan, queue-route, and source
   immutability tests.
2. Regenerate frontend API types and run the frontend typecheck after the
   queue contract changes.
3. Create a brand-new, uniquely named disposable Compose project with only
   synthetic text fixtures. Start all five services, seed only its `win`
   mapping, and confirm the RQ interval entry and worker are live.
4. Add the synthetic Sekiro fixture after baseline setup, wait at least two
   ten-second intervals without initiating a manual scan, and verify its
   catalog or pending queue target through the disposable stack.
5. Compare the full source manifests byte-for-byte before and after, then
   remove only the exact project volumes and temporary root.

## Safety and Security Boundaries

- The UAT may use only temporary text fixtures, a uniquely named disposable
  MariaDB/Redis project, a read-only fixture bind, and the established tunnel
  at port 3344. It must not touch Team4s, NAS mounts, real ROMs, or a
  persistent database.
- Queue target titles are server-derived from records already authorized by
  the list endpoint. No title, queue id, target id, version, or candidate
  evidence supplied by the browser gains authority.
- Interval recovery means future RQ occurrences remain scheduled. It must not
  hide a failure, broaden scan scope, bypass mapping authorization, or run a
  duplicate production cron.

## Completion Criteria

- The disposable scheduler and worker automatically process a fresh Sekiro
  text fixture after the ten-second interval, including after a prior failed
  execution.
- Unmapped platforms are ignored, while the mapped `win` fixture scans through
  the existing authorized command path.
- Queue cards identify the true ROM/DLC target separately from candidates.
- Fixture manifests remain identical and UAT cleanup remains isolated.
