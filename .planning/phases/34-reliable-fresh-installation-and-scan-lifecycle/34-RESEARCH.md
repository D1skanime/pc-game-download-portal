---
phase: 34
status: researched
created: 2026-10-18
confidence: source-verified-runtime-cause-unconfirmed
---
# Phase 34 Research

## Scope and method
Canonical Linux checkout /home/d1sk/pc-game-download-portal on team4s-linux,
branch codex/phase-32-pgdp-naming, verified before writing. Planning only.
Read 34-CONTEXT.md as authoritative user decisions. No production code changed.

## Evidence and uncertainty
1. frontend/src/v2/composables/useScanLifecycle/index.ts uses module-global
   installed=false, sets true on installation, and never resets it. Each
   useSocketEvent subscription removes itself on Vue scope disposal.
   AppLayout.vue invokes the installer. A scope disposal then reinstallation
   therefore leaves handlers absent. This is a demonstrable source-level
   lifecycle defect. Reproduce it through mount/unmount/remount and the real
   auth/setup-to-app route before claiming it caused the current live hang.
2. frontend/src/services/socket.ts has autoConnect:false; useSocketEvent
   normally calls connect. The legacy scan adapter emits without acceptance
   acknowledgement. useLibraryOperation marks scanning/running before receiving
   server confirmation and cancellation immediately changes to cancelled.
   No bounded confirmation or durable operation lookup accompanies those calls.
3. Offline Socket.IO emits are normally buffered, not simply discarded. A
   missing backend log and an idle queue alone do not prove early clicking or
   a disconnected socket. Trace connection, event transmission, handler entry,
   acceptance and persistence with a non-secret correlation ID.
4. backend/endpoints/sockets/scan.py enqueues execute_mixed_scans, but
   _scan_job_func_names recognizes scan_platforms and SCAN_LIBRARY_TASK_FUNC.
   Existing duplicate guards, stop handling and startup restoration therefore
   omit the actual manual scan job family. Test function identity explicitly.
5. frontend/src/plugins/router.ts treats SHOW_SETUP_WIZARD=false as setup
   complete and redirects away from /setup. backend/endpoints/heartbeat.py
   derives that flag from admin existence. Setup.vue creates the account before
   assignment, keeps createdUserId only in memory and loses it on reload. This
   does not implement recovery after partial setup. Preserve the public setup
   security boundary while distinguishing enrolled admin from completed setup.
6. backend/endpoints/tasks.py already supplies task list/status/detail and RQ
   scan_stats. Reuse this infrastructure rather than another job queue.
   ScanStats persists aggregate job metadata and emits progress; events are
   not durable source-of-truth snapshots and currently lack operation lineage.
7. MappedScanCommand already freezes mapping ID/revision. Reuse central storage
   resolution and existing scan execution. Never persist absolute user paths as
   command scope or bypass immutable-source checks on resume.
8. backend/tests/conftest.py has autouse DB creation/migrations and destructive
   table cleanup. Prior container pytest runs targeted localhost:3306 and failed.
   Use a dedicated disposable test database/user/network and fail-closed guard.
   Never run this suite against the dev application database.

## Reuse and architecture recommendation
- Keep one existing Socket.IO client, Axios/CSRF client, storage resolver and
  scan processing pipeline. Fix listener ownership symmetrically; do not merely
  add another socket or retry loop.
- Add a durable server operation envelope around existing execution, not a
  parallel scanner. Reuse RQ tasks status projection where possible.
- Prefer authenticated REST commands/status through current API infrastructure
  for submit/reconcile/cancel/resume; Socket.IO stays a progress notification
  channel. If planning retains acknowledged socket submission, it must offer the
  same durable lookup, authorization and bounded reconciliation semantics.
- Stable request ID and normalized payload digest are essential. Same key/same
  payload returns the accepted operation; key reuse with changed payload conflicts.
  Authorize every retrieval and mutation. Concurrent starts must be serialized.
- Acceptance must survive the DB-to-queue gap: durable dispatch intent with
  idempotent reconciliation, deterministic job identity and attempt fencing.
  A committed acceptance followed by enqueue failure remains observable and
  recoverable, never silently lost or duplicated.
- Define one transition table covering checking, accepted/queued, running,
  stopping, cancelled, interrupted/recovering, blocked, failed, completed and
  completed-with-warnings. UI projection uses confirmed versioned snapshots.
  Connection loss is a separate presentation state, not job cancellation.
- Persistence must retain minimal request, mapping revision, source evidence,
  progress/checkpoint, attempt/lease token, intentional-cancel marker and safe
  bounded diagnostics. Do not persist plaintext passwords, tokens or provider
  secrets in job payloads or logs.
