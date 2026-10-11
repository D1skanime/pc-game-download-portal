---
title: Resolve PC automation review items after canonical manual metadata correction
type: quick
status: planned
quick_task: 261002-idn
slug: resolve-a-pc-automation-review-queue-ite
files_modified:
  - backend/handler/database/pc_automation_handler.py
  - backend/tests/handler/database/test_pc_automation.py
  - backend/endpoints/roms/pc_metadata.py
  - backend/tests/endpoints/roms/test_pc_metadata.py
  - .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md
---

# Resolve PC automation review items after canonical manual metadata correction

## Objective

When the established parent or component metadata-selection endpoint has
successfully persisted an operator's manual correction, resolve only the
matching pending PC automation row on the server. The item must therefore
leave the pending review queue without allowing browser input to name a queue
row, a fingerprint, or a terminal state.

The observed failure is reproducible: `POST /api/roms/2/pc-components/1/metadata-selection`
returned 200 and persisted Steam app id `2138330`, while its related
`PcAutomationQueue` record remained `pending` with the selection's old target
version. The existing v2 queue correctly reloads after MatchRomDialog success;
it requires no client-side workaround.

Use the existing terminal `claimed` state, which is already excluded from
`list_pending`, rather than adding a browser-facing API or a new schema state.
Retain the durable row as audit evidence.

## Tasks

<task type="auto" tdd="true">
<name>Task 1: Add a stale-safe, target-derived manual-resolution transition</name>
<files>backend/handler/database/pc_automation_handler.py, backend/tests/handler/database/test_pc_automation.py</files>
<read_first>backend/models/pc_automation.py, backend/handler/database/pc_automation_handler.py, backend/tests/handler/database/test_pc_automation.py, backend/alembic/versions/0133_pc_automation_queue.py</read_first>
<behavior>
- Given a pending parent or eligible DLC/extra queue row whose stored target incarnation and `target_updated_at` equal the version that a canonical metadata selection just consumed, the handler transitions that row to terminal `claimed` and it is absent from `list_pending`.
- Given no row, a non-pending row, a different target identity/incarnation, or a row created or reopened against a newer target version, resolution is an idempotent no-op and never closes that newer review item.
- The transition locks and derives its target from server-supplied endpoint context only. It does not accept a queue id, fingerprint, candidate identity, or desired queue state from an HTTP request.
</behavior>
<action>Write focused database tests first, then add one narrow `DBPcAutomationHandler` transition for a successful manual selection. Accept only target kind plus authoritative parent/component identity and the pre-update target version that the canonical guarded persistence has already proven. Locate the unique queue row by its server-derived target identity under a row lock; require `PENDING`, the exact old target incarnation, and the exact old target version before setting the established terminal `CLAIMED` state and attempt timestamp. Return a typed outcome that distinguishes a transition from a harmless no-op for internal observability, but do not create a new externally supplied queue action. Do not modify candidate evidence, reopen a row, delete evidence, or add a migration because `claimed` is already a portable terminal queue state.</action>
<verify><automated>cd backend && uv run pytest tests/handler/database/test_pc_automation.py -q</automated></verify>
<done>Only the exact old pending row for the corrected target becomes terminal; stale, new, or unrelated review rows remain pending and visible.</done>
</task>

