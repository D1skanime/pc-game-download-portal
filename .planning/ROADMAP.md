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
**Plans:** 14/15 plans executed

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
- [ ] 18-15-PLAN.md — Re-run the 186-test Compose suite and full PostgreSQL cycle, then record final closure evidence.
