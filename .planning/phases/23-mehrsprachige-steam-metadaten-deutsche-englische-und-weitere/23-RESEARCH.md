# Phase 23: Mehrsprachige Steam-Metadaten - Research

**Researched:** 2026-10-02  
**Domain:** Persisted, locale-aware Steam description variants  
**Confidence:** HIGH

## User Constraints

### Locked Decisions

- If a selected UI language is not stored for a game, show the English Steam description.
- Store multiple available Steam language variants rather than overwriting the single display summary.

### Specific Ideas

- Preserve language provenance such as `de` and `en` for each stored variant.

### Deferred Ideas (OUT OF SCOPE)

- Translating non-Steam providers or operator-authored text.
- Changing artwork, DLC matching, or the Phase 22 review queue.

## Summary

The current Steam path fetches one configured primary locale (`german`) and, only when fields are absent, one English fallback. `SteamHandler._build_rom()` reduces those results to one `name` and one `summary`; `normalize_steam()` then writes that summary into the single display column. The existing `steam_metadata` JSON records only provenance such as `language`, `fallback_language`, and `fallback_fields`. Therefore it cannot retain both German and English descriptions. [VERIFIED: `backend/handler/metadata/steam_handler.py`, `backend/handler/metadata/steam_merge.py`]

Use the already portable JSON ownership boundary, not a new provider or translation service: add a versioned `text_variants` object inside each ROM and PC-component `steam_metadata`, keyed by normalized BCP-47-like base tags (`de`, `en`, ...). Every entry contains only non-empty Steam-owned textual fields and its Steam source language. Fetch the configured language set for the same validated Steam app ID, merge it additively, and never let it overwrite `manual_metadata` or non-Steam provider fields. [VERIFIED: `backend/models/rom.py`, `backend/alembic/versions/0128_add_steam_metadata.py`, `backend/handler/metadata/steam_merge.py`]

**Primary recommendation:** Persist all configured Steam text variants during the normal enrichment/claim path and select the detail-page text client-side from the returned variant map by UI base language, with `en` as the only fallback.

## Architectural Responsibility Map

| Capability                   | Primary tier     | Secondary tier        | Rationale                                                                                                           |
| ---------------------------- | ---------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Fetch and normalize variants | API/backend      | Steam storefront      | Existing typed Steam adapter owns network I/O and validation.                                                       |
| Durable ownership/provenance | Database/storage | API/backend           | `steam_metadata` already accompanies `steam_id` on ROMs and components.                                             |
| Select displayed language    | Browser/client   | API response          | The selected Vue locale is client state, while the detail response already carries the metadata.                    |
| Fallback to English          | Browser/client   | Backend normalization | UI must deterministically choose `selected base tag`, then `en`, then existing summary only when no variants exist. |

## Recommended Data and Flow

```text
Steam app id (already matched/claimed)
  -> appdetails once per configured Steam language, same app id
  -> validate type/id, trim non-empty name/short_description
  -> normalize Steam language to UI base tag
  -> steam_metadata.text_variants = { de: {...}, en: {...}, ... }
  -> normal guarded merge persists JSON for Rom or RomComponentMetadata
  -> DetailedRom response exposes variants
  -> GameDetails / PcDlcDetail selects locale.split('_')[0], else en
```

Recommended JSON contract:

```json
{
  "app_id": 1091500,
  "source": "storefront",
  "text_variants": {
    "de": { "source_language": "german", "name": "...", "summary": "..." },
    "en": { "source_language": "english", "name": "...", "summary": "..." }
  }
}
```

Keep `summary` and `name` as the existing compatibility/display fields. The frontend should prefer a selected Steam variant only when that field is Steam-owned, so manual text and existing non-Steam authoritative values remain unchanged. This preserves the current guarded-merge contract rather than silently making a localized Steam description override an editor. [VERIFIED: `backend/handler/metadata/steam_merge.py`, `backend/tests/handler/metadata/test_steam_merge.py`]

