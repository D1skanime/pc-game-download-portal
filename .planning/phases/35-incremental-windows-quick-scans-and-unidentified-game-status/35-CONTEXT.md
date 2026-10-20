<!-- markdownlint-configure-file {"MD033": {"allowed_elements": ["domain", "decisions", "specifics", "canonical_refs", "code_context", "deferred"]}} -->

# Phase 35: Incremental Windows quick scans and unidentified game status - Context

**Gathered:** 2026-10-20
**Status:** Ready for planning

<domain>

## Phase Boundary

Make Windows quick scans incremental while preserving discovery of new games,
collection children, DLCs and updates. Keep unidentified games visible with an
accurate distinction between unresolved identification, unchanged inventory and
an actual metadata retry. Manual and scheduled scans use the same implementation.

The user requested this follow-up after shipping the accepted Phase 33 live UAT
and Phase 34 scan implementation to main. Phase 35 code has not been implemented.

</domain>

<decisions>

## Implementation Decisions

### Quick scan behavior
- **D-01:** A known, identified Windows game whose relevant inputs are unchanged
  should not repeat expensive component hashing, enrichment or media publication
  on every quick scan.
- **D-02:** New games and new or changed DLCs, updates and component files must
  still be discovered. Nested changes must not be missed merely because the
  top-level game directory's modification time is unchanged.
- **D-03:** Preserve explicit complete, hash, update and targeted retry semantics,
  and other platforms' existing quick-scan behavior.

### Collection folders and scheduled discovery
- **D-04:** A confirmed collection folder remains a collection and cannot return
  as a game. New direct child games are discovered by normal and scheduled scans.
- **D-05:** The user-approved Dev autoscan interval is 15 minutes. Implement one
  shared discovery and skip policy for manual and scheduled scans.

### Unidentified games and truthful status
- **D-06:** Unidentified games remain visible on subsequent scans. Re-listing
  Castlevania.Belmonts.Curse-RUNE as unidentified is acceptable; repeatedly doing
  all work for an unchanged, identified game is the problem to solve.
- **D-07:** Status and counters must distinguish inventory/skip work, unresolved
  identification and actual provider attempts. Do not imply a provider retry
  when no provider request occurred.
- **D-08:** Keep retry eligibility and execution separate. Exact automatic
  retry/backoff is a planning decision. The discussion did not establish that
  every unknown game should query every provider every 15 minutes.

### Shared safety and maintainability
- **D-09:** Reuse mapped scanning, collection inventory, durable acceptance and
  worker/fence boundaries. Do not create a second resolver, component classifier,
  scan lifecycle or fingerprint implementation.
- **D-10:** Preserve Games/source files, existing database and owned media. No
  reset is part of this phase. Cache reuse must not bypass mapping revisions,
  attempt ownership, cancellation or final media publication proof.
- **D-11:** Continue repository code-size policy: target 500 logical lines for new
  production modules, respect the 1,000-line hard limit and extract coherent
  responsibilities instead of enlarging legacy monoliths.

### Choices for planning
- Choose a bounded change detector and justify invalidation rules. A directory
  timestamp alone cannot detect nested additions or changes.
- Define baseline adoption for existing entries and safe behavior when evidence
  is missing, stale or unreadable, including restart and mapping changes.
- Define bounded unknown-game retry/backoff and manual retry behavior.
- Reuse v2 status patterns and preserve locale parity for any new labels.

</decisions>

<specifics>

## Specific Ideas

Castlevania is the motivating collection example. Its selected child replaces
the mistaken parent entry; adding another child later must work through normal
scanning and autoscan. The user observed repeated Windows processing and asked
how other platforms skip known games. The user explicitly required shared code
and continued file-size limits.

</specifics>

<canonical_refs>

## Canonical References

Downstream agents must read these before planning or implementing:

- `CLAUDE.md`: canonical Linux environment, shared code and size limits.
- `.planning/PROJECT.md`: immutable source-library product boundary.
- `.planning/STATE.md`: current shipping and planning handoff.
- `.planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-10-SUMMARY.md`:
  collection classification, parent retirement and future child discovery.
- `.planning/phases/33-fresh-install-first-run-pc-storage-mapping-before-library-sc/33-ACCEPTANCE-RECEIPTS.json`:
  accepted live scope and evidence.
- `.planning/phases/34-reliable-fresh-installation-and-scan-lifecycle/34-IMPLEMENTATION.md`:
  connected durable scanner and safety boundaries.
- `.planning/phases/34-reliable-fresh-installation-and-scan-lifecycle/34-ACCEPTANCE.md`:
  historical evidence and acceptance limits. Frozen 34-16 remains INCONCLUSIVE.

### Shipping baseline

PR #1 merged to main as `e758a06fd519d4bea7397d1ed86b8ba157802268`.
Its tree matches tested source `970fd4c455c8ddb55c5d8c692fed4fa18099d085`.
All 28 shipping checks passed, including all 16 complete MariaDB/PostgreSQL suite
jobs, three-dialect migrations, frontend gates and browser CI. Browser CI passed
29 tests with six fixture-dependent skips. Physical gamepad testing and previous
independent deep review/production Portainer acceptance remain open.

- [Merged PR #1](https://github.com/D1skanime/pc-game-download-portal/pull/1)
- [Complete SQL suites](https://github.com/D1skanime/pc-game-download-portal/actions/runs/39403404175)
- [Browser CI](https://github.com/D1skanime/pc-game-download-portal/actions/runs/39403404116)

These shipping results do not implement or accept Phase 35.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets
- `backend/endpoints/sockets/scan.py::should_scan_rom`: explicitly repeats quick
  scans for known nested Windows games so component changes are not missed.
- `backend/handler/filesystem/roms_handler.py::FSRomsHandler.get_pc_components`:
  existing component inventory entry point.
- `backend/handler/scan_collection_discovery.py::collection_inventory`:
  shared mapped collection inventory and new direct child discovery.
- `backend/handler/scan_collection_policy.py`: mapping-bound classification and
  protection against publishing a collection parent as a game.
- `backend/tasks/scheduled/scan_library.py`: scheduler submits commands through
  shared durable acceptance.

### Required Regression Coverage
- Repeated unchanged identified Windows quick scans avoid expensive work.
- New games, collection children and changed nested DLC/update content remain
  discoverable even with an unchanged top-level directory timestamp.
- Unknown games remain visible and retry status reflects actual provider work.
- Manual and scheduled scans agree; other platforms retain their behavior.
- Restart/mapping/cache invalidation, cancellation and stale-attempt boundaries
  remain safe, and source manifests remain unchanged.

</code_context>

<deferred>

## Deferred Ideas

Matching quality for individual unreleased or unknown titles is separate from
deciding whether to repeat unchanged work. This phase does not close previous
physical gamepad, independent review or Portainer gates.

</deferred>
