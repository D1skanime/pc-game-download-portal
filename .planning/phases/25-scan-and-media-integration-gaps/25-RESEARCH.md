# Phase 25: Scan and Media Integration Gaps - Research

**Researched:** 2026-10-07  
**Domain:** RomM scan, PC component classification, provider enrichment, owned media, and v2 operation integration  
**Confidence:** HIGH

## User Constraints

- Research canonical Linux checkout /home/d1sk/romm via team4s-linux. [VERIFIED: user request and preflight]
- Do not modify source code or deploy. [VERIFIED: user request]
- Do not assume Phase 24 is complete. [VERIFIED: user request; .planning/ROADMAP.md:688-710; 24-VALIDATION.md:1-31]
- Reuse PlatformStorageMapping, the v2 operation contract, the existing socket lifecycle, provider resolver, and owned-media persistence. [VERIFIED: user request; 24-CONTEXT.md:43-54]

## Summary

Phase 25 is an integration-gap closure phase, not a new scan architecture. Phase 24 added frontend contracts, provider selection, lifecycle observers, policy vocabulary, and metadata/media-only flags, but its own records leave backend/provider wiring, caller migration, final verification, and MariaDB/browser gates unresolved. [VERIFIED: 24-09-SUMMARY.md:1-10; 24-13-SUMMARY.md:104-133; 24-14-SUMMARY.md:39-68]

The confirmed live defect is in refresh_provider_owned_media: it reads rom.metadata_source, but Rom has no mapped metadata_source; RomComponentMetadata does. Component selection/database paths use the component field for provider/manual state. The fix must supply parent provider provenance explicitly or through an existing parent authority, not copy the component field and not add a parallel metadata model. [VERIFIED: backend/handler/metadata/rom_media.py:102-110; backend/models/rom.py:388-414,812-930; backend/handler/database/roms_handler.py:2522-2557]

PC discovery supports exact top-level base, update, dlc, expansion(s), hotfix, language-pack, and extra, plus named children under DLC/expansion. OST is recognized by generic soundtrack category matching but not as a PC component layout. NFO has no component kind or parser branch. [VERIFIED: backend/handler/filesystem/roms_handler.py:136-184,542-640; backend/models/rom.py:86-110; backend/tests/handler/filesystem/test_roms_handler.py:46-48,1791-1977]

**Primary recommendation:** close parent provider resolution, per-ROM/component result isolation, and explicit OST/NFO characterization through existing authorities, preserving the current mapping, operation, socket, provider, PC/DLC, and owned-media boundaries. [VERIFIED: 24-07-REUSE-MATRIX.md:1-15; recommendation from inspected gaps]

## Architectural Responsibility Map

| Capability                                 | Primary Tier       | Secondary Tier     | Rationale                                                                                                                                                                                                                   |
| ------------------------------------------ | ------------------ | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Storage scope/mapping revision             | Database / Storage | API / Backend      | Mapping UI/APIs and mapped scan commands own root, revision, preview, and source boundary. [VERIFIED: PlatformStorageMapping.vue:39-355; backend/handler/scan_command.py]                                                   |
| Operation normalization/provider selection | Browser / Client   | API / Backend      | OperationRequest, operations translator, and useProviderResolution normalize v2 inputs before legacy payloads. [VERIFIED: frontend/src/v2/data/contracts.ts:80-288; operations.ts:227-289; useProviderResolution.ts:72-161] |
| Scan execution/persistence                 | API / Backend      | Database / Storage | Socket enqueues mapped scans; scan/database handlers identify, enrich, and persist. [VERIFIED: backend/endpoints/sockets/scan.py:1080-1270; backend/handler/scan_handler.py:512-700]                                        |
| PC classification                          | Database / Storage | API / Backend      | Read-only filesystem manifests are reconciled into component rows. [VERIFIED: backend/handler/filesystem/roms_handler.py:542-640]                                                                                           |
| Provider media/owned persistence           | API / Backend      | Database / Storage | Existing metadata handlers normalize/download; parent/component repositories persist owned media. [VERIFIED: rom_media.py:65-131; steam_owned_media.py:76-140; roms_handler.py:2786-2831]                                   |
| Socket progress/v2 state                   | Browser / Client   | API / Backend      | useScanLifecycle is the sole subscriber/state synchronizer. [VERIFIED: useScanLifecycle/index.ts:40-224]                                                                                                                    |