- Restart recovery must prove prior execution stopped/fenced and revalidate the
  existing source/mapping identity contract before scheduling one continuation.
  If the existing source snapshot cannot prove unchanged identity, block with a
  clear recovery action rather than claim a safe automatic resume.
- Indexed content is retained. Resume processes unfinished work idempotently.
  Changed source or mapping invalidates automatic resume and never redirects work.
- Metadata provider failures become per-item diagnostics and retry scopes,
  not a general exception-swallowing rule for storage/auth/programming failures.
- Setup readiness is server-derived from actual account, mapping and root
  conditions. Persist only minimal setup progress. Route incomplete enrolled
  admins back to the right step after authentication. No password persistence
  and no reopened unauthenticated initial-admin creation.

## Recommended plan boundaries
1. Reproduce lifecycle and job identity defects; isolated test harness and one
   authoritative state/acceptance protocol with traceable requirements.
2. Durable operation acceptance, schema/API, authorization and dispatch recovery.
3. Worker status, cancellation, checkpoints, restart reconciliation and safe
   targeted metadata retry through existing scan engine.
4. Persistent setup completion/recovery and authenticated routing.
5. Typed frontend operation state and reconciling lifecycle, existing UI patterns,
   all locale coverage and status restoration.
6. Integrated fault tests and fresh production-like Portainer proof, then repeat
   Phase 33 browser acceptance. Split further if any plan exceeds safe task size.

## Maintainability and security
New runtime modules <=500 lines; larger existing scan/view files get narrow
integration seams and extracted coherent helpers. Never add a second resolver,
queue lifecycle or platform mapping model.
Threats: unauthorized job enumeration/control, untrusted scope/paths, duplicate
submission and replay, stale-worker updates after resume, cancellation races,
secret disclosure, diagnostic bloat and test-database destruction.
Enforce server auth/scopes, normalized immutable scope, bounded payload/status
retention, attempt/version fencing and safe test target validation.

## Validation Architecture
Existing frameworks: pytest/pytest-asyncio, Vitest/Vue Test Utils, Playwright.
Infrastructure prerequisites must be completed first:
- Dedicated disposable SQL database (MariaDB plus migration parity for PostgreSQL
  and supported MySQL where changed), separate Redis namespace/service and
  read-only synthetic Games root with owned output directories.
- Host/network settings explicitly passed before Python imports; no production
  .env dump. Check isolated database name before autouse cleanup.
- Existing container command for frontend:
  docker exec pgdp-dev sh -lc 'cd /app/frontend && npm run test -- --run src/v2/views/Scan.test.ts src/v2/data/operations.test.ts'
  This is a baseline only, not proof of runtime behavior.
- New frontend tests must exercise actual mount/unmount/remount, disconnected
  submit, late acknowledgement, same-key replay, confirmed cancellation and
  recovery snapshot projection with fake timers and explicit event ownership.
- Backend tests exercise concurrent acceptance, accepted-before-enqueue crash,
  worker loss, mapping/source invalidation, cancellation races, auth/CSRF,
  stale attempt writes and targeted metadata retry. Commands must use dedicated
  test fixture configuration, not the live development DB.
- Playwright traverses real setup account creation, injected assignment failure,
  reload/login continuation, completion CTA, immediate click, double click,
  dropped acceptance response, no worker, reconnect, restart, mapping change,
  cancellation and provider failure. Assert authoritative operation/job counts
  and real catalog progress rather than UI text alone.
- Browser acceptance in app: fresh disposable stack with 8 mapped fixture
  platforms, first scan completes and records games; inspect both PGDP themes,
  keyboard/touch/mouse/gamepad and inline persistent error/recovery states.
- Full frontend typecheck/build/i18n and focused backend suites are required.
  Prior typecheck errors in MatchRom/types.test.ts and
  Settings/pgdpFolderMappings.ts must be recorded and resolved or explicitly
  handled as a gate; they are not passing checks.
- No production or test success claims without command output and fixture identity.
  Phase 33 remains open until real fresh-stack first scan acceptance passes.

## Primary sources
- https://socket.io/docs/v4/client-offline-behavior/ : disconnected events buffer.
- https://socket.io/docs/v4/delivery-guarantees/ : default delivery is at most once;
  additional guarantees and refresh-safe replay require application support.
Source code findings above are primary project evidence. No runtime root cause
was asserted without a completed reproduction.

## Bounded lifecycle reproduction
Executed read-only inside pgdp-dev using installed TypeScript.transpileModule
and Node vm on the actual useScanLifecycle/index.ts. Stores were stubbed;
useSocketEvent registration and scope disposal were simulated. The real
installScanLifecycle function produced:
- listeners_after_first_install=5
- listeners_after_scope_disposal=0
- listeners_after_reinstall=0
This proves the install/dispose/reinstall defect, not the exact live route trigger.
