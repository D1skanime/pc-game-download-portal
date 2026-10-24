# Roadmap: RomM PC Library

## Overview

Milestone v1.2 adds a cross-platform Tauri/Rust downloader to the existing
immutable PC-library model. It delivers selected original files directly to a
user-chosen Windows or Linux/Bazzite destination, resumes safely, verifies every
file, and never creates a whole-game ZIP or changes the NAS library.

## Phases

- [x] **Phase 1: Immutable Storage Foundation** - Establish portable root and mapping identity plus canonical, adversarially tested path resolution. (completed 2026-08-05)
- [x] **Phase 2: Read-only Policy Boundary** - Enforce one server-side operation policy and separate source storage from every writable RomM location. (completed 2026-08-10)
- [x] **Phase 3: Mapping Administration Contracts** - Provide authorized, audited APIs for roots, safe browsing, and mapping lifecycle operations. (completed 2026-08-11)
- [x] **Phase 4: V2 Storage Design Specification** - Derive a RomM-native design contract for the new storage surfaces from read-only Team4s principles. (completed 2026-08-12)
- [x] **Phase 5: Preview and Read-path Cutover** - Make preview, scanning, watching, hashing, streaming, and downloading mapping-aware and non-mutating. (completed 2026-08-12)
- [ ] **Phase 6: Safe Lifecycle and Legacy Migration** - Make catalog removal and legacy-layout migration explicit, reversible, and source-safe.
- [ ] **Phase 7: V2 Storage Administration Experience** - Deliver accessible root, browser, mapping, and preview workflows in the sole active UI.
- [x] **Phase 8: Bounded V1 Removal** - Remove the frozen frontend and compatibility paths behind a dedicated v2 regression gate. (completed 2026-08-27)
- [x] **Phase 9: Operational Immutability Proof** - Functionally accepted after completed isolated UAT (2026-08-31). The optional synthetic-harness replacement is deferred from this milestone.
- [ ] **Phase 10: PC Integration Model** - Model immutable PC game components and manifests, then enrich recognized games through safe metadata sources.
- [x] **Phase 14: Immutable Download Manifests** - Turn selected existing PC components into stable, hash-backed download manifests. (completed 2026-09-16)
- [x] **Phase 15: Direct Resumable Transfer** - Serve manifest files directly with snapshot-bound HTTP Range resume and no ZIP packaging. (completed 2026-09-16)
- [ ] **Phase 16: Cross-platform Desktop Client** - Retain the Tauri/Rust Windows and Linux/Bazzite prototype for later cleanup; mandatory installers and desktop distribution are cancelled product scope.
- [x] **Phase 17: Browser Download Manager** - Deliver browser-only direct downloads from v2 with server-validated component or allowed-file selection, one immutable manifest, original direct member downloads, a standard attachment baseline, an optional capability-detected File System Access enhancement, controlled queues, and read-only source safety. Phase 16 installer UAT does not block this phase. (completed 2026-09-18)

## Phase Details

### Phase 1: Immutable Storage Foundation

**Goal**: Operators have a portable storage model whose roots and relative mappings cannot resolve outside the approved immutable library.
**Depends on**: Nothing (first phase)
**Requirements**: ROOT-01, ROOT-02, ROOT-03, ROOT-04, PATH-01, PATH-02, PATH-03, PATH-04, PATH-05, TEST-01
**Success Criteria** (what must be TRUE):

1. An operator can register the deployment-mounted library as an active `external_read_only` root and see its safe health state without any probe creating content.
2. A platform location is stored only as a normalized relative path, separate from the deployment-owned container root and without a NAS host path.
3. Valid nested and Unicode directories resolve inside the root, while absolute, drive, UNC, traversal, missing, file-target, disabled-root, and symlink cases fail closed.
4. The storage schema upgrades across MariaDB, MySQL, and PostgreSQL without changing any source-library content.

**Plans:** 7/7 plans complete

Plans:

- [x] `01-01-PLAN.md` - Immutable storage models and portable 0108 migration
- [x] `01-02-PLAN.md` - Pure lexical normalization and bounded errors
- [x] `01-03-PLAN.md` - Non-mutating health and canonical resolution
- [x] `01-04-PLAN.md` - Atomic root registration and mapping persistence
- [x] `01-05-PLAN.md` - Adversarial matrix and cross-dialect evidence
- [x] `01-06-PLAN.md` - PostgreSQL-safe mapping locks and bounded persistence errors
- [x] 01-07-PLAN.md - MariaDB/MySQL errno-gated duplicate diagnostic classification

### Phase 2: Read-only Policy Boundary

**Goal**: Every operation addressing an external root is authorized by one deny-by-default policy before filesystem access.
**Depends on**: Phase 1
**Requirements**: ROOT-05, SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05, SAFE-06, TEST-03
**Success Criteria** (what must be TRUE):

1. Users can list, stat, read, scan, hash, stream, and download external content while all RomM-owned output remains outside the root.
2. Direct API and internal workflow attempts to create, upload, write, overwrite, rename, move, copy, delete, extract, patch, or create directories are rejected before filesystem access.
3. The same denials hold on a writable test fixture and on a container-mounted `:ro` fixture, proving that application policy does not depend on mount errors.
4. Every existing filesystem mutation path is either governed by the central policy or demonstrably unable to address an external root.

**Plans:** 11/11 plans complete

Plans:

**Wave 1: Policy contract**

- [x] 02-01-PLAN.md - Closed policy kernel and denial matrix

**Wave 2: Operation-bound access**

- [x] 02-02-PLAN.md - Descriptor-relative operation capabilities

**Wave 3: Trusted storage composition**

- [x] 02-03-PLAN.md - Trusted legacy external-root provider, singleton overlap validation, and owned-storage mutation boundary

**Wave 4: Read consumers**

- [x] 02-04-PLAN.md - Complete external read-consumer enforcement

**Wave 5: Mutation consumers (parallel after Waves 3 and 4)**

- [x] 02-05-PLAN.md - Existing endpoint and mixed ROM enforcement
- [x] 02-06-PLAN.md - Archive, ZIP, exporter, audio, and patch enforcement
- [x] 02-07-PLAN.md - Sync, watcher, platform, cleanup, and task enforcement

**Wave 6: Closed inventory**

- [x] 02-08-PLAN.md - Closed post-enforcement inventory gate

**Wave 7: Deployment and final evidence**

- [x] 02-09-PLAN.md - Dual-mount and canonical final gate

**Wave 8: Verification gap closure**

- [x] 02-10-PLAN.md - Close external identity authority and fail-closed inventory discovery

**Wave 9: Independent discovery gap closure**

- [x] 02-11-PLAN.md - Close alias-aware and typed raw-root AST authority discovery

**Cross-cutting constraints**

- Authorization is deny-by-default, uses trusted storage classification, and occurs before any filesystem observation or mutation.
- External reads and RomM-owned writes require separate operation-bound grants; caller path text cannot forge storage authority.
- Direct API denials use the stable bounded HTTP 403 contract, while job and internal denials fail visibly and terminally without fallback or partial success.
- The mutation inventory is closed: every seam is policy-governed or structurally and testably RomM-owned-only, and any unclassified seam blocks completion.
- Writable and container-mounted read-only fixtures must produce identical denial results without path disclosure.

### Phase 3: Mapping Administration Contracts

**Goal**: Authorized administrators can safely inspect roots and manage one audited, non-overlapping relative mapping per platform.
**Depends on**: Phase 2
**Requirements**: MAP-01, MAP-02, MAP-03, MAP-04, MAP-05, MAP-06, API-01, API-02, API-03, API-04, AUD-01, AUD-02, TEST-02
**Success Criteria** (what must be TRUE):

1. An administrator can list safe root status and browse only directories contained within a selected root using relative paths.
2. An administrator can create, change, test, inspect, and remove a platform mapping through typed APIs without source mutation.
3. Multiple platforms can use distinct directories under one root, while duplicate or ancestor/descendant overlaps and second active mappings are rejected clearly.
4. Unauthenticated callers cannot enumerate library structure, non-administrators cannot mutate mappings, and missing mappings never fall back silently.
5. Mapping changes produce an audit record with actor, timestamp, platform, action, and old/new relative values without leaking host or unrelated filesystem paths.

