# Phase 20: Media management and owned soundtrack uploads - Research

**Researched:** 2026-09-28
**Domain:** RomM-owned game media, media selection state, safe uploads, and browser soundtrack playback
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

### Provider screenshot management

- Show provider screenshots in Media as candidates for the overview.
- The operator can deselect a provider screenshot from the overview or delete
  it permanently from RomM-owned media storage.
- A normal scan must not restore a deleted provider asset.
- An explicit full-media refresh restores the complete provider candidate set.

### Artwork and backgrounds

- Show provider artwork candidates in Media.
- Permit artwork and screenshot candidates to be selected as backgrounds.
- Permit uploads of operator-owned artwork to RomM-owned storage only.
- Support multiple chosen backgrounds, rotating with smooth transitions that
  respect reduced-motion preferences.

### Soundtrack

- Support only manual uploads to RomM-owned storage in this phase.
- Accept MP3, AAC, FLAC, OGG, OPUS, M4A, and WAV.
- Let the operator include and order playable tracks per game using the
  existing player.
- Do not crawl SteamGridDB or another external audio provider, and do not add
  automatic track metadata enrichment.

### Safety

- Never rename, move, delete, or otherwise write to the external source
  library.
- Keep provider media and the user-selected display state separate.

### the agent's Discretion

- Choose data model, endpoints, component composition, and migration design
  that preserve existing v2 and owned-storage patterns.
- Choose focused UAT fixtures and test coverage for refresh, deletion,
  selection, upload, ordering, and reduced-motion behavior.

### Deferred Ideas (OUT OF SCOPE)

- Automatic soundtrack metadata and external audio providers.
- The unresolved Steam localized-summary overwrite defect; it is tracked as a
  separate scan/merge bug and is out of this phase.
  </user_constraints>

## Project Constraints (from AGENTS.md)

- Work only in `/home/d1sk/romm` on the Linux checkout; preserve unrelated changes and do not access a NAS mount or alter Team4s. [VERIFIED: codebase grep]
- New backend behavior follows endpoint to handler to database/filesystem layers, uses protected routes and managed sessions, and carries focused tests. [VERIFIED: codebase grep]
- Database migrations must work on MariaDB, MySQL, and PostgreSQL. A changed API schema or route requires OpenAPI client generation and a frontend typecheck. [VERIFIED: codebase grep]
- New v2 work stays in `frontend/src/v2/`, uses existing `R*` primitives, strict TypeScript, tokens, `useCan`, `useConfirm`, `useSnackbar`, universal input, and translated locale strings. [VERIFIED: codebase grep]
- Destructive actions require confirmation, with Cancel initially focused. Source-library filesystem actions would require typed confirmation, but this phase must expose no source-library mutation action. [VERIFIED: codebase grep]
- UI verification includes both themes, all input modalities, responsive breakpoints, reduced motion, and browser testing. [VERIFIED: codebase grep]
- Documentation and code are English and must not use em dashes. Run `trunk fmt && trunk check`; never bypass hooks. [VERIFIED: codebase grep]

## Summary

Phase 20 must introduce a first-class RomM-owned media catalog for a game. The current `path_screenshots` and `merged_screenshots` fields only expose a flat, downloaded provider list, while v2 derives a selected background from component-local media and the current soundtrack UI derives its playlist from `RomFile` rows. Neither represents provider provenance, permanent deletion, explicit restore, display selection, background ordering, or an owned audio track. [VERIFIED: codebase grep]

The existing component-owned media pattern is useful for storage, protected read endpoints, optimistic updates, and cleanup, but it is intentionally limited to DLC components. Reusing it for the parent game would incorrectly bind Phase 20 media to a DLC-only route and lifecycle. Create parent-ROM owned-media tables and endpoints instead, using the same owned resources descriptor and transactional cleanup pattern. [VERIFIED: codebase grep]

The legacy soundtrack routes must not be wired into v2. Their upload route authorizes `SIDECAR_WRITE` on `legacy_external_storage`, creates `<rom>/soundtrack`, and their delete route authorizes deletion against that storage. That violates the phase's immutable-source boundary before any UI choice can make it safe. [VERIFIED: codebase grep]

**Primary recommendation:** introduce a parent-ROM owned-media catalog with durable provider tombstones and separate ordered placements; build all Phase 20 reads, uploads, deletes, selections, refreshes, background rotation, and playback from it, while leaving the legacy source-writing soundtrack routes unused. [VERIFIED: codebase grep]

## Architectural Responsibility Map

| Capability                                          | Primary Tier       | Secondary Tier     | Rationale                                                                                                                                                        |
| --------------------------------------------------- | ------------------ | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Provider candidate inventory and permanent deletion | Database / Storage | API / Backend      | Candidate provenance, owned path, and tombstone state must survive scans and browser sessions. [VERIFIED: codebase grep]                                         |
| Explicit full-media refresh                         | API / Backend      | Database / Storage | Provider discovery and owned-resource downloads happen server-side, then merge into the catalog transactionally. [VERIFIED: codebase grep]                       |
| Media selection and ordered placements              | Database / Storage | API / Backend      | Overview selection, background rotation, and soundtrack order are durable game state, not a browser preference. [VERIFIED: codebase grep]                        |
| Artwork and audio upload validation                 | API / Backend      | Database / Storage | The server must authenticate, validate bytes and type, assign an owned name, and write only through the owned descriptor. [VERIFIED: codebase grep]              |
| Media management UI                                 | Browser / Client   | API / Backend      | Media is the operator surface and calls typed protected APIs, but cannot enforce source immutability itself. [VERIFIED: codebase grep]                           |
| Background rotation and reduced-motion behavior     | Browser / Client   | Database / Storage | The client consumes the ordered selected-background list and the existing two-layer backdrop; persistence only supplies ordered URLs. [VERIFIED: codebase grep]  |
| Soundtrack queue and playback                       | Browser / Client   | API / Backend      | The existing Pinia player owns the persistent audio element and queue mechanics; the backend supplies owned tracks and inline content. [VERIFIED: codebase grep] |

