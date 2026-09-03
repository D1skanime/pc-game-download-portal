# Phase 12: DLC detail pages for local PC components - Expanded Research

**Researched:** 2026-09-03
**Domain:** Vue 3 v2 detail UI, FastAPI component-scoped metadata, owned media, and notes
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

### Dedicated DLC experience

- **D-01:** A local DLC has its own detail page, rather than only an expanded
  row in the PC Components area.
- **D-02:** The page is reachable from both the Overview DLC card and the
  PC Components list, with clear back navigation to the parent game.
- **D-03:** The page follows the parent game's tab language: Overview,
  Files, Media, and Notes. There is no DLC save-data feature in this phase.
- **D-04:** Overview presents a prominent cover, title, description, and
  DLC-only screenshots or other selected media. Files presents only the
  selected DLC's manifest entries and DLC-specific downloadable artwork.
- **D-05:** Media accepts and manages only RomM-owned DLC media: images,
  screenshots, artwork, soundtrack, and videos. It does not write to or
  otherwise mutate the immutable source library.
- **D-06:** Notes are scoped to the individual DLC, not shared with the parent
  game. Save data remains owned by and available from the parent game because
  the DLC runs through it. There is no separate DLC save-data feature.

### Unified metadata matching

- **D-07:** Replace the bespoke, simplified PC metadata-candidate view with
  the existing polished `ROM zuordnen` matching experience for both the
  PC parent game and every PC component, including DLCs.
- **D-08:** PC Components' `Metadaten suchen` and the DLC detail page's
  overflow action `ROM zuordnen` are two entry points to that one shared
  matching flow.
- **D-09:** The shared flow retains its provider filters, result list,
  description preview, and cover-selection UI. When the target is a DLC, its
  explicit selection writes metadata and selected provider media only to that
  DLC, never to the parent game.
- **D-10:** Selected provider images are imported as RomM-owned DLC media only
  after the user explicitly confirms the match. The feature must not mutate
  source files or silently apply artwork.

### DLC actions and information

- **D-11:** The DLC detail page has an overflow action menu with all
  applicable component actions: `ROM zuordnen`, poster/media selection, and
  downloading the DLC's local files.
- **D-12:** Technical component information, such as size, version evidence,
  and checksums, belongs on the DLC detail experience and may reuse existing
  detail patterns.

### the agent's Discretion

- Exact responsive composition, cover fallback, which Media subtab owns each
  supported media kind, and the precise technical metadata fields shown may
  follow existing v2 Game Details conventions.

### Deferred Ideas (OUT OF SCOPE)

- DLC-specific save data is intentionally not a feature: save data stays with
  the parent game because the DLC depends on it.
  </user_constraints>

## Summary

Phase 12 is now a vertical component-resource extension, not only a presentation page. The existing nested DLC route, resolver, hero, and immutable manifest components form a safe starting point, but the current implementation does not expose component-owned uploads, notes, provider-media import, or the parent-style tab/action model. [VERIFIED: `frontend/src/v2/views/PcDlcDetails.vue`, `frontend/src/v2/components/GameDetails/PcDlcDetail.vue`, `frontend/src/v2/components/GameDetails/PcDlcFiles.vue`]

The polished `MatchRomDialog` must be reused at the visual/body level, not called unchanged for a PC target. Its shell accepts a `SimpleRom`, calls the generic `/roms/{id}/search` endpoint, and persists through `updateRom`, which would write the parent ROM. Existing PC APIs already provide review-first parent and DLC candidates, optimistic versions, and component-specific metadata persistence, but they lack user-entered query support and do not persist selected candidate media. [VERIFIED: `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`, `frontend/src/v2/components/MatchRom/`, `backend/endpoints/roms/pc_metadata.py`, `backend/handler/database/roms_handler.py`]

**Primary recommendation:** Extract the existing matcher shell and `components/MatchRom/` bodies behind a typed match-target adapter. Add component-safe search, confirmation, and owned-media import endpoints. Model independently uploaded/provider-derived DLC media and DLC notes as component-owned records, while retaining the existing manifest-bound local-image records for source-evidence selection. [VERIFIED: codebase inspection and locked decisions D-03 through D-10]

## Architectural Responsibility Map

