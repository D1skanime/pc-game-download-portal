# Phase 17 Release-Hardening Plan

**Status:** Approved for planning only. Phase 17 is not complete and Phase 18 must not begin.

**Goal:** Make browser downloads truthful, recoverable, safe for large files, and verified in real isolated browsers.

**Audit baseline:** `mark_served()` has no caller; stream requests lack transfer/item attribution; no central session completion exists; Enhanced `verified` is only local; pause and cancel share one abort path; FSA pause does not prove persisted bytes; every GET/Range full-hashes the source; standard batches only anchor clicks; history is hidden while queue rows exist; retry/attempt lineage and action UI are missing; current verification is `gaps_found` with no MariaDB or browser evidence.

## Invariants

- Keep immutable manifests and direct member streaming as the only delivery route. No ZIP, desktop helper, custom scheme, client source path, NAS write, Team4s change, restart, or deployment.
- Standard mode may state `handed_to_browser` and `served` only. It never claims the browser saved a file.
- Enhanced `verified` is server-persisted only after exact expected bytes and SHA-256 match the manifest.
- A retry creates a new persistent attempt. It does not overwrite a cancelled or failed attempt.
- A UI timer may dismiss a toast but must never hide or delete transfer history.

## 17-H01: Transfer state machine and attempts

**Modify:** `backend/models/download_transfer.py`, a new Alembic migration, `backend/handler/database/download_transfers_handler.py`, transfer response schemas/tests.

1. Write transition-table tests before implementation for `queued -> active -> verified`, `queued -> handed_to_browser -> served`, `active -> paused -> active`, `active -> cancelled`, `active -> failed`, and source-change terminal states. Reject invalid direct transitions.
2. Add explicit activity/terminal outcomes and bounded error codes for network, permission, write/disk, source change, checksum mismatch, expiry, and user cancellation.
3. Add attempt lineage and member-restricted retry selection, validated against opaque members of the original immutable manifest.
4. Add one transaction-locked reconciliation method called after every item mutation. Define session status and result separately: status is active, completed, cancelled, or stale; a terminal result is success, partial, failed, or cancelled. It sets terminal item ended_at, aggregates observed bytes, and ends a session only after all selected items are terminal. Thus 77 verified plus 3 failed is completed with result partial, not indefinitely active merely because retry remains possible.
5. Run model/handler tests against isolated MariaDB, MySQL, and PostgreSQL migration targets before committing.

## 17-H02: Attributed direct streaming and served persistence

**Modify:** `backend/endpoints/download_manifests.py`, `backend/endpoints/download_transfers.py`, transfer handler/tests, generated API types, `frontend/src/services/api/downloadTransfers.ts`.

1. Carry transfer session and item identity to the member request. Validate owner, visible ROM, manifest, opaque member, item, and state before opening a source descriptor. Never accept a filesystem path.
2. Wrap the response iterator so mark_served records only the attributed byte coverage after that response body has been yielded by the application. A completed Range response proves only its requested range, never the whole member. Mark an item served only when its full byte coverage is proven for that attempt; disconnects and iterator failures must not produce served.
3. Add full GET, Range GET, attribution mismatch, owner masking, disconnect, and strict `If-Match` regression tests.

## 17-H03: Large-file revalidation without a pre-stream full hash

**Modify:** `backend/handler/filesystem/roms_handler.py`, manifest/filesystem tests, integrity documentation.

1. Test replacement, truncation, mtime, device/inode, expiry, and Range resume source changes before changing behavior.
2. Replace `source.hash("sha256")` before each GET with descriptor-bound structural comparison against the manifest-captured size, `mtime_ns`, device, and inode. Stream from the checked read-only descriptor so a pathname replacement cannot switch bytes within one request.
3. Preserve strict snapshot If-Match for resume and final Enhanced SHA-256. Document the remaining threat boundary: an immutable read-only mount differs from an adversary who can modify bytes while preserving all metadata. Record fixture/server I/O as well as first-byte time, proving a 40 GiB Range start does not pre-read the full 50 GiB source.
4. Measure request-to-first-byte using isolated sparse 5 GiB and >50 GiB fixtures; it must not scale with a server-side full hash.

## 17-H04: FSA pause, resume, cancel, and recovery

**Modify:** `frontend/src/v2/composables/useBrowserDownloadQueue/index.ts`, hash worker if needed, unit/browser tests.

1. Add failing tests separating pause, cancel, network abort, checksum mismatch, and permission loss. Intentional pause must not emit `fail`; cancel must persist `cancel`; no catch block may overwrite either state.
2. Replace controller-only handling with an operation record containing explicit abort reason. Pause stops new chunks, closes the writable stream, rereads actual destination size, then persists `paused`.
3. Resume only from physically persisted bytes, with exact If-Match, Range, 206, and Content-Range. Prefer sequentially rehashing the persisted local file, then hash the remaining stream, before considering serialized hash state. Add serialized cryptographic state only if measurement proves the simpler local rehash unacceptable. If safety cannot be proven, offer restart, not pseudo-resume.
4. Make cancellation and checksum restart explicit: require confirmation before replacing/truncating a local file, start at offset zero, and create a new attempt.
5. Provide folder re-selection when FSA permission is lost without discarding a valid server attempt.

