# Phase 22: Bulk-automatisierung für PC-Spiel- und DLC-Zuordnung - Context

**Gathered:** 2026-10-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Automate discovery and metadata enrichment for large PC libraries after new,
correctly named main-game folders appear in the read-only library. The phase
must automatically match safe main-game and DLC candidates, run on a
configurable background interval, and give administrators one efficient review
queue for exceptions rather than requiring a per-ROM workflow.

</domain>

<decisions>
## Implementation Decisions

### Main-game automation

- **D-01:** A correctly named main-game folder may be matched and applied
  without confirmation when the Steam result is unambiguous. The enrichment
  fetches Steam text, IGDB metadata, and available provider media through the
  existing non-destructive paths.
- **D-02:** No result or an ambiguous result is never applied automatically;
  it becomes a review-queue item.

### DLC and expansion automation

- **D-03:** After a main game has a trusted Steam identity, its local DLC and
  expansion components may use a tolerant title comparison against the
  official related-item list, but only one plausible result may be applied.
- **D-04:** Missing, tied, or otherwise unsafe DLC relations remain pending
  review. Existing manual selections and protected provider data are never
  overwritten by a background run.

### Exception review queue

- **D-05:** The administration UI provides one centralized queue with the
  suggested candidate, cover, platform, and reason for confidence or failure.
- **D-06:** Operators can accept, search/correct, or skip an item, and can use
  multi-selection when applying the same safe decision to comparable queued
  items.

### Background processing

- **D-07:** New PC folders are discovered by a configurable periodic background
  scan, with a production `*/15 * * * *` cron default. A separate
  `PC_AUTOMATION_UAT_INTERVAL_SECONDS=10` development/UAT override is disabled
  by default, rejects production configuration, and uses an explicitly tested
  interval runner rather than a six-field cron or filesystem watcher. Newly
  discovered eligible games then enter the automatic matching flow.
- **D-08:** The UI exposes processing progress and outstanding review items.
  Background work never writes to, renames, moves, or deletes source-library
  content.

### Claude's Discretion

- Choose bounded confidence scoring, job persistence, retry behavior, and the
  smallest API/UI seams that reuse the existing scan, Steam, IGDB, component,
  and media reconciliation contracts.
- Define safe batch-action eligibility so each application is still traceable
  and cannot silently apply an ambiguous candidate.
- A skip is terminal only for the current target incarnation and decision
  fingerprint; target changes or an explicit authorized requeue make it
  eligible for review again.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product and prior decisions

- `.planning/ROADMAP.md` — Phase 22 scope and dependency on Phase 21.
- `.planning/REQUIREMENTS.md` — immutable library and PC metadata constraints.
- `.planning/phases/19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric/19-CONTEXT.md` — fail-closed PC, IGDB, and DLC identity decisions.
- `.planning/phases/20-media-management-and-owned-soundtrack-uploads/20-CONTEXT.md` — provider media and user-selection protection.
- `.planning/phases/21-unify-admin-pc-scans-with-german-steam-metadata-and-media/21-CONTEXT.md` — German-first Steam enrichment and scan parity.

### Existing implementation seams

- `backend/handler/scan_handler.py` — PC component detection, scan lifecycle, and automatic DLC linking.
- `backend/handler/metadata/pc_match_handler.py` — validated PC Steam and IGDB candidate collection.
- `backend/handler/metadata/steam_handler.py` — Steam Storefront lookup and localization behavior.
- `backend/endpoints/sockets/scan.py` — scan progress and PC DLC enrichment socket flow.
- `backend/endpoints/roms/pc_metadata.py` — manual-safe parent and component metadata selection endpoints.
- `frontend/src/v2/components/Dialogs/MatchRomDialog.vue` — existing manual matching UI and event contract.
- `frontend/src/v2/components/GameDetails/PcComponents.vue` — PC component presentation and manual-match entry point.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `ScanHandler` and its PC component lifecycle can discover newly indexed main
  games and local DLC components.
- `PcMetadataMatchHandler` already validates Steam and IGDB candidates before
  metadata persistence.
- The v2 `MatchRomDialog` and `PcComponents` event flow supply the existing
  safe manual correction path.

### Established Patterns

- Scans, provider metadata, and owned media are non-destructive to the
  external library.
- Automatic DLC enrichment is fail-closed and must retain IGDB/Steam identity
  safeguards.
- Backend response schemas remain the OpenAPI source of truth for any new
  review-queue API surface.

### Integration Points

- Scheduled scan/RQ orchestration and scan Socket.IO events for recurring
  background discovery and progress.
- PC metadata endpoint and handler layer for queue acceptance and correction.
- Active v2 administration and game-detail surfaces for queue visibility and
  existing manual-match reuse.

</code_context>

<specifics>
## Specific Ideas

- The expected scale is roughly 1,000 PC games, so the normal path cannot
  require opening each game, choosing main game/DLC, and searching manually.
- Main-game folder names can be assumed correct. DLC names can use tolerant
  matching only when there is one clear plausible candidate.
- A periodic scan with a 15-minute production default and a 10-second UAT
  setting is preferred to immediate filesystem watching for NAS/Docker
  reliability.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

_Phase: 22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung_
_Context gathered: 2026-10-01_
