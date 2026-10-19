---
phase: 34-reliable-fresh-installation-and-scan-lifecycle
plan: "07"
subsystem: ui
tags: [typescript, axios, csrf, idempotency, scan-operations, vitest]
requires:
  - phase: 34-02
    provides: Durable authenticated operation authority and generated scan contracts
  - phase: 34-05
    provides: Backend-owned generated setup continuation contracts
provides:
  - Generated-contract adaptation preserving targeted scope and provider/media intent
  - Shared authenticated commands with original-key reconciliation and confirmed snapshots
  - Actor-scoped nonsecret identity recovery and logout/session fencing
affects: [34-06, 34-11, 34-12, 34-08]
tech-stack:
  added: []
  patterns: [bounded authenticated reconciliation, actor-scoped identity, confirmed command snapshots]
key-files:
  created:
    - frontend/src/v2/data/adapters/scanOperations.ts
    - frontend/src/v2/data/adapters/scanOperations.test.ts
  modified:
    - frontend/src/v2/data/contracts.ts
    - frontend/src/v2/data/operations.ts
    - frontend/src/v2/data/operations.test.ts
    - frontend/src/v2/data/adapters/legacy/scan.ts
    - frontend/src/v2/sourceMutationInventory.test.ts
key-decisions:
  - Reuse the existing Axios client and its CSRF interceptors for every command and lookup.
  - Keep browser identity separate from generated server version/attempt/job lineage.
  - Reconcile ambiguous submission by original request key before one bounded same-key replay.
  - Persist only request/operation identity under the authenticated actor and fence late session responses.
  - Preserve asynchronous legacy exports while leaving confirmed facade projection to 34-12.
requirements-completed: ["D-05","D-06","D-07","D-08","D-09","D-10","D-11","D-12","D-13","D-14","D-15","D-16","SCAN-06","UI-04","UI-06"]
requirements-scope: plan-contribution-only
duration: 20 min
completed: 2026-10-19
---

# Phase 34 Plan 07: Typed Scan Command Adapter Summary

Scan commands now return backend-confirmed snapshots through the existing authenticated client, retain original request identity during response loss, and preserve mapped subfolders and provider/media options.

## Scope and Environment

Tasks: 2/2. This summary records 34-07 only. Requirement identifiers above describe this plan's contribution, not closure of shared requirements or phase-wide acceptance.

Preflight passed through ssh team4s-linux: Linux, /home/d1sk/pc-game-download-portal, branch codex/phase-32-pgdp-naming, origin https://github.com/D1skanime/pc-game-download-portal.git, and RomM PC Library planning identity. The legacy Node GSD CLI loaded init and state; workflow.use_worktrees=false. Recorded implementation window began 2026-10-19T11:04:18Z, after context reading, and ended approximately 11:24Z.

Read canonical CLAUDE.md, AGENTS.md, execute-plan workflow/references, the full assigned plan, CONTEXT, RESEARCH, PATTERNS, VALIDATION, 34-WAVE2-QA and dependency summaries. Repository frontend behavior and pre-PR guides informed client reuse and verification; TDD and verification guides informed failure classification and evidence. Review was performed by the executor, without nested agents.

No Windows project writes, branch switch, worktree, push, live database access, live scan, restart or deployment occurred. All tests and generation used the existing guarded Phase 34 Run/CLI with synthetic read-only Games and disposable SQL/Redis. Source/test snapshots include the canonical working tree; this is not a claim of a globally clean HEAD-only build.

## Task Commits

| Task | RED | GREEN |
| --- | --- | --- |
| 1: Authoritative contracts and normalized payloads | 5d7841a03 | 4cd7a914a |
| 2: Shared authenticated commands and reconciliation | f9966f574 | df9d7d0ea |

Both RED commits precede GREEN. Normal hooks passed. No tracked file was deleted.

## Behavior Delivered

- Contracts re-export backend-generated operation/setup types. Confirmed server lineage can accompany an operation result without replacing local request identity.
- Normalization bounds request keys to the backend grammar and bounds local identifiers. Locale/provider normalization retains policies, mapped revisions, selected ROM/platform scope and Unicode relative subfolders.
- REST adaptation reuses the existing legacy payload translation. Full/media aliases map to backend-supported scan types; metadata-only/media-only flags survive. Preview cannot submit work.
- submit, byRequest, active, status, restore, cancel, resume and retryMetadata use the existing Axios/CSRF client, with an 8-second per-request timeout.
- Identical simultaneous submissions share one pending request. A different pending submission is rejected. An ambiguous POST first looks up its original key. Only a confirmed 404 permits one same-key, same-payload replay; lookup outage, forbidden or conflict never causes a blind POST.
- Explicit same-key replay still reaches backend digest validation after lookup. A changed payload cannot bypass server conflict enforcement.
- Browser persistence contains only request_key and operation_id under the authenticated actor. It excludes source paths, provider options, credentials and payloads. Missing/invalid/unavailable storage falls back to server active lookup.
- Auth reset, actor changes, successful shared-client logout and unauthorized responses clear retained identity. Session generation rejects late responses from a prior actor/logout.
- Mutations carry expected version and a stable key within reconciliation. Metadata retry sends bounded selected item IDs only. An uncertain mutation reconciles the original accepted operation before any same-body replay; confirmed version progress is returned for the caller to assess.
- Legacy payload/start/stop exports remain. Start/stop delegate asynchronously to this adapter; their competing Socket.IO emits were removed. Facade awaiting/projection remains owned by 34-12.
- Tests exercise the actual adapter and real shared-client interceptors, injecting faults only at Axios transport. These are client behavioral tests, not new SQL/worker/browser acceptance proof.