## Exact Integration Gaps

### Provider resolution for owned media

- Parent refresh directly dereferences the missing Rom.metadata_source. [VERIFIED: backend/handler/metadata/rom_media.py:102-110]
- Component metadata has metadata_source and writes it during component candidate application. [VERIFIED: backend/models/rom.py:388-414; backend/handler/database/roms_handler.py:2522-2537]
- Steam scan reconciliation already supplies explicit "steam" to the common candidate discovery path. [VERIFIED: backend/handler/metadata/steam_owned_media.py:83-90; backend/handler/scan_handler.py:1453-1486]
- Parent owned-media uniqueness is (rom_id, provider, provider_media_id) and must remain unchanged. [VERIFIED: backend/models/rom.py:489-559]

Plan consequence: pass resolved parent provider/media patch explicitly into the existing parent refresh/reconcile path. Do not infer parent provenance from component metadata. Adding a parent metadata_source column is an open schema decision, not a default fix. [ASSUMED: parent field-level provenance requirement is not locked]

### Per-item error isolation

- Provider fetches are isolated per ROM with gather(return_exceptions=True). [VERIFIED: backend/handler/scan_handler.py:1097-1137]
- Media-only catches per-ROM exceptions but only logs and omits the item from aggregate stats, with no item result/diagnostic. [VERIFIED: backend/endpoints/sockets/scan.py:1127-1173]
- PC component enumeration/sync/linking is under one broad try, so a component-level failure can abandon the whole component reconciliation for that ROM. [VERIFIED: backend/handler/scan_handler.py:672-697]
- Automatic IGDB/Steam component links have no per-component exception boundary. [VERIFIED: backend/handler/scan_handler.py:99-153]
- Optional IGDB component-media imports isolate downloads and clean failed paths, but do not report typed outcomes. [VERIFIED: backend/endpoints/sockets/scan.py:176-223]
- Frontend already defines stable item outcomes/diagnostics, while backend remains aggregate stats plus ROM events. [VERIFIED: frontend/src/v2/data/contracts.ts:226-287; backend/endpoints/sockets/scan.py:288-336]

Plan consequence: add the smallest backward-compatible backend item-result bridge, correlate by stable ROM/component identity, preserve existing scan:* events, and never match by arrival order. [VERIFIED: 24-CONTEXT.md:45-64]

### PC folder classification: OST, DLC, Expansion, NFO

- Exact one-part top-level names are classified; unknown/nested names return UNRESOLVED. [VERIFIED: backend/handler/filesystem/roms_handler.py:172-184]
- expansion and expansions already map to DLC, with named child components. [VERIFIED: roms_handler.py:621-640; test_roms_handler.py:1791-1884]
- OST is a soundtrack alias only in category_matches, not in PC component parsing. [VERIFIED: roms_handler.py:136-140; test lines 46-48]
- NFO is absent from RomComponentKind and the manifest builder. [VERIFIED: models/rom.py:102-110; roms_handler.py:542-640]

Plan consequence: add read-only OST/NFO characterization fixtures first, then lock product behavior. Do not turn descriptive folders into DLC/extra or add a new component kind/table without proving existing local-media/metadata contracts cannot express the requirement. [ASSUMED: desired OST/NFO semantics are not locked]

### Reuse boundaries and Phase 24 status

