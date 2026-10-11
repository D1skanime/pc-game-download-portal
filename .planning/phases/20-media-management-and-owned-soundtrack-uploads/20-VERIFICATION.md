---
phase: 20-media-management-and-owned-soundtrack-uploads
verified: 2026-09-28T15:33:05Z
status: gaps_found
score: 17/20 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Deleting a provider candidate remains reversible through an explicit full-media refresh without changing its placements."
    status: failed
    reason: "The live refresh route accesses `rom.provider_metadata`, but `provider_metadata` is defined only on `RomComponentMetadata`, not on the parent `Rom`. Every call to POST /roms/{id}/media/refresh therefore raises AttributeError before provider discovery or tombstone restoration."
    artifacts:
      - path: "backend/endpoints/roms/media.py"
        issue: "refresh_media reads a nonexistent parent-ROM attribute at line 86."
      - path: "backend/models/rom.py"
        issue: "Parent Rom has no provider_metadata field; the only field is on RomComponentMetadata."
    missing:
      - "Read parent-ROM artwork from its actual persisted metadata field, add endpoint-level refresh coverage, and prove tombstone restoration through the HTTP route."
---

# Phase 20: Media management and owned soundtrack uploads Verification Report

**Phase Goal:** Let operators manage provider and RomM-owned game media, select ordered overview/background assets, and upload/order/play owned soundtracks without any write to the external source library.
**Verified:** 2026-09-28T15:33:05Z
**Status:** gaps_found
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                           | Status    | Evidence                                                                                                                                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Provider assets remain candidates while overview/background placements change independently.                                    | VERIFIED  | `RomOwnedMedia` and `RomOwnedMediaPlacement` are separate models; placement mutations operate on placement rows only in `roms_handler.py:639-735`.                                      |
| 2   | Provider deletion is durable across normal work and explicit refresh restores the candidate without selecting it.               | FAILED    | `delete_owned_media` tombstones provider rows and `reconcile_provider_owned_media` can reactivate them, but the reachable refresh route crashes before it calls reconciliation.         |
| 3   | Background and soundtrack placement replacement is ordered, complete, cross-game safe, and role-compatible.                     | VERIFIED  | Locked parent-ROM query, expected timestamp, full-membership comparison, role check, and atomic replacement in `roms_handler.py:500-513,693-735`.                                       |
| 4   | Media, not Overview, is the management surface for provider screenshots and artwork.                                            | VERIFIED  | `MediaTab.vue` mounts Screenshots and Artwork subtabs; `GameDetails.vue` only resolves ordered placements for display.                                                                  |
| 5   | Artwork and soundtrack uploads are bounded and stored under RomM-owned resources with server-generated names.                   | VERIFIED  | `media.py:196-235` accepts only artwork/soundtrack; `resources_handler.py:133-188` validates image bytes or audio extension/size and writes `fs_resources_path/owned-media`.            |
| 6   | First selected background is immediate fallback; two or more rotate only on the active details route in persisted server order. | VERIFIED  | `GameDetails.vue:183-209` sorts background placements by `position`; `scheduleBackgroundRotation` sets index 0 before creating an interval.                                             |
| 7   | Reduced motion produces no periodic background swaps.                                                                           | VERIFIED  | `GameDetails.vue:74,201-209` passes `!reducedMotion.value`; the scheduler returns before `setInterval` when rotation is disabled.                                                       |
| 8   | Operators upload, include, and order owned soundtracks only, with no automatic metadata enrichment.                             | VERIFIED  | `SoundtrackPanel.vue:53-104,127-205` filters owned `soundtrack` candidates, uses placement order, and does not call `getSoundtrackMetadata`.                                            |
| 9   | Included-track rows and Previous/Next consume the identical order.                                                              | VERIFIED  | Both use `includedTracks`, sorted by placement position; `playerTracks()` is passed once to `loadPlaylistForRom`, and store navigation indexes that playlist.                           |
| 10  | Deleting an active owned track stops it, confirms deletion, removes catalog placements, and avoids legacy soundtrack routes.    | VERIFIED  | `SoundtrackPanel.vue:214-238` stops active playback before confirmation and calls only `deleteOwnedMedia`; handler deletion cascades placements. Targeted static regression passed.     |
| 11  | Existing RomM-owned screenshots and compatible covers backfill as manageable candidates without provider refresh.               | VERIFIED  | Migration 0129 derives candidates from persisted `path_screenshots`, `path_cover_s`, and `path_cover_l`, with no provider call.                                                         |
| 12  | Migrated overview screenshots retain persisted order and migration never accesses source-library paths.                         | VERIFIED  | 0129 accepts only bounded `roms/` image resource identifiers, writes database rows only, and assigns screenshot position. No filesystem, HTTP, copy, rename, or delete API is imported. |
| 13  | Parent-ROM role/label contracts are durable and only compatible roles can be placed on each surface.                            | VERIFIED  | Immutable `RomOwnedMediaRole`, safe filename-only label validation, generated response fields, and role/surface checks exist.                                                           |
| 14  | Legacy source-writing soundtrack mutations are not used by v2 Media.                                                            | VERIFIED  | Media components call `/media/*` wrappers; targeted `sourceMutationControls` regression passed and `SoundtrackPanel.vue` has no `/soundtracks` call.                                    |
| 15  | Visible Phase 20 copy has complete locale parity.                                                                               | VERIFIED  | Fresh locale parity and sort commands passed for all 17 non-English locales.                                                                                                            |
| 16  | Protected routes authorize reads and mutations and use parent-owned resources.                                                  | VERIFIED  | All Phase 20 routes are decorated with `ROMS_READ` or `ROMS_WRITE`; content uses `OwnedStorageKind.RESOURCES`, not `legacy_external_storage`.                                           |
| 17  | The Phase 20 migration and API behavior have runnable backend proof on the current checkout.                                    | UNCERTAIN | Fresh focused pytest run collected 30 tests but all errored during fixture setup because `127.0.0.1:3306` is unavailable. No backend assertion ran.                                     |
| 18  | Revision 0129 has cross-dialect migration-cycle evidence.                                                                       | UNCERTAIN | Recorded MariaDB/PostgreSQL cycles stop at 0128. The 0129 evidence is a SQLite simulation only.                                                                                         |
| 19  | Themes, breakpoints, all input modalities, real playback, and reduced-motion behavior have been observed.                       | UNCERTAIN | `20-UAT.md` is marked approved but its detailed matrix/checklist remains blank, so it is not criterion-by-criterion evidence.                                                           |
| 20  | Repository-wide Trunk validation passed for the final shared worktree.                                                          | UNCERTAIN | `20-VALIDATION.md` correctly records an incomplete global `trunk check`, terminated after about 90 seconds, not a pass.                                                                 |