| Capability                                                      | Primary Tier       | Secondary Tier     | Rationale                                                                                                                                                                                                                                                |
| --------------------------------------------------------------- | ------------------ | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Match dialog visual layout, filters, result cards, cover picker | Browser / Client   | API / Backend      | The current shared Vue dialog and body variants own interaction; the API supplies only reviewable candidate data. [VERIFIED: `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`, `frontend/src/v2/components/MatchRom/`]                            |
| Match target validation and applying metadata/media             | API / Backend      | Database / Storage | The backend must prove parent/component containment, permissions, candidate identity, optimistic version, and owned-resource storage before persistence. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`, `backend/handler/database/roms_handler.py`] |
| DLC detail tabs and action entry points                         | Browser / Client   | API / Backend      | Route and tab state belong in Vue Router; all writes use typed component APIs. [VERIFIED: `frontend/src/v2/views/PcDlcDetails.vue`, `frontend/src/v2/views/GameDetails.vue`]                                                                             |
| Immutable file list and downloads                               | API / Backend      | Browser / Client   | Manifest membership and external read authorization are server authority; the client only renders/downloads known members. [VERIFIED: `backend/models/rom.py`, `frontend/src/v2/components/GameDetails/PcDlcFiles.vue`]                                  |
| Uploaded and imported component media                           | Database / Storage | API / Backend      | Bytes must enter only an owned resource root, with DB records scoped to the resolved component. [VERIFIED: `backend/handler/filesystem/resources_handler.py`, `backend/models/rom.py`]                                                                   |
| DLC notes                                                       | Database / Storage | API / Backend      | Notes need durable component ownership, visibility and author checks, then typed client editing. [VERIFIED: `backend/models/rom.py`, `backend/endpoints/roms/notes.py`]                                                                                  |

## Project Constraints (from AGENTS.md and CLAUDE.md)

- Work only in the Linux canonical checkout, preserve unrelated dirty work, and do not touch Team4s, NAS mounts, or services outside the task. [VERIFIED: `AGENTS.md`, `CLAUDE.md`]
- New UI belongs only under `frontend/src/v2`; v1 is frozen. Use existing `R*` primitives, strict TypeScript, vue-i18n, responsive breakpoint conventions, and mouse, touch, keyboard, and gamepad input. [VERIFIED: `CLAUDE.md`, `.claude/skills/frontend-v2-components/SKILL.md`, `.claude/skills/frontend-v2-input/SKILL.md`]
- The backend schema and routes are the API authority. Backend response or route changes require generated frontend types and a frontend typecheck. [VERIFIED: `CLAUDE.md`, `.claude/skills/backend-development/SKILL.md`]
- External PC library roots are immutable. No source upload, write, rename, move, delete, extraction, or remote-artwork write is permitted. All derived content belongs in RomM-owned storage. [VERIFIED: `.planning/REQUIREMENTS.md`, `12-CONTEXT.md`, `backend/endpoints/roms/pc_metadata.py`]
- New logic needs automated tests. Run Trunk, relevant pytest/Vitest, typecheck, i18n checks for locale changes, and manual UI checks across themes, breakpoints, and input modalities before handoff. [VERIFIED: `CLAUDE.md`, `.claude/skills/pre-pr-verification/SKILL.md`]
- Documentation, code, and commit messages are English; do not use em dashes. [VERIFIED: `CLAUDE.md`]

## Current Contracts and Gaps

| Area                 | Current contract                                                                                                                                                                                                                                                                                             | Gap to close                                                                                                                    | Recommended change                                                                                                                                                                                                                                               |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nested DLC route     | `PcDlcDetails.vue` safely parses decimal IDs, loads the parent, and accepts only a child component with `kind === "dlc"`. [VERIFIED: `frontend/src/v2/views/PcDlcDetails.vue`]                                                                                                                               | Detail state is presentation-only and does not refresh after child mutations.                                                   | Keep the resolver as the sole client containment guard, add a typed reload callback after match/media/note mutations. [VERIFIED: codebase inspection]                                                                                                            |
| Generic match UI     | `MatchRomDialog` has the desired search, provider chips, grid/list bodies, description preview, and cover picker. It persists a `SimpleRom` using generic `updateRom`. [VERIFIED: `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`, `frontend/src/v2/components/MatchRom/`]                           | Calling it for a component would overwrite parent ROM data.                                                                     | Extract a target-neutral matcher shell and pass an explicit parent-ROM or DLC-component target adapter. [VERIFIED: `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`]                                                                                      |
| PC parent match      | `GET /roms/{id}/pc-metadata-candidates` and `POST /roms/{id}/pc-metadata-selection` use review-first candidates and optimistic `rom.updated_at`. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`]                                                                                                         | No free-text search input, no candidate cover selection persistence.                                                            | Extend the PC matching contract to accept explicit title or ID query input and selected media IDs, maintaining the existing optimistic version. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`, locked D-07 through D-10]                                    |
| DLC match            | Component endpoints prove DLC kind and parent membership, then persist separate component metadata with `component.updated_at`. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`, `backend/handler/database/roms_handler.py`]                                                                              | Candidate media is returned but ignored by `metadata-selection`; candidates are recomputed at POST time from an implicit title. | Include entered search input and selected candidate-media descriptors in selection semantics, then persist/import only after explicit POST. [VERIFIED: `backend/handler/metadata/pc_match_handler.py`, `backend/endpoints/roms/pc_metadata.py`]                  |
| Existing local media | `RomComponentLocalMedia` represents a direct manifest image with mandatory source path/digest and only `cover`, `background`, or `gallery` roles. [VERIFIED: `backend/models/rom.py`]                                                                                                                        | Uploaded files and provider screenshots/video/audio have no source manifest member or digest and cannot fit this schema.        | Retain it for verified source-image promotion. Add a distinct general owned-component-media model for uploads and provider imports. [VERIFIED: `backend/models/rom.py`, locked D-05 and D-10]                                                                    |
| Component cover      | Selecting a manifest cover writes a Rom-level `path_cover_l/path_cover_s`, even though the record belongs to one component. [VERIFIED: `backend/handler/database/roms_handler.py`]                                                                                                                           | A DLC cover can affect parent presentation and cannot represent multiple isolated component covers safely.                      | Give the general owned-component-media model an explicit component cover role, render it first for DLC hero, and do not update parent cover columns from DLC workflows. [VERIFIED: `backend/handler/database/roms_handler.py`, locked D-09]                      |
| Parent Media tab     | `MediaTab` includes manual, screenshots, artwork and soundtrack patterns, but its screenshot and soundtrack write routes address legacy ROM-library paths. [VERIFIED: `frontend/src/v2/components/GameDetails/MediaTab.vue`, `backend/endpoints/roms/screenshot.py`, `backend/endpoints/roms/soundtrack.py`] | Reusing those write endpoints would violate immutable external storage.                                                         | Reuse only their v2 display/composition patterns. Implement component-owned upload/read/delete routes backed by owned storage. [VERIFIED: `backend/endpoints/roms/screenshot.py`, `backend/endpoints/roms/soundtrack.py`, locked D-05]                           |
| Parent notes         | `RomNote` and `/roms/{id}/notes` are ROM-scoped; `NotesTab` calls those routes and receives notes through `DetailedRomSchema`. [VERIFIED: `backend/models/rom.py`, `backend/endpoints/roms/notes.py`, `frontend/src/v2/components/GameDetails/NotesTab.vue`]                                                 | A DLC cannot have isolated notes without an ownership column and component routes.                                              | Add a component-note model or nullable component foreign key with unambiguous component-specific uniqueness and routes. Prefer a distinct `RomComponentNote` to avoid weakening the existing ROM note contract. [VERIFIED: `backend/models/rom.py`, locked D-06] |

