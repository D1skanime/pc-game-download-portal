---
title: Fix Phase 22 UAT stale manual-correction queue resolution and localized unnamed candidates
type: quick
status: planned
quick_task: 261002-kbd
slug: fix-phase-22-uat-findings-resolve-stale-
files_modified:
  - backend/handler/database/pc_automation_handler.py
  - backend/tests/handler/database/test_pc_automation.py
  - backend/endpoints/roms/pc_metadata.py
  - backend/tests/endpoints/roms/test_pc_metadata.py
  - frontend/src/stores/pcAutomation.ts
  - frontend/src/v2/components/Settings/PcAutomationQueue.vue
  - frontend/src/v2/components/Settings/PcAutomationQueue.test.ts
  - frontend/src/v2/views/Settings/Administration.vue
  - .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md
requirements: [D-05, D-06, D-08]
must_haves:
  truths:
    - "A successful canonical parent or component correction retires its older pending review evidence, so the pending count falls after the queue reload."
    - "A queue row created or reopened for a target version newer than the correction's consumed version stays pending."
    - "Unnamed queue candidates render the translated fallback in every shipped locale, never an i18n lookup key."
  artifacts:
    - path: backend/handler/database/pc_automation_handler.py
      provides: "Server-derived, stale-safe post-manual-selection queue transition"
    - path: frontend/src/v2/components/Settings/PcAutomationQueue.vue
      provides: "Settings-namespace localized candidate fallback"
    - path: .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md
      provides: "Fresh 20-fixture manual-correction and localization proof"
  key_links:
    - from: backend/endpoints/roms/pc_metadata.py
      to: backend/handler/database/pc_automation_handler.py
      via: "post-success, server-derived selection target and canonical expected version"
      pattern: "resolve_after_manual_selection"
    - from: frontend/src/v2/components/Settings/PcAutomationQueue.vue
      to: frontend/src/locales/*/settings.json
      via: "settings.pc-automation locale namespace"
      pattern: "settings\\.pc-automation\\.unnamed-candidate"
---

# Fix Phase 22 UAT stale queue resolution and localized candidate fallback

## Objective

Close the exact stale review evidence that a successful canonical PC metadata
selection has superseded, while preserving a review row that was created for a
newer target version. Correct every Phase 22 queue translation lookup to use
the existing `settings` namespace so missing candidates display the localized
fallback instead of `pc-automation.unnamed-candidate`.

The UAT evidence is authoritative: the component metadata-selection request
returned `200` and persisted Steam app id `2138330`, but its queue row stayed
`pending`. This is not a missing browser save. The existing resolver accepts
only a queue row whose target version exactly equals the selection's expected
version. It therefore leaves behind a valid older queue row when the canonical
correction consumes a later target version. The browser currently receives
literal keys because `pc-automation` lives inside each locale's `settings.json`
namespace, whose keys are addressed as `settings.pc-automation.*`.

Do not add an endpoint, request field, queue id, fingerprint, terminal state,
or client-controlled transition. Do not expose a new OpenAPI contract or
regenerate generated API types.

## Context

- `.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-CONTEXT.md`
- `.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-01-SUMMARY.md`
- `.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-03-SUMMARY.md`
- `.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-04-SUMMARY.md`
- `.planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-05-SUMMARY.md`
- `.planning/quick/261002-idn-resolve-a-pc-automation-review-queue-ite/261002-idn-PLAN.md`
- `backend/models/pc_automation.py`
- `backend/handler/database/roms_handler.py`
- `frontend/src/locales/index.ts`
- `frontend/src/locales/en_US/settings.json`

<interfaces>

From `backend/handler/database/pc_automation_handler.py`:

```python
def resolve_after_manual_selection(
    *, target_kind: PcAutomationTargetKind, rom_id: int,
    component_id: int | None, consumed_target_updated_at: datetime,
) -> PcAutomationQueueResult: ...
```

This internal handler receives only target identity and the authoritative
optimistic version already consumed by canonical persistence. It must continue
to derive the queue row server-side and retain the durable `claimed` terminal
state.

From `frontend/src/locales/index.ts`:

```ts
messages[locale][namespace] = localeModule.default;
```

Each `settings.json` object is mounted below `settings`; Phase 22 translations
must therefore use `settings.pc-automation.*`, including the fallback and all
queue action, status, and error keys.

</interfaces>

## Tasks

<task type="auto" tdd="true">
<name>Task 1: Make the internal manual-resolution transition stale-safe for older evidence</name>
<files>backend/handler/database/pc_automation_handler.py, backend/tests/handler/database/test_pc_automation.py</files>
<read_first>backend/models/pc_automation.py, backend/handler/database/pc_automation_handler.py, backend/tests/handler/database/test_pc_automation.py, backend/handler/database/roms_handler.py</read_first>
<behavior>
- Given a pending parent or eligible component review row for the same target incarnation whose stored target version is older than, or equal to, the canonical selection version just successfully consumed, the transition changes that older row to `claimed`, timestamps the attempt, and removes it from `list_pending`.
- Given no matching row, a non-pending row, a wrong target identity/incarnation, or a row whose stored target version is newer than the consumed canonical selection version, the transition is an idempotent `UNCHANGED` no-op. In particular, it must not claim a row reopened by a later scan or target update.
- The transition locks the target and queue row and accepts no browser data, queue id, fingerprint, candidate id, or requested state. It neither deletes nor rewrites candidate evidence.
</behavior>
<action>Write the focused regression tests first, including the UAT shape where queue evidence predates a later successful manual selection, an equal-version queue row, and a concurrently replaced/reopened row whose target version is newer. Then narrow `resolve_after_manual_selection` to select and lock the one target-derived queue row, require `PENDING` and the same parent incarnation, and claim only evidence at or before the already-consumed canonical optimistic version. Compare persisted timezone-aware versions using the database-supported ordering and retain the existing typed `PcAutomationQueueResult` outcomes. Do not weaken the queue handler's ordinary `claim`, skip, requeue, or review-action version checks, and do not add a migration.</action>
<verify><automated>cd backend && uv run pytest tests/handler/database/test_pc_automation.py -q</automated></verify>
<done>A successful canonical correction can retire its older stale queue evidence, while a newer concurrent/reopened pending row remains reviewable.</done>
</task>

<task type="auto" tdd="true">
<name>Task 2: Invoke the broadened transition only after canonical selection persistence succeeds</name>
<files>backend/endpoints/roms/pc_metadata.py, backend/tests/endpoints/roms/test_pc_metadata.py</files>
<read_first>backend/endpoints/roms/pc_metadata.py, backend/handler/database/roms_handler.py, backend/handler/database/pc_automation_handler.py, backend/tests/endpoints/roms/test_pc_metadata.py</read_first>
<behavior>
- A successful parent or DLC/extra metadata-selection response invokes the internal resolver using only its route target and the exact optimistic version that canonical persistence accepted.
- A 409 stale selection, 422 unknown candidate, failed media import, unsupported component, and failed canonical persistence do not invoke the resolver.
- The endpoint does not accept or return queue authority, and a resolver no-op never converts a successful metadata selection into an error response.
</behavior>
<action>Extend the existing endpoint tests before changing endpoint wiring. Keep resolution after the canonical `apply_pc_metadata_candidate` or `apply_pc_component_metadata_candidate` success and after any required selected-media persistence, because the existing endpoint must preserve its no-resolution-on-failed-media contract. Pass only server-known target kind, parent/component ids, and `selection.expected_version`, which is the optimistic token that the guarded database write proved. Preserve the base-component delegation to the parent route, visibility checks, response schemas, and OpenAPI surface. Do not move resolution into MatchRomDialog, the queue store, or a browser callback.</action>
<verify><automated>cd backend && uv run pytest tests/endpoints/roms/test_pc_metadata.py tests/handler/database/test_pc_automation.py -q</automated></verify>
<done>Only a successful canonical manual correction can resolve stale evidence for that exact server-derived target, and request/response contracts remain unchanged.</done>
</task>

<task type="auto" tdd="true">
<name>Task 3: Use the settings locale namespace for every queue string and prove the 20-fixture UAT</name>
<files>frontend/src/stores/pcAutomation.ts, frontend/src/v2/components/Settings/PcAutomationQueue.vue, frontend/src/v2/components/Settings/PcAutomationQueue.test.ts, frontend/src/v2/views/Settings/Administration.vue, .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md</files>
<read_first>frontend/src/locales/index.ts, frontend/src/locales/en_US/settings.json, frontend/src/locales/de_DE/settings.json, frontend/src/stores/pcAutomation.ts, frontend/src/v2/components/Settings/PcAutomationQueue.vue, frontend/src/v2/components/Settings/PcAutomationQueue.test.ts, frontend/src/v2/views/Settings/Administration.vue, .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md</read_first>
<behavior>
- A null, empty, or whitespace-only candidate title renders the current locale's `settings.pc-automation.unnamed-candidate` value in visible text, image alt text, correction target label, select label, and action labels.
- The Administration tab, queue loading/empty/error/batch/action messages, and store fallback use `settings.pc-automation.*`, never an unscoped `pc-automation.*` lookup key or a literal key string.
- The existing 18 `settings.json` locale contracts remain complete, sorted, and genuinely localized. No new locale file or English-only placeholder is introduced.
</behavior>
<action>Write component tests that use a realistic translator mapping (including a non-English `settings.pc-automation.unnamed-candidate` value) and queue items with absent and blank titles, then update all Phase 22 queue lookup paths from `pc-automation.*` to `settings.pc-automation.*`. Centralize the display title once in the feature component and reuse it for visual content, alt/ARIA text, correction payload labels, and action tooltips so null and blank values cannot leak a key. Update the queue-store fallback and Administration tab lookup to the same namespace. The full locale batch already contains the required nested `pc-automation` objects, so do not duplicate it at the locale root; use locale-parity and sorted-key validation to guard all 18 existing contracts. Append the actual fresh isolated UAT evidence only after running it: a new uniquely named Compose project, a new temporary read-only 20-text-fixture source, existing idempotent `win` mapping seed, Quick Scan, German UI check of unnamed rows, Cyberpunk 2077: Phantom Liberty app id `2138330` correction, a pending-count decrease, a retained newer stale row, byte-identical fixture manifests, and label-bound cleanup. Never record keys, passwords, NAS paths, Team4s paths, or real game files.</action>
<verify><automated>cd frontend && npm run test -- --run src/v2/components/Settings/PcAutomationQueue.test.ts && python3 src/locales/check_i18n_locales.py && python3 src/locales/check_i18n_sorted.py && npm run typecheck</automated></verify>
<done>The v2 queue displays translated fallback text across the existing locale contract, and the recorded isolated UAT proves correction removes only the intended old row without source-fixture mutation.</done>
</task>

## Verification

1. Run the focused handler and endpoint suites in a disposable MariaDB-backed
   environment, not against a host-loopback or production database:

   ```bash
   cd backend && uv run pytest tests/handler/database/test_pc_automation.py tests/endpoints/roms/test_pc_metadata.py -q
   ```

2. Run the focused v2 test, locale parity/sort checks, and frontend typecheck:

   ```bash
   cd frontend && npm run test -- --run src/v2/components/Settings/PcAutomationQueue.test.ts
   python3 src/locales/check_i18n_locales.py
   python3 src/locales/check_i18n_sorted.py
   npm run typecheck
   ```

3. Run the browser checkpoint in a new disposable 20-fixture stack following
   `22-UAT.md`. Login through the established SSH tunnel on port 3344, select
   German, scan the mapped read-only `win` fixture library, and verify the
   three unnamed entries display translated text. Correct only Cyberpunk 2077:
   Phantom Liberty to Steam id `2138330`; it must leave the pending queue and
   reduce its count by one. Prove a row reopened for a newer target version
   remains pending. Compare every saved fixture manifest byte-for-byte before
   cleanup, then delete only that named Compose project's volumes and the exact
   temporary directory.

## Safety and Security Boundaries

- Canonical metadata persistence remains the authority. The browser cannot
  resolve queue evidence by supplying an id, version, fingerprint, or state.
- The resolver keeps its target-derived row lock and target incarnation check.
  Its only broadened condition is that evidence older than the guarded
  successful selection can be retired, while evidence newer than that
  selection remains pending.
- The UAT source is a fresh read-only temporary directory of text files. It
  must never reach a NAS, Team4s mount, real game library, real game bytes,
  production database, or global Docker cleanup command.

## Completion Criteria

- The stale Cyberpunk queue regression is covered at handler and endpoint
  levels, and a successful manual correction retires the exact old pending
  evidence.
- A newer concurrent/reopened pending item is still visible after an older
  correction completes.
- Every queue translation reference resolves through `settings.pc-automation`,
  with existing 18-locale parity and sorted files passing.
- Fresh 20-fixture UAT evidence records the browser result and unchanged source
  manifest without secrets or production paths.