**Plans:** 6/6 plans complete

Plans:

- [x] 03-01-PLAN.md - Portable mapping lifecycle and immutable audit schema
- [x] 03-02-PLAN.md - Pure live health and bounded contained directory browsing
- [x] 03-03-PLAN.md - Transactional optimistic mapping lifecycle and audit service
- [x] 03-04-PLAN.md - Authorized safe root and browser API contracts
- [x] 03-05-PLAN.md - Typed audited mapping administration API lifecycle
- [x] 03-06-PLAN.md - Non-mutating preview, OpenAPI generation, and final evidence

### Phase 4: V2 Storage Design Specification

**Goal**: The new storage workflows have an implementation-ready RomM v2 design contract informed by Team4s principles without copying its code, assets, or identity.
**Depends on**: Phase 3
**Requirements**: UI-05
**Success Criteria** (what must be TRUE):

1. A reviewed specification defines hierarchy, spacing, typography, navigation, card, and state-presentation rules for storage roots, folder browsing, and platform mappings.
2. The specification maps every proposed pattern to RomM's Vue v2 tokens, primitives, responsive system, and universal input conventions.
3. Reviewers can verify that Team4s was inspected read-only and that no React component, source file, asset, branding, or runtime dependency was copied or modified.

**Plans:** 3/3 plans complete
**UI hint**: yes

Plans:

- [x] 04-01-PLAN.md - Backend, route, workflow, deep folder selection, and scalability contract
- [x] 04-02-PLAN.md - Accessible states, v2 system mapping, provenance, traceability, and validation
- [x] 04-03-PLAN.md - Universal input fidelity gap closure and objective live-architecture gates

### Phase 5: Preview and Read-path Cutover

**Goal**: All discovery and content-read workflows use stable mappings and preserve the external archive byte-for-byte.
**Depends on**: Phase 3
**Requirements**: SCAN-01, SCAN-02, SCAN-03, SCAN-04, SCAN-05, SCAN-06
**Success Criteria** (what must be TRUE):

1. An administrator can request a bounded preview showing safe health, file and directory counts, estimated size, and clear partial or pending status without creating catalog records.
2. Manual, scheduled, and watcher-driven scans resolve the active platform mapping and persist discoveries only to RomM-owned storage.
3. Hashing, streaming, playing, downloading, worker, and redirect paths read the mapped source without writing beside it or using the legacy fixed layout.
4. Queued work detects a changed or missing mapping identity and fails clearly instead of being silently redirected.

**Plans**: 8/8 plans complete

Plans:

- [x] `05-01-PLAN.md` - Integration contract and executable storage inventory
- [x] `05-02-PLAN.md` - Mapping-bound scan context and pipeline cutover
- [x] `05-03-PLAN.md` - Manual, scheduled, and watcher scan orchestration
- [x] `05-04-PLAN.md` - Bounded durable scan preview
- [x] `05-05-PLAN.md` - Hashing and single-file delivery cutover
- [x] `05-06-PLAN.md` - Multi-file download preflight and immutable delivery
- [x] `05-07-PLAN.md` - Complete mapped read cutover gates
- [x] `05-08-PLAN.md` - Metadata export destination hardening

### Phase 6: Safe Lifecycle and Legacy Migration

**Goal**: Operators can remove catalog state and bridge existing layouts without restructuring or deleting source content.
**Depends on**: Phase 5
**Requirements**: CAT-01, CAT-02, CAT-03, CAT-04, MIG-01, MIG-02, MIG-03, MIG-04, MIG-05
**Success Criteria** (what must be TRUE):

1. A user can remove a game from the catalog while every original source file and directory remains unchanged.
2. An administrator can remove a mapping without deleting indexed games or source content, and external-root mutation actions remain absent and server-blocked.
3. Existing supported layouts can be represented as roots and relative mappings without moving, renaming, copying, or creating library content.
4. Ambiguous legacy layouts require an explicit manual mapping rather than a guess, and any compatibility fallback is visible and time-bounded.
5. Mappings survive restarts and normal deployment operations, with portable and practically reversible database migration behavior.

**Plans**: 54/54 plans complete, manually accepted on 2026-09-15.

**Closure note**: The product and targeted acceptance checks were accepted after UAT. The final disposable full-run evidence publisher did not replace its historical JSON record, despite cleanup, stopped-service, generated-tree, and baseline audits passing. This was explicitly accepted for closure to unblock the next phase.

Plans:

- [x] `06-01-PLAN.md` - Durable ownership and lifecycle schema
- [x] `06-02-PLAN.md` - Catalog-only game removal
- [x] `06-03-PLAN.md` - Mapping removal, cancellation, and reconnection
- [x] `06-04-PLAN.md` - Exact bounded legacy detection
- [x] `06-05-PLAN.md` - Typed impact preview and manual outcomes
- [x] `06-06-PLAN.md` - Atomic per-platform migration
- [x] `06-07-PLAN.md` - Productive first-use CAS integration
- [x] `06-08-PLAN.md` - Typed rollback API and durable persistence
- [x] `06-09-PLAN.md` - Integration immutability and contract closure
- [x] `06-10-PLAN.md` - Close the detached user-value and retained-identity reconnection gap.
- [x] `06-11-PLAN.md` - Remove forbidden source-file deletion affordances and language from the active v2 ROM removal flow.
- [x] `06-12-PLAN.md` - Bind migration confirmation to the current canonical source and exact catalog identity set.
- [x] `06-13-PLAN.md` - Replace blanket platform rollback with exact prior catalog restoration.
- [x] `06-14-PLAN.md` - Close the three bounded robustness warnings from Phase 6 review.
- [x] `06-15-PLAN.md` - Re-run Phase 6 as a complete, adversarial closure and correct its validation evidence.
- [x] `06-16-PLAN.md` - Establish the source locale contract and first bounded translation batch for catalog-only ROM removal.
- [x] `06-17-PLAN.md` - Complete the bounded catalog-only translation rollout and prove repository-wide locale parity.
- [x] `06-18-PLAN.md` - Remove active-v2 mutation of generic and sidecar/shared files under the external source root.
- [x] `06-19-PLAN.md` - Make retained identity reconnection durable, idempotent, and retry-safe.
- [x] `06-20-PLAN.md` - Repair seeded-0111 portability and the aggregate HASH budget race.
- [x] `06-21-PLAN.md` - Bind rollback to immutable migration-time row lineage.
- [x] `06-22-PLAN.md` - Make harness cleanup retry-safe and correct screenshot lifecycle contracts.
- [x] `06-23-PLAN.md` - Run final Phase 6 integration and adversarial closure. (completed 2026-08-20)
- [x] `06-24-PLAN.md` - Remove firmware external mutation authority and prove backend denial.
- [x] `06-25-PLAN.md` - Remove active-v2 external upload and source-directory creation.
- [x] `06-26-PLAN.md` - Close source rename and install the final v2 mutation inventory.
- [x] `06-27-PLAN.md` - Authorize changed source names before every database, owned-resource, or filesystem effect.
- [x] `06-28-PLAN.md` - Enforce immutable rollback lineage across supported bulk ORM mutation paths.
- [x] `06-29-PLAN.md` - Make the active-v2 external-mutation inventory complete and fail closed.
- [x] `06-30-PLAN.md` - Correct lower-bound semantics for budget-limited legacy observations.
- [x] `06-31-PLAN.md` - Make owned create and replace writes complete and failure-atomic.
- [x] `06-32-PLAN.md` - Re-run complete Phase 6 integration and adversarial verification.

**Wave 1 — Gap closure: independent safety foundations**

Dependency note: Plans 06-33, 06-34, 06-35, 06-36, 06-37, 06-38, 06-40, and 06-41 have no new-plan dependencies and can execute in parallel.