## Standard Stack

| Layer    | Use                                                                         | Purpose                                                                                 | Why                                                                                                                                                                                                      |
| -------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend | Existing Vue 3, Vue Router, Pinia, vue-i18n, Vuetify-backed `R*` primitives | Detail tabs, dialog interaction, URL state, localized actions                           | This is the active v2 stack and is already used by Game Details and MatchRom. [VERIFIED: `CLAUDE.md`, `frontend/src/v2/views/GameDetails.vue`, `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`]  |
| Backend  | Existing FastAPI, SQLAlchemy 2, Alembic, owned resource handler             | Protected nested APIs, DB ownership, storage writes                                     | This follows the repository endpoint to handler to storage/model layering. [VERIFIED: `CLAUDE.md`, `.claude/skills/backend-development/SKILL.md`]                                                        |
| Tests    | Existing Vitest/Vue Test Utils and pytest                                   | UI target routing, dialog adapter behavior, API permission/containment, resource safety | Both frameworks already cover the relevant v2 and PC metadata modules. [VERIFIED: `frontend/src/v2/components/GameDetails/PcMetadataReview.test.ts`, `backend/tests/endpoints/roms/test_pc_metadata.py`] |

No package installation is required or recommended. [VERIFIED: codebase inspection]

## Architecture Patterns

### 1. One visual matcher, target-specific persistence adapters

```text
PC parent "Metadaten suchen" ─────┐
PC DLC "Metadaten suchen" ───────┼─> Shared MatchRom visual shell
DLC page ⋮ "ROM zuordnen" ───────┘    search + filters + grid/list + preview
                                           |
                                           v
                            MatchTarget adapter (explicit discriminated union)
                              |                              |
                              v                              v
                  parent PC endpoints                 nested DLC endpoints
                  candidate/apply to Rom              candidate/apply to component
                              |                              |
                              └──────── explicit confirmation ┘
                                           |
                                           v
                               owned component media import only
```

Use a discriminated frontend type such as `PcMatchTarget = { kind: "rom"; romId: number; label: string } | { kind: "component"; romId: number; componentId: number; label: string }`. It owns search, selection, apply, and refresh callbacks. The shared visual shell must never infer target type from a route or a numeric ID. [VERIFIED: target distinctions in `backend/endpoints/roms/pc_metadata.py`; target design is a prescriptive codebase-derived recommendation]

