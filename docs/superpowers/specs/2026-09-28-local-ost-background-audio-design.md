# Local OST Background Audio Design

## Goal

Let an operator select locally scanned GOG soundtrack tracks as a game's
background audio. When the user opens that game's detail page, one selected
track is chosen at random and plays alongside the selected visual background.

The feature reads the original OST files in the game library. It never copies,
uploads, modifies, or deletes them.

## Scope

- Recognize `ost` as an alias for the existing `soundtrack` directory category
  during scans, in addition to `soundtrack` and `soundtracks`.
- Show locally scanned soundtrack files in `Media > Soundtrack` as read-only
  candidates.
- Let an operator mark or unmark each local track as background audio.
- Persist the selection per ROM and keep it valid only while its source
  `RomFile` exists and remains categorized as a soundtrack.
- Randomly choose one selected local track when the user enters that ROM's
  detail route, and stop it when leaving the route or entering another ROM.

Out of scope: copying tracks to owned resources, metadata lookup, a Media-tab
audio player, playlist ordering, changes to legacy source-writing soundtrack
routes, and automatic playback outside a ROM detail page.

## Data Model

Add a dedicated local-background-audio placement table. Each row contains a
ROM id and a `RomFile` id, with a uniqueness constraint for the pair and a
foreign key cascade when either record is removed. It is intentionally
separate from `rom_owned_media_placements`: the latter requires a
RomM-owned resource, while these rows point to immutable source-library files.

The database handler validates all mutations atomically:

1. The ROM's version matches the request's expected version.
2. The `RomFile` belongs to that ROM.
3. The file category is `soundtrack`.
4. The caller's requested set contains no duplicates.

The detailed ROM response exposes the selected local soundtrack file ids. The
existing `files` response already provides the immutable name, category, and
content identity required by the UI.

## API and Authorization

Add read/write operations under the protected parent-ROM media namespace.
They use the same visibility checks, `roms.read`/`roms.write` scopes, optimistic
version checks, and authoritative detailed-ROM response pattern as current
media placement mutations. They mutate only the new database relation.

No endpoint writes to the game library. Playback uses the existing protected
ROM-file content route, so access control and read-only storage policy stay in
effect.

## UI and Playback

`Media > Soundtrack` contains a read-only local-OST list. A track has one
clear action:

- `Use as background music`
- `Do not use as background music`

Selected tracks have a visible background-music badge. There is no play,
pause, upload, download, sorting, or deletion control for local OST entries.
The existing owned-soundtrack upload flow remains unchanged.

On navigation to a ROM detail page, the view derives the selected local tracks
from the detailed ROM, randomly selects one, and gives its protected file URL
to a dedicated hidden background-audio element. It uses the same lifecycle
cleanup as visual background rotation and does not use the interactive
soundtrack player or its mini-player. On route leave, selected-ROM change,
failed fetch, empty selection, or an audio decoding/autoplay failure, it stops
and clears the audio state. Browser autoplay restrictions may leave the page
silent by design; no fallback play control is rendered.

## Error Handling

The Media action refreshes the authoritative ROM after success. A `409` from a
stale version refreshes state and presents the existing conflict feedback. A
missing, reclassified, or cross-ROM file is rejected by the server. A scan
that removes a track cascades the selection row, so a later page load cannot
try to play a stale path.

## Verification

- Backend tests cover `ost` categorization, safe selection mutation,
  cross-ROM rejection, category rejection, optimistic conflicts, and cascade
  behavior.
- Endpoint tests cover visibility, scopes, and response hydration.
- Frontend tests cover candidate and selected-state rendering, mutation
  recovery, random selection only from marked local tracks, route cleanup, and
  the absence of source-library mutation calls.
- Run migration upgrade/downgrade checks plus backend tests, frontend Vitest,
  typecheck, locale parity/sorting when copy is added, and Trunk checks.
