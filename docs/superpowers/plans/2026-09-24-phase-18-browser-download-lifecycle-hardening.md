# Phase 18 Browser Download Lifecycle Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the existing browser download lifecycle without changing classic RomM downloads or source-library safety.

**Architecture:** Retain the existing manifest, direct-member stream, transfer-session, and v2 queue architecture. Centralize durable state transitions in `DBDownloadTransfersHandler`, extend only the existing session model for attempt lineage and soft hiding, then connect existing endpoints and UI components to that authority.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, pytest, Vue 3, TypeScript, Vitest, Playwright, File System Access API.

**Spec:** `docs/superpowers/specs/2026-09-24-browser-download-lifecycle-hardening-design.md`

## Global Constraints

- Never write to an external source root or create ZIPs, archives, extracted files, heuristics, desktop-client features, or a replacement transfer protocol.
- Keep `/api/roms/{id}/content/{file_name}`, `getDownloadPath()`, EmulatorJS, Ruffle, classic ZIP/M3U behavior, and classic permissions independent of transfer sessions and manifests.
- Preserve opaque IDs and exclude NAS paths, local absolute paths, tokens, headers, and exception details from APIs, history, logs, and UI.
- Keep `DownloadTransferItemStatus.ACTIVE` and `DownloadTransferSessionStatus.ACTIVE`; map the former to the UI word `downloading` rather than renaming enums.
- Treat `_EVENT_LIMIT = 4096` as a bounded session budget. Progress sampling reserves one lifecycle/terminal event per selected member and never makes a terminal event impossible.

## Review Focus

- A generic HTTP 409 must not be converted to stale without a recognized snapshot or manifest lifecycle code.
- A successful terminal session must remain completed after its manifest expires.
- A queued cancellation must persist exactly one cancellation event and never become paused after an abort race.
- A hidden ROM must be absent from a bulk history response without issuing one visibility query per session.
- A non-PC ROM must not fetch archive sets or enter the manifest/session flow.

### Task 1: Record the Phase-18 baseline and protect classic RomM paths

**Files:**