## Standard Stack

No package installation is required. Use Python 3.13, aiohttp through the existing context session, SQLAlchemy `CustomJSON`, FastAPI/Pydantic response schemas, Vue 3, Pinia, and vue-i18n already in the repository. [VERIFIED: `CLAUDE.md`, `.claude/skills/backend-development/SKILL.md`, `frontend/src/locales/index.ts`]

The frontend has 18 selectable locales in `stores/language.ts`; selection must reduce `de_DE` to `de` and `en_US`/`en_GB` to `en`. Steam uses its own request language identifiers such as `german` and `english`, so maintain an explicit, tested mapping rather than assuming either naming system is interchangeable. [VERIFIED: `frontend/src/stores/language.ts`, `backend/config/__init__.py`, `backend/handler/metadata/steam_handler.py`]

## Architecture Patterns

### 1. Bounded configuration, not browser-triggered provider calls

Add one explicit ordered configuration value for stored Steam text languages, defaulting to the current primary language plus English. De-duplicate it after canonicalization and cap it to the supported application UI locales. Each enrichment fetches that bounded set for the same `steam_id`; malformed, unavailable, or empty responses are no-ops for that variant. Do not call Steam when a browser language changes. The existing client has retry/rate limiting at 0.6 requests/sec, so unbounded per-locale scans would make a bulk scan impractically slow. [VERIFIED: `backend/adapters/services/steam.py`, `backend/handler/metadata/steam_handler.py`]

### 2. Additive provenance merge

`normalize_steam()` should merge `text_variants` with prior valid entries, replace only the incoming language's Steam-owned entry, and retain existing variants when one language fetch fails. Preserve existing `fields`, `fallback_fields`, genres, categories, media, and manual protections. Apply the same helper to `Rom` and `RomComponentMetadata`, because both currently carry independent `steam_id` and `steam_metadata`. [VERIFIED: `backend/models/rom.py`, `backend/handler/metadata/pc_steam_enrichment.py`, `backend/handler/metadata/pc_automation.py`]

### 3. Detail-only presentation selection

Expose the variant map in the existing generated API types. Add a small pure frontend resolver with exhaustive tests: selected language first, English second, then the legacy persisted string. Use it in both parent `GameDetails` and `PcDlcDetail`, which currently read `summary` directly. Avoid altering list/search payload semantics unless a visible list use requires localized descriptions. [VERIFIED: `backend/endpoints/responses/rom.py`, `frontend/src/v2/views/GameDetails.vue`, `frontend/src/v2/components/GameDetails/PcDlcDetail.vue`]

## Don't Hand-Roll

| Problem            | Do not build                           | Use instead                                                             |
| ------------------ | -------------------------------------- | ----------------------------------------------------------------------- |
| Translation        | Machine translation or guessed strings | Steam's localized `appdetails` response, persisted as source text       |
| Locale matching    | Region-specific duplication            | One tested base-language resolver (`de_DE -> de`) plus English fallback |
| New metadata store | Separate translation/provider tables   | Existing `steam_metadata` JSON ownership boundary                       |
| Provider retry     | New HTTP client or browser fetches     | Existing `SteamService` rate limiter/retry behavior                     |

## Common Pitfalls

1. **Treating English fallback as a replacement.** Current fallback is conditional only for missing primary fields. Phase 23 must retain both non-empty responses, not collapse to one `summary`. Test primary and English descriptions that both exist. [VERIFIED: `backend/handler/metadata/steam_handler.py`]
2. **Overwriting manual/provider text.** The visible field selection must honour `manual_metadata` and the current Steam ownership `fields` mechanism. Test manual title/summary and non-Steam summary preservation. [VERIFIED: `backend/handler/metadata/steam_merge.py`]
3. **Mixing locale formats.** UI tags use underscores and Steam values are English words. A single mapping/canonicalizer must reject blank/unknown keys and prevent duplicate `en_US`/`en_GB` storage. [VERIFIED: `frontend/src/stores/language.ts`, `backend/config/__init__.py`]
4. **Leaking response size into gallery scans.** Variant payload is most useful on the single-ROM detail response. Keep scans bounded and verify list endpoint performance/shape remains compatible. [ASSUMED]
5. **Breaking portable upgrades.** JSON migration changes must work on MariaDB, MySQL, and PostgreSQL, and downgrade cleanly, per repository migration policy. [VERIFIED: `.claude/skills/backend-development/SKILL.md`]