Extract reusable state and markup from `MatchRomDialog.vue` while preserving `MatchRomBodyGrid.vue`, `MatchRomBodyList.vue`, `MatchRomProviderFilter.vue`, and their cover-source choice behavior. Do not duplicate those bodies in a new `PcMetadataReview` surface. [VERIFIED: `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`, `frontend/src/v2/components/MatchRom/`, locked D-07]

The backend candidate route must accept the same explicit `search_term` and `search_by` inputs as the visual dialog. The current PC handler derives a title internally, so an exact match-dialog search cannot be implemented by client-side filtering alone. Preserve default derived-title behavior when no query is supplied, then validate and use user input server-side for provider lookup. [VERIFIED: `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`, `backend/handler/metadata/pc_match_handler.py`]

### 2. Explicit candidate confirmation and provider media import

`PcMetadataCandidate` currently includes provider, IDs, summary availability, and a list of media URLs, but response schemas intentionally omit raw fields and selection requests only carry candidate ID plus expected version. The handler recomputes candidates during selection. [VERIFIED: `backend/handler/metadata/pc_match_handler.py`, `backend/endpoints/responses/rom.py`, `backend/endpoints/roms/pc_metadata.py`]

Keep recomputation as the authority check, but make the POST include the exact search request and a bounded list of selected candidate-media references. Recompute with the same query, find the candidate, verify every selected media reference belongs to that candidate and has an allowed role/type, fetch or copy it through the owned resource handler, then create only component-owned media records. This avoids trusting browser-provided URLs and preserves review-first behavior. [VERIFIED: existing recomputation pattern in `backend/endpoints/roms/pc_metadata.py`; recommendation implements locked D-09 and D-10]

Provider media must be fetched only after the final confirm action. Page load, dialog opening, provider filtering, result preview, and closing the dialog must remain read-only with no owned-media side effect. [VERIFIED: `12-CONTEXT.md` D-10, `backend/endpoints/roms/pc_metadata.py`]

For remote media, use the repository's existing download/resource safeguards rather than browser URLs as persisted content. Reject unsafe schemes, enforce response-size and content-type limits, validate decoded image or media type, and write only beneath `RESOURCES_BASE_PATH` through an owned descriptor. A URL shown in a candidate response is not a persistence authority. [VERIFIED: `backend/handler/filesystem/resources_handler.py`, `.claude/skills/backend-development/SKILL.md`; specific fetch validation is a security-prescriptive recommendation]

### 3. Separate source-backed local images from owned component media

Keep `RomComponentLocalMedia` for Phase 11 local image promotion because it ties selection to immutable manifest `source_relative_path` and `source_sha256`. Do not make its source fields nullable for uploaded or provider media, because rescans use that evidence and current role replacement iterates all component records. [VERIFIED: `backend/models/rom.py`, `backend/handler/database/roms_handler.py`]

Create a separate `RomComponentOwnedMedia` entity, owned by `rom_components`, with at minimum: component ID, owned path, media category or role, MIME type, optional original filename, origin (`upload` or `provider`), optional provider identity, created/updated timestamps, and deterministic deletion ownership. Its cover, background, gallery/screenshot, artwork, soundtrack, and video categories should be explicit enums. It must never contain a source-library path. [VERIFIED: existing model constraints in `backend/models/rom.py`; prescriptive design for D-05 and D-10]

Use a component-scoped owned-media endpoint family, for example nested under `/roms/{rom_id}/pc-components/{component_id}/media`. Every route must resolve the component through the authorized parent and restrict writes to DLCs for this phase. File upload, list, replace-selection, deletion, and owned download are different operations and must each validate component ownership. [VERIFIED: nested component checks in `backend/endpoints/roms/pc_metadata.py`; prescriptive design for D-05 and D-11]

Existing generic screenshot and soundtrack upload APIs must not be reused as write paths because they authorize legacy `COVER_WRITE`, `SIDECAR_WRITE`, or `DELETE` against ROM filesystem storage. Their display patterns may be adapted after data is supplied through owned component APIs. [VERIFIED: `backend/endpoints/roms/screenshot.py`, `backend/endpoints/roms/soundtrack.py`]

### 4. Component-scoped notes, not save data

Use a new `RomComponentNote` table rather than adding optional `component_id` to `RomNote`. A distinct table keeps existing ROM-note uniqueness, indexes, response loading, and routes unchanged, makes component ownership mandatory, and prevents accidental parent-note reads from the DLC detail response. [VERIFIED: `backend/models/rom.py`, `backend/endpoints/roms/notes.py`; prescriptive design for D-06]

Mirror the `RomNote` title/content/public/tags/author/timestamp contract and ownership checks in nested component-note endpoints. Extract or parameterize only presentation/editor logic from `NotesTab.vue`, so the DLC tab calls component-note APIs and refreshes only its component state. Do not reuse `NotesTab` unchanged because it always uses parent `rom.id` endpoints and `DetailedRomSchema.all_user_notes`. [VERIFIED: `frontend/src/v2/components/GameDetails/NotesTab.vue`, `backend/endpoints/roms/notes.py`]