## Actual Verification

| Command/check | Actual result |
| --- | --- |
| Task 1 exact frontend operations.test.ts command, RED | Exit 1: 22 cases, seven assertion failures for missing identifier bounds |
| Task 1 exact command, final GREEN | Exit 0: 24 passed |
| Task 2 exact frontend adapters/scanOperations.test.ts command, RED | Exit 1: three behavioral assertion failures through existing legacy exports |
| Task 2 expanded suite | Exit 0: 37 passed |
| Additional reactive mapped-request regression | Exit 1: 37 passed, one DataCloneError; fixed at JSON command boundary |
| Task 2 exact command after fix | Exit 0: 38 passed |
| Combined operations.test.ts and adapters/scanOperations.test.ts | Exit 0: 62 passed, zero failures/errors |
| Existing sourceMutationInventory.test.ts, all cases retained | Exit 1: 19 passed, one existing setup assignment classification failure |
| Isolated npm run generate | Exit 0; all five scoped models and their existing export lines match byte-for-byte |
| Full regenerated-contract npm run typecheck | Exit 2: known roms.ts:212-213 schema drift only |
| Retained-contract npm run typecheck | Exit 0, repeated with final source in combined batch |
| Final isolated npm run build | Exit 0, including token prebuild and PWA output |
| Scoped Trunk checks, normal commit hooks, git diff --check | Passed |

Exact task commands were:

- python3 backend/tools/phase34.py frontend src/v2/data/operations.test.ts
- python3 backend/tools/phase34.py frontend src/v2/data/adapters/scanOperations.test.ts
- python3 backend/tools/phase34.py frontend src/v2/data/operations.test.ts src/v2/data/adapters/scanOperations.test.ts (equivalent frontend_command invocation in the combined Run batch)

The combined batch used Run.start/exec/close with frontend_command and retained JUnit. Typecheck/build commands ran inside that disposable frontend, not the application container.

All eleven generated server states retain version, attempt, job, item and queue lineage in executable adapter tests. Other cases cover immediate/double click, delayed/lost response, same-key replay, changed-payload conflict, lookup timeout, storage/memory loss, actor isolation, logout races, anonymous/forbidden/not-found/conflict/outage distinctions, existing CSRF refresh, confirmed cancellation, explicit resume and selected metadata retry.

The full frontend suite was not rerun. The recorded Wave 2 baseline remains 1009 passed/four failed: three planned lifecycle REDs and the setup inventory failure. This is not a global-green claim. Build output retains existing CSS/dependency/chunk warnings.

## Generated Contract Evidence and Limits

34-02/05 already produced all five scoped models. They were verified, not hand-edited or regenerated into the canonical tree. The generator exported OpenAPI on isolated container loopback 127.0.0.1:3344 and ran the actual npm run generate.

The first probe required whole-index equality and failed that comparison after all five model comparisons passed. The second probe verified each scoped export line and retained the unrelated full-index diff. Full generation adds/reorders unrelated schemas, including other setup/metadata/media contracts. Its typecheck still reports only:

- src/stores/roms.ts:212: Record<string, number> | undefined is not assignable to Record<string, number>.
- src/stores/roms.ts:213: number[] | undefined is not assignable to number[].

No unrelated generated output was retained. The canonical generated files and index remain unchanged. Restoring the existing generated baseline only inside the disposable snapshot produces a passing retained-contract typecheck. Full-regeneration compatibility remains an open gate.

## Retained Linux Evidence

Each root is under /tmp and retains evidence/commands.json, redacted logs, JUnit where applicable, source-before/source-after manifests and cleanup.json. Private generated target manifests remain under control; credentials are not reproduced.