**Score:** 17/20 truths verified

### Required Artifacts

| Artifact                                                           | Expected                                                              | Status                   | Details                                                                                      |
| ------------------------------------------------------------------ | --------------------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------- |
| `backend/models/rom.py`                                            | Candidate, placement, role, and tombstone persistence                 | VERIFIED                 | Substantive ORM models and constraints, used by handler and response schema.                 |
| `backend/alembic/versions/0122_parent_rom_owned_media.py`          | Portable parent-ROM catalog persistence                               | VERIFIED                 | Exists, substantive, and is in the Alembic lineage consumed by 0128/0129.                    |
| `backend/alembic/versions/0129_backfill_legacy_rom_owned_media.py` | Idempotent legacy backfill                                            | VERIFIED with limitation | Substantive database-only migration, but only SQLite simulation has current direct evidence. |
| `backend/handler/database/roms_handler.py`                         | Transactional catalog, placements, tombstones, refresh reconciliation | VERIFIED                 | Used by all media routes; locks parent ROM and checks version/ownership.                     |
| `backend/endpoints/roms/media.py`                                  | Protected parent-owned media API                                      | PARTIAL                  | All routes are wired, but explicit refresh reads nonexistent `Rom.provider_metadata`.        |
| `backend/handler/filesystem/resources_handler.py`                  | Owned image/audio storage                                             | VERIFIED                 | Generates names below owned resource paths and is called by refresh/upload routes.           |
| `frontend/src/services/api/rom.ts`                                 | Typed Phase 20 client wrappers                                        | VERIFIED                 | `/media` wrappers are consumed by all Media management components.                           |
| `frontend/src/v2/components/GameDetails/ScreenshotsSubtab.vue`     | Provider screenshot management                                        | VERIFIED                 | Renders parent-owned candidates and placement/delete calls with canonical refresh.           |
| `frontend/src/v2/components/GameDetails/ArtworkSubtab.vue`         | Artwork upload and ordered backgrounds                                | VERIFIED                 | Upload, placement, reorder, conflict recovery, and deletion are wired.                       |
| `frontend/src/v2/components/GameDetails/SoundtrackPanel.vue`       | Owned soundtrack queue and player                                     | VERIFIED                 | Ordered placement state flows to the shared player, no legacy writes.                        |
| `frontend/src/v2/views/GameDetails.vue`                            | Ordered reduced-motion-aware background display                       | VERIFIED                 | Server placement order flows into the route-scoped scheduler.                                |
| `frontend/src/locales/*/rom.json`                                  | Media copy in every supported locale                                  | VERIFIED                 | Current parity and ordering checks pass.                                                     |

