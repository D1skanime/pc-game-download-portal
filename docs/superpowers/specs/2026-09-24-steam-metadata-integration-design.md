# Steam Metadata Integration Design

## Intent

Add the official RomM Steam storefront metadata provider to this PC-focused
fork without replacing IGDB or repurposing SteamGridDB. Steam improves PC game
and safely identified DLC metadata, especially German text. IGDB remains the
relationship authority for DLC detection and the source of PC-specific
structured data such as themes and franchises.

## Scope and boundaries

The port uses the current upstream Steam service, typed payloads, handler,
provider registration, heartbeat, rate limiting, and app-ID persistence as the
baseline. Fork-specific behavior is isolated to localized retrieval and the
existing PC metadata candidate and component application flows.

SteamGridDB keeps the `sgdb` source slug and its artwork-only behavior. Steam
uses the new `steam` source slug and provides structured store metadata.

Steam is automatically eligible only for `win`, `linux`, and `mac`. The fork's
`dos`, `win3x`, and `win9x` platforms are excluded from automatic Steam search
to prevent anachronistic or weak matches. A future explicit Steam App ID tag is
allowed to resolve an intentionally pinned app ID without enabling blind
searches for those platforms.

Classic ROM platforms remain outside the Steam provider path. Adding `steam`
to the global source enum and priority validation must not make a non-PC scan
call Steam.

## Configuration and availability

The provider is enabled only when `STEAM_API_ENABLED=true`. It requires no API
key. The following explicit configuration values are added:

| Environment variable          | Default | Purpose                                                     |
| ----------------------------- | ------- | ----------------------------------------------------------- |
| `STEAM_API_ENABLED`           | `false` | Enables Steam metadata requests.                            |
| `STEAM_API_LANGUAGE`          | `de`    | Preferred Storefront language.                              |
| `STEAM_API_COUNTRY`           | `CH`    | Preferred Storefront region.                                |
| `STEAM_API_FALLBACK_LANGUAGE` | `en`    | Language used only when preferred localized text is absent. |
| `STEAM_API_FALLBACK_COUNTRY`  | `US`    | Region paired with the fallback language.                   |

The service sends the configured language and country to both store search and
app-details requests. For a resolved app, the preferred-language details are
read first. Missing localized textual fields are filled from a fallback details
request only; no empty Steam values overwrite populated provider data.

The upstream request limiter, timeout handling, 429 retries, malformed-payload
handling, and heartbeat remain in place. Provider failures resolve to no Steam
result and never abort IGDB, MobyGames, LaunchBox, or SteamGridDB processing.

## Data model and API contract

Main games follow upstream's established `Rom.steam_id` and
`Rom.steam_metadata` contract. A migration adds equivalent nullable
`steam_id` and JSON `steam_metadata` fields to `RomComponentMetadata`, along
with response-schema serialization where component metadata is exposed.

`steam_metadata` retains the normalized upstream Steam metadata shape and may
hold language provenance needed to make refresh behavior observable. It is not
a replacement for `igdb_metadata`. Existing IDs and metadata from IGDB, Moby,
SteamGridDB, and LaunchBox are preserved.

The metadata source enum, scan-priority validation allowlist, heartbeat
response, provider registry, refresh selection UI, and provider presentation
gain `steam` consistently. The UI labels Steam as Steam and leaves all
SteamGridDB names, IDs, assets, and controls unchanged.

## Matching and merge behavior

For an eligible PC main game, Steam searches the Storefront using the upstream
similarity threshold and store type validation. An explicit Steam App ID is
preferred over a name lookup. Existing Steam IDs are refreshed by ID rather
than replaced by a new filename guess. The match extends the existing ROM; it
never creates a second ROM.

The PC candidate matcher lists Steam beside `igdb`, `moby`, `sgdb`, and
`launchbox`. Applying a Steam candidate resolves its selected app ID to full
details before persistence. A candidate stores only non-empty values and
provider-scoped Steam data.

The display/application merge is field-specific:

| Field group                                                 | Preferred source                                      | Fallback and preservation                                                      |
| ----------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------ |
| Localized title and summary                                 | Steam preferred locale                                | Steam fallback locale, then existing metadata; never overwrite a manual value. |
| Developer, publisher, release date                          | Steam when non-empty and reliable                     | Existing PC/IGDB data stays when Steam omits a field.                          |
| Themes, franchise, related games, DLC relationships         | IGDB                                                  | Steam does not replace them.                                                   |
| Cover and screenshots                                       | Existing artwork priority and explicit selected media | Steam supplies candidates but does not bypass artwork policy.                  |
| `main_developer`, `publishers`, `themes`, `pc_release_date` | Existing Phase-13 structure                           | Steam can fill compatible empty values, not clear or simplify fields.          |

Manual overrides remain authoritative. Existing persistence code must keep its
source and override semantics, and Steam application must use the same guarded
paths rather than direct model writes.

## DLC safety rule

IGDB remains the first and required identity step for automatic DLC enrichment:

1. The parent game's cached IGDB `expansions` and `dlcs` relationships identify
   a candidate.
2. Exactly one related IGDB candidate is hydrated and retained.
3. Only then may Steam search for a DLC store item using that known DLC title.
4. Steam data is applied only for one sufficiently confident DLC result, and,
   where returned by Steam, a relationship to the parent's known Steam App ID
   confirms it.
5. A zero, ambiguous, bundle, soundtrack, edition, or mismatched-parent result
   leaves the existing IGDB DLC metadata unchanged.

No folder-name-only Steam DLC matching is introduced. Steam enriches the same
component row and never creates a component.

## Observability

Steam logs use structured context without payload or secrets: provider, PC
platform, normalized query, app ID when known, selected language, confidence,
and fallback outcome. Disabled, unsupported platform, unavailable Storefront,
rate-limited, empty response, and ambiguous DLC outcomes are distinguishable in
logs and do not become scan-fatal errors.

## Test plan

Tests cover the upstream port and the fork integration:

- Steam source registration, config validation, disabled state, heartbeat,
  timeout/429 degradation, and no API key requirement.
- `win`, `linux`, and `mac` matching, plus no automatic query for classic ROMs,
  `dos`, `win3x`, and `win9x`.
- Preferred German text, partial German payload fallback to English, empty
  Steam fields preserving IGDB values, and persisted Steam App IDs.
- Main-game merge combinations: Steam summary with IGDB themes, Steam release
  with IGDB franchise, Steam publisher with IGDB relationships, and artwork
  priority preservation.
- Manual metadata protection, re-scrape of an existing IGDB game, and no
  duplicate ROM creation.
- Existing IGDB DLC discovery, a single safe Steam DLC enrichment, German DLC
  fallback, missing Steam DLC retention of IGDB values, ambiguous result
  refusal, and parent mismatch refusal.
- Backend unit and endpoint suites, migration upgrade/downgrade checks,
  frontend type generation and typecheck when API schema changes, and relevant
  frontend tests for provider labels or refresh selection.

## Upstream compatibility record

The initial port tracks upstream RomM commit
`eaba9c70d1ef462022c7b4a1ab9846ddb214b66c` at the time of design. Directly
ported concepts and files are the Steam service, Steam typed payloads, Steam
handler, Steam enable flag, metadata source registration, heartbeat, scan
resolution, Rom persistence fields, and their tests. Fork-specific code stays
in localized Steam detail resolution, PC candidate integration, component
metadata persistence, and field-level merge tests.

## Explicit exclusions

This work does not add translation, Steam login, library or ownership sync,
downloads, installation, achievements, cloud functionality, a generic metadata
aggregator, or a new generic matching framework.
