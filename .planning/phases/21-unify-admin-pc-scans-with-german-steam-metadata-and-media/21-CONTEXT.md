# Phase 21: Unify admin PC scans with German Steam metadata and media - Context

**Gathered:** 2026-09-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Make administrator-triggered scans for eligible Windows, Linux, and macOS PC games use the same guarded Steam enrichment as targeted-ROM scans: German-first text, same-App-ID English fallback, and idempotent Steam-media reconciliation. The change covers new games and existing games in `update` and `complete` scans, without modifying the external source library.

</domain>

<decisions>
## Implementation Decisions

### Shared enrichment and localization

- **D-01:** Both administrator and targeted-ROM PC scans call one shared enrichment boundary. It receives scan type, current ROM state, platform, filesystem name, selected providers, and scan context; it returns a normalized patch and never mutates ORM state directly.
- **D-02:** For an eligible Steam-enabled PC scan, use a persisted valid Steam App ID when present; otherwise allow one normalized-name resolution. Resolve German details first and fetch English only for fields missing from the German payload of that same App ID. Never perform a second broad name search after an App ID is selected.
- **D-03:** Apply the same behavior to newly discovered games and to existing games processed by `update` or `complete`. Keep quick, hash-only, classic-ROM, and excluded-platform behavior unchanged unless it already enters the eligible shared PC path.

### Provenance, manual fields, and provider authority

- **D-04:** Existing Steam provenance decides which earlier Steam-owned display fields may refresh. Manually entered title, summary, developer, publisher, release date, and selected artwork remain authoritative and unchanged.
- **D-05:** Steam may enrich localized title, summary, developer, publisher, release data, cover candidates, and screenshot candidates. IGDB remains authoritative for themes, franchises, related-game relationships, and DLC discovery; this phase does not change Steam DLC identity rules.
- **D-06:** Unavailable, malformed, ambiguous, invalid, or rate-limited Steam responses produce an empty patch and must not erase text, media, placement, or metadata from Steam or another provider.

### Steam media reconciliation and placement

- **D-07:** Treat Steam cover and screenshot URLs as provider candidates. Reconcile them idempotently by trusted provider origin and canonical source URL; a refresh may tombstone vanished provider candidates but never deletes RomM-owned uploads.
- **D-08:** Automatic placement is allowed only on unclaimed surfaces: a preferred Steam cover may fill overview and Steam screenshots may fill background using the existing ordering rules. Manual overview/background placement, user uploads, and explicit provider selections are never replaced, removed, or reordered by scans.
- **D-09:** Reconciled Steam candidates remain visible and editable through the Phase 20 Media interface.

### Verification and operational boundary

- **D-10:** Focused tests must prove scan-path parity, German-first fallback, new/update/complete coverage, manual protection, automatic placement only for unclaimed surfaces, failure isolation, platform gating, and idempotent provider-media reconciliation that leaves uploads untouched.
- **D-11:** Browser UAT uses only the isolated Witcher-style fixture and covers a new game, existing refresh, German Steam text, automatic media, manual override protection, and absence of source-library mutation.
- **D-12:** Do not access a NAS mount, alter Team4s, use Docker Compose, or write to external source-library paths as part of this phase.

### Claude's Discretion

- Choose the smallest seam-compatible API and helper decomposition that reuses `SteamHandler`, `normalize_steam`, the existing PC matching path, and Phase 20 owned-media reconciliation.
- Select focused fixtures and assertions that distinguish the scan policy from the unrelated dev/UAT deployment differences.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase design and predecessor decisions

- `docs/superpowers/specs/2026-09-29-admin-pc-scan-steam-parity-design.md` — authoritative Phase 21 behavior, safety boundary, media policy, validation, and exclusions.
- `.planning/phases/18-steam-metadata-integration-f-r-pc-games-und-dlcs/18-CONTEXT.md` — Steam provider, localization, provenance, and DLC-safety decisions to preserve.
- `.planning/phases/19-fix-pc-quick-scan-igdb-matching-and-safe-dlc-expansion-enric/19-CONTEXT.md` — PC-only matching and IGDB-first component/DLC constraints.
- `.planning/phases/20-media-management-and-owned-soundtrack-uploads/20-CONTEXT.md` — provider-media, uploads, placement, and external-source-library safety rules.

### Codebase patterns

- `.planning/codebase/ARCHITECTURE.md` — endpoint-to-handler layering, scan path, ROM identity, and filesystem safety constraints.
- `.planning/codebase/INTEGRATIONS.md` — Steam and SteamGridDB integration boundaries and configuration context.
- `.planning/codebase/STACK.md` — backend/frontend tooling and test commands.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `backend/handler/metadata/steam_handler.py` and `backend/adapters/services/steam.py`: existing Steam App-ID resolution and localized-details acquisition.
- `backend/handler/metadata/steam_merge.py::normalize_steam`: guarded, non-empty Steam patch construction with provenance and media candidates.
- `backend/handler/metadata/pc_match_handler.py`: current PC-provider matching and Steam DLC safety boundary.
- `backend/handler/metadata/rom_media.py` plus Phase 20 owned-media models/endpoints: reconciliation and presentation surfaces for provider candidates and RomM-owned uploads.
- `frontend/src/v2/components/GameDetails/MediaTab.vue`, `ArtworkSubtab.vue`, and `ScreenshotsSubtab.vue`: existing operator review and override path for reconciled media.

### Established Patterns

- Keep scanning and metadata behavior in handlers; endpoints and frontend are not the correct place for scan policy.
- Metadata adapters return normalized provider data; guarded persistence/reconciliation applies it after provider calls succeed.
- One logical `Rom` owns provider metadata and media candidates; user files remain owned storage and are distinct from external source-library bytes.

### Integration Points

- Administrator scan orchestration must use the same PC enrichment seam as the targeted-ROM scan.
- The resulting Steam media candidates must flow through existing owned-media reconciliation and placement policy, then be rendered by the v2 Media UI without a parallel media model.

</code_context>

<specifics>
## Specific Ideas

- The isolated Witcher-style fixture is the browser-UAT reference case; it must not depend on a dev or UAT server having identical data.
- The work follows the already integrated Phase 18–20 Steam and owned-media behavior rather than introducing a new provider or media transport.

</specifics>

<deferred>
## Deferred Ideas

- Steam login, ownership, installation, or library synchronization.
- Translation changes for non-Steam providers and changes to Steam DLC identity/relationship rules.
- Any NAS, Team4s, Docker Compose, or external source-library operation.

### Reviewed Todos (not folded)

- `2026-09-03-fix-pc-dlc-notes-soundtrack-and-artwork-uploads.md` — only overlaps on media terminology; its DLC notes/soundtrack/upload scope is not part of administrator Steam scan parity and remains deferred.

</deferred>

---

_Phase: 21-unify-admin-pc-scans-with-german-steam-metadata-and-media_
_Context gathered: 2026-09-30_