### Key Link Verification

| From                    | To                     | Via                                               | Status  | Details                                                                              |
| ----------------------- | ---------------------- | ------------------------------------------------- | ------- | ------------------------------------------------------------------------------------ |
| `media.py`              | `resources_handler.py` | owned resource upload/download/delete descriptors | WIRED   | Direct calls and `OwnedStorageKind.RESOURCES` usage.                                 |
| `ScreenshotsSubtab.vue` | `rom.ts`               | typed placement/delete/refresh then `refreshRom`  | PARTIAL | Calls are present, but `refreshOwnedMedia` reaches the broken backend refresh route. |
| `ArtworkSubtab.vue`     | `rom.ts`               | artwork upload and complete placement replacement | WIRED   | Calls and response refresh handling present.                                         |
| `SoundtrackPanel.vue`   | `soundtrackPlayer.ts`  | `includedTracks` to `loadPlaylistForRom`          | WIRED   | Same computed ordered list feeds rows and queue navigation.                          |
| `GameDetails.vue`       | `useBackgroundArt`     | sorted placement URLs                             | WIRED   | Data from detailed ROM response becomes ordered background URLs.                     |
| 0129 migration          | `RomOwnedMedia` tables | legacy resource identifiers to rows/placements    | WIRED   | Reflection, insert, identity lookup, and placement inserts exist.                    |

### Data-Flow Trace (Level 4)

| Artifact                | Data Variable             | Source                                                         | Produces Real Data | Status       |
| ----------------------- | ------------------------- | -------------------------------------------------------------- | ------------------ | ------------ |
| `ScreenshotsSubtab.vue` | `providerScreenshots`     | `props.rom.owned_media` from detailed ROM                      | Yes                | FLOWING      |
| `ArtworkSubtab.vue`     | `backgrounds`             | `props.rom.owned_media_placements` plus candidate IDs          | Yes                | FLOWING      |
| `SoundtrackPanel.vue`   | `includedTracks`          | soundtrack placements sorted by server `position`              | Yes                | FLOWING      |
| `GameDetails.vue`       | `selectedBackgrounds`     | detailed-ROM placements and owned resource paths               | Yes                | FLOWING      |
| `media.py` refresh      | provider candidate source | parent ROM URL fields plus nonexistent `rom.provider_metadata` | No                 | DISCONNECTED |

### Behavioral Spot-Checks

| Behavior                            | Command                                                                                                                                       | Result                                                               | Status                 |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ---------------------- |
| Media UI/source-route regressions   | `npm run test -- --run ...ScreenshotsSubtab ...ArtworkSubtab ...SoundtrackPanel ...soundtrackPlayer ...sourceMutationControls`                | 5 files, 29 tests passed                                             | PASS                   |
| Locale parity/sort                  | `python3 src/locales/check_i18n_locales.py && python3 src/locales/check_i18n_sorted.py`                                                       | All translations complete and sorted                                 | PASS                   |
| Backend catalog/API/migration tests | `uv run pytest tests/models/test_rom_owned_media_migration.py tests/handler/database/test_rom_media.py tests/endpoints/roms/test_media.py -q` | 30 setup errors, MariaDB refused `127.0.0.1:3306`; no assertions ran | SKIP, topology blocked |
| Explicit refresh runtime path       | static model-to-route trace                                                                                                                   | `Rom` has no `provider_metadata` declaration; line 86 accesses it    | FAIL                   |

### Probe Execution

Step 7c: SKIPPED. No Phase 20 probe was declared and no `scripts/**/tests/probe-*.sh` file exists.

### Requirements Coverage

The requirements file does not define MEDIA-01 through MEDIA-07 individually. Their authoritative behavior wording is the Phase 20 research traceability table.