## 17-H05: Verified persistence, retry, and durable history

**Modify:** transfer API/handler/tests, queue, `DownloadManager.vue`, `DownloadTransferHistory.vue`, component tests.

1. Post Enhanced `verified` after writer close and SHA check; backend validates bytes and digest.
2. Add owner-authorized retry and history-removal APIs. Retrying failed/cancelled/stale members creates a linked attempt containing only those members. Removing history never silently aborts an active transfer.
3. Rehydrate active sessions and history separately after navigation/refresh. Retention is server-defined, not a five-second frontend removal.
4. Test three attempts (`failed`, `cancelled`, `verified`), removal of only one, and retry of 3 failed members without redownloading 77 verified archive members.

## 17-H06: Truthful standard browser handoff

**Modify:** queue composable, selection/mode UI, translations/tests, browser matrix.

1. Replace the claimed active-download queue with bounded browser handoff batches. Anchor concurrency is never described as browser download concurrency.
2. Before multi-file handoff, show file count and automatic-download permission warning. Require a user-controlled Continue action for later batches; do not fire an 80-anchor burst.
3. Record handoff and display browser-managed, handed-to-browser, and server-served wording accurately.
4. Test one, ten, and eighty member ordering, then execute those cases in Firefox, Chrome, and Edge.

## 17-H07: Download manager UX

**Modify:** `DownloadManager.vue`, `DownloadTransferHistory.vue`, focused child components/styles, locale strings/tests.

1. Render Active and History independently so terminal attempts remain visible while active rows exist.
2. Group compact rows by component with collapsible summaries, archive-set context, completed/total counts, and bytes.
3. Expose text plus icon and only valid actions: Pause/Cancel active, Resume/Cancel paused, Retry/Remove recoverable terminal entries. Add accessible error copy.
4. Add aggregate progress/counts without ETA unless a stable tested estimator exists.

## 17-H08: Responsive, bulk actions, and performance

**Modify:** manager/history styles/tests and progress-observation code.

1. Implement mobile-first touch targets and compact rows, then desktop columns for name, size, progress, state, and actions using existing v2 tokens.
2. Add bulk Pause, Resume, confirmed Cancel-all, and Retry-failed-component. Each dispatches only state-valid operations and reports partial errors.
3. Throttle frontend rendering and server observations by measured byte/time thresholds. Prove 80 transfers do not persist one event per 64 KiB chunk.
4. Measure DOM count, reactivity, API calls, and memory for 80 members; add virtualization only if measurements require it.

## 17-H09: Automated gates

**Modify:** backend endpoint/handler tests, frontend tests, Playwright isolated fixture setup.

1. Make focused backend tests run against an isolated MariaDB service, not a developer-machine port assumption.
2. Add browser automation for FSA detection, picker denial, pause/resume/cancel, refresh interruption, permission loss, checksum mismatch, and history retry. Clearly label mocks where a real browser API cannot be used safely.
3. Require frontend tests, typecheck, build, backend focused suite, migration checks, and source safety checks before UAT.

## 17-H10: Real isolated UAT and completion evidence

**Modify:** `17-BROWSER-MATRIX.md`, `17-DOWNLOAD-EVIDENCE.md`, `17-VERIFICATION.md` only after the evidence exists.

1. Use an approved isolated read-only fixture, never the real NAS. Capture source tree, size, SHA-256, and access time before/after each case.
2. Run Standard 1/10/80-member handoffs in Firefox, Chrome, and Edge, recording permission prompts, batches, browser behavior, and history.
3. Run Enhanced >4 GiB and preferably >50 GiB cases: start, pause, resume, cancel, retry, checksum mismatch, source change, permission loss, refresh, final SHA, first-byte time, memory, and real resume offset.
4. Run a 50-80 member archive-set case, including required selection, grouping, retry-only-failed, and three persistent attempts.
5. Update Phase 17 to `passed` only when every automated and live gate has evidence. Then, and only then, discuss Phase 18.

## Dependency order

`H01 -> H02/H05`; `H03 -> H02/H04`; `H04 -> H05`; `H05 + H06 -> H07`; `H07 -> H08`; `H01-H08 -> H09 -> H10`.

## Review checklist

- Every server operation is owner-scoped and manifest/member-bound.
- No state claims more than the server/client can prove.
- Every resume offset equals real FSA-persisted file bytes.
- No source mutation, path disclosure, ZIP route, or desktop dependency is introduced.
- Unit success never substitutes for required live browser and large/multi-file evidence.