- [x] `06-33-PLAN.md` - Make OwnedCreate a complete-durable-content-or-no-final-publication primitive.
- [x] `06-34-PLAN.md` - Mask hidden screenshot-upload targets before every owned filesystem or database effect.
- [x] `06-35-PLAN.md` - Separate metadata-only HEAD validation from productive GET use and encode download filenames safely.
- [x] `06-36-PLAN.md` - Close every remaining transport-form blind spot in the active-v2 semantic mutation inventory.
- [x] `06-37-PLAN.md` - Define exact private source-observed identity evidence at the detector boundary.
- [x] `06-38-PLAN.md` - Install the approved primary-manual copy contract in en_US and the first locale batch.
- [x] `06-40-PLAN.md` - Create the singular request and progress contract consumed by the safe manual UI.
- [x] `06-41-PLAN.md` - Add the viewer control contract needed to keep the existing manual visible but non-racing while replacement is pending.

**Wave 2 — Gap closure: dependent persistence and replacement**

Dependency note: Plan 06-39 depends on 06-38; Plan 06-42 depends on 06-37; Plan 06-43 depends on 06-33.

- [x] `06-39-PLAN.md` - Complete the approved primary-manual translations and global locale parity.
- [x] `06-42-PLAN.md` - Persist only bounded digests of exact source-observed identities and invalidate rows that lack that evidence.
- [x] `06-43-PLAN.md` - Make primary-manual replacement single-file, serialized by compare-and-swap, and failure-atomic.

**Wave 3 — Gap closure: migration and active-v2 integration**

Dependency note: Plan 06-44 depends on 06-35 and 06-42; Plan 06-45 depends on 06-38, 06-39, 06-40, 06-41, and 06-43.

- [x] `06-44-PLAN.md` - Bind legacy preview and migration reconnection to the exact private source-observed identity set.
- [x] `06-45-PLAN.md` - Implement the approved single-file primary-manual interaction without redesigning Game Details or Phase 7 storage administration.

**Wave 4 — Gap closure: dialect authority**

Dependency note: Plan 06-46 depends on 06-44.

- [x] `06-46-PLAN.md` - Extend the authoritative migration verifier for the private source-identity revision and exact reconnection behavior.

**Wave 5 — Gap closure: final adversarial integration**

Dependency note: Plan 06-47 depends on every new implementation plan, 06-33 through 06-46.

- [x] `06-47-PLAN.md` - Run the complete adversarial Phase 6 closure and update evidence only after exact cleanup.

### Phase 7: V2 Storage Administration Experience

**Goal**: Administrators can complete the safe storage-root and platform-mapping workflow end to end in accessible UI v2 surfaces.
**Depends on**: Phase 4, Phase 5, Phase 6
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-06
**Success Criteria** (what must be TRUE):

1. An administrator can see each root's identity, immutable mode, activity, health, last check, and safe errors without host-path leakage.
2. An administrator can navigate and select nested or Unicode directories only within the chosen root.
3. An administrator can select a root and directory, test it, preview the scan, save the mapping, and remove it from one coherent v2 workflow.
4. The interface explains that RomM indexes but never changes original files and presents accessible loading, empty, error, forbidden, unreachable, and pending states.
5. The complete workflow is usable with mouse, touch, keyboard, and gamepad across supported responsive layouts.

**Plans**: 4/4 complete
**UI hint**: yes

### Phase 8: Bounded V1 Removal

**Goal**: The fork boots only UI v2, with every supported route and shared dependency proven intact after the frozen frontend is removed.
**Depends on**: Phase 7
**Requirements**: V2-01, V2-02, V2-03, V2-04, V2-05
**Success Criteria** (what must be TRUE):

1. Users enter UI v2 directly with no UI-version preference, switch, named-view fallback, or `NotReady` handoff to v1.
2. Every supported route renders a real v2 view, while deliberately retired routes fail or redirect according to an explicit route inventory.
3. Pairing, authentication, theme, router, shared stores, API services, generated types, and overlays required by v2 pass a dedicated regression suite after v1 files are deleted.
4. Frozen v1 views, components, layouts, console surfaces, banners, fallbacks, and v1-only compatibility code are absent from the shipped frontend.

**Plans**: Closed by manual live-UAT acceptance on 2026-09-15.

**Closure note**: The remaining production-like proof is intentionally delegated to the user's live UAT. Keep the fast automated safety tests; do not require the expensive full temporary-stack gate for ordinary development changes.

### Phase 9: Operational Immutability Proof

**Goal**: Operators have production-like evidence and guidance showing that supported NAS workflows preserve the archive and do not disrupt Team4s.
**Depends on**: Phase 8
**Requirements**: TEST-04, TEST-05, TEST-06, DOC-01, DOC-02, DOC-03
**Success Criteria** (what must be TRUE):

1. Integration evidence covers read-only mounting, multiple mappings, mapping changes, scanning, streaming, downloading, restart persistence, legacy migration, nginx, and worker paths.
2. Before/after evidence shows source content, names, structure, sizes, hashes, and non-access timestamps unchanged across every supported workflow.
3. An operator can deploy one `:ro` root with separate writable storage and follow documented mapping, browsing, migration, catalog-removal, security, troubleshooting, limitation, and atime guidance.
4. Operational instructions require an approved maintenance window for a real NAS mount and prohibit Team4s source, service, restart, or active-encode changes.

**Plans**: Manual UAT closure

### Phase 10: PC Integration Model

**Goal**: Operators can model existing PC games as immutable component sets and enrich recognized games without changing any source library.
**Depends on**: Phase 9
**Requirements**: PCMOD-01, PCMOD-02, PCMOD-03, PCMOD-04, PCMETA-01, PCMETA-02, PCLB-01, PCLB-02, PCRP-01, PCSAFE-01, PCTEST-01
**Success Criteria** (what must be TRUE):

1. An operator can inspect one PC game as a base game with explicitly classified updates, DLCs, hotfixes, language packs, and extras.
2. Each component has a stable manifest of contained relative files, byte sizes, and strong digests, while the read-only source root remains unchanged.
3. A recognized PC game can be matched against configured IGDB, SteamGridDB, MobyGames, and a read-only local LaunchBox library, with the selected metadata and eligible media visible in v2.
4. Ambiguous component layouts, unavailable providers, and unsupported media sources fail clearly and never create, rename, move, or modify source files.
5. RiotPixels is only enabled after documented API, rights, and operational constraints have passed a dedicated provider evaluation.

**Plans**: 3/3 plans executed
**UI hint**: yes

## Progress

| Phase                                   | Plans Complete | Status      | Completed  |
| --------------------------------------- | -------------- | ----------- | ---------- |
| 1. Immutable Storage Foundation         | 7/7            | Complete    | 2026-08-05 |
| 2. Read-only Policy Boundary            | 11/11          | Complete    | 2026-08-10 |
| 3. Mapping Administration Contracts     | 6/6            | Complete    | 2026-08-11 |
| 4. V2 Storage Design Specification      | 3/3            | Complete    | 2026-08-12 |
| 5. Preview and Read-path Cutover        | 8/8            | Complete    | 2026-08-12 |
| 6. Safe Lifecycle and Legacy Migration  | 52/54          | In Progress |            |
| 7. V2 Storage Administration Experience | 3/3            | Complete    | 2026-08-26 |
| 8. Bounded V1 Removal                   | 4/4            | Complete    | 2026-08-27 |
| 9. Operational Immutability Proof       | Manual UAT     | Complete    | 2026-09-15 |
| 10. PC Integration Model                | 3/3            | Complete    | 2026-09-15 |
| 14. Immutable Download Manifests        | 4/4            | Complete    | 2026-09-16 |
| 15. Direct Resumable Transfer           | 3/3            | Complete    | 2026-09-16 |
| 16. Cross-platform Desktop Client       | 5/6            | In Progress |            |
| 17. Browser Download Manager            | 13/13          | Complete    | 2026-09-24 |

