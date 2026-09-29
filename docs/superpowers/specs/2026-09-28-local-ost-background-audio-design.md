# Local and Owned OST Background Audio Design

## Goal

Let an operator select locally scanned GOG soundtrack tracks and RomM-uploaded
soundtrack tracks as a game's background audio. When the user opens that
game's detail page, one selected track is chosen at random and plays alongside
the selected visual background.

The feature reads original OST files in the game library and separately reads
RomM-owned uploaded audio. It never copies, uploads, modifies, or deletes an
original library file.

## Scope

- Recognize `ost` as an alias for the existing `soundtrack` directory category
  during scans, in addition to `soundtrack` and `soundtracks`.
- Show locally scanned soundtrack files in `Media > Soundtrack` as read-only
  candidates.
- Let an operator mark or unmark each local track as background audio.
- Let an operator mark or unmark each active RomM-owned soundtrack candidate
  as background audio, independent of its inclusion in the manual soundtrack
  queue.
- Persist the selection per ROM and keep it valid only while its source
  `RomFile` exists and remains categorized as a soundtrack.
- Persist an owned-track selection only when the owned media candidate belongs
  to the ROM and has the `soundtrack` role. A later inactive candidate may
  retain its historical selection row, but is never eligible for playback.
- Randomly choose one selected, valid local or active owned track from one
  unified candidate collection when the user enters that ROM's detail route.
  Each candidate has equal probability regardless of origin. Stop playback
  when leaving the route or entering another ROM.

Out of scope: metadata lookup, changes to legacy source-writing soundtrack
routes, and automatic playback outside a ROM detail page. The existing
Media-tab audio player and its ordered manual soundtrack queue remain separate
from background-audio selection.

## Data Model

Keep the dedicated local-background-audio placement table. Each row contains a
ROM id and a `RomFile` id, with a uniqueness constraint for the pair and a
foreign key cascade when either record is removed. It is intentionally
separate from `rom_owned_media_placements`: the latter requires a
RomM-owned resource, while these rows point to immutable source-library files.

Add a dedicated owned-background-audio placement table. Each row contains a
ROM id and a `RomOwnedMedia` id, with a uniqueness constraint for the pair and
foreign key cascades. It is separate from `rom_owned_media_placements` because
the latter describes display and manual-playlist surfaces, while this relation
describes detail-page background playback. It is also separate from local
selection because a source `RomFile` and a RomM-owned candidate have different
lifecycles and protected content routes.

The database handler validates all mutations atomically:

1. The ROM's version matches the request's expected version.
2. Each selected resource belongs to that ROM.
3. A local file category is `soundtrack`, while an owned media candidate is
   active and has the `soundtrack` role.
4. The caller's requested set contains no duplicates.

The detailed ROM response exposes selected local soundtrack file ids and
selected owned soundtrack media ids. The existing `files` and `owned_media`
responses provide the immutable name, role, state, and protected content
identity required by the UI. The UI filters invalid or inactive persisted
selections before building the unified playback collection.

## API and Authorization

Add read/write operations for the owned selection under the protected
parent-ROM media namespace. They use the same visibility checks,
`roms.read`/`roms.write` scopes, optimistic-version checks, and authoritative
detailed-ROM response pattern as current media placement mutations. They mutate
only the owned-background-audio relation; local selection retains its existing
route and contract.

No endpoint writes to the game library. Local playback uses the existing
protected ROM-file content route and owned playback uses the protected owned
media content route, so access control and read-only storage policy stay in
effect.

## UI and Playback

`Media > Soundtrack` contains a read-only local-OST list and RomM-owned
soundtrack candidates. A local or owned track has one independent background
action:

- `Use as background music`
- `Do not use as background music`

Selected tracks have a visible background-music badge. The existing owned
soundtrack upload, manual inclusion, ordering, player, download, and deletion
flow remains unchanged. Selecting a background track neither adds it to nor
removes it from the manual soundtrack queue.

On navigation to a ROM detail page, the view derives selected local and active
owned tracks from the detailed ROM, combines them into one collection, randomly
selects one unified candidate with equal per-candidate probability, and gives
its protected content URL to a dedicated hidden background-audio element. It
uses the same lifecycle cleanup as visual background rotation and does not use
the interactive soundtrack player or its mini-player. On route leave,
selected-ROM change, failed fetch, empty selection, or an audio
decoding/autoplay failure, it stops and clears the audio state. Browser autoplay
restrictions may leave the page silent by design; no fallback play control is
rendered.

## Error Handling

The Media action refreshes the authoritative ROM after success. A `409` from a
stale version refreshes state and presents the existing conflict feedback. A
missing, reclassified, or cross-ROM local file is rejected by the server. A
scan that removes a local track cascades its selection. An inactive owned track
is ignored for playback and cannot be newly written by a replacement request;
its historical selection row may remain. Physical deletion of an owned track
cascades its selection, so a later page load cannot try to play a stale path.

## Verification

- Backend tests cover `ost` categorization, safe local and owned selection
  mutations, cross-ROM rejection, role/category rejection, inactive-write
  rejection, optimistic conflicts, and physical-delete cascade behavior.
- Endpoint tests cover visibility, scopes, and response hydration.
- Frontend tests cover local and owned candidate selected-state rendering,
  mutation recovery, one combined equal-probability random candidate
  collection that ignores inactive owned tracks, route cleanup, and the
  absence of source-library mutation calls.
- Run migration upgrade/downgrade checks plus backend tests, frontend Vitest,
  typecheck, locale parity/sorting when copy is added, and Trunk checks.