There is no DLC save-data tab, save counter, save/state upload, or save-data storage migration. Save data remains a parent-ROM concern. [VERIFIED: locked D-03, D-06, Deferred Ideas]

### 5. Detail page composition and actions

Keep `PcDlcDetails.vue` as the parent-owned route resolver. Extend `PcDlcDetail.vue` into the main page shell with URL-persisted `overview`, `files`, `media`, and `notes` tabs, a component-only data model, a back link to the parent, and an `RMenu` overflow action entry point. [VERIFIED: `frontend/src/v2/views/PcDlcDetails.vue`, `frontend/src/v2/views/GameDetails.vue`, `12-UI-SPEC.md`]

The Overview hero reads component metadata and owned/component-local media only. It must never use `parent.name`, parent `path_cover_*`, parent screenshot collections, or a flattened list from sibling components. The Files tab renders only `component.manifest_members`; downloads must use the existing external read/download authority and exact manifest identity, never raw relative paths or prefix guessing. [VERIFIED: `frontend/src/v2/components/GameDetails/PcDlcDetail.vue`, `frontend/src/v2/components/GameDetails/PcDlcFiles.vue`, `backend/models/rom.py`]

The PC Components list must use the same match-dialog launcher for the PC parent and for each DLC. The DLC page overflow invokes the identical launcher with the same DLC target. `PcMetadataReview.vue` becomes obsolete after parity is proven and should be removed rather than retained as a second candidate UI. [VERIFIED: `frontend/src/v2/components/GameDetails/PcComponents.vue`, `frontend/src/v2/components/GameDetails/PcMetadataReview.vue`, locked D-07 and D-08]

## Database, Schema, and Migration Implications

| Change                                      | Why                                                                                                                                                                                    | Migration/API work                                                                                                                                                                                                                                                         |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rom_component_owned_media` table and enums | Existing local-media columns require source manifest evidence and support image-only roles. [VERIFIED: `backend/models/rom.py`]                                                        | Add portable Alembic DDL with foreign key to `rom_components`, owned-resource indexes, and explicit role/origin enum values. Expose typed list and mutation response schemas, then run frontend type generation. [VERIFIED: `.claude/skills/backend-development/SKILL.md`] |
| `rom_component_notes` table                 | Current `rom_notes` is parent-ROM scoped by a required `rom_id`. [VERIFIED: `backend/models/rom.py`]                                                                                   | Add component foreign key, user foreign key, unique component/user/title constraint, public and component/user indexes, endpoint schemas and nested CRUD routes. [VERIFIED: `backend/models/rom.py`, `backend/endpoints/roms/notes.py`]                                    |
| Component response expansion                | Detail route receives `PcComponentSchema` from parent `DetailedRomSchema`. [VERIFIED: `backend/endpoints/responses/rom.py`, `frontend/src/v2/views/PcDlcDetails.vue`]                  | Add component-owned media and visible component notes to the schema, or provide dedicated child endpoints. Do not add parent notes or save data. Generate frontend types after the OpenAPI change. [VERIFIED: `CLAUDE.md`, locked D-03 and D-06]                           |
| Match request/selection expansion           | Current candidate fetch derives title and selection has only candidate ID/version. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`, `backend/handler/metadata/pc_match_handler.py`] | Add bounded search fields and selected candidate media references; use them consistently for parent and component targets. Preserve 409 optimistic-version handling. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`]                                                   |

Alembic revisions must be reviewed and prove both upgrade and downgrade on MariaDB and PostgreSQL. Do not rely on autogenerated DDL without checking enum, index, foreign-key, and downgrade behavior. [VERIFIED: `.claude/skills/backend-development/SKILL.md`]

## Don't Hand-Roll

| Problem                                 | Do not build                                              | Use instead                                                                                                | Why                                                                                                                                                                                                       |
| --------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Match-result layout and cover selection | A second PC-specific candidate dialog                     | Extracted `MatchRomDialog` shell plus existing `MatchRomBodyGrid`, `MatchRomBodyList`, and provider filter | It already implements the exact user-approved UX and avoids divergent filter/result behavior. [VERIFIED: `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`, `frontend/src/v2/components/MatchRom/`] |
| Dialog/menu/focus behavior              | Custom modal, custom context menu, custom Escape handling | `RDialog`, `RMenu`, and existing MatchRom overlay behavior                                                 | v2 primitives manage responsive overlay and input scope behavior. [VERIFIED: `.claude/skills/frontend-v2-input/SKILL.md`, `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`]                        |
| Source image selection                  | Re-reading arbitrary source paths from the client         | Existing manifest-bound local media candidate and preview flow                                             | It verifies type/member/component before copying to owned resources. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`]                                                                                  |
| Parent-style media writes               | Generic screenshot/soundtrack upload routes               | New owned component-media storage routes                                                                   | Existing generic routes write legacy ROM filesystem locations and are unsafe for immutable PC roots. [VERIFIED: `backend/endpoints/roms/screenshot.py`, `backend/endpoints/roms/soundtrack.py`]           |
| Note editing experience                 | A duplicated markdown editor                              | An extracted/parameterized NotesTab editor/index composite                                                 | This preserves the established editor, visibility, confirmation, and URL-state conventions while swapping API ownership. [VERIFIED: `frontend/src/v2/components/GameDetails/NotesTab.vue`]                |

