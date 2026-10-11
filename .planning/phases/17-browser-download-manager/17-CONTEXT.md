# Phase 17: Browser Download Manager - Context

**Gathered:** 2026-09-17
**Status:** Ready for planning
**Source:** User-approved phase specification and code audit

<domain>
## Phase Boundary

RomM v2 provides a browser-only PC download workflow for whole games, selected
components, and allowed individual files. It builds exactly one immutable
Phase-14 manifest from the validated selection and delivers each original file
through the Phase-15 direct transfer endpoint. It does not install games,
extract or combine archives, create ZIPs, stage source data, expose NAS paths,
or write to source roots.

Standard browser attachment download is mandatory. A File System Access API
mode is an optional feature-detected enhancement that streams into a
user-approved directory without buffering complete large files.
</domain>

<decisions>
## Locked Product Decisions

### Architecture and safety

- Phase 14 manifests and Phase 15 direct member transfer remain the only
  manifest and source-file delivery authority. Do not create a parallel
  download endpoint or archive route.
- Manifest members expose opaque file IDs, validated relative destinations,
  exact sizes, SHA-256 digests, and strong snapshots only. NAS and source
  paths never reach the client.
- Direct transfer preserves Range, 206, Content-Range, Accept-Ranges, strong
  validators, If-Range or If-Match semantics, and fail-closed source-change
  behavior.
- Large original files stream directly. They are never wholly buffered,
  split, staged, copied, or reconstructed server-side.
- All session, history, and test output remains outside external source roots.
  The phase must provide before/after source evidence.

### Selection and dependencies

- The primary UX is component-oriented: Main Game, Updates, DLCs, and Extras.
  File selection is a detail view.
- Eligible optional files can be selected individually. A deselected optional
  file is absent from both manifest and queue.
- Required archive sets are explicit persisted domain data, not a filename or
  regex heuristic. An incomplete required set cannot create a manifest. The
  UI explains that all set members must be downloaded together.
- The server validates all component, file, and required-set selections before
  creating the immutable manifest.

### Browser modes and transfer semantics

- Standard browser attachment download is the universal baseline. It starts a
  bounded sequence of original attachment downloads and may require browser
  permission for multiple downloads. RomM must not evade browser safeguards.
- Standard-mode state means `handed_to_browser`, never locally saved,
  checksum-verified, or resumed by RomM.
- Enhanced mode is available only through capability detection, never
  user-agent detection. It uses a user-initiated directory picker, validates
  each manifest destination again, streams Fetch responses to writable file
  handles, and avoids whole-file Blob or ArrayBuffer buffering.
- Enhanced resume sends the exact manifest snapshot with Range and If-Match;
  it accepts only an exact matching 206 response. Changed source or manifest
  state is terminal and tells the user to restart.
- Queue concurrency is a centrally configured value, not duplicated constants.
  It limits files, not artificial ranges of one original file.
- Pause and cancel apply to browser-managed enhanced transfers only where the
  page can reliably control them. Refresh, navigation, closed tabs, and
  browser restart must not receive unsupported persistence guarantees.

### Session, history, and terminology

- Download sessions are owner-scoped, path-free tracking records linked to a
  manifest and game. They are not file-delivery credentials.
- Session records preserve selected totals and per-item status, observed bytes,
  start, activity, and end times. Browser-reported data is observational.
- `served` means the server fully delivered an HTTP response. It never means a
  browser saved a local file. Enhanced `verified` is reserved for streamed
  local SHA-256 equality.
- History presents selected components and server transfer facts without
  asserting PC storage success.
- Completed, cancelled, failed, and expired session records, including their
  bounded observational events, are retained for 90 days and then deleted by a
  RomM-owned cleanup path. Active sessions whose manifests expire are marked
  expired and cannot be resumed.

### Desktop product change

- The Phase-16 desktop client is retained as a prototype. Mandatory desktop
  distribution, installers, Tauri handoff, custom schemes, and local services
  are cancelled product scope.
- Phase-16 Windows, Linux, and Bazzite installer UAT does not block Phase 17.
Do not delete desktop code in this phase. Record reuse, desktop-only, and
obsolete components for later cleanup.
</decisions>

<canonical_refs>

## Canonical References

- `.planning/phases/14-immutable-download-manifests/14-VERIFICATION.md` - immutable manifest authority
- `.planning/phases/15-direct-resumable-transfer/15-VERIFICATION.md` - direct range transfer authority
- `.planning/phases/15-direct-resumable-transfer/15-UAT.md` - large local streaming evidence
- `.planning/phases/16-cross-platform-desktop-client/16-CONTEXT.md` - retained prototype scope
- `.planning/phases/17-browser-download-manager/17-RESEARCH.md` - code and browser research
- `.planning/phases/17-browser-download-manager/17-UI-SPEC.md` - approved UI contract
- `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` - planning status
- `backend/endpoints/download_manifests.py` - manifest and direct transfer API
- `backend/handler/database/download_manifests_handler.py` - manifest selection authority
- `frontend/src/v2/components/GameDetails/PcComponents.vue` - existing PC detail surface
  </canonical_refs>

<specifics>
## Required Evidence

- A greater-than-4-GiB ISO transfer with direct Range behavior.
- A multi-file split game with controlled queue ordering.
- Update-only and DLC-only selection, plus multi-component selection.
- Optional-file exclusion and required-set rejection.
- Enhanced resume and source-change rejection with byte identity checks.
- Expired manifest and unauthorized access fail closed.
- Browser matrix documentation for Firefox, Chrome, and Edge, covering
  standard mode, enhanced availability, multi-file behavior, and Range.
- No real NAS, Team4s deployment, service restart, or source-root write.
</specifics>

<deferred>
## Deferred

- Desktop-code cleanup and packaging removal.
- Game installation, extraction, mounting, launching, cloud sync, and server
archive creation.
</deferred>

---

_Phase: 17-browser-download-manager_
_Context gathered: 2026-09-17 from user specification and code audit_