### Phase 11: Local PC Media and DLC Navigation

**Goal:** Let an operator select safe local PC artwork, match DLC independently,
and open locally owned DLC files from Overview without leaving RomM.
**Requirements**: PCLM-01, PCLM-02, PCDLC-01, PCDLC-02, PCSAFE-01, PCTEST-01
**Depends on:** Phase 10
**Plans:** 3/3 plans executed

Plans:

- [x] 11-01-PLAN.md: Persist and reconcile manifest-bound local media safely.
- [x] 11-02-PLAN.md: Add independent DLC review and internal v2 navigation.
- [x] 11-03-PLAN.md: Prove the isolated end-to-end flow and record UAT.

### Phase 12: DLC detail pages for local PC components

**Goal:** Each locally present, independently matched PC DLC has a dedicated, parent-owned v2 detail page that presents its selected local identity, media, and immutable files without changing the source library.
**Requirements**: TBD
**Depends on:** Phase 11
**Plans:** 12/12 plans executed

Plans:

- [x] 12-02-PLAN.md: Register the canonical route and strict parent-owned resolver.
- [x] 12-04-PLAN.md: Localize the first bounded DLC-detail locale batch.
- [x] 12-05-PLAN.md: Complete DLC-detail locale parity.
- [x] 12-01-PLAN.md: Route both parent-detail DLC entry points to the canonical page.
- [x] 12-03-PLAN.md: Render selected component detail evidence and immutable files.
- [x] 12-06-PLAN.md: Prove source safety and complete visual and input validation.
- [x] 12-07-PLAN.md: Persist component-owned media and notes.
- [x] 12-08-PLAN.md: Add target-aware PC matcher APIs.
- [x] 12-09-PLAN.md: Expose contained DLC resources and downloads.
- [x] 12-10-PLAN.md: Route PC metadata actions through the shared matcher.
- [x] 12-11-PLAN.md: Deliver the DLC detail experience.
- [x] 12-12-PLAN.md: Record automated acceptance and user UAT.

### Phase 13: PC IGDB metadata and DLC media

**Goal:** Enrich Windows PC parent ROMs and unambiguously linked DLCs with
normalized IGDB metadata and RomM-owned media, then present it in their v2
detail views without mutating the source library.
**Requirements**: PC-specific developer, publishers, themes, Windows release
date, owned cover/screenshots/artwork, and parent/DLC detail presentation.
**Depends on:** Phase 12
**Plans:** 5/5 plans executed

Plans:

- [x] 13-01-PLAN.md: Normalize and persist structured PC IGDB metadata.
- [x] 13-02-PLAN.md: Enrich scan-time parents and unambiguous DLCs with owned media.
- [x] 13-03-PLAN.md: Expose and render PC metadata/media in v2 parent and DLC details.
- [x] 13-04-PLAN.md: Verify safety, metadata, media, and focused UAT.
- [x] 13-05-PLAN.md: Close accepted DLC media and notes UX gaps. (completed 2026-09-14)

### Phase 14: Immutable Download Manifests

**Goal:** A selected whole PC game or component set has one immutable,
hash-backed download manifest without changing the source library.
**Depends on:** Phase 13
**Requirements:** DLMT-01, DLMT-02, DLMT-03

**Success Criteria:**

1. A user can select a whole game or exact components and receive a stable,
   server-authorized manifest.

2. Every manifest member has a safe relative destination path, exact byte size,
   and SHA-256 snapshot.

3. Changed, expired, or unsafe snapshots fail clearly and never authorize a
   mixed source version.

**Plans:** 4/4 plans complete

Plans:

- [ ] `14-01-PLAN.md` - Persist the immutable, owner-scoped download-manifest aggregate and portable 0119 migration.
- [ ] `14-02-PLAN.md` - Capture trusted current evidence and create all-or-nothing selected manifests with explicit lifecycle states.
- [ ] `14-03-PLAN.md` - Expose protected JSON manifest creation and retrieval APIs, then regenerate the additive OpenAPI contract.

### Phase 15: Direct Resumable Transfer

**Goal:** The server transfers each manifest file directly and safely resumes
large partial files without packaging or extracting content.
**Depends on:** Phase 14
**Requirements:** XFER-01, XFER-02, XFER-03, XFER-04

**Success Criteria:**

1. A 100-GB-class original file is delivered as itself, never as a whole-game
   ZIP or ZIP part.

2. A valid Range request resumes exactly at the verified partial byte offset.
3. A changed source snapshot fails rather than mixing data from two versions.
4. Sizes and offsets above 4 GiB remain correct and concurrency is bounded.

**Plans:** 3/3 plans complete

### Phase 16: Cross-platform Desktop Client

**Goal:** Retain a Tauri/Rust prototype for Windows and Linux/Bazzite download
recovery while deferring desktop cleanup. Mandatory installers, desktop handoff,
and distribution are cancelled product scope.
**Depends on:** Phase 15
**Requirements:** CLNT-01, CLNT-02, CLNT-03, CLNT-04, CLNT-05

**Success Criteria:**

1. The client resumes interrupted downloads after restart without re-downloading
   verified bytes.

2. It validates SHA-256 and atomically completes each original file.
3. It creates only manifest-authorized paths below the selected destination and
   clearly handles disk-full and permission failures.

**Plans:** 5/6 plans executed, with installer UAT blocked and non-blocking for Phase 17

### Phase 17: Browser Download Manager

**Goal:** RomM v2 lets users select PC game components or allowed individual files
and download the original immutable manifest files directly in the browser, with
a standard browser attachment baseline, an optional capability-detected File
System Access enhancement, and verified read-only source safety. Desktop handoff,
installers, and distribution are not part of this phase.
**Depends on:** Phase 14, Phase 15
**Requirements:** UXDL-01, SAFE-01, TEST-01

**Success Criteria:**

1. v2 creates an immutable manifest for a valid component or allowed file
   selection and downloads its original files without desktop software or ZIP
   packaging.

2. Standard browser downloads work as the compatible baseline; File System
   Access is capability-detected and never required.

3. The queue, transfer history, source-change handling, range protocol, and
   terminology distinguish browser handoff from a server-served response and
   enhanced-mode local verification.

4. The complete flow leaves the NAS and source library unchanged, does not
   expose source paths, and covers large-file and multi-file evidence.

**Plans:** 13/13 plans complete. Chromium live UAT completed; Firefox and Edge explicitly waived by product decision.

### Phase 18: Steam Metadata Integration für PC Games und DLCs

**Goal:** Add the official Steam Storefront provider to eligible PC games and safely identified DLC components, with German-first text while preserving IGDB relationships, manual data, and SteamGridDB's artwork-only role.
**Requirements**: [STEAM-01, STEAM-02, STEAM-03, STEAM-04, STEAM-05]
**Depends on:** Phase 17
**Plans:** 15/15 plans complete

Plans:

- [x] 18-01-PLAN.md — Harden the localized upstream-close Steam service, handler, and no-key configuration.
- [x] 18-02-PLAN.md — Repair the migration graph, persist Steam IDs/provenance, and prove migrations against disposable PostgreSQL.
- [x] 18-03-PLAN.md — Complete provider priority, heartbeat, distinct responsive/accessibility-verified v2 Steam presentation, and production build.
- [x] 18-04-PLAN.md — Integrate Steam PC candidates through one manual-safe merge policy.
- [x] 18-05-PLAN.md — Add IGDB-first safe Steam DLC enrichment.
- [x] 18-06-PLAN.md — Expose the stable API schema and regenerate TypeScript contracts separately from model migrations.
- [x] 18-07-PLAN.md — Add stored-ID-first PC automatic Steam scans without classic-ROM regressions.
- [x] 18-08-PLAN.md — Run phase-wide evidence gates and record the upstream/fork compatibility boundary.
- [x] 18-09-PLAN.md — Persist Steam provenance only on existing PC components without duplication or IGDB-field loss.
- [x] 18-10-PLAN.md — Fail closed when IGDB DLC hydration cannot establish an authoritative identity.
- [x] 18-11-PLAN.md — Run focused backend and MariaDB/PostgreSQL migration evidence in canonical Compose context.
- [x] 18-12-PLAN.md — Correct the generated detailed-ROM contract key link and audit closure coverage.
- [x] 18-13-PLAN.md — Diagnose and correct the two remaining parent-selection and component-persistence suite failures.
- [x] 18-14-PLAN.md — Make the historical PostgreSQL 0118 metadata view replacement type-stable and portable.
- [x] 18-15-PLAN.md — Re-run the 186-test Compose suite and full PostgreSQL cycle, then record final closure evidence.

