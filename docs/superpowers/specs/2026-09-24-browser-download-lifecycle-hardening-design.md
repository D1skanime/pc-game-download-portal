# Browser Download Lifecycle Hardening and Completion Design

## Purpose

Phase 18 completes the browser download lifecycle introduced in Phase 17. It does not replace the immutable manifest or direct-member delivery design. The scope is limited to durable lifecycle truth, recovery, current visibility, archive-set UI integration, and evidence for the existing browser modes.

## Invariants

- External libraries remain read-only. No operation writes, renames, deletes, archives, extracts, or creates sidecars in a source root.
- The immutable manifest remains the selection, authorization, snapshot, and member-identity authority. IDs remain opaque and APIs expose no source or client absolute paths, credentials, or signed URLs.
- Original members are streamed directly. There is no server ZIP, split, extraction, assembly, launcher, desktop-client, or installer scope.
- Standard attachment handoff and enhanced File System Access transfers remain separate modes with separate truth claims.

## Current-Code Findings

The current code already has `DownloadTransferSession`, item, and append-only event records; a locked item reducer; a terminal session reducer; exact enhanced SHA-256 observation validation; explicit `pause` and `cancel` abort intent; direct-member attribution; and server-only `mark_served()` on an unranged, fully consumed response. These capabilities are retained.

The remaining gaps are integration and lifecycle gaps:

1. `list_download_transfers()` serializes owner-scoped sessions without an `assert_rom_visible()` check for each returned session.
2. `GameDetails.vue` does not request `/{rom_id}/download-archive-sets`, so `PcComponents` receives no real archive-set policy despite supporting it.
3. Enhanced progress is held locally except for start, pause, failure, and verification. It needs bounded journal snapshots. Snapshot mismatch is currently recorded as a generic failure rather than `stale`.
4. A cancelled queued item is only changed locally. The journal is not guaranteed to receive a cancellation observation.
5. `resumeSession()` creates an unrelated new session and does not express retry lineage. History cannot show attempts as one recovery sequence.
6. History hard-deletes terminal records. A user-facing hide operation should preserve audit evidence while removing an entry from the default list.
7. Phase 17 artifacts are inconsistent: `17-14-PLAN.md` and its hardening commits exist, but it lacks a summary and STATE says 13 rather than 14 plans. Phase 18 records the factual baseline without rewriting history.

## Lifecycle Authority

Backend enums keep their existing names: item `queued`, `active`, `handed_to_browser`, `served`, `verified`, `paused`, `cancelled`, `failed`, and `stale`; session `active`, `completed`, `cancelled`, `failed`, `expired`, and `stale`. UI copy maps `active` to downloading. No rename-only migration is introduced.

The database handler is the only durable transition authority. It locks the session and item, validates event-specific predecessor state and byte bounds, appends exactly one bounded event, and calls one session reducer. Invalid client observations return 409, while malformed payloads retain FastAPI's 422 contract. `verified` requires enhanced mode, exactly expected bytes, and the captured SHA-256. Progress cannot regress inside an attempt. A restart creates a new attempt, so it never mutates an earlier attempt's progress back to zero.

The reducer preserves terminal truth. A session of all `verified` enhanced items is completed and successful. A standard session is successful only when all applicable members are server-served; handed-to-browser never asserts a saved local file. All cancelled items yield cancelled. Failed and stale cases yield the appropriate terminal failure state. Cleanup reconciles only active sessions, so a completed session cannot later become stale because its manifest expires.

## Attempts, Recovery, and History

Each retry or restart creates a new, owner-scoped session linked to its prior attempt and records an incrementing attempt number. It contains only the selected failed, cancelled, or stale member subset. Existing successful items are not requested again. A compact history groups attempts by their root session, while keeping each item event auditable.

`dismissed_at` is added only to the session record. Dismissal hides a terminal attempt from the owner's default history, does not delete events, and is reversible only through a later administrative/audit workflow if needed. Scheduled 90-day physical retention remains the only routine deletion path.

Enhanced recovery requires the user to select a directory again after a reload. The client opens the safe relative destination, reads its actual size, hashes persisted bytes, sends exact `Range` plus `If-Match`, verifies the final digest, then posts `verified`. Restart is a distinct user action that intentionally truncates or recreates only the selected local destination after confirmation; resume never deletes local bytes automatically.

## Event Integration

Enhanced transfers send a throttled `progress` observation by both elapsed time and byte advancement, plus mandatory snapshots at pause, cancel, error, and verification. The threshold is centralized and tested, preventing one event per chunk. The client identifies an abort by explicit operation intent, so cancellation cannot later become paused. It reports `cancel` for every cancelled persisted item, including an item that has not begun streaming.

Snapshot-invalid responses (409, 410, 412) call the existing stale authority, not generic failure handling. Observation delivery failures are reported as a separate journal-sync error and never delete a valid local enhanced file.

`mark_served()` remains server-only and is called only after a full un-ranged attributed response finishes. Ranged delivery does not claim full service.

## Archive-Set and UI Behavior

When the PC Components tab is entered, Game Details loads archive sets through the existing read-scoped ROM route. It passes explicit loading, loaded-empty, success, and error state to `PcComponents` and `DownloadSelectionDialog`. An archive-set request error blocks beginning a policy-sensitive download and is visible to the user. An empty successful response keeps the existing component/member fallback. No filename heuristic is added.

The manager shows a stable, mobile-first row with safe filename, component or game context, bytes, status, actionable error copy, and only state-allowed controls. Enhanced offers pause, resume, cancel, retry, or restart as its current attempt permits. Standard mode never offers false progress, resume, verification, or local-save guarantees. The selected backend queue limit stays unchanged unless measurement proves the current configuration unsafe.

## Visibility and Sensitive Data

Every list, get, mutate, dismiss, retry, attributed stream, and archive-set operation checks both owner scope and current `assert_rom_visible()` scope. Serialization is restricted to existing safe destination names, byte facts, timestamps, state, and bounded error codes. Tests prohibit source roots, absolute paths, local directory handles, Authorization values, tokens, and unexpected exception text in API and rendered output.

## Verification Strategy

Backend tests cover every allowed and denied transition, byte/hash validation, session reduction, terminal expiry preservation, retry lineage, current visibility, `served`, stale mapping, and no sensitive fields. Frontend tests cover the abort-reason regression, pause/resume, queued cancellation, restart, partial resume, throttling, archive-set fetch states, state-specific history actions, and truthful standard-mode vocabulary.

Browser evidence uses an isolated fixture only, never Team4s or a real NAS. It covers Chromium standard and enhanced flows, Firefox standard handoff/history, and Edge enhanced behavior when supported. It records unsupported capability cases honestly. Sparse fixtures test offsets and accounting above 4 GiB; multi-part fixtures test required and optional archive-set ordering and a single-part retry. Before-and-after source facts prove no mutation.

## Out of Scope

Desktop/Tauri work, installation, launching, archive extraction or assembly, archive-name inference, ZIP packaging, source writes, generic redesign, background services, P2P, and a new transfer protocol are excluded.