| Purpose | Evidence root |
| --- | --- |
| Task 1 assertion RED | pgdp34-f076ea1281ce43fd83a93c227fd5c794-7y5v_pnd |
| Task 1 initial 24 GREEN | pgdp34-10ac677f46e7475b8f04a7a231812a31-7bgomr0c |
| Initial full-index comparison failure | pgdp34-c70e8d70364d4e4e8eba9710c137b6bb-xous2nmc |
| Scoped generation, full/retained typechecks | pgdp34-99314e3f49cb4fbe903e13652852c169-t4qolg97 |
| Task 1 final 24 GREEN | pgdp34-489b0583984a492ab6176cc53c8253ea-hxh43f3h |
| Task 2 behavioral RED | pgdp34-6d3e3b5757c74ea9997aafdd3bb4d09e-jlo_ahgh |
| Initial compatibility GREEN | pgdp34-ace3f8034f57471fbc3085225115ff39-3mbehvl0 |
| Expanded 37 GREEN | pgdp34-3d552095cfd64c62aba8a5b6d7a650f5-xen9hnuc |
| Reactive request failure | pgdp34-5a1126325b35456bb3e6e14aff8f75ed-089ok0ru |
| Final adapter 38 GREEN | pgdp34-732014fd72894b28be00b1aa743fa9bd-7bi1zjer |
| Combined 62, inventory, final typecheck/build and self-check | pgdp34-c1c17547528048268423771634e79de9-aprl6r55 |

All eleven final cleanup receipts report clean=true, source_unchanged=true, empty remaining resources and absent checkout snapshots. Final read-only inventory found zero Phase 34 containers, volumes and networks. No global prune was used.

The combined batch initially exited nonzero at its ad-hoc ownership recovery assertion after successful test/typecheck/build commands. Its check compared a full container ID to short IDs and expected the wrong mount boundary. Recovery resolved exact full IDs, validated the actual /app/frontend bind against the owned snapshot, restored only its dist ownership and ran normal Run.close. The separate recovery command exited 0 with a verified cleanup receipt. The initial orchestration failure is not counted as a passing workflow or TDD RED.

## Deviations from Plan

1. [Rule 2 - Critical] Added two exact POST authority classifications in the existing sourceMutationInventory.test.ts table. New submit/cancel/resume/retry calls must remain visible to the closed inventory. Existing extraction, assertions, negative coverage and unknown-route rejection remain intact. The full inventory reaches only its previously recorded setup.ts assignFolders failure. Commit df9d7d0ea.
2. [Rule 1 - Bug] A real reactive request failed structured cloning. Serializing the typed JSON command before awaiting detaches Vue proxies and freezes the pending wire payload. The new runtime regression went from one failure to GREEN, then combined 62 passed. Commit df9d7d0ea.
3. [Rule 3 - Verification] Existing generated contracts were verified in isolation instead of duplicated. Whole-index drift and the known full-generation typecheck failure are recorded above; no unrelated schema/store fix was attempted.
4. The existing assertNever helper now enforces exhaustiveness at the touched scope translation switch, satisfying the normal lint gate without removing that helper.

## Known Stubs and Threat Surface

No goal-blocking adapter stub was introduced. Empty item arrays/defaults and nullable active lookup represent real protocol semantics. Confirmed snapshots come from the shared HTTP client; no mock authority or source-string assertion substitutes for adapter behavior.

The added browser persistence and authenticated command calls are within the plan's threat model. No new backend endpoint, schema, resolver, scanner, queue, media writer or source-storage authority was introduced. New scanOperations.ts is 405 physical lines; operations.ts is 411, contracts.ts 305 and the legacy adapter 18, all below 500 even before logical-line exclusions. Test files are exempt.

## Outstanding Gates and Handoff

- The existing POST /setup/folders/assign authority classification remains with 34-06. Its inventory failure is retained, not hidden.
- Full generated-contract compatibility remains failed at roms.ts:212-213. Retained-contract typecheck/build pass.
- Listener lifecycle/status integration belongs to 34-11; confirmed facade awaiting/projection and UI integration belong to 34-12. Worker/restart/provider/production/Portainer/browser acceptance remains with its assigned plans.
- During execution the parent reported an independent 34-15 media review with eight blockers and one warning. Those findings were not reviewed, changed or repaired by 34-07. Phase quality remains open for the parent to repair and reverify.
- No Phase 33 or whole-phase closure, deployment or shared requirement completion is claimed.

STATE, ROADMAP, REQUIREMENTS, Phase 33 UAT/VALIDATION, the dirty setup response maximum of 500, both Compose files and the two untracked pgdp_test directories were preserved. Hash receipts verify the protected tracked bytes stayed unchanged during this execution. No media/report file was edited. No authentication gate required operator action.

## Self-Check: PASSED

Verified all seven changed source/test files exist; all four task commits resolve in RED-before-GREEN order; no commit deleted tracked files; scoped generated comparisons pass; final JUnit counts match the claims; all eleven cleanup/source receipts pass and snapshots are absent. Protected-file hashes match their captured values. Normal task hooks and whitespace checks pass. The failed full-generation, inventory and initial batch orchestration results remain explicit above. Shared planning updates are reserved for the parent.