<task type="auto" tdd="true">
<name>Task 2: Invoke manual resolution only after guarded parent or component persistence succeeds</name>
<files>backend/endpoints/roms/pc_metadata.py, backend/tests/endpoints/roms/test_pc_metadata.py</files>
<read_first>backend/endpoints/roms/pc_metadata.py, backend/handler/database/roms_handler.py, backend/handler/database/pc_automation_handler.py, backend/tests/endpoints/roms/test_pc_metadata.py, backend/tests/endpoints/roms/test_pc_automation.py</read_first>
<behavior>
- A successful manual parent selection resolves only the old pending parent queue row for that ROM; a successful manual DLC/extra selection resolves only the old pending component row.
- A stale selection that receives 409, an unknown candidate that receives 422, a failed media import, or a selection with no matching old row leaves every queue row unchanged.
- A retry/scan that replaces the old row after the selection's version was read cannot be accidentally resolved by the later manual-selection completion.
- The existing metadata-selection request and OpenAPI contract remain unchanged. Supplying generic manual-match fields cannot forge automation queue state.
</behavior>
<action>Extend the existing endpoint tests before wiring. In both `select_pc_metadata_candidate` and `select_pc_component_metadata_candidate`, capture the selection's expected target version only as the optimistic input already verified by the canonical `apply_pc_metadata_candidate` or `apply_pc_component_metadata_candidate` call. Call the new internal queue transition only after that guarded write succeeds, using server-known parent/component ids and the verified consumed version. Keep failed or stale selection behavior unchanged, and do not expose queue ids, fingerprints, target kinds, or state in `PcMetadataSelectionRequest`, response schemas, generated frontend contracts, MatchRomDialog, or the v2 queue store. Keep media handling and the response behavior intact; a queue no-op must not turn a successful manual match into an HTTP failure.</action>
<verify><automated>cd backend && uv run pytest tests/endpoints/roms/test_pc_metadata.py tests/endpoints/roms/test_pc_automation.py tests/handler/database/test_pc_automation.py -q</automated></verify>
<done>Every successful canonical manual correction removes only its exact stale pending automation item from the queue, while rejected, stale, raced, and unrelated operations preserve safe queue state.</done>
</task>

<task type="auto">
<name>Task 3: Re-run the correction proof in a freshly seeded isolated fake-library UAT stack</name>
<files>.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md</files>
<read_first>.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md, .planning/quick/261002-hft-seed-the-isolated-phase-22-uat-database-/261002-hft-PLAN.md, backend/docker-compose.pc-integration-test.yml, backend/tools/seed_phase22_uat_database.py, backend/tests/integration/test_scan_source_immutability.py</read_first>
<action>Append a precise fresh-UAT correction verification section. Use a new uniquely named disposable Compose project, a new `mktemp -d` fixture directory, the read-only 20-file Windows fixture set, and the existing idempotent Phase 22 database seeder. Do not access a NAS, Team4s path, real game, production database, or global Docker resources. Capture the fixture manifest before scanning and after every browser action. Run Quick Scan, record the pending queue count, correct the Cyberpunk 2077: Phantom Liberty component through the existing MatchRomDialog with Steam app id 2138330, then prove via the authenticated queue API or disposable database query that its target-derived row is terminal `claimed` and is absent from the pending list while unrelated entries remain pending. Repeat the stale proof by creating or retaining a newer target incarnation before attempting resolution and verify it stays pending. Record only non-secret identifiers and outcomes, compare before/after manifests byte-for-byte, then remove only the explicit Compose project volumes and that exact temporary directory. Keep credentials and provider keys in the local environment and out of the record.</action>
<verify><automated>cd backend && uv run pytest tests/integration/test_scan_source_immutability.py tests/handler/database/test_pc_automation.py tests/endpoints/roms/test_pc_metadata.py -q</automated></verify>
<done>The UAT record provides a repeatable isolated proof that manual correction resolves the exact queue item, preserves stale safety, and never mutates fake fixture sources.</done>
</task>

## Verification

1. Run the focused database, metadata-endpoint, queue-endpoint, and source
   immutability suites listed above in the disposable MariaDB-backed test path.
2. In a newly created isolated stack, scan the 20 read-only text fixtures,
   perform the Cyberpunk DLC correction, and confirm the exact queue row is
   terminal `claimed`, the pending count decreases by one, and unrelated rows
   remain pending.
3. Compare the pre/post fixture manifests, including names, types, sizes,
   timestamps, and SHA-256 values. They must be identical before cleanup.

## Safety and Security Boundaries

- The metadata-selection endpoint remains the sole route from an operator's
  correction to queue resolution. It proves the selection's optimistic version
  through canonical persistence before it can signal the queue handler.
- Queue mutation is target-derived and version-bound on the server. No generic
  browser payload can resolve an arbitrary queue item.
- The UAT stack is disposable, the source fixture is mounted read-only, and
  cleanup targets only the named Compose project and its dedicated temporary
  directory.