## Standard Stack

### Core

| Library / facility                                               |                      Version | Purpose                                                                      | Why Standard                                                                                                                                                                                                                  |
| ---------------------------------------------------------------- | ---------------------------: | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FastAPI `UploadFile`, `File`, `Form`                             | existing FastAPI `~=0.134.0` | Multipart upload routes with typed companion fields                          | The project already uses this endpoint pattern for component media; FastAPI documents `UploadFile` as a spooled async file interface. [VERIFIED: codebase grep] [CITED: https://fastapi.tiangolo.com/tutorial/request-files/] |
| SQLAlchemy 2.0 plus Alembic                                      |  existing `~=2.0` / `~=1.16` | Parent media catalog, tombstones, placements, and migration                  | This is the repository's ORM and migration path across all supported databases. [VERIFIED: codebase grep]                                                                                                                     |
| Owned resources descriptor and `FSResourcesHandler`              |    existing project facility | All stored provider copies, uploaded images, and uploaded audio              | Existing component media writes and reads use this descriptor, not the external ROM handler. [VERIFIED: codebase grep]                                                                                                        |
| Pillow                                                           |            existing `~=12.3` | Decode and verify uploaded artwork bytes                                     | Existing owned component upload validation trusts decoded image content rather than a browser MIME claim. [VERIFIED: codebase grep]                                                                                           |
| Mutagen                                                          |            existing `~=1.47` | Existing local audio type/tag helpers when needed for safe format inspection | It is already used by `utils/audio_tags.py`; do not add a provider or enrichment integration. [VERIFIED: codebase grep]                                                                                                       |
| Vue 3, Pinia, existing `useSoundtrackPlayer` and `BackgroundArt` |      existing frontend stack | Management UI, queue, media controls, and smooth backdrop cross-fade         | Both player and two-layer background infrastructure already exist and should be extended rather than duplicated. [VERIFIED: codebase grep]                                                                                    |

### Supporting

| Facility                                                         | Purpose                                                       | When to Use                                                                                                                                                                                      |
| ---------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `RDropzone` and `storeUpload`                                    | Native file selection, drag/drop, upload progress feedback    | Artwork and soundtrack upload controls. [VERIFIED: codebase grep]                                                                                                                                |
| `useConfirm`, `useSnackbar`, `useCan`                            | Confirmation, outcome feedback, and permission-gated controls | Provider asset deletion, uploaded-asset deletion, refresh, ordering, and uploads. [VERIFIED: codebase grep]                                                                                      |
| `useReducedMotion` and `@media (prefers-reduced-motion: reduce)` | Respect user and platform motion preference                   | Disable timer-driven rotation and cross-fade animation in reduced-motion mode. [VERIFIED: codebase grep] [CITED: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion] |

### Alternatives Considered

| Instead of                                  | Could Use                                                               | Tradeoff                                                                                                                                                                                                  |
| ------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parent owned-media catalog                  | Overload `Rom.path_screenshots` and `RomFile`                           | Flat path and source-file records cannot preserve provenance, a tombstone, independent placement, or a safe owned audio endpoint. [VERIFIED: codebase grep]                                               |
| New parent media endpoints                  | Existing `/soundtracks` upload/delete routes                            | Existing routes write and delete under the external ROM path, violating locked Safety decisions. [VERIFIED: codebase grep]                                                                                |
| Ordered placement table                     | Store `selected` booleans and order columns directly on every media row | A placement table keeps the provider/upload candidate separate from each presentation purpose and permits one image to be a background without changing its candidate identity. [VERIFIED: codebase grep] |
| Browser-native playback with error feedback | Server-side transcoding                                                 | The scope permits the listed original formats and prohibits adding external audio providers or enrichment; transcoding adds an unneeded encoder, queue, storage, and failure surface. [ASSUMED]           |

**Installation:** None. This phase uses existing dependencies and project facilities. [VERIFIED: codebase grep]

## Architecture Patterns

### System Architecture Diagram

```text
provider metadata / existing downloaded provider assets       operator file
                 |                                                |
                 v                                                v
  explicit full-media refresh only                         upload endpoint
                 |                                                |
                 +---------------------+--------------------------+
                                       v
                   validate bytes, generate server path, write only
                   through OwnedStorageKind.RESOURCES
                                       |
                                       v
                       RomOwnedMedia candidate catalog
              (origin, provider identity, MIME, owned path, tombstone)
                                       |
                  +--------------------+--------------------+
                  |                    |                    |
                  v                    v                    v
       overview placement(s)  background placements    soundtrack placements
       selected/unselected    ordered and enabled       included and ordered
                  |                    |                    |
                  v                    v                    v
          Overview screenshots  AppLayout two-layer     existing Pinia player
                                BackgroundArt rotation  and owned content route

normal scan ------------------------------------------------------------X
does not modify media candidates, tombstones, or placements
```

The explicit refresh may repopulate provider candidates, but it must not merge them through the normal scan media downloader, because normal scans must not resurrect a deleted asset. [VERIFIED: codebase grep]

### Recommended Project Structure

```text
backend/
├── models/rom.py                              # Parent owned-media and placement ORM models/enums
├── alembic/versions/0xxx_parent_rom_media.py  # Portable catalog/placement migration
├── endpoints/roms/media.py                    # Candidate, upload, selection, order, delete, refresh, content routes
├── endpoints/responses/rom.py                 # Typed request/response schemas included by DetailedRom
├── handler/database/roms_handler.py           # Optimistic catalog and placement transactions
├── handler/filesystem/resources_handler.py    # Owned image/audio store and bounded cleanup helpers
├── tests/endpoints/roms/test_media.py         # Auth, ownership, refresh, tombstone, upload, content tests
└── tests/handler/database/test_rom_media.py   # Ordering, stale-version, cleanup and uniqueness tests
frontend/src/
├── services/api/rom.ts                        # Generated/typed media calls after OpenAPI regeneration
├── stores/roms.ts                             # Consume added detailed-ROM media shape
├── stores/soundtrackPlayer.ts                 # Generic owned-track identity, not RomFile-only identity
├── v2/components/GameDetails/MediaTab.vue     # Management composition and refresh action
├── v2/components/GameDetails/ScreenshotsSubtab.vue # Provider candidates and overview selection
├── v2/components/GameDetails/ArtworkSubtab.vue     # Provider/uploaded artwork and background selection
├── v2/components/GameDetails/SoundtrackPanel.vue   # Owned upload, include, order, playback
├── v2/components/AppShell/BackgroundArt.vue        # Consume rotating resolved background list
└── locales/*/rom.json                         # All translated user-facing strings
```

The final file split is discretionary, but the API response must be added to `DetailedRom`, then frontend generated types must be regenerated rather than hand-maintained. [VERIFIED: codebase grep]

### Pattern 1: Candidate state, tombstone, and display placement are independent

**What:** model a persisted candidate record separately from one or more persisted placement records. A provider deletion sets a durable tombstone or leaves a durable deletion record after owned-file removal; removing a placement only changes presentation state. [VERIFIED: codebase grep]

**When to use:** for every provider screenshot/artwork, every uploaded artwork, and every uploaded soundtrack track. [VERIFIED: codebase grep]

**Recommended model:**

```python
# Source: proposed extension of backend/models/rom.py, following
# RomComponentOwnedMedia plus its protected owned-resource endpoints.
class RomOwnedMedia(BaseModel):
    rom_id: Mapped[int]
    kind: Mapped[RomOwnedMediaKind]  # image or audio
    role: Mapped[RomOwnedMediaRole]  # screenshot, artwork, soundtrack
    origin: Mapped[RomOwnedMediaOrigin]  # provider or upload
    provider: Mapped[str | None]
    provider_media_id: Mapped[str | None]
    source_url: Mapped[str | None]
    mime_type: Mapped[str]
    owned_path: Mapped[str | None]
    deleted_at: Mapped[datetime | None]

class RomMediaPlacement(BaseModel):
    rom_id: Mapped[int]
    media_id: Mapped[int]
    surface: Mapped[RomMediaSurface]  # overview, background, soundtrack
    position: Mapped[int]
```

Give provider candidates a unique stable key, preferably `(rom_id, origin, provider, provider_media_id)`. If a provider lacks a stable media ID, derive and persist a stable URL digest during refresh rather than use array index or downloaded filename. [ASSUMED]

**Why:** placement changes cannot accidentally make the media source disappear, and an explicit refresh can restore a deleted provider candidate without treating it as a fresh overview/background selection. This implements the locked provider/display-state boundary. [VERIFIED: codebase grep]

### Pattern 2: Explicit media refresh is reconciliation, normal scan is non-authoritative

**What:** add a dedicated protected `POST /api/roms/{id}/media/refresh` operation that discovers the complete current provider set, downloads/validates it into owned storage, reactivates prior tombstones, upserts candidate provenance, and leaves upload-origin candidates and placements intact. [ASSUMED]

**When to use:** only after an explicit operator action. A normal scan must not call it or mutate owned-media records. [VERIFIED: codebase grep]

**Required merge semantics:**

1. A normal scan preserves the catalog, tombstones, and placements exactly. [VERIFIED: codebase grep]
2. Deleting a provider item removes its owned bytes when present and persists its stable provider identity as deleted. [ASSUMED]
3. Refresh reacquires every provider candidate, including a tombstoned one, but restores it unselected. Existing overview/background/soundtrack placement is not inferred from provider order. [ASSUMED]
4. Refresh does not delete operator-uploaded assets and does not reorder a user-curated background or soundtrack placement. [ASSUMED]

### Pattern 3: Owned upload, content, and cleanup transaction

**What:** validate upload input before persistence, store it under the configured owned resources base with a server-generated name, create/update the catalog in an optimistic transaction, and remove the just-written owned file on stale/version failure. On delete, remove the database record or mark its tombstone first in a transaction, then best-effort remove only that owned path. [VERIFIED: codebase grep]

**When to use:** all artwork and soundtrack writes/deletes. [VERIFIED: codebase grep]

**Example:**

```python
# Source: pattern in backend/endpoints/roms/pc_component_resources.py
rom = _visible_rom(request, rom_id)
content, mime_type, extension = await validate_owned_upload(upload)
owned_path = await fs_resource_handler.store_rom_owned_media(
    rom, generated_name, content, extension
)
try:
    applied = db_rom_handler.create_rom_owned_media(
        rom.id, request.user.id, expected_version, ...
    )
    if applied is None:
        raise ValueError("The ROM changed before media was stored")
except ValueError:
    await fs_resource_handler.remove_file(owned_path)
    raise HTTPException(status_code=409)
```

Use `UploadFile` rather than reading arbitrary audio entirely into memory, apply a per-file and request-total cap before expensive parsing, sanitize neither client path nor client-controlled destination into storage, verify artwork by decoding with Pillow, and derive output MIME from an allowlist instead of trusting `UploadFile.content_type`. FastAPI documents that `UploadFile` is spooled, while OWASP recommends allowlists, generated filenames, size limits, and storage outside the webroot. [CITED: https://fastapi.tiangolo.com/tutorial/request-files/] [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html]

### Pattern 4: Ordered lists use one reorder operation and deterministic positions

**What:** represent selected backgrounds and included soundtrack tracks as per-surface ordered placements. Submit the complete ordered list of IDs plus `expected_version`, validate that every ID belongs to the target ROM and appropriate role, then rewrite only that surface's positions atomically. [ASSUMED]

**When to use:** include/exclude/reorder actions, not ordinary candidate listing. [ASSUMED]

**Why:** integer positions make the player queue and rotation sequence deterministic, eliminate duplicate membership, and make stale concurrent edits a clear `409` instead of a silent lost update. The repository already uses expected-update timestamps for owned component media. [VERIFIED: codebase grep]

### Pattern 5: Reuse the background provider and player, adapt their input contract

**What:** extend `GameDetails.vue` to resolve an ordered `background` placement list and pass it to the existing `useBackgroundArt`/`AppLayout` path. Add a timer only while a game details page with at least two selected backgrounds is active. On each tick use the existing two-layer setter; stop and show a static first selected background when reduced motion is enabled. [VERIFIED: codebase grep]

For soundtrack playback, make `PlayerTrack` identify an owned media record and content URL rather than a `RomFile` ID, and have `SoundtrackPanel` use the selected ordered placements. Keep the existing mini-player and its single app-wide `HTMLAudioElement`. [VERIFIED: codebase grep]

Do not promise uniform browser decoding of every accepted extension. Browser codec/container support varies, with AAC particularly platform-dependent in Firefox; accepted files should be stored and listed, while the existing player error surface must present a playback failure if the browser cannot decode a specific asset. [CITED: https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Audio_codecs] [CITED: https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/error_event]

### Anti-Patterns to Avoid

- **Reusing `RomFile` for uploads:** `RomFile` means discovered source-library content and routes its content through source-file endpoints. [VERIFIED: codebase grep]
- **Calling the legacy soundtrack API from the new UI:** both write and delete are blocked by source-read-only policy on external roots and are architecturally wrong even where legacy storage is writable. [VERIFIED: codebase grep]
- **Using `path_screenshots` index as candidate identity:** refresh reorders and regenerates that list, making a persisted deletion or selection attach to the wrong image. [ASSUMED]
- **Hard-deleting a provider record without a tombstone:** the next provider reconciliation cannot distinguish an operator deletion from a never-seen candidate. [ASSUMED]
- **Treating `accept` as server validation:** browser file-picker filtering is advisory; server decode/type and byte limits remain mandatory. [CITED: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/file] [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html]
- **Adding a second audio element or a second player store:** the current mini-player deliberately owns one mounted audio element and survives Media navigation. [VERIFIED: codebase grep]
- **Rotating with an unbounded global timer:** rotation must be scoped to the active game details screen, cleared on route/selection change, and disabled for reduced motion. [VERIFIED: codebase grep]

## Don't Hand-Roll

| Problem                    | Do Not Build                            | Use Instead                                                                                                                           | Why                                                                                                                          |
| -------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Source write authorization | Per-endpoint path checks                | Existing storage composition and owned resources descriptor                                                                           | Storage policy makes authority explicit and already separates owned writes from external reads. [VERIFIED: codebase grep]    |
| Image validation           | Extension-only check                    | Pillow decode/verify plus MIME allowlist                                                                                              | Existing component media upload verifies decoded PNG/JPEG/WebP before writing. [VERIFIED: codebase grep]                     |
| File upload UI             | Raw input/drop event handling           | `RDropzone` and `storeUpload`                                                                                                         | Existing v2 manual and screenshot flows supply the UX and progress pattern. [VERIFIED: codebase grep]                        |
| Destructive confirmation   | Inline `confirm()` or immediate delete  | `useConfirm`                                                                                                                          | It supplies the shared dialog, cancel-first focus, loading behavior, and snackbar outcome pattern. [VERIFIED: codebase grep] |
| Reorder widget             | Custom pointer-only drag implementation | Existing interactive primitives plus accessible move-up/move-down controls, or an existing sortable primitive only if already present | Keyboard/gamepad parity is mandatory; no sortable package is currently established in the repository. [ASSUMED]              |
| Playback queue             | A new audio store/player                | `useSoundtrackPlayer`, `SoundtrackPanel`, `MiniPlayer`                                                                                | They already synchronize queue, transport, volume, and a persistent audio element. [VERIFIED: codebase grep]                 |
| Background fade            | A new backdrop component                | `AppLayout` two-layer setter and `BackgroundArt`                                                                                      | It already prevents flash and handles cross-fade layer swaps. [VERIFIED: codebase grep]                                      |

**Key insight:** media bytes, provider identity, presentation membership, and order are four different concerns. Modeling any two as the same thing is what would make deletion, refresh, multiple backgrounds, or ordered tracks incorrect. [ASSUMED]

## Common Pitfalls

### Pitfall 1: A normal scan resurrects deleted provider media

**What goes wrong:** the operator deletes a provider screenshot, then an ordinary scan silently recreates it. [VERIFIED: codebase grep]

**Why it happens:** the current scan path compares provider URL lists and calls `get_rom_screenshots()` to write numbered screenshot files, with no provenance/tombstone lookup. [VERIFIED: codebase grep]

**How to avoid:** remove Phase 20 candidate reconciliation from ordinary scan flows. Only the explicit refresh route reactivates deleted provider identities. [ASSUMED]

**Warning signs:** a normal scan test observes a `store_rom_owned_media` or provider-download call, or a tombstoned candidate returns active afterward. [ASSUMED]

### Pitfall 2: Refresh changes what users see without a selection action

**What goes wrong:** a newly restored provider candidate becomes an overview screenshot or background automatically. [ASSUMED]

**Why it happens:** candidate persistence and display membership are stored in the same field or inferred from provider list position. [ASSUMED]

**How to avoid:** restore candidates as unplaced; preserve existing placement rows and their order. [ASSUMED]

**Warning signs:** a refresh-only request changes `overview` or `background` placement rows. [ASSUMED]

### Pitfall 3: New audio upload reaches the source library

**What goes wrong:** an upload or delete touches `<rom>/soundtrack` under an external root. [VERIFIED: codebase grep]

**Why it happens:** existing legacy soundtrack endpoints are convenient and already parse audio, but explicitly call the external storage policy for write/delete. [VERIFIED: codebase grep]

**How to avoid:** do not import or call `legacy_external_storage`, `fs_rom_handler.make_directory`, or `RomFile` CRUD from any Phase 20 endpoint. Add a source-mutation inventory regression like the existing v2 safety tests. [VERIFIED: codebase grep]

**Warning signs:** source mutation audit detects `/soundtracks` POST/DELETE client calls or a Phase 20 endpoint uses `StorageOperation.SIDECAR_WRITE`. [VERIFIED: codebase grep]

### Pitfall 4: Upload validation accepts a disguised or oversized file

**What goes wrong:** a `.mp3` name, client MIME header, or image extension is accepted without validating bounded bytes. [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html]

**Why it happens:** client filtering and filename checks are confused with server-side validation. [CITED: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/file]

**How to avoid:** validate extension plus detected/decoded image type, enforce size quotas before parsing, generate destination names, return `nosniff` content responses, and never accept a target path from the request. [VERIFIED: codebase grep] [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html]

**Warning signs:** a test can upload image bytes with an audio extension, image bytes above limit, traversal filename, or a content type inconsistent with the stored response. [ASSUMED]

### Pitfall 5: Ordering works visually but not in playback or rotation

**What goes wrong:** moving a track/background changes one local array but player next/previous or rotation still follows name/DB order. [VERIFIED: codebase grep]

**Why it happens:** `SoundtrackPanel` currently sorts source tracks alphabetically and the background setter receives one URL, not an ordered collection. [VERIFIED: codebase grep]

**How to avoid:** make the placement `position` the sole ordering source for both resolved DetailRom output and player/rotation inputs. [ASSUMED]

**Warning signs:** a reorder test passes API response assertions but `next()` plays alphabetical order. [ASSUMED]

### Pitfall 6: Motion preference is only cosmetic

**What goes wrong:** CSS removes the fade but JavaScript continues periodic background swaps and network/image churn. [VERIFIED: codebase grep]

**Why it happens:** the existing shell exposes `useReducedMotion`, but timer behavior is new application logic. [VERIFIED: codebase grep]

**How to avoid:** gate timer creation and swaps on `useReducedMotion().enabled`, clear it reactively, and keep one static selected background while enabled. [ASSUMED]

**Warning signs:** fake-timer tests observe background setter calls after reduced motion becomes true. [ASSUMED]

## Code Examples

### Safe media refresh boundary

```python
# Source: proposed endpoint pattern, informed by existing storage composition.
@protected_route(router.post, "/{id}/media/refresh", [Scope.ROMS_WRITE])
async def refresh_rom_media(request: Request, id: int, body: MediaRefreshRequest):
    rom = _visible_rom(request, id)
    candidates = await media_provider_handler.collect_candidates(rom)
    return await media_handler.reconcile_explicit_refresh(
        rom=rom,
        actor_id=request.user.id,
        expected_version=body.expected_version,
        candidates=candidates,
    )
```

The handler must be reachable only from this explicit route, not from scan code. [ASSUMED]

### Atomic placement reorder

```python
# Source: proposed database-handler pattern, modeled on component expected-version writes.
def replace_placements(rom_id, surface, media_ids, expected_updated_at):
    rom = lock_rom_for_expected_version(rom_id, expected_updated_at)
    assert_all_media_belong_to_rom_and_surface(rom, media_ids, surface)
    delete_existing_placements(rom_id, surface)
    for position, media_id in enumerate(media_ids):
        add_placement(rom_id, media_id, surface, position)
    rom.updated_at = utcnow()
```

The concrete handler must raise the repository's normal bounded conflict response rather than use Python `assert` for request validation. [ASSUMED]

### Reduced-motion-aware rotation

```ts
// Source: proposed use in GameDetails.vue, reusing useReducedMotion and useBackgroundArt.
watchEffect((onCleanup) => {
  const urls = selectedBackgroundUrls.value;
  if (urls.length === 0) return;
  setBackgroundArt(urls[0]);
  if (reducedMotion.enabled.value || urls.length < 2) return;

  let index = 0;
  const timer = window.setInterval(() => {
    index = (index + 1) % urls.length;
    setBackgroundArt(urls[index]);
  }, BACKGROUND_ROTATION_MS);
  onCleanup(() => window.clearInterval(timer));
});
```

`setBackgroundArt` already drives the shell's A/B cross-fade. The new code must only decide sequence and lifetime. [VERIFIED: codebase grep]

## State of the Art

| Old Approach                               | Current Phase 20 Approach                                 | Impact                                                                                                   |
| ------------------------------------------ | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Flat `path_screenshots` downloaded by scan | Provenanced owned candidate catalog with explicit refresh | Supports durable deletion and restores without source mutation. [VERIFIED: codebase grep] [ASSUMED]      |
| Component-local background only            | Parent-ROM ordered background placements                  | Enables game-level artwork/screenshot backgrounds and rotation. [VERIFIED: codebase grep] [ASSUMED]      |
| Source `RomFile` soundtrack entries        | Owned audio media and placements                          | Removes source-library write/delete risk and enables operator order. [VERIFIED: codebase grep] [ASSUMED] |
| Alphabetical soundtrack sorting            | Placement ordering                                        | Makes queue order match operator intent. [VERIFIED: codebase grep] [ASSUMED]                             |

**Deprecated/outdated for this phase:**

- `POST /api/roms/{id}/soundtracks` and `DELETE /api/roms/{id}/soundtracks/{file_id}` must not be exposed or reused by v2 Media because they mutate legacy source storage. [VERIFIED: codebase grep]

## Assumptions Log

| #   | Claim                                                                                                | Section                 | Risk if Wrong                                                                      |
| --- | ---------------------------------------------------------------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------- |
| A1  | A separate parent-ROM `RomOwnedMedia` plus `RomMediaPlacement` model is the smallest correct schema. | Architecture Patterns   | Migration may need adaptation to an existing uninspected parent media abstraction. |
| A2  | Provider identity can use provider media ID or a persisted URL digest if no provider ID exists.      | Pattern 1               | A bad identity can duplicate or wrongly restore candidates.                        |
| A3  | Refresh should restore deleted provider candidates unselected while retaining existing placements.   | Pattern 2               | Product expectation of “restore” might instead require restoring selection.        |
| A4  | Complete-list atomic reorder with integer positions is appropriate for each surface.                 | Pattern 4               | API ergonomics may need a different optimistic update representation.              |
| A5  | Existing v2 primitives have no established accessible sortable-list primitive.                       | Don't Hand-Roll         | An available project primitive could be missed.                                    |
| A6  | Server-side transcoding is out of scope and unnecessary for accepted original formats.               | Alternatives Considered | Browser support requirements could require a conversion strategy.                  |

## Open Questions

1. **What counts as the stable provider identity for each existing provider screenshot/artwork?**
   - What we know: current generic ROM screenshots are stored as numbered paths and source URL lists are consumed by scan code. [VERIFIED: codebase grep]
   - What's unclear: not every adapter surface exposes a provider-native media ID to this phase. [ASSUMED]
   - Recommendation: define a canonical `provider + provider_media_id` where available; otherwise use a documented normalized URL digest. Lock this before migration work. [ASSUMED]

2. **Does explicit refresh restore only a candidate, or also its former display placement?**
   - What we know: locked decisions require full candidate restoration and separately require provider media and user-selected display state to remain separate. [VERIFIED: codebase grep]
   - What's unclear: “restore” does not explicitly state whether the former selection returns. [ASSUMED]
   - Recommendation: restore candidates unselected, preserving the separation and avoiding unexpected overview/background changes. Ask for confirmation only if product ownership interprets restore differently. [ASSUMED]

3. **What upload quota is appropriate for owned audio?**
   - What we know: existing component image upload is capped at 10 MiB and current tag parsing skips files over 512 MiB. [VERIFIED: codebase grep]
   - What's unclear: soundtrack duration/count/storage budget has no locked product limit. [VERIFIED: codebase grep]
   - Recommendation: make this a deployment-safe, explicit server limit with a request-total cap and test boundary values before shipping. [ASSUMED]

4. **Should embedded local file tags be displayed?**
   - What we know: the existing source soundtrack UI reads persisted local tag metadata, while the phase excludes automatic metadata enrichment. [VERIFIED: codebase grep]
   - What's unclear: whether parsing an uploaded file's embedded tags is considered enrichment for this phase. [ASSUMED]
   - Recommendation: do not add new tag extraction/persistence behavior in Phase 20. Display the uploaded filename and let a future metadata phase decide tag policy. [ASSUMED]

## Environment Availability

| Dependency                                             | Required By                         | Available | Version                    | Fallback                                                                                                                                                          |
| ------------------------------------------------------ | ----------------------------------- | --------: | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `uv`                                                   | Backend tests/migrations            |         ✓ | 0.12.3                     | none needed. [VERIFIED: codebase grep]                                                                                                                            |
| Node/npm                                               | Frontend generation/typecheck/tests |         ✓ | Node 24.19.0, npm 11.17.0  | none needed. [VERIFIED: codebase grep]                                                                                                                            |
| Existing FastAPI, Pillow, Mutagen dependencies         | Upload and media validation         |         ✓ | pinned in `pyproject.toml` | none needed. [VERIFIED: codebase grep]                                                                                                                            |
| Browser supporting each accepted audio container/codec | Client playback                     |    varies | runtime-dependent          | Store/list accepted track and surface native-player error if unsupported. [CITED: https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Audio_codecs] |

**Missing dependencies with no fallback:** None for implementation. [VERIFIED: codebase grep]

**Missing dependencies with fallback:** Per-codec browser support varies; no server dependency is required because this phase does not transcode. [CITED: https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Audio_codecs]

## Validation Architecture

### Test Framework

| Property           | Value                                                                                                                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Framework          | pytest 9 with pytest-asyncio for backend, Vitest for frontend. [VERIFIED: codebase grep]                                                                                              |
| Config file        | `backend/pytest.ini`, `frontend/package.json`. [VERIFIED: codebase grep]                                                                                                              |
| Quick run command  | `cd backend && uv run pytest tests/endpoints/roms/test_media.py tests/handler/database/test_rom_media.py -x`; `cd frontend && npm run test -- GameDetails`. [VERIFIED: codebase grep] |
| Full suite command | `cd backend && uv run pytest`; `cd frontend && npm run typecheck && npm run test && npm run build`. [VERIFIED: codebase grep]                                                         |

### Phase Requirements → Test Map

Roadmap requirements are currently `TBD`; use the following Phase 20 acceptance IDs in plans until requirements are formally assigned. [VERIFIED: codebase grep]

| Req ID   | Behavior                                                                                 | Test Type                                    | Automated Command                                                                                         | File Exists?               |
| -------- | ---------------------------------------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------------------------- |
| MEDIA-01 | Provider screenshots are candidates and overview selections are independent.             | backend integration + frontend unit          | `uv run pytest tests/endpoints/roms/test_media.py -k overview`; `npm run test -- ScreenshotsSubtab`       | ❌ Wave 0                  |
| MEDIA-02 | Provider deletion persists across normal scan, explicit refresh restores candidate only. | backend integration                          | `uv run pytest tests/endpoints/roms/test_media.py -k 'tombstone or refresh or normal_scan'`               | ❌ Wave 0                  |
| MEDIA-03 | Provider/uploaded art can be selected and ordered as backgrounds.                        | backend integration + frontend unit          | `uv run pytest tests/handler/database/test_rom_media.py -k background`; `npm run test -- GameDetails`     | ❌ Wave 0                  |
| MEDIA-04 | Rotation cleans up and reduced motion prevents rotating swaps.                           | frontend unit with fake timers               | `npm run test -- GameDetails`                                                                             | ❌ Wave 0                  |
| MEDIA-05 | Artwork and accepted audio upload only to owned storage.                                 | backend endpoint + source-mutation inventory | `uv run pytest tests/endpoints/roms/test_media.py tests/endpoints/test_storage_policy_denials.py -x`      | ❌ Wave 0                  |
| MEDIA-06 | Included soundtrack tracks retain operator order in panel and next/previous queue.       | backend handler + frontend unit              | `uv run pytest tests/handler/database/test_rom_media.py -k soundtrack`; `npm run test -- SoundtrackPanel` | ❌ Wave 0                  |
| MEDIA-07 | Legacy source-writing soundtrack calls are absent from v2 Media.                         | static regression                            | `npm run test -- sourceMutation`                                                                          | existing inventory, extend |

### Sampling Rate

- **Per task commit:** focused backend pytest and affected Vitest suite. [VERIFIED: codebase grep]
- **Per wave merge:** backend affected suite, frontend typecheck and test. [VERIFIED: codebase grep]
- **Phase gate:** full backend/frontend checks, migration upgrade/downgrade on supported engines, OpenAPI generation, both-theme/browser/input UAT. [VERIFIED: codebase grep]

### Wave 0 Gaps

- [ ] `backend/tests/endpoints/roms/test_media.py` for auth, owned storage, upload limits, source safety, tombstones, and refresh. [ASSUMED]
- [ ] `backend/tests/handler/database/test_rom_media.py` for placement ordering, ownership, stale version, uniqueness, and cleanup. [ASSUMED]
- [ ] Frontend tests for candidate selection, background timer lifecycle/reduced motion, and owned queue ordering. [ASSUMED]
- [ ] Add all locale keys and run the two locale parity/sort checks. [VERIFIED: codebase grep]

## Security Domain

### Applicable ASVS Categories

| ASVS Category           | Applies                       | Standard Control                                                                                                                                                                                                                                           |
| ----------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| V2 Authentication       | yes                           | Existing protected routes and authenticated request actor. [VERIFIED: codebase grep]                                                                                                                                                                       |
| V3 Session Management   | yes                           | Existing auth/CSRF/session middleware via canonical API client. [VERIFIED: codebase grep]                                                                                                                                                                  |
| V4 Access Control       | yes                           | `Scope.ROMS_READ` for content/listing and `Scope.ROMS_WRITE` for mutation, plus ROM visibility and media-to-ROM ownership checks. [VERIFIED: codebase grep]                                                                                                |
| V5 Input Validation     | yes                           | Server allowlists, generated filenames, byte quotas, Pillow decode/verify, audio type validation, bounded IDs and expected-version schemas. [VERIFIED: codebase grep] [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html] |
| V6 Cryptography         | no new phase-specific control | Do not invent a media checksum or encryption scheme; use existing storage/auth infrastructure. [ASSUMED]                                                                                                                                                   |
| V12 Files and Resources | yes                           | Owned descriptor for writes/reads, no caller paths, `X-Content-Type-Options: nosniff`, and no external-root storage operation. [VERIFIED: codebase grep]                                                                                                   |

### Known Threat Patterns for uploads/media

| Pattern                                     | STRIDE                             | Standard Mitigation                                                                                                                                                                                                                 |
| ------------------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Path traversal or source-library write      | Tampering / Elevation              | Never accept a destination path, generate owned names, route only through owned resources descriptor, and retain the existing external policy deny tests. [VERIFIED: codebase grep]                                                 |
| MIME/extension spoofing                     | Tampering                          | Decode artwork bytes, use extension and type allowlists for audio, set server-controlled content type and `nosniff`. [VERIFIED: codebase grep] [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html] |
| Oversized upload/parser resource exhaustion | Denial of Service                  | Per-file/request caps, streamed/spooled uploads, and bounded tag/image parsing. [CITED: https://fastapi.tiangolo.com/tutorial/request-files/] [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html]  |
| Cross-ROM media ID access                   | Information Disclosure / Tampering | Resolve parent ROM, assert visibility, and verify every media/placement belongs to that ROM before read/write/delete. [VERIFIED: codebase grep]                                                                                     |
| Stale reorder/delete overwrites newer state | Tampering                          | Expected version plus transactional row update and bounded `409` conflict. [VERIFIED: codebase grep]                                                                                                                                |

## Sources

### Primary (HIGH confidence)

- `backend/models/rom.py`, `backend/handler/database/roms_handler.py`, `backend/handler/filesystem/resources_handler.py` - current local/owned media models, durable storage paths, and optimistic cleanup behavior. [VERIFIED: codebase grep]
- `backend/endpoints/roms/soundtrack.py` - legacy source-writing soundtrack behavior that Phase 20 must avoid. [VERIFIED: codebase grep]
- `backend/endpoints/roms/pc_component_resources.py` - protected owned upload/read/delete endpoint pattern. [VERIFIED: codebase grep]
- `backend/endpoints/sockets/scan.py`, `backend/handler/scan_handler.py`, `backend/handler/filesystem/resources_handler.py` - current normal-scan screenshot download behavior. [VERIFIED: codebase grep]
- `frontend/src/v2/components/GameDetails/{MediaTab,ScreenshotsSubtab,ArtworkSubtab,SoundtrackPanel}.vue`, `frontend/src/stores/soundtrackPlayer.ts`, `frontend/src/v2/layouts/AppLayout.vue`, `frontend/src/v2/components/AppShell/BackgroundArt.vue` - existing v2 composition/player/backdrop patterns. [VERIFIED: codebase grep]
- [FastAPI request files](https://fastapi.tiangolo.com/tutorial/request-files/) - multipart and `UploadFile` behavior. [CITED: https://fastapi.tiangolo.com/tutorial/request-files/]
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) - upload validation and storage controls. [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html]
- [MDN audio codec guide](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Audio_codecs) - browser codec/container variability. [CITED: https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Audio_codecs]
- [MDN prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion) - motion-preference media feature. [CITED: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion]

### Secondary (MEDIUM confidence)

- None.

### Tertiary (LOW confidence)

- None. All design inferences are explicitly marked `[ASSUMED]` in the body and Assumptions Log.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, all proposed facilities already exist in the repository; no new package is required. [VERIFIED: codebase grep]
- Architecture: HIGH for the need to separate owned candidate, placement, and legacy source-writing flows; MEDIUM for the exact new parent table shape. [VERIFIED: codebase grep] [ASSUMED]
- Pitfalls: HIGH for source mutation, current scan restoration, and v2 player/backdrop constraints; MEDIUM for exact refresh semantics pending one product interpretation. [VERIFIED: codebase grep] [ASSUMED]

**Research date:** 2026-09-28
**Valid until:** 2026-10-28