- The v2 contract already contains scopes, profiles, policies, capabilities, preview, retry, and stable item IDs. [VERIFIED: frontend/src/v2/data/contracts.ts:80-288]
- Component scopes are deliberately rejected by the generic translator and remain on specialized PC/DLC APIs. [VERIFIED: frontend/src/v2/data/operations.ts:204-225,291-323; 24-13-SUMMARY.md:61-83]
- useScanLifecycle remains the only socket subscriber; useLibraryOperation observes/wraps it. [VERIFIED: useScanLifecycle/index.ts:40-64; 24-08-SUMMARY.md:47-103]
- Phase 24 Plan 09 explicitly leaves backend scan/provider wiring for follow-up. [VERIFIED: 24-09-SUMMARY.md:1-10]
- Roadmap records Phase 24 as 7/12 executed, with 24-07, 24-09, 24-10, 24-11, and 24-12 open. [VERIFIED: .planning/ROADMAP.md:688-710]

## Recommended Plan Slices

1. Characterization and confirmed-error regression: parent refresh with no Rom.metadata_source, explicit Steam/non-Steam provider inputs, and separation from component provenance. [VERIFIED: rom_media.py:102-131; test_steam_owned_media.py; test_pc_metadata.py]
2. Provider/media integration: reuse resolve_steam_pc_enrichment, discover_provider_media, existing reconcile/import methods, optimistic versions, cleanup intents, and parent/component catalogs. [VERIFIED: pc_steam_enrichment.py:14-74; rom_media.py:23-131; roms_handler.py:2786-2831]
3. PC classification policy: fixtures for OST/ost, DLC, Expansion/expansions, NFO, mixed and nested cases; preserve exact matching, traversal rejection, deterministic ordering, and source digest invariance. [VERIFIED: roms_handler.py:172-184,542-640; existing test structure]
4. Per-item result/isolation bridge: isolate component enumeration/linking failures; map outcomes to OperationItemOutcome/OperationDiagnostic; preserve aggregate stats and existing socket events. [VERIFIED: scan_handler.py:99-153,672-697,1097-1137; contracts.ts:226-287]
5. Verification/UAT: source-mocked tests first; then MariaDB-backed tests, frontend suite/typecheck/build, and browser UAT for classic, PC parent, DLC/expansion, media-only, provider failure, partial retry, manual protection, no source mutation, themes, responsive/input modes. [VERIFIED: 24-VALIDATION.md:12-31; 24-13-SUMMARY.md:104-133; 24-14-SUMMARY.md:39-68]

## Explicit Anti-Duplication Constraints

- No second storage profile/model. Reuse PlatformStorageMapping, mapping APIs, mapped commands, preview/version checks. [VERIFIED: 24-07-REUSE-MATRIX.md:6-15]
- No second operation contract. Extend contracts.ts/operations.ts only for missing backend/result/provenance vocabulary. [VERIFIED: contracts.ts:80-288]
- No second socket lifecycle/subscriber. useScanLifecycle remains event authority. [VERIFIED: useScanLifecycle/index.ts:40-64]
- No second provider resolver. Extend existing v2 resolver and backend enrichment helpers. [VERIFIED: useProviderResolution.ts:72-161; pc_steam_enrichment.py:27-74]
- Do not infer parent provider from RomComponentMetadata.metadata_source; they are separate persistence domains. [VERIFIED: models/rom.py:388-414,812-930]
- No generic component scan path. Keep specialized PC/DLC matcher APIs. [VERIFIED: operations.ts:204-225; 24-13-SUMMARY.md:73-83]
- No second owned-media catalog/cleanup path. Reuse RomOwnedMedia, RomComponentOwnedMedia, reconcile/import/version/cleanup authorities. [VERIFIED: models/rom.py:489-565; roms_handler.py:2786-2831]
- Do not let provider/media failure erase successful metadata or sibling results. [VERIFIED: scan_handler.py:1097-1137; gap at 672-697]
- Do not claim Phase 24 completion before blocked gates and human UAT are rerun. [VERIFIED: .planning/ROADMAP.md:688-710; 24-VALIDATION.md:27-31]

## Common Pitfalls

