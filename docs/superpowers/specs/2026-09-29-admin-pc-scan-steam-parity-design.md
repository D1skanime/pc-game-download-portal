# Admin PC Scan Steam Parity Design

## Purpose

Phase 21 makes an administrator-triggered PC scan use the same complete Steam
metadata pipeline as a targeted ROM scan. For eligible Windows, Linux, and macOS
PC games, Steam data is requested in German first and falls back to English only
for missing fields of the same resolved Steam App ID.

The phase repairs both newly discovered games and existing games processed by
the `update` or `complete` scan types. It never modifies the external source
library.

## User-visible behavior

When Steam is enabled and selected for an eligible PC scan:

1. A new matching game receives the German Steam title, summary, developer,
   publisher, and release data where Steam provides them.
2. An existing game processed by `update` or `complete` receives the same
   refresh behavior.
3. A field that an operator manually set remains unchanged.
4. Steam cover and screenshot candidates are reconciled into the RomM-owned
   media catalog.
5. Steam media is automatically placed on the overview or background only if
   that surface has no manual selection. An operator's later manual placement
   takes precedence over every later scan.
6. An unavailable, malformed, ambiguous, or rate-limited Steam response does
   not erase existing text, media, placement, or metadata from any other
   provider.

## Architecture

Introduce one shared PC scan enrichment boundary. Both the administrator scan
and targeted-ROM scan provide it the scan type, current ROM state, platform,
filesystem name, selected providers, and scan context. The boundary returns a
normalized patch, not ORM mutations.

The boundary reuses the existing Steam resolution and `normalize_steam` rules:

```text
Admin scan or targeted ROM scan
  -> shared PC enrichment boundary
  -> Steam lookup by stored ID, otherwise one normalized name search
  -> German details for resolved App ID
  -> English details only for missing fields of that App ID
  -> normalized text patch plus Steam media candidates
  -> guarded database reconciliation and placement policy
```

The existing Steam metadata provenance remains the authority for deciding which
previously Steam-owned display fields may be refreshed. Manual metadata remains
authoritative. IGDB remains authoritative for themes, franchises, related-game
relationships, and DLC discovery.

## Provider-media policy

Steam cover and screenshot URLs are provider candidates, not arbitrary direct
asset writes. Reconciliation is idempotent and keyed by trusted provider origin
and canonical source URL. A rescan updates provider candidates and can tombstone
vanished candidates without deleting RomM uploads.

Automatic placement is deliberately narrow:

- A manual overview or background placement is never changed by a scan.
- With no manual placement, the preferred Steam cover may fill the overview
  surface and Steam screenshots may fill the background surface according to
  the existing ordering rules.
- The selected candidate is still visible and editable in the Phase 20 media
  interface.
- Existing user uploads and explicit provider selections are not deleted or
  reordered by automatic Steam refresh.

## Scan eligibility and safety

The shared step runs only when Steam is selected and enabled, and only on the
already supported Steam PC platforms. New games may resolve by normalized name;
existing games use their persisted Steam ID when available. `update` and
`complete` runs perform the same enrichment. Quick, hash-only, classic-ROM,
and excluded-platform behavior remains unchanged unless it already invokes the
same eligible PC enrichment path.

All lookup errors degrade to an empty Steam patch. The handler must not create
source files, write source paths, or make a second broad name search after an
App ID has been selected.

## Validation

Focused automated coverage must prove:

- admin and targeted PC scans produce the same normalized Steam patch;
- German text wins over English fallback and fallback fills only absent German
  values;
- a new eligible PC game receives Steam text and reconciled media;
- `update` and `complete` refresh an existing eligible PC game;
- manual text and manual media placement survive every refresh;
- automatic Steam placement is created only for unclaimed surfaces;
- Steam failure, ambiguity, and invalid media leave existing state untouched;
- unsupported platforms never call Steam;
- provider-media reconciliation is idempotent and does not affect uploads.

The browser UAT uses the isolated Witcher-style fixture only. It verifies a new
PC game and an existing refreshed game, German Steam text, automatic media,
manual override protection, and no source-library mutation.

## Out of scope

- Translating non-Steam providers.
- Steam login, ownership, installation, or library synchronization.
- Changes to Steam DLC identity and relationship rules.
- Replacing manually selected artwork, backgrounds, or metadata.
- Any NAS, Team4s, Docker Compose, or external source-library change.