## Common Pitfalls

### Pitfall 1: Reusing `MatchRomDialog` without changing its target contract

**What goes wrong:** Selecting a DLC result writes to the parent `Rom` because `onBodyConfirm` constructs a `SimpleRom` and invokes `romApi.updateRom`. [VERIFIED: `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`]

**Avoidance:** Make target type explicit in the component API and route every search/apply operation through an adapter. Unit-test that a DLC target never calls `updateRom`, and that a parent target never calls component selection routes. [VERIFIED: current generic behavior; test recommendation]

### Pitfall 2: Matching from a query but validating from a different derived title

**What goes wrong:** The user sees one search result list, but POST recomputes candidates with the implicit component folder title and rejects or applies a mismatched record. [VERIFIED: `backend/handler/metadata/pc_match_handler.py`, `backend/endpoints/roms/pc_metadata.py`]

**Avoidance:** Carry a bounded, normalized search request in candidate and selection calls. Recompute the selection server-side with the same request. [VERIFIED: current endpoint behavior; prescriptive recommendation]

### Pitfall 3: Letting provider URLs become persistent media authority

**What goes wrong:** The frontend displays or saves a remote provider URL as a DLC asset, causing unstable media, SSRF exposure, or unreviewed external content. [VERIFIED: candidate media are raw URLs in `backend/handler/metadata/pc_match_handler.py`]

**Avoidance:** Persist only a copied, validated owned resource after explicit confirmation. Server-side selection verifies candidate membership and resource type. [VERIFIED: locked D-10; prescriptive recommendation]

### Pitfall 4: Extending manifest-bound local media for uploads

**What goes wrong:** Nullable source digest/path breaks rescan guarantees and can cause role replacement to delete media from other components because existing logic iterates all components. [VERIFIED: `backend/models/rom.py`, `backend/handler/database/roms_handler.py`]

**Avoidance:** Keep source-backed media and uploaded/provider-owned media in different models and explicitly scope every replacement query to the component. [VERIFIED: codebase inspection]

### Pitfall 5: Borrowing parent data in a child view

**What goes wrong:** A matched DLC shows the parent cover, notes, screenshots, save counts, or media because Game Details data is ROM-wide. [VERIFIED: `frontend/src/v2/views/GameDetails.vue`, `backend/endpoints/responses/rom.py`]

**Avoidance:** Build DLC tab props from the resolved component only. Add tests containing contrasting parent/sibling/DLC data. [VERIFIED: `frontend/src/v2/views/PcDlcDetails.vue`, locked D-04 and D-06]

### Pitfall 6: Reusing legacy write endpoints for the Media tab

**What goes wrong:** Screenshot/soundtrack uploads reach ROM filesystem paths and violate the external-root policy. [VERIFIED: `backend/endpoints/roms/screenshot.py`, `backend/endpoints/roms/soundtrack.py`]

**Avoidance:** New DLC media write routes must have owned storage as their only filesystem target. Include source mutation inventory assertions for every new endpoint and UI feature. [VERIFIED: `frontend/src/v2/sourceMutationControls.test.ts`, locked D-05]

## Code Examples

### Typed match target adapter boundary

```ts
type PcMatchTarget =
  | { kind: "rom"; romId: number; label: string }
  | { kind: "component"; romId: number; componentId: number; label: string };

async function applyPcMatch(target: PcMatchTarget, selection: MatchSelection) {
  return target.kind === "rom"
    ? romApi.selectPcMetadataCandidate({ romId: target.romId, selection })
    : romApi.selectPcComponentMetadataCandidate({
        romId: target.romId,
        componentId: target.componentId,
        selection,
      });
}
```

This follows the existing split between parent and component selection routes, while preventing accidental parent persistence. [VERIFIED: `frontend/src/services/api/rom.ts`, `backend/endpoints/roms/pc_metadata.py`]

### Component-only route resolution

```ts
const selectedComponent = parent.components?.find(
  (candidate) => candidate.id === componentId && candidate.kind === "dlc",
);
if (!selectedComponent) state.value = "unavailable";
```

Continue resolving from the fetched parent rather than treating the child route ID as authority. [VERIFIED: `frontend/src/v2/views/PcDlcDetails.vue`]