- Modify: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`
- Create: `.planning/phases/18-browser-download-lifecycle-hardening/18-CONTEXT.md`
- Modify: `frontend/src/utils/index.test.ts`, `frontend/src/v2/views/GameDetails.test.ts`, `backend/tests/endpoints/roms/test_rom.py`

**Interfaces:**

- Consumes: classic `getDownloadPath({ rom, fileIDs })` and `PC_PLATFORM_SLUGS` in `GameDetails.vue`.
- Produces: Phase-18 requirement mapping and executable compatibility regression baseline.

- [ ] Write failing frontend tests that assert a Game Boy/SNES fixture has no PC Components tab or archive-set request, while `getDownloadPath()` produces `/api/roms/{id}/content/{file_name}` for one file and retains `file_ids` for a multi-file selection.
- [ ] Write failing endpoint coverage that exercises the existing single-file and multi-file/M3U content responses without any manifest or transfer-session query.
- [ ] Implement only missing test fixtures and assertions. Do not change the classic route, player routes, or `getDownloadPath()` implementation.
- [ ] Add Phase 18 as v1.3 in the planning files. Mark Phase 17 as accepted architecture with an unexecuted-plan/summary inconsistency and retained hardening gaps; do not change historical Phase-17 artifacts.
- [ ] Run `cd frontend && npm run test -- utils GameDetails` and `cd backend && uv run pytest tests/endpoints/roms/test_rom.py -q`.
- [ ] Commit with `docs: start phase 18 lifecycle hardening`.

### Task 2: Make lifecycle and attempt authority explicit in the existing transfer journal

**Files:**

- Modify: `backend/models/download_transfer.py`, `backend/handler/database/download_transfers_handler.py`, `backend/endpoints/responses/download_transfer.py`
- Create: `backend/alembic/versions/0125_download_transfer_attempts.py`
- Modify: `backend/tests/models/test_download_transfer.py`, `backend/tests/handler/database/test_download_transfers_handler.py`

**Interfaces:**

- Consumes: `append_observation()`, `_reconcile_locked()`, and existing `DownloadTransferSession` records.
- Produces: `create_retry_attempt()`, `dismiss_session()`, structured observation failure codes, and a reducer table used by endpoint and queue tasks.

- [ ] Write handler tests for every legal predecessor: progress queued/active, pause active, resume paused, verified enhanced-active with exact digest, cancel nonterminal, and failed nonterminal. Assert illegal transitions, terminal transitions, excess bytes, regressed bytes, and invalid digest fail with the endpoint-mappable conflict domain.
- [ ] Write reducer-table tests for all-verified, all-served, all-cancelled, all-failed, all-stale, served-plus-failed, verified-plus-cancelled, and failed-plus-cancelled item sets. Assert exact session status, result, and immutable `ended_at` behavior after expiry cleanup.
- [ ] Add nullable root-attempt identity, positive attempt number, nullable `dismissed_at`, and indexed owner/root history fields only if absent. The migration backfills existing rows as attempt one rooted at themselves without source access.
- [ ] Implement a bounded observation result/error vocabulary, including `snapshot_changed`, `manifest_expired`, `manifest_revoked`, `integrity_mismatch`, `download_io`, and `journal_sync`. Make stale transition accept only recognized manifest/snapshot facts, not a raw HTTP status.
- [ ] Implement retry creation under locks: accept only terminal failed/cancelled/stale source attempts, select only their non-successful members, set root and attempt number, and leave prior rows/events untouched. Implement terminal soft dismissal instead of physical user deletion.
- [ ] Reserve event capacity before adding progress: reject or coalesce excess progress while retaining lifecycle and terminal events for every nonterminal member. Keep `_EVENT_LIMIT` 4096 unless a measured test proves another bound necessary.
- [ ] Run `cd backend && uv run pytest tests/models/test_download_transfer.py tests/handler/database/test_download_transfers_handler.py -q` and migration upgrade/downgrade on the isolated database.
- [ ] Commit with `feat(downloads): add durable attempt lifecycle`.

### Task 3: Bind visibility, observations, stale facts, and history APIs to the durable authority

**Files:**

- Modify: `backend/endpoints/download_transfers.py`, `backend/endpoints/download_manifests.py`, `backend/endpoints/responses/download_transfer.py`
- Modify: `backend/handler/database/download_transfers_handler.py`, `backend/tests/endpoints/test_download_transfers.py`, `backend/tests/endpoints/test_download_manifests.py`

**Interfaces:**

- Consumes: Task 2 retry/dismiss/reducer APIs and `assert_rom_visible()`.
- Produces: bulk-visible session list, typed retry/dismiss routes, and code-specific stale observations.

- [ ] Write an endpoint test with visible and currently hidden sessions for one owner, then assert list excludes the hidden record and its ROM ID, member filename, bytes, manifest ID, timestamps, and states. Add a query-count assertion proving visibility is loaded in bulk rather than per session.
- [ ] Implement `get_sessions()` with ORM eager loading or a visibility-aware joined predicate, then call `assert_rom_visible()` only without N+1 behavior or apply the existing visibility predicate at query time. Preserve 404 masking for get/mutate routes.
- [ ] Write tests for malformed observations (422), illegal transitions (409), a generic 409 that remains failure, and recognized `manifest_expired`, `manifest_revoked`, and `source_changed` facts that become stale. Assert no raw source or exception text is serialized.
- [ ] Add typed retry and dismiss API routes that only operate on owner-visible terminal sessions; serialize root attempt, attempt number, dismissal state, safe event facts, and no paths.
- [ ] In `get_download_manifest_member()`, retain `mark_served()` only after a completed full attributed body, never on range or disconnect. Map verified source replacement to the typed stale fact and test it.
- [ ] Run `cd backend && uv run pytest tests/endpoints/test_download_transfers.py tests/endpoints/test_download_manifests.py -q`.
- [ ] Commit with `feat(downloads): secure lifecycle history APIs`.

### Task 4: Complete enhanced queue persistence, resume, restart, and error separation

**Files:**

- Modify: `frontend/src/services/api/downloadTransfers.ts`, `frontend/src/v2/composables/useBrowserDownloadQueue/index.ts`, `frontend/src/v2/composables/useBrowserDownloadQueue/index.test.ts`
- Modify: `frontend/src/v2/utils/downloadManifestPath.test.ts`, `frontend/src/v2/workers/downloadHash.worker.ts` only if its existing protocol lacks a tested restart seam

**Interfaces:**

- Consumes: typed retry/dismiss/observation routes from Task 3 and existing `enhancedMember()`.
- Produces: explicit queue operation intent, bounded progress observer, resume/restart actions, and typed local error categories.

- [ ] Write failing Vitest cases for pause then resume, cancel then aborted fetch rejection, queued cancel, checksum mismatch, source-change response, journal-observation failure after a verified local file, restart-from-zero, and a partial file resumed at its actual persisted offset.
- [ ] Keep explicit operation reason (`pause`, `cancel`, `timeout`) as the abort discriminator. Make every catch branch use that reason rather than `signal.aborted`; cancellation must stay cancelled even if the async catch runs after UI state changed.
- [ ] Add a centralized progress sampler with time and byte thresholds. It may update local UI per chunk but sends at most the permitted sampled events, flushes on pause/cancel/failure/verification, and reserves event capacity via server response handling.
- [ ] On known stale response facts, call the typed stale route and show source-change guidance. On journal-sync failure, retain the local file and show journal-sync guidance without relabeling the transfer as checksum or snapshot failure.
- [ ] Replace unrelated `resumeSession()` creation with the typed retry attempt route. Resume reuses actual local bytes and exact Range/If-Match; restart requires an explicit action and recreates/truncates only the selected safe destination after user confirmation.
- [ ] Run `cd frontend && npm run test -- useBrowserDownloadQueue downloadManifestPath` and `npm run typecheck`.
- [ ] Commit with `feat(downloads): persist enhanced recovery lifecycle`.

### Task 5: Wire archive-set policy safely into the PC-only game detail flow

**Files:**

- Modify: `frontend/src/v2/views/GameDetails.vue`, `frontend/src/v2/components/GameDetails/PcComponents.vue`, `frontend/src/v2/components/GameDetails/DownloadSelectionDialog.vue`
- Modify: `frontend/src/v2/views/GameDetails.test.ts`, `frontend/src/v2/components/GameDetails/PcComponents.test.ts`, `frontend/src/v2/components/GameDetails/DownloadSelectionDialog.test.ts`

**Interfaces:**

- Consumes: existing `GET /roms/{rom_id}/download-archive-sets` response and PC slug boundary.
- Produces: explicit archive-set loading, loaded-empty, error, and policy-ready props.

- [ ] Write component tests proving a PC slug fetches archive sets on entering its component tab and passes them to `PcComponents`, a successful empty response preserves the old component flow, and a non-PC fixture performs no archive-set request and renders no PC tab.
- [ ] Write a failing policy-error case in which the archive-set request fails and the dialog cannot silently start a fallback selection that could omit required members.
- [ ] Add request sequencing and unmount invalidation matching the existing history hydration pattern. Pass explicit `archiveSetsLoading` and `archiveSetsError` state to the dialog; expose a retryable, localized error rather than treating errors as empty data.
- [ ] Preserve the existing generic backend endpoint and free component/member fallback only for an explicit loaded-empty result. Do not add filename rules for multipart or multi-disc ROMs.
- [ ] Run `cd frontend && npm run test -- GameDetails PcComponents DownloadSelectionDialog` and `npm run typecheck`.
- [ ] Commit with `feat(pc): load archive-set download policy`.

### Task 6: Turn transfer history into a safe recovery surface without classic UI regression

**Files:**

- Modify: `frontend/src/v2/components/GameDetails/DownloadManager.vue`, `frontend/src/v2/components/GameDetails/DownloadTransferHistory.vue`, `frontend/src/v2/components/GameDetails/DownloadTransferHistory.test.ts`, `frontend/src/v2/components/GameDetails/DownloadManager.test.ts`
- Modify: `frontend/src/locales/en_US/rom.json` and every parity locale file only for new user-visible recovery copy

**Interfaces:**

- Consumes: Task 3 attempt metadata/routes and Task 4 queue actions.
- Produces: grouped attempts, status-specific recovery controls, soft hide, and truthful standard/enhanced copy.

- [ ] Write failing row-action tests for downloading pause/cancel, paused resume/restart/cancel, failed retry or restart, cancelled retry, stale new-manifest guidance, verified/completed no recovery action, and standard handed-to-browser/served rows without progress, local completion, or verification claims.
- [ ] Render attempt grouping using root attempt identity and attempt number, with safe filename, component context, bytes, bounded error text, and stable action placement on mobile and desktop. Do not render opaque IDs, paths, tokens, or local handles.
- [ ] Wire retry/restart/dismiss to the typed API and queue. “Remove from history” calls soft hide; it does not delete audit rows. Existing scheduled retention remains responsible for eventual physical deletion.
- [ ] Add localized error and recovery keys, then run locale parity and sorting checks.
- [ ] Run `cd frontend && npm run test -- DownloadManager DownloadTransferHistory` plus locale checks and `npm run typecheck`.
- [ ] Commit with `feat(downloads): add recovery history actions`.

### Task 7: Verify compatibility, source safety, large files, and real browser behavior

**Files:**

- Modify: `backend/tests/endpoints/roms/test_rom.py`, `backend/tests/endpoints/test_download_manifests.py`, `backend/tests/endpoints/test_download_transfers.py`
- Modify: `frontend/src/v2/sourceMutationControls.test.ts`, `frontend/playwright/` download coverage, `.planning/phases/18-browser-download-lifecycle-hardening/18-VALIDATION.md`, `.planning/phases/18-browser-download-lifecycle-hardening/18-SUMMARY.md`, `.planning/STATE.md`

**Interfaces:**

- Consumes: all preceding lifecycle, UI, and compatibility contracts.
- Produces: isolated evidence and an honest phase closure record.

- [ ] Add sparse greater-than-4-GiB unit/integration fixtures for Range offset, progress arithmetic, resume, final hash, and bounded memory. Add an 80-member archive-set fixture proving stable order, required/optional selection, a single-member retry, and no re-download of verified members.
- [ ] Run source before/after evidence using an isolated fixture only: tree, names, sizes, hashes, and timestamps. Assert no source-root writes, sidecars, archive output, or absolute-path leakage.
- [ ] Run backend focused suites, frontend focused suites, full typecheck, locale checks, and Trunk. Run migration upgrade/downgrade on MariaDB, MySQL, and PostgreSQL where the isolated services are available; record unavailable infrastructure as blocked rather than passing.
- [ ] Run Playwright cases in Chromium for classic single/multi-file, standard PC handoff, enhanced pause/resume/cancel/retry/restart, source change, expiry, and final SHA. Run Firefox classic handoff/history and Edge enhanced tests when supported; state capability limitations precisely.
- [ ] Update Phase-18 validation, summary, roadmap status, and STATE only from fresh evidence. List genuine unavailable checks or product gaps explicitly and do not claim Phase 18 complete if any required gate lacks evidence.
- [ ] Commit with `test(downloads): verify lifecycle completion` and `docs: record phase 18 verification`.