### Phase 19: Fix PC quick-scan IGDB matching and safe DLC/expansion enrichment

**Goal:** Repair automatic Windows PC scans so compact names resolve with IGDB as reliably as Steam; repair existing Steam-only Windows PC records on IGDB-selected metadata refresh without duplicates; preserve fail-closed IGDB-first DLC/expansion enrichment and explicit manual component selection.
**Requirements**: D-01, D-02, D-03, D-04, D-05, D-06
**Depends on:** Phase 18
**Plans:** 2/2 plans complete

Plans:
**Wave 1**

- [x] 19-01-PLAN.md — Normalize compact Windows lookup titles only at the automatic IGDB name-search boundary.

**Wave 2** _(blocked on Wave 1 completion)_

- [x] 19-02-PLAN.md — Recover Steam-only Windows metadata in place and prove safe DLC/expansion enrichment.

### Phase 20: Media management and owned soundtrack uploads

**Goal:** Let operators manage provider and RomM-owned game media, select ordered overview/background assets, and upload/order/play owned soundtracks without any write to the external source library.
**Requirements**: MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MEDIA-05, MEDIA-06, MEDIA-07
**Depends on:** Phase 19
**Plans:** 10/10 plans complete

Plans:
**Wave 1**

- [x] 20-01-PLAN.md — Persist parent-ROM owned-media candidates, tombstones, placements, and safe ordering.

**Wave 2**

- [x] 20-09-PLAN.md — Add parent-owned media role and safe display-label contracts.

**Wave 3**

- [x] 20-10-PLAN.md — Backfill existing RomM-owned legacy media into manageable candidates.

**Wave 4**

- [x] 20-02-PLAN.md — Expose protected owned-media storage and API contracts.

**Wave 5**

- [x] 20-03-PLAN.md — Deliver provider screenshot management in v2 Media.

**Wave 6**

- [x] 20-04-PLAN.md — Deliver artwork/background ordering and reduced-motion-aware rotation.
- [x] 20-05-PLAN.md — Deliver owned soundtrack queue/player behavior.

**Wave 7**

- [x] 20-06-PLAN.md — Translate the first bounded Media locale batch.

**Wave 8**

- [x] 20-07-PLAN.md — Complete locale parity for all supported languages.

**Wave 9**

- [x] 20-08-PLAN.md — Record cross-dialect, cross-stack, and browser UAT evidence.

### Phase 21: Unify admin PC scans with German Steam metadata and media

**Goal:** Administrator scans for eligible Windows, Linux, and macOS PC games share targeted Steam enrichment: German-first same-App-ID text, non-destructive provenance/manual protection, and idempotent RomM-owned Steam-media reconciliation without source-library writes.
**Requirements**: STEAM-02, STEAM-05 (reused and extended for administrator-scan parity)
**Depends on:** Phase 20
**Plans:** 4 plans

Plans:

**Wave 1**

- [ ] 21-01-PLAN.md — Create the shared pure Steam PC patch and selected-candidate parity.
- [ ] 21-02-PLAN.md — Add durable safe Steam provider-media inventory reconciliation.

**Wave 2**

- [ ] 21-03-PLAN.md — Reconcile validated Steam media through RomM-owned storage.

**Wave 3**

- [ ] 21-04-PLAN.md — Wire new/update/complete scans, source-boundary tests, and Witcher-only UAT evidence.

### Phase 22: Bulk-automatisierung für PC-Spiel- und DLC-Zuordnung

**Goal:** Automatically discover newly added, correctly named PC game folders on a safe periodic schedule, apply only unambiguous Steam/IGDB/DLC metadata and media, and route every uncertain case to one protected, efficient administrator review queue.
**Requirements**: D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08
**Depends on:** Phase 21
**Plans:** 6 plans

Plans:

**Wave 1**

- [x] 22-01-PLAN.md — Persist an idempotent, version-bound PC automation review queue and guarded state machine.

**Wave 2**

- [x] 22-02-PLAN.md — Add fail-closed automatic PC matching and scheduled mapped discovery with Steam coverage and a tested UAT override.

**Wave 3**

- [x] 22-03-PLAN.md — Expose protected generated queue APIs with server-side candidate revalidation and safe batch application.

**Wave 4**

- [x] 22-04-PLAN.md — Deliver the v2 centralized review queue and manual-match reuse.

**Wave 5**

- [x] 22-05-PLAN.md — Translate the centralized queue through the full locale set and prove locale parity.

**Wave 6**

- [x] 22-06-PLAN.md — Prove isolated source immutability and complete browser UAT for scheduled bulk automation.

### Phase 23: Mehrsprachige Steam-Metadaten: deutsche, englische und weitere verfügbare Beschreibungstexte je Steam-App dauerhaft speichern und nach UI-Sprache anzeigen. (accepted 2026-10-05)

**Goal:** Persist German, English, and further configured Steam text variants per app, then display the stored variant that matches the selected UI language while preserving manual and non-Steam display authority.
**Requirements**: STEAM-02, STEAM-04, STEAM-05
**Depends on:** Phase 22
**Cross-cutting constraints:** Use only bounded server-side Steam language configuration and the existing `steam_metadata` JSON ownership boundary. Keep enrichment non-destructive and same-App-ID validated, expose variants only on detailed responses, resolve UI locale selection locally with English fallback, and use only isolated synthetic fixtures for UAT. No browser-to-Steam requests, database migration, NAS, Team4s, real library, or production data access is permitted.
**Plans:** 3 plans

Plans:

**Wave 1**

- [x] 23-01-PLAN.md: Acquire bounded, validated Steam text variants for the same app ID.

**Wave 2** (depends on 23-01)

- [x] 23-02-PLAN.md: Persist guarded parent and DLC Steam text variants through all enrichment paths.

**Wave 3** (depends on 23-02)

- [x] 23-03-PLAN.md: Publish typed detail metadata, resolve the selected UI language, and prove isolated browser UAT.

### Phase 24: V2 quality stabilization and legacy boundary cleanup

**Goal:** Make direct-v2 reliable and maintainable by fixing the observed test, router, i18n, prop-type, accessibility, and token issues, then establish and execute a typed data-access boundary that removes direct v2 dependence on legacy stores and services. Split oversized components and finish with production build and browser verification without changing read-only source-library guarantees.
**Requirements**: QA-01, QA-02, QA-03, QA-04, QA-05, QA-06, QA-07, QA-08
**Depends on:** Phase 23
**Cross-cutting constraints:** Preserve direct-v2 boot and all supported routes. Do not restore v1. Do not modify external libraries or use NAS, Team4s, real library data, or production credentials. Keep API contracts backend-owned, regenerate generated types after schema changes, preserve manual/provider ownership rules, and keep source-mutation controls fail-closed.
**Plans:** 14/14 plans executed

**Wave 1**

- [x] 24-01-PLAN.md: Repair current v2 test failures and runtime contract warnings.

**Wave 2** (depends on 24-01)

- [x] 24-02-PLAN.md: Close i18n parity, accessibility, and design-token governance gaps.
- [x] 24-03-PLAN.md: Harden router parameters, bootstrap behavior, and stale compatibility remnants.

**Wave 3** (depends on 24-02 and 24-03)

- [x] 24-04-PLAN.md: Introduce the v2 typed data-access boundary without behavior changes.

**Wave 4** (depends on 24-04)