| Requirement | Source Plan  | Description                                                  | Status      | Evidence                                                                           |
| ----------- | ------------ | ------------------------------------------------------------ | ----------- | ---------------------------------------------------------------------------------- |
| MEDIA-01    | 20-01, 20-03 | Provider screenshots and independent overview selection      | SATISFIED   | Separate candidate/placement models and Media UI wiring.                           |
| MEDIA-02    | 20-01, 20-02 | Tombstone persists; explicit refresh restores candidate only | BLOCKED     | HTTP refresh crashes before reconciliation.                                        |
| MEDIA-03    | 20-04        | Provider/uploaded art selected and ordered as backgrounds    | SATISFIED   | Compatible placement, complete reorder, and UI/background resolver.                |
| MEDIA-04    | 20-04        | Rotation cleanup and reduced-motion behavior                 | NEEDS HUMAN | Scheduler logic is correct; actual visual/motion observation remains undocumented. |
| MEDIA-05    | 20-02        | Art/audio upload only to owned storage                       | SATISFIED   | Parent-owned route and resources descriptor, no external source descriptor.        |
| MEDIA-06    | 20-05        | Soundtrack panel and queue retain operator order             | SATISFIED   | One ordered `includedTracks` source feeds both display and player.                 |
| MEDIA-07    | 20-05        | v2 Media omits legacy source-writing soundtrack calls        | SATISFIED   | Targeted regression passes and source uses only `/media/*`.                        |

### Anti-Patterns Found

| File                                                                | Line    | Pattern                                                                                                           | Severity | Impact                                                                                                                                                     |
| ------------------------------------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/endpoints/roms/media.py`                                   | 86      | Attribute access has no matching parent-ROM model field                                                           | BLOCKER  | Explicit provider refresh, a locked Phase 20 decision, is unreachable.                                                                                     |
| `backend/tests/endpoints/roms/test_media.py` and v2 component tests | various | Most targeted tests inspect source text rather than invoke endpoint/component behavior                            | WARNING  | They pass while the broken `refresh_media` attribute access is untested.                                                                                   |
| `backend/alembic/versions/0129_backfill_legacy_rom_owned_media.py`  | 227-235 | Downgrade deletes every row with the legacy provider identifier rather than selecting a migration-specific marker | WARNING  | Contradicts the summary's marker-bounded-downgrade claim; not needed for the forward user flow, but should be reviewed before relying on downgrade safety. |
| phase validation                                                    | n/a     | Database topology and global Trunk validation incomplete                                                          | WARNING  | Do not represent backend assertions, 0129 cross-dialect evidence, or repository-wide lint as passing.                                                      |

### Human Verification Required

### 1. Full Media interaction matrix

**Test:** After the refresh fix, use an authorized and read-only account across dark/light, xs through desktop, mouse, keyboard, touch, and gamepad. Exercise provider refresh, selection, upload, ordering, cancel/delete, and conflict recovery.

**Expected:** Only permitted actions appear; the Media tab remains usable with no layout/focus defect and no source-library changes.

**Why human:** Visual layout, input modality, permissions presentation, and external source immutability cannot be fully established by static inspection.

### 2. Reduced-motion and soundtrack playback

**Test:** With two backgrounds, compare normal and reduced-motion behavior on and off the active game-details route. Upload two permitted tracks, reorder, play, use next/previous, test decode error/retry, and delete the active track.

**Expected:** Normal mode rotates only on the active route in saved order; reduced motion stays static. Player order matches rows and deletion is confirmed without touching a source file.

**Why human:** Browser media decoding, real timing, accessibility, and actual device behavior need runtime observation.

### Gaps Summary

The phase goal is not achieved because its explicit provider refresh operation is broken at the reachable backend API boundary. `refresh_media` tries to obtain artwork from a `Rom.provider_metadata` attribute that does not exist. The direct handler has a tombstone restoration implementation, but it is orphaned from a working HTTP refresh operation.

The validation record also correctly documents limits that must remain limits: focused backend tests cannot reach their forced local MariaDB, revision 0129 was not rerun through MariaDB/PostgreSQL, and the repository-wide Trunk check has no final result. These are warnings, not passing evidence. There are no later milestone phases to which this gap can be deferred.

_Verified: 2026-09-28T15:33:05Z_
_Verifier: the agent (gsd-verifier)_