## Validation Architecture

| Behavior                                                                           | Test type       | Location / command                                     |
| ---------------------------------------------------------------------------------- | --------------- | ------------------------------------------------------ |
| Fetches German and English for same app ID, retains both                           | async unit      | `backend/tests/handler/metadata/test_steam_handler.py` |
| Additive JSON merge, malformed/missing locale non-destructive, manual preservation | unit            | `backend/tests/handler/metadata/test_steam_merge.py`   |
| Parent and DLC response expose variants                                            | schema/endpoint | response schema tests adjacent to ROM endpoint tests   |
| `de_DE -> de`, English fallback, legacy fallback                                   | Vitest          | new resolver test beside GameDetails utility/component |
| UI language switch updates parent and DLC description                              | browser UAT     | isolated Docker fixture only, no NAS or real library   |

Run focused backend tests through `cd backend && uv run pytest ...`, frontend unit tests through `cd frontend && npm run test`, then regenerate types if response schemas change and run `npm run typecheck`. Finish with `trunk fmt && trunk check`. [VERIFIED: `CLAUDE.md`, `.claude/skills/backend-development/SKILL.md`]

## Security Domain

| Area               | Control                                                                                                  |
| ------------------ | -------------------------------------------------------------------------------------------------------- |
| Input validation   | Accept only configured, canonical language identifiers and non-empty strings from typed Steam responses. |
| Provider isolation | Keep existing rate limit, retries, and no-op behavior for failed Steam requests.                         |
| Access control     | Reuse existing ROM detail authorization, do not add a public provider endpoint.                          |
| Data integrity     | Do not mutate the source library; only RomM-owned database JSON changes.                                 |

## Project Constraints (from AGENTS.md)

- Work only in `/home/d1sk/romm` on the canonical Linux checkout, preserve unrelated changes, and never access the real NAS/Team4s for this phase.
- Keep endpoints thin and use the backend handler, typed adapter, model, response-schema, migration, generated-type, and test conventions.
- New user-visible frontend strings require all locale files and i18n parity/sort checks; avoid them if this phase can reuse existing strings.
- Do not add secrets, do not bypass hooks, and use Trunk for formatting/linting.

## Open Questions

None blocking. The plan should define the bounded default language list as current configured primary locale plus English, and make additional stored Steam locales an explicit operator configuration rather than attempting every Steam locale during every scan.

## Sources

- [VERIFIED: `backend/handler/metadata/steam_handler.py`] Current language fetch, fallback, and result collapse.
- [VERIFIED: `backend/handler/metadata/steam_merge.py`] Existing provider/manual ownership protections.
- [VERIFIED: `backend/models/rom.py`, `backend/alembic/versions/0128_add_steam_metadata.py`] ROM and component persistence boundary.
- [VERIFIED: `frontend/src/stores/language.ts`, `frontend/src/v2/views/GameDetails.vue`, `frontend/src/v2/components/GameDetails/PcDlcDetail.vue`] UI locale and existing description presentation.
- [VERIFIED: `docs/superpowers/specs/2026-10-01-steam-supplemental-metadata-and-dlc-design.md`] Existing Steam provenance and non-destructive enrichment scope.

## Assumptions Log

| #   | Claim                                                                               | Risk if wrong                                                                |
| --- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| A1  | Returning variants only on detail responses avoids meaningful gallery payload cost. | Planner may need a response projection if summaries are used in a list view. |