- [x] 24-05-PLAN.md: Migrate v2 domains from legacy stores and services in bounded slices.
- [x] 24-06-PLAN.md: Decompose oversized v2 components and remove presentation coupling.

**Wave 5** (depends on 24-05 and 24-06)

- [x] 24-07-PLAN.md: Establish storage-aware operation contracts and compatibility translation.
- [x] 24-08-PLAN.md: Centralize provider resolution and operation lifecycle.
- [x] 24-09-PLAN.md: Define metadata/media ownership and per-item result policies.
- [x] 24-10-PLAN.md: Migrate every scan, refresh, matching, cover, and PC/DLC entry point.
- [ ] 24-11-PLAN.md: Run final Linux gates, preservation matrix, browser UAT, and document the handoff.

**Wave 9** (depends on 24-08, 24-09, and 24-10)

- [x] 24-12-PLAN.md: Inventory and decompose oversized runtime files without duplicating existing domain logic.

**Wave 10** (depends on 24-12)

### Phase 25: Scan-/Medien-Integration härten

**Goal:** Complete the end-to-end scan and media contract for mapped PC and classic-platform libraries by resolving provider authority, isolating per-item media failures, classifying OST as source-backed soundtrack audio with an existing download-to-owned-upload flow, and proving metadata, media, DLC, expansion, localization, and source immutability without duplicating existing storage, mapping, PC, provider, or socket logic.
**Depends on:** Phase 24
**Cross-cutting constraints:** Reuse PlatformStorageMapping, the v2 operation contract, the shared socket lifecycle, existing provider resolution, PC component ownership, and owned-media persistence. New production files target at most 500 logical lines; files above 500 require a decomposition decision; new files above 1,000 are prohibited except approved generated artifacts.
**Plans:** 4 plans

Plans:

**Wave 1**

- [ ] 25-01-PLAN.md: Repair provider-aware media reconciliation and per-item scan failure isolation.

**Wave 2** (depends on 25-01)

- [ ] 25-02-PLAN.md: Complete PC classification for OST, DLC, Expansion, archives, and NFO sidecars.

**Wave 3** (depends on 25-01 and 25-02)

- [ ] 25-03-PLAN.md: Run focused gates and blocking Linux Dev/browser UAT.
- [ ] 25-04-PLAN.md: Close correlated item outcomes, component isolation, and MariaDB evidence gaps.

### Phase 26: UI-UX Abschluss und manuelle, mehrsprachige Metadatenpflege

**Goal:** Close the remaining UI/UX gaps from live Linux Dev UAT and provide a
language-scoped manual description editor that preserves provider data and
works consistently for parent games, DLCs, and expansions.
**Depends on:** Phase 25
**Cross-cutting constraints:** Reuse the existing metadata, provider,
permission, locale, detail-surface, query invalidation, and v2 component
abstractions. Do not create a parallel storage, mapping, scan, or metadata
ownership model. Existing animation, sharp-background, soundtrack-role,
Steam, and scan fixes are regression scope only.
**Plans:** 3/3 plans complete

Plans:

**Wave 1**

- [x] 26-01-PLAN.md: Add the canonical locale-scoped manual description contract and lifecycle tests.

**Wave 2** (depends on 26-01)

- [x] 26-02-PLAN.md: Add the v2 detail-surface editor with provenance, reset, locale parity, and accessible states.

**Wave 3** (depends on 26-01 and 26-02)

- [x] 26-03-PLAN.md: Run automated regression gates and live Linux Dev/browser UAT for the complete UI scope.

### Phase 27: Reproduzierbare Portainer-/Docker-Installation für die RomM-Version

**Goal:** Publish a sanitized, reproducible Portainer/Docker installation path
for the GitHub main branch so another user supplies only their own storage
paths, secrets, and optional metadata-provider credentials while ROMs, media,
database contents, and real secrets remain outside Git.
**Requirements**: DEPLOY-27-01, DEPLOY-27-02, DEPLOY-27-03, DEPLOY-27-04
**Depends on:** Phase 26
**Cross-cutting constraints:** Reuse examples/docker-compose.example.yml,
docker/init_scripts/docker-entrypoint.sh, existing storage/media mounts, and
the existing migration/bootstrap path. Keep dev compose separate. Do not add a
parallel storage, mapping, metadata, media, or database architecture. Never
commit .env files, secrets, ROMs, images, database dumps, or runtime artifacts.
**Plans:** 3/3 plans complete

Plans:

**Wave 1**

- [x] 27-01-PLAN.md: Define the sanitized Portainer stack, operator env contract, and secret-safety checks.

**Wave 2** (depends on 27-01)

- [x] 27-02-PLAN.md: Close startup, migration, persistence, health, and secret-file behavior gaps.

**Wave 3** (depends on 27-01 and 27-02)

- [x] 27-03-PLAN.md: Publish installation documentation and run clean-clone Portainer/Docker UAT.

### Phase 28: YouTube preview, Steam app ID, and PC save/media management

**Goal:** Extend PC metadata and save/media handling while preserving existing storage and ownership boundaries.
**Depends on:** Phase 27
**Plans:** 4 plans

- [ ] 28-01-PLAN.md
- [ ] 28-02-PLAN.md
- [ ] 28-03-PLAN.md
- [ ] 28-04-PLAN.md

### Phase 29: Role-aware metadata, clickable themes, and multilingual behavior

**Goal:** Complete role-aware metadata, theme navigation, and multilingual behavior.
**Depends on:** Phase 28
**Plans:** 4/4 plans complete

- [x] 29-01-PLAN.md
- [x] 29-02-PLAN.md
- [x] 29-03-PLAN.md
- [x] 29-04-PLAN.md

### Phase 30: User-friendly Portainer installation documentation

**Goal:** Improve the user-facing Portainer installation documentation and verification path.
**Depends on:** Phase 29
**Plans:** 3 plans

- [ ] 30-01-PLAN.md
- [ ] 30-02-PLAN.md
- [ ] 30-03-PLAN.md

### Phase 31: Consistent multilingual game descriptions

**Goal:** Provide consistent multilingual game descriptions across supported detail surfaces.
**Depends on:** Phase 30
**Plans:** 1 plan

- [ ] 31-01-PLAN.md

### Phase 32: PGDP naming/Fresh Installation

**Goal:** Establish a clean PGDP deployment identity for fresh installs while retaining canonical RomM runtime contracts and protecting existing storage from mutation.
**Requirements:** PGDP-32-01
**Depends on:** Phase 31
**Plans:** 1/3 plans complete

- [x] 32-01-PLAN.md: Create the naming inventory and align fresh-install Compose/runtime/backend fixtures.
- [ ] 32-02-PLAN.md
- [ ] 32-03-PLAN.md

### Phase 33: Fresh-install first-run PC storage mapping before library scan

**Goal:** On a fresh installation, setup discovers direct folders under the mounted `Games` directory, auto-associates known names, lets the administrator assign unknown folders to PGDP platforms inline, persists safe internal mappings, and continues to normal administration only after the server confirms those mappings are ready for later scan/read flows.
**Requirements**: PGDP-33-01
**Depends on:** Phase 32
**Plans:** 10/10 plans executed; live-UAT collection correction added

Plans:

- [x] 33-01-PLAN.md - Historical storage primitives retained as internal mapping foundation
- [x] 33-02-PLAN.md - Implement server-owned direct Games-folder discovery and assignment API
- [x] 33-03-PLAN.md - Historical Home/Scan readiness gate retained for integration updates
- [x] 33-04-PLAN.md - Replace first-run summary with inline PGDP folder assignment
- [x] 33-05-PLAN.md - Connect saved assignments to backend scan and mapped read readiness
- [x] 33-07-PLAN.md - Complete mandatory locale parity for inline assignment
- [x] 33-08-PLAN.md - Gate Home and Scan on all-mapping readiness
- [x] 33-06-PLAN.md - Run fresh Linux stack and in-app browser UAT (tested live scope accepted 2026-10-20; gamepad and deep review remain open)
- [x] 33-09-PLAN.md - Complete dependent locale batch for inline assignment
- [x] 33-10-PLAN.md - Persist explicit collection folders, retire mistaken parent games safely and discover future children through normal and scheduled scans