### Owned-media persistence boundary

```text
explicit confirm or upload
  -> authenticated nested component endpoint
  -> parent/component containment and MIME/size validation
  -> RomM-owned resource write
  -> component-owned DB record
  -> detail refresh
```

There must be no source root path, raw client path, or implicit provider import in this sequence. [VERIFIED: locked D-05 and D-10; existing owned write pattern in `backend/handler/filesystem/resources_handler.py`]

## Validation Architecture

### Test Framework

| Property           | Value                                                                                                                                                                         |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend framework | Vitest with Vue Test Utils. [VERIFIED: `frontend/vitest.config.ts`, `frontend/src/v2/components/GameDetails/PcMetadataReview.test.ts`]                                        |
| Backend framework  | pytest. [VERIFIED: `backend/tests/endpoints/roms/test_pc_metadata.py`]                                                                                                        |
| Quick frontend run | `cd frontend && npm run test -- src/v2/components/GameDetails src/v2/components/Dialogs src/v2/components/MatchRom src/v2/views/PcDlcDetails.test.ts` [VERIFIED: `CLAUDE.md`] |
| Quick backend run  | `cd backend && uv run pytest tests/endpoints/roms/test_pc_metadata.py tests/handler/metadata/test_pc_match_handler.py -q` [VERIFIED: existing test paths]                     |
| Static checks      | `cd frontend && npm run typecheck`; `trunk fmt --no-fix` and `trunk check --no-fix` for touched files. [VERIFIED: `CLAUDE.md`]                                                |

### Phase Behavior to Test Map

| Behavior                                                                  | Test type                    | Required proof                                                                                                                                                                                      |
| ------------------------------------------------------------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parent and DLC `Metadaten suchen` open the same visual matcher            | Vue unit                     | Assert both launch paths mount the shared matcher with different typed targets, not `PcMetadataReview`. [VERIFIED: `frontend/src/v2/components/GameDetails/PcComponents.vue`, locked D-07 and D-08] |
| DLC matcher cannot call generic `updateRom`                               | Vue unit                     | Spy on API adapter, confirm only nested component selection is called. [VERIFIED: `MatchRomDialog.vue` current risk]                                                                                |
| Explicit query returns/revalidates the same parent or component candidate | pytest endpoint/handler      | Query, select with same request, then prove mismatched candidate/query is rejected. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`]                                                             |
| Selected provider media is not persisted until explicit confirmation      | pytest endpoint              | Snapshot owned storage/model state across GET, filter/search, cancel, then assert changes only after valid POST. [VERIFIED: locked D-10]                                                            |
| Component media upload/import remains owned and isolated                  | pytest endpoint/integration  | Verify parent and sibling media records/paths stay unchanged, source manifest/tree remains byte-identical. [VERIFIED: locked D-05; `backend/models/rom.py`]                                         |
| Component notes are isolated                                              | pytest endpoint and Vue unit | Parent and sibling notes do not appear; authorization and owner-only update/delete rules apply. [VERIFIED: `backend/endpoints/roms/notes.py`, locked D-06]                                          |
| DLC tab shell remains safe                                                | Vue unit                     | Invalid/stale/foreign/non-DLC route shows escape state; tabs omit save data and parent media. [VERIFIED: `frontend/src/v2/views/PcDlcDetails.vue`, `12-UI-SPEC.md`]                                 |
| Files/downloads are exact component members                               | Vue unit plus endpoint test  | No parent files or raw-path download; each action is bounded to a manifest member. [VERIFIED: `frontend/src/v2/components/GameDetails/PcDlcFiles.vue`, `backend/models/rom.py`]                     |
| Source mutation inventory                                                 | Static regression test       | Extend `sourceMutationControls.test.ts` for new matcher/media/note routes and ensure no forbidden source-mutation seams. [VERIFIED: `frontend/src/v2/sourceMutationControls.test.ts`]               |

### Manual Verification Gate

Run the dialog and every DLC tab in dark and light themes at xs, sm, md, and xl. Verify mouse, touch, keyboard, and gamepad navigation through overflow menu, dialog filters, grid/list result selection, cover selection, uploads, notes, and destructive owned-media deletion. Confirm that closing or cancelling the dialog has no metadata/media side effect. [VERIFIED: `.claude/skills/pre-pr-verification/SKILL.md`, `.claude/skills/frontend-v2-input/SKILL.md`]

### Database and Type Generation Gate

If models or endpoint schemas change, run migration upgrade and downgrade checks for MariaDB and PostgreSQL, regenerate `frontend/src/__generated__/` from OpenAPI, and then run frontend typecheck. [VERIFIED: `.claude/skills/backend-development/SKILL.md`, `CLAUDE.md`]

## Security Domain

| ASVS category                      | Applies | Control                                                                                                                                                                                                                                                                                          |
| ---------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| V4 Access Control                  | Yes     | Protect every nested route with the established read/write scopes, call `assert_rom_visible`, and prove component belongs to the parent before all reads/writes. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`]                                                                             |
| V5 Input Validation                | Yes     | Strict path/ID constraints, title/query length limits, manifest membership validation, MIME/content validation, and server-side candidate-media membership checks. [VERIFIED: endpoint `Path(ge=1)` patterns in `backend/endpoints/roms/pc_metadata.py`; remaining controls are required design] |
| V10 Malicious Code / File Handling | Yes     | Accept uploads only into owned storage, restrict media categories/types/sizes, and never execute or extract uploaded or provider media. [VERIFIED: immutable storage constraints in `.planning/REQUIREMENTS.md`; required design]                                                                |
| V12 File and Resources             | Yes     | Keep external roots read-only, no raw path authority, and stream downloads through existing authorized capabilities. [VERIFIED: `.planning/REQUIREMENTS.md`, `frontend/src/v2/sourceMutationControls.test.ts`]                                                                                   |