- Parent/component provenance confusion: parent refresh fails before reconciliation because it reads a component-only field. [VERIFIED: rom_media.py:102-110; models/rom.py:388-414]
- Aggregate success hides item failure: media-only failures are warnings/omissions, not typed outcomes. [VERIFIED: scan.py:1145-1173]
- One component aborts siblings: broad try wraps the whole component block. [VERIFIED: scan_handler.py:672-697]
- OST/NFO accidental component creation: broadening weak folder inference crosses the current safety boundary. [VERIFIED: roms_handler.py:172-184; semantics recommendation is [ASSUMED]]
- Verification theater: frontend focus passes while MariaDB, build, and browser gates remain blocked/unrun. [VERIFIED: 24-VALIDATION.md:12-31]

## Code Examples

Existing explicit provider shape: source = _steam_media_source(patch); candidates = discover_provider_media("steam", source). [VERIFIED: backend/handler/metadata/steam_owned_media.py:20-29,76-90]

Existing component boundary: component operations throw an OperationTranslationError requiring the PC/DLC matcher API. [VERIFIED: frontend/src/v2/data/operations.ts:204-225]

Existing exact layout policy: parse_pc_component_layout returns UNRESOLVED for non-one-part paths and otherwise uses the explicit PC_COMPONENT_LAYOUTS map. [VERIFIED: backend/handler/filesystem/roms_handler.py:172-184]

## Runtime State Inventory

Not applicable. This is not a rename/refactor/migration phase. [VERIFIED: phase scope]

## Environment Availability

| Dependency | Required By               | Available            | Version                       | Fallback                                                                                                       |
| ---------- | ------------------------- | -------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Python     | Backend inspection/tests  | yes                  | 3.10.12                       | Repository .venv where configured; guide targets 3.13+. [VERIFIED: SSH probe; CLAUDE.md]                       |
| Node/npm   | Frontend tests/typecheck  | no on non-login PATH | not exposed                   | Use Phase 24 explicit Node path /home/d1sk/.nvm/versions/node/v24.19.0/bin. [VERIFIED: 24-08-SUMMARY.md:86-91] |
| MariaDB    | Backend integration tests | no                   | unavailable at 127.0.0.1:3306 | Keep source-mocked tests separate and mark integration blocked. [VERIFIED: 24-VALIDATION.md:18-25; SSH probe]  |
| Redis CLI  | Socket/job diagnostics    | no CLI               | not exposed                   | Use approved repository service tooling only. [VERIFIED: SSH probe]                                            |
| GSD SDK    | Phase helper              | no on non-login PATH | command not found             | Direct inspection was used; no source change was made. [VERIFIED: SSH probe]                                   |

## Validation Architecture

| Property       | Value                                                                                                                                                                            |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend        | pytest/pytest-asyncio; repository .venv/bin/pytest. [VERIFIED: CLAUDE.md; 24-14-SUMMARY.md:24-37]                                                                                |
| Frontend       | Vitest and vue-tsc. [VERIFIED: CLAUDE.md; 24-VALIDATION.md:12-17]                                                                                                                |
| Quick backend  | .venv/bin/pytest backend/tests/handler/filesystem/test_roms_handler.py backend/tests/handler/metadata/test_steam_owned_media.py -q. [VERIFIED: paths exist; recommended command] |
| Quick frontend | npm run test -- --run src/v2/data/operations.test.ts src/v2/composables/useProviderResolution.test.ts src/v2/composables/useLibraryOperation.test.ts. [VERIFIED: Phase 24 focus] |
| Full gate      | frontend suite, backend integration with MariaDB, production build, browser UAT, each recorded separately. [VERIFIED: 24-VALIDATION.md:12-31]                                    |

### Phase Requirements to Test Map

| Seam                       | Test                                                                                    | Exists                                                             |
| -------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Parent provider resolution | Refresh never reads Rom.metadata_source and uses explicit provider                      | Add/extend backend/tests/handler/metadata/test_rom_media.py        |
| Media item failure         | One ROM fails while sibling succeeds with typed result                                  | Partial backend/tests/endpoints/sockets/test_scan.py -k media_only |
| OST/DLC/Expansion/NFO      | Classification and source digest invariance                                             | Extend backend/tests/handler/filesystem/test_roms_handler.py       |
| Component isolation        | One component failure does not abort sibling                                            | Add backend/tests/handler/test_scan_handler.py                     |
| v2 boundary                | Component operation stays specialized; generic scan compatible                          | Existing operations.test.ts and sourceMutationControls.test.ts     |
| UAT                        | Classic/PC/DLC/media-only/provider failure/retry/manual/source immutability/input modes | Deferred browser procedure                                         |