### Phase 34: Reliable fresh installation and scan lifecycle

**Goal:** A fresh PGDP installation recovers incomplete setup and reaches a completed first library scan. First and normal scans expose confirmed durable state, bounded actionable failures and safe restart/cancellation recovery while preserving source storage.
**Requirements**: D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12, D-13, D-14, D-15, D-16
**Depends on:** Phase 33 implementation foundation; its open 33-06 browser acceptance is repeated after stabilization.
**Plans:** 5/16 plans executed; media corrective acceptance remains open

Plans:

**Wave 1**

- [x] 34-01-PLAN.md - Safe isolated test harness and executable defect reproductions

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 34-02-PLAN.md - Durable acceptance, operation persistence and authorized lookup
- [x] 34-05-PLAN.md - Authenticated setup recovery and completion state

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 34-15-PLAN.md - Attempt-owned media publication, exact recovery and shared transaction fence

**Wave 4** *(34-16 is the next isolated feasibility experiment; 34-07 needs completed 02/05)*

- [ ] 34-16-PLAN.md - Bounded test-only content-proof feasibility and mandatory decision checkpoint
- [x] 34-07-PLAN.md - Generated contracts and typed scan operation adapter

**Worker corrective prerequisite** *(after 34-16 decision and accepted media correction)*

- [ ] 34-03-PLAN.md - Recoverable dispatch, job recognition and worker fencing

The 34-16 experiment does not close CR05 or release 03 by SUMMARY existence. Production integration needs a subsequent explicit planning decision, unchanged regression evidence and independent review. CR10, CR09 and WR02 remain open. Historical 34-15 completion does not constitute media quality acceptance.

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 34-04-PLAN.md - Trusted checkpoints, safe restart and targeted metadata retry
- [ ] 34-06-PLAN.md - Resumable setup interface and explicit first-scan action
- [ ] 34-11-PLAN.md - Scope-safe lifecycle listeners and status reconciliation

**Wave 6** *(blocked on Wave 5 completion)*

- [ ] 34-09-PLAN.md - Setup recovery translations, first locale batch
- [ ] 34-12-PLAN.md - Server-confirmed scan states and persistent recovery actions

**Wave 7** *(blocked on Wave 6 completion)*

- [ ] 34-10-PLAN.md - Setup recovery translations, remaining locales
- [ ] 34-13-PLAN.md - Scan recovery translations, first locale batch

**Wave 8** *(blocked on Wave 7 completion)*

- [ ] 34-14-PLAN.md - Scan recovery translations, remaining locales

**Wave 9** *(blocked on Wave 8 completion)*

- [ ] 34-08-PLAN.md - Cross-process faults, production-like installation and Phase 33 reacceptance

**Cross-cutting constraints:**

- PGDP terminology, accessibility labels and interpolation semantics remain consistent.

### Phase 35: Incremental Windows quick scans and unidentified game status

**Goal:** Reuse unchanged identified Windows games during quick scans while reliably discovering new games, collection children and changed DLC/update content. Unidentified games remain visible with truthful retry status.
**Requirements**: D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, SCAN-01, SCAN-02, SCAN-06, PCSAFE-01, PCTEST-01, UI-06, QA-04, QA-05, QA-06, QA-07. Phase-local decisions are delivery requirements; global IDs are regression/support mappings and do not change historical completion status.
**Depends on:** The implemented Phase 33/34 scan and collection lifecycle merged through PR #1. Historical independent review, physical gamepad and production Portainer acceptance remain separate open items.
**Status:** Complete, 14/14 plans implemented; live UAT explicitly accepted by the user on 2026-10-21. Independent verification confirms 24/24 functional truths. The legacy summary/localized-description defect is captured for a separate follow-up phase. Historical gates and global requirement acceptance remain unchanged.
**Plans:** 14/14 plans executed

**Success Criteria** (what must be TRUE):

1. Unchanged identified Windows games avoid repeated expensive component hashing, enrichment and media publication during manual and scheduled quick scans.
2. New games, new direct collection children and new or changed nested DLC/update content are found even when the parent directory timestamp is unchanged.
3. Unidentified games remain visible, and status distinguishes inventory reuse, unresolved identification and actual provider retry.
4. One shared implementation preserves mapping revisions, worker ownership, cancellation, source immutability and publication safety; existing scan modes and other platforms keep their semantics.
5. Regression and end-to-end evidence covers unchanged, changed, new and unidentified cases through manual and 15-minute scheduled entry points.

Plans:

**Wave 1**

- [x] 35-01-PLAN.md - Shared bounded PC inventory and contracts
- [x] 35-02-PLAN.md - Portable durable baseline and retry storage
- [x] 35-03-PLAN.md - Windows identity, scope and bounded retry policy
- [x] 35-04-PLAN.md - Actual provider request and logical execution observations
- [x] 35-09-PLAN.md - Incremental-scan copy in the first nine locales

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 35-05-PLAN.md - Shared quick-scan reuse and safe changed-file reconciliation
- [x] 35-13-PLAN.md - Remaining nine locales and mandatory combined parity gate

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 35-06-PLAN.md - Fenced baseline completion and bounded metadata-only retries

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 35-07-PLAN.md - Durable orthogonal inventory, identity and retry status

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 35-08-PLAN.md - Isolated generated contracts and typed status transport

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 35-14-PLAN.md - Monotonic frontend status projection and bounded pages

**Wave 7** *(blocked on Wave 6 completion)*

- [x] 35-10-PLAN.md - Accessible v2 status summary and persistent unresolved rows

**Wave 8** *(blocked on Wave 7 completion)*

- [x] 35-11-PLAN.md - Actual isolated manual and scheduled worker proof

**Wave 9** *(blocked on Wave 8 completion)*

- [x] 35-12-PLAN.md - Isolated browser, security and final exact-source verification

**Cross-cutting constraints:**

- All scan status labels use actual translations and preserve interpolation

### Phase 36: Localized provider descriptions without legacy summary

**Goal:** Fetch, persist and display descriptions in the selected system language for Steam PC/Windows games and ScreenScraper console ROMs. Cover manual search, matching, confirmation, metadata refresh and all scan entry points, including scheduled scans. Use explicit English fallback, preserve manual text and Phase35 quick-scan performance, and retire legacy summary presentation.
**Requirements:** DESC-01, DESC-02, DESC-03, DESC-04, DESC-05, DESC-06, DESC-07, DESC-08, DESC-09, DESC-10, DESC-11.
**Depends on:** Phase35, merged to main through PR2 at b0d3f6ad61fdb5a502349fa449e5458e77de25d4 and accepted in live UAT.
**Status:** Complete, accepted by the user on 2026-10-23 after authorized Dev deployment and joint live UAT. All 17 plans and 35 tasks implemented; 24/24 technical truths verified. Cancellation workaround, unavailable controller/zoom and unexecuted live subcases remain documented exceptions. Historical obligations are unchanged.
**Plans:** 17/17 plans complete

**Success Criteria:**

1. No v2 description surface displays the obsolete unlocalized summary as a description fallback or silently stores it under a locale.
2. German/English provider text and any explicit fallback preserve their language and source; manual text remains protected.
3. A newly identified game and a game with an existing Steam identity but missing variants can acquire configured languages using the same bounded provider/merge owners, without repeating expensive inventory/media work for unchanged games.
4. Isolated regression and connected UI/worker evidence reproduce the Elden Ring failure and prove repair, empty/failure/backoff behavior, manual protection, concurrency and request accounting.
5. Existing data, auth, Games/media and15-minute schedule remain intact; no automatic deployment or historical acceptance closure.

Plans:

**Wave 1**

- [x] 36-01-PLAN.md - Establish conservative pure completeness/slot contracts and non-destructive field-wise provider merge. No DDL.
- [x] 36-14-PLAN.md - Make the existing global scan language priority the authorized administrative default and freeze one effective metadata_locale in every accepted operation request.

