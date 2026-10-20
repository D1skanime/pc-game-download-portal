# Phase 34: Reliable fresh installation and scan lifecycle - Context

**Gathered:** 2026-10-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Make fresh setup, first scan submission, execution status and recovery reliable
from a clean PGDP installation through the first completed library scan.
Every waiting state must resolve to a confirmed server state or an actionable
error. Reuse the existing storage mapping and scan lifecycle infrastructure.

Phase 33 remains open at browser acceptance plan 33-06. Implement and verify
Phase 34 stabilization before repeating that fresh-install acceptance. Its
dependency on Phase 33 means using the implemented mapping foundation, not
requiring an already successful Phase 33 browser acceptance.

Scope covers normal scans as well as the first scan, because both use the same
operation boundary. It does not redesign game recognition or add download features.
</domain>

<decisions>
## Implementation Decisions

### Setup recovery and completion
- **D-01:** If account creation succeeds but folder assignment fails, resume the incomplete setup step. Preserve saved assignments and avoid requiring another administrator account.
- **D-02:** A missing or unreadable Games root keeps the affected step visible with a clear cause and Retry check action.
- **D-03:** After a connection loss during save, reconcile server state and repeat only missing steps. An uncertain response is not proof that saving failed.
- **D-04:** Finish setup with an explicit Start first scan action on a completion screen. Do not silently start scanning.

### Scan start and errors
- **D-05:** Show checking start, queued and running according to confirmed server state. Disable repeated start actions while submission is pending.
- **D-06:** Bound acknowledgement waiting, then reconcile server state. Show the accepted job or a persistent actionable error. Repeating a submission must not create duplicate work.
- **D-07:** An accepted job that cannot start or stops executing must produce a persistent message in the scan window with its cause and next action. Indefinite 0/0 progress is unacceptable.
- **D-08:** Metadata provider failures do not prevent indexing other readable games. Finish with warnings identifying affected games and offer targeted metadata retries.

### Recovery and deliberate cancellation
- **D-09:** Reloading or reopening the browser automatically restores the existing job and current server progress without starting another scan.
- **D-10:** Browser connection loss does not stop server execution. Show the disconnection and status-reconciliation state, reconnect automatically, and restore confirmed progress.
- **D-11:** After server or worker restart, automatically resume interrupted work only after verifying unchanged source and mapping identity. If that verification fails or identity changed, explain the condition and wait for the user.
- **D-12:** Deliberate cancellation preserves indexed results, remains stopping until the server confirms the stop, and requires an explicit Resume action. Do not automatically resume intentionally cancelled jobs.

### Existing user constraints
- **D-13:** Retain the established PGDP v2 appearance and components. User-facing states and errors must be understandable and localized.
- **D-14:** Reuse existing storage resolvers, mappings, job and lifecycle contracts. Do not create duplicate implementations, hardcoded operator paths, game-specific fixes, or hardcoded UI strings.
- **D-15:** New runtime modules must stay within 500 lines unless a decomposition review justifies an exception. Extract coherent responsibilities rather than growing legacy monoliths.
- **D-16:** Games remain read-only; application-owned progress, metadata and assets stay outside source storage. Implementation, tests, commits and deployment run on the verified canonical Linux checkout.

### Engineering discretion and proof
- The researcher and planner choose the transport, persistence, timeout values and retry policy after inspecting existing code. User decisions define observable behavior, not a mandatory new transport.
- Prove the current failure before selecting a fix. The earlier claim that early clicking or a disconnected socket caused the hang was a hypothesis, not established evidence.
- A missing acknowledgement can follow successful server acceptance. Recovery must reconcile rather than blindly enqueue again.
- Demonstrate bounded recovery or actionable failure through actual fault tests, not source-string assertions alone.
- Cover immediate first click, repeated click, delayed acknowledgement, lost acknowledgement after acceptance, unavailable worker, reload, browser disconnect, server/worker restart, changed mapping/source, explicit cancellation and metadata provider failure.
- Include a production-like Portainer/worker path as well as development execution. Record unavailable test infrastructure as a verification gap rather than a passing result.
- Repeat a clean installation through completed first scan in the in-app browser before closing Phase 33 acceptance.
</decisions>

<canonical_refs>
## Canonical References

Downstream agents must read these before planning or implementing.

### Project and phase decisions
- `CLAUDE.md`: canonical Linux environment, quality and decomposition constraints. Its current checkout supersedes the outdated path in PROJECT.md.
- `.planning/ROADMAP.md`: Phase 34 and open Phase 33 acceptance.
- `.planning/PROJECT.md`: read-only archive boundary and product scope.
- `.planning/REQUIREMENTS.md`: scan, mapping, storage safety and verification contracts.
- `.planning/phases/32-pgdp-namensumstellung-fresh-installation/32-CONTEXT.md`: fresh installations and retained runtime identifiers.
- `.planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-UAT.md`: outstanding fresh-install acceptance.
- `.planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-VALIDATION.md`: prior verification evidence and gaps.

### Existing implementation boundaries
- `frontend/src/v2/views/Auth/Setup.vue`: account and assignment completion.
- `frontend/src/v2/views/Scan.vue`: mapping readiness, submission and progress.
- `frontend/src/v2/composables/useLibraryOperation.ts`: operation submission, cancellation and retry state.
- `frontend/src/v2/composables/useScanLifecycle/index.ts`: application-wide scan lifecycle listeners.
- `frontend/src/v2/composables/useSocketEvent/index.ts`: connection and subscription lifecycle.
- `frontend/src/v2/data/adapters/legacy/scan.ts`: scan transport boundary.
- `frontend/src/services/socket.ts`: shared Socket.IO client.
- `backend/endpoints/sockets/scan.py`: scan authorization, mapped commands and execution.
- `backend/handler/scan_handler.py`: scan processing.
- `backend/endpoints/heartbeat.py`: health and legacy setup compatibility.
- `backend/startup.py`: startup and job infrastructure.

No external specification was introduced during discussion.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
Existing setup assignment APIs, storage readiness checks, immutable mapped
commands, operation contracts, scan stores and lifecycle composables should form
one coherent end-to-end flow.

### Established patterns
Backend owns durable state and API contracts. UI v2 uses shared primitives,
localized messages and typed adapters. RQ and Redis already provide job
infrastructure; inspect available identity and status mechanisms before adding any.

### Integration points
Setup completion, authenticated shell mounting, socket ownership, submission
acceptance, queue/worker status, reconnect reconciliation and explicit cancellation
must be tested together. Check lifecycle cleanup and reinstallation across
setup-to-app navigation as well as connection timing.

The observed browser showed running 0/0 while the database had eight active
mappings and no games, the worker was idle, and no new queue job or scan-start
log was observed. These observations locate an investigation boundary but do
not prove that a disconnected socket is the sole cause.
</code_context>

<specifics>
## Specific Ideas

The user wants a guided installation that detects failures and avoids dead
states. The existing mounted Games root contains direct platform directories
assigned during setup. A complete first scan, rather than a successful page
load or HTTP 200, is the practical acceptance outcome.
</specifics>

<deferred>
## Deferred Ideas

Game-container recognition and metadata matching redesign are outside this
stability phase. Existing targeted subfolder scans must keep working through
the shared operation boundary.
</deferred>