### Wave 0 Gaps

- Parent provider-resolution regression. [VERIFIED: model/handler mismatch]
- OST/NFO characterization fixtures and locked policy. [VERIFIED: no parser tests]
- Per-component failure-isolation test. [VERIFIED: broad try boundary]
- Backend-to-v2 item-result correlation test. [VERIFIED: frontend vocabulary exists; backend aggregate events]
- MariaDB test service. [VERIFIED: 24-VALIDATION.md:18-25]

## Security Domain

V2, V3, V4, V5, and V6 apply. Preserve protected scan/media routes, scope checks, expected-version checks, HTTPS provider URL validation, bounded downloads, relative-path checks, SHA-256 identities, and read-only source capabilities. [VERIFIED: backend/endpoints/roms/media.py:59-81; backend/endpoints/sockets/scan.py:1568-1631; backend/handler/metadata/rom_media.py:32-99; backend/handler/filesystem/roms_handler.py:172-184,542-548]

## Sources

### Primary (HIGH confidence)

- Current model/handlers: backend/models/rom.py; backend/handler/metadata/rom_media.py; steam_owned_media.py; pc_steam_enrichment.py; backend/handler/scan_handler.py.
- Current scan/classification/socket boundaries: backend/handler/filesystem/roms_handler.py; backend/endpoints/sockets/scan.py.
- Current v2 boundaries: frontend/src/v2/data/contracts.ts; operations.ts; useProviderResolution.ts; useScanLifecycle/index.ts.
- Phase 24 evidence: 24-CONTEXT.md; 24-07-REUSE-MATRIX.md; 24-08-SUMMARY.md; 24-09-SUMMARY.md; 24-13-SUMMARY.md; 24-14-SUMMARY.md; 24-VALIDATION.md; .planning/ROADMAP.md.

### Secondary (MEDIUM confidence)

- backend/tests/handler/filesystem/test_roms_handler.py:46-48,1725-1977.
- backend/tests/endpoints/roms/test_pc_metadata.py:213-321.
- frontend/src/v2/sourceMutationInventory.test.ts and sourceMutationControls.test.ts.

### Tertiary (LOW confidence)

- None for core conclusions. OST/NFO product semantics and final event shape remain open questions.

## Assumptions Log

| #   | Assumption                                                                                  | Risk                                                             |
| --- | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| A1  | OST is soundtrack/media evidence, not a new PC component kind.                              | Wrong catalog/download surface.                                  |
| A2  | NFO is a metadata sidecar, not a downloadable component.                                    | Missing deliberate NFO behavior.                                 |
| A3  | Parent provider is passed explicitly rather than persisted as a new parent metadata_source. | Schema migration may be required if parent provenance is locked. |

## Open Questions

1. Decide exact OST behavior: soundtrack candidate, component, or ignored. [VERIFIED: no current PC OST branch; recommendation [ASSUMED]]
2. Decide exact NFO behavior: informational sidecar, metadata input, or manifest member. [VERIFIED: no current branch; recommendation [ASSUMED]]
3. Decide whether parent provider identity is operation-scoped or persisted. [VERIFIED: parent field absent; recommendation [ASSUMED]]
4. Decide the smallest backward-compatible event shape for item outcomes. [VERIFIED: frontend typed vocabulary and backend aggregate events; recommendation [ASSUMED]]

## Metadata

**Confidence breakdown:** Standard stack/reuse HIGH; architecture HIGH; confirmed defect/pitfalls HIGH; OST/NFO semantics and final event shape MEDIUM pending decisions. [VERIFIED: inspected code and artifacts]

**Research date:** 2026-10-07  
**Valid until:** 2026-10-21, or until scan/media/provider contracts change.