**Wave 2** *(blocked on assigned prior dependency waves)*

- [x] 36-11-PLAN.md - Expose canonical bounded text-only Steam retrieval and additive typed provenance through existing enrichment/schema owners.
- [x] 36-13-PLAN.md - Fetch and normalize ScreenScraper console descriptions in explicit DE/FR/EN slots through the existing provider, preserving non-destructive merge and text-only work.

**Wave 3** *(blocked on assigned prior dependency waves)*

- [x] 36-02-PLAN.md - Extend the existing operation-wide retry owner with description-purpose selection, durable cooldown and a narrow checked text patch. Preserve the unidentified retry policy.

Purpose: Deliver the approved description-language correction through existing owners.
Output: Tested behavior and explicit task verification receipts.

- [x] 36-04-PLAN.md - Add a provenance-bearing typed resolution seam and generate backend contracts while preserving existing callers until their atomic migration.

**Wave 4** *(blocked on assigned prior dependency waves)*

- [x] 36-03-PLAN.md - Wire warm identified QUICK reuse and newly persisted IGDB-derived Steam IDs into the same bounded coordinator, for manual and scheduled operations.

Purpose: Deliver the approved description-language correction through existing owners.
Output: Tested behavior and explicit task verification receipts.

- [x] 36-08-PLAN.md - Translate approved source/fallback and Cancel editing wording for en_US, en_GB, bg_BG, cs_CZ, de_DE, es_ES.
- [x] 36-09-PLAN.md - Translate approved source/fallback and Cancel editing wording for fr_FR, hu_HU, it_IT, ja_JP, ko_KR, pl_PL.
- [x] 36-15-PLAN.md - Connect administrative interface-language selection to authorized global scan preference and remove stale browser metadata language as a manual scan override.
- [x] 36-16-PLAN.md - Propagate one captured language through console and PC search/confirmation and same-ID missing-description repair at existing interactive boundaries.

**Wave 5** *(blocked on assigned prior dependency waves)*

- [x] 36-10-PLAN.md - Translate approved source/fallback and Cancel editing wording for pt_BR, ro_RO, ru_RU, tr_TR, zh_CN, zh_TW.
- [x] 36-17-PLAN.md - Capture selected interface language for manual ROM matching search, choice and confirmation and verify durable localized results after reload.

**Wave 6** *(blocked on assigned prior dependency waves)*

- [x] 36-05-PLAN.md - Wire game and component overview surfaces to typed locale/source results after all18locale parity, keeping empty edit access and existing controls.

**Wave 7** *(blocked on assigned prior dependency waves)*

- [x] 36-12-PLAN.md - Protect exact-locale editor draft ownership and atomically finish caller migration by removing the transitional string/legacy seam.

**Wave 8** *(blocked on assigned prior dependency waves)*

- [x] 36-06-PLAN.md - Prove real description repair through authenticated HTTP/RQ and scheduled execution, plus revoked authority, in token-owned disposable MariaDB and PostgreSQL fixtures.

Purpose: Deliver the approved description-language correction through existing owners.
Output: Tested behavior and explicit task verification receipts.

**Wave 9** *(blocked on assigned prior dependency waves)*

- [x] 36-07-PLAN.md - Complete actual connected browser acceptance and frozen-source SQL/frontend/security/receipt validation. Produce reviewable evidence without automatic deployment.

Purpose: Deliver the approved description-language correction through existing owners.
Output: Tested behavior and explicit task verification receipts.

**Cross-cutting constraints:** PreferredDE/FRprovidertext precedesEnglishfallback whileallmanualstorage isprotected. Reuseexistingauthorizedglobalpriority,immutableoperationlocale,provider/merge/retry/fenceowners. CoveractualSteamPC/ScreenScraperROMfetch/persistence,manualsearch/confirmation/refreshandallscanpaths. Preservewarmreuse,18locales,andisolateddual-SQL/worker/browserproof. No livechanges/deploymentfromplanning.

### Phase 37: ZockArchive screenshot management UI redesign

**Goal:** Make screenshot upload reachable while browsing large collections and compact the existing screenshot management UI, preserving loaded data, multi-placement order, ownership, visibility, lightboxes and permissions through existing frontend handlers and APIs.
**Depends on:** Phase36, merged and user-accepted on 2026-10-23 at b58945bbffe472e65dba441cf9fc82e9c244348e.
**Requirements:** ZA-SHOT-01, ZA-SHOT-02, ZA-SHOT-03, ZA-SHOT-04, ZA-SHOT-05, ZA-SHOT-06, ZA-SHOT-07, ZA-SHOT-08, ZA-SHOT-09, ZA-SHOT-10, ZA-SHOT-11, ZA-SHOT-12.
**Status:** Complete:4/4 plans implemented; user accepted the observed Dev UAT scope on2026-10-24. Merged via PR6 at2a2789775c3cc645fa4a8a86efa277912035b78c after all GitHub checks passed, including16 backend shards. Final local frontend1,669/1,669 and38 assembled non-controller browser cases passed. Physical controller and separate production Portainer acceptance remain outside this accepted scope.
**Plans:**4 plans,8 tasks,3 waves

**Success Criteria:**

1. Upload remains reachable at the top and after long scrolling without duplicate upload logic or overlapping navigation.
2. Compact responsive cards expose truthful source, placement and permission-aware actions; multiple placements and ordering survive.
3. Provider, owner and community behavior remains faithful to current backend semantics, with no invented hide/delete or sort behavior.
4. Existing APIs, storage, permissions and other media surfaces remain intact; no backend or schema change is included.
5. Existing behavior tests, real-scroll browser checks, both themes and desktop/mobile evidence verify the redesign; architecture descriptions accompany it.

Plans:

**Wave1**

- [x] 37-01-PLAN.md: Existing action/upload owner and safe entity-bound completion.
- [x] 37-03-PLAN.md: All18 localized screenshot action and outcome contracts.

**Wave2 (depends on Wave1)**

- [x] 37-02-PLAN.md: Compact cards, sticky upload, scroll anchoring and architecture documentation.

**Wave3 (depends on Wave2)**

- [x] 37-04-PLAN.md: Isolated real-browser regressions, desktop/mobile captures and final frontend quality.

Cross-cutting constraints: Existing provider/personal/community ownership and placement order remain authoritative. One upload owner, no backend/schema/permission/storage change, all18 locales, existing design/input/scroll mechanisms and preserved local data.

### Phase 38: ZockArchive product and repository rebranding

**Goal:** Rebrand visible product identity and active repository/release/install references to ZockArchive and rename the same GitHub repository, preserving history, upstream attribution and installed storage/auth/API compatibility.
**Requirements**: ZA-BRAND-01, ZA-BRAND-02, ZA-BRAND-03, ZA-BRAND-04, ZA-BRAND-05, ZA-BRAND-06, ZA-BRAND-07, ZA-BRAND-08, ZA-BRAND-09, ZA-BRAND-10
**Depends on:** Phase 37
**Plans:** 6/9 plans executed

Plans:

- [x] 38-01-PLAN.md: Centralize browser identity, titles and real PWA outputs
- [x] 38-02-PLAN.md: Render shared text identity in active auth, navigation and release surfaces
- [x] 38-03-PLAN.md: Complete all eighteen localized product identities and remaining active copy
- [x] 38-04-PLAN.md: Update backend product metadata while preserving protocols and overrides
- [x] 38-05-PLAN.md: Rebrand desktop display and project metadata without renaming persisted identities
- [x] 38-06-PLAN.md: Update current operator documentation and product-owned release automation
- [ ] 38-07-PLAN.md: Adapt exact repository guards and current naming/install verifiers
- [ ] 38-08-PLAN.md: Prove compatible identity on owned browser, SQL and populated-install targets
- [ ] 38-09-PLAN.md: Perform verified same-repository rename and deliver reviewed feature integration