## Environment Availability

| Dependency                             | Required by                                 |            Available | Version    | Fallback                                                                                                                                  |
| -------------------------------------- | ------------------------------------------- | -------------------: | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Node.js                                | frontend typecheck, Vitest, generated types |                  Yes | v24.19.0   | None required. [VERIFIED: local command]                                                                                                  |
| npm                                    | frontend scripts                            |                  Yes | 11.17.0    | None required. [VERIFIED: local command]                                                                                                  |
| Python `uv`                            | pytest, Alembic                             |                  Yes | 0.12.3     | None required. [VERIFIED: local command]                                                                                                  |
| Existing configured metadata providers | matcher result data                         | Deployment-dependent | Not probed | Dialog must show existing unavailable-provider result and remain non-mutating. [VERIFIED: `backend/handler/metadata/pc_match_handler.py`] |

## Assumptions Log

| #   | Claim                                                                                                                                  | Section                | Risk if wrong                                                                                                                                            |
| --- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1  | Provider image/video import can be supported through the existing owned resource handler after adding bounded remote-fetch validation. | Architecture Pattern 2 | The exact helper may need a new internal resource-handler method, but no user decision changes. [ASSUMED]                                                |
| A2  | A distinct `RomComponentOwnedMedia` model is lower-risk than expanding `RomComponentLocalMedia`.                                       | Architecture Pattern 3 | The final model may instead be a carefully migrated generalized model, but it must preserve source-evidence semantics and component isolation. [ASSUMED] |

## Open Questions

None. The user selected provider-media import after explicit confirmation, component-only notes, no DLC saves, and the existing match dialog as the mandatory visual flow. Exact categories, hero fallback, and responsive composition remain delegated discretion. [VERIFIED: `12-CONTEXT.md`]

## Sources

### Primary

- `12-CONTEXT.md` and `12-UI-SPEC.md`, locked product and design decisions. [VERIFIED: local planning artifacts]
- `frontend/src/v2/components/Dialogs/MatchRomDialog.vue` and `frontend/src/v2/components/MatchRom/`, existing match UI and generic persistence behavior. [VERIFIED: codebase]
- `backend/endpoints/roms/pc_metadata.py`, `backend/handler/metadata/pc_match_handler.py`, and `backend/handler/database/roms_handler.py`, current PC metadata review, candidate, and persistence contracts. [VERIFIED: codebase]
- `backend/models/rom.py`, component, local-media, and parent-note data contracts. [VERIFIED: codebase]
- `frontend/src/v2/views/PcDlcDetails.vue`, `PcDlcDetail.vue`, and `PcDlcFiles.vue`, current nested route and child presentation. [VERIFIED: codebase]
- `.claude/skills/backend-development/SKILL.md`, `frontend-v2-components/SKILL.md`, `frontend-v2-input/SKILL.md`, and `pre-pr-verification/SKILL.md`, repository implementation and verification constraints. [VERIFIED: local skill documentation]

## Metadata

**Confidence breakdown:**

- Existing stack and contracts: HIGH, directly inspected code and repository instructions. [VERIFIED: cited codebase files]
- Matcher target-adapter architecture: HIGH, it is required to avoid the verified generic parent-write path and satisfy locked D-07 through D-09. [VERIFIED: cited codebase files and `12-CONTEXT.md`]
- Owned media and note model design: MEDIUM, the gap is verified but the exact migration shape is an implementation design choice. [VERIFIED: cited model files; see A1-A2]
- Pitfalls and validation: HIGH, derived from the existing tests, storage boundary, and verified endpoint behavior. [VERIFIED: cited codebase files]

**Research date:** 2026-09-03
**Valid until:** 2026-10-03, unless the active Phase 12 implementation changes its API contracts.
