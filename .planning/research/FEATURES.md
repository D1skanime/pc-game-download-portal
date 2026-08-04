# Feature Landscape

**Domain:** NAS-first, read-only game library management
**Project:** RomM PC Library, milestone 1
**Researched:** 2026-08-04
**Confidence:** HIGH for repository-backed scope and dependencies; MEDIUM for workflow details that still require phase specification

## Scope Position

Milestone 1 is a storage-safety and compatibility milestone. It does not need to reinvent RomM's existing authenticated catalog, metadata, scan, streaming, download, collections, user state, or browser-player capabilities. It must replace the assumption that RomM owns a prescribed writable library layout with a durable contract for indexing an existing archive through one approved, immutable root.

The product promise is stronger than a read-only Docker mount. Administrators must be able to understand what root is active, map existing folders without exposing absolute paths, preview the effect of a scan, and remove catalog state without risking source content. Every backend entry point must enforce the same policy even if the UI is bypassed or the external mount is accidentally writable.

## Table Stakes

Missing any of these makes the milestone unsafe, incomplete, or unusable for the stated NAS workflow.

| ID | Feature | Why Expected | Complexity | Milestone 1 requirement |
|----|---------|--------------|------------|-------------------------|
| TS-01 | One approved external storage root | The user mounts an existing NAS tree once and must not maintain one Docker mount per platform | High | Represent one root with an immutable `external_read_only` mode. Application data and generated files remain outside it. Do not offer a writable toggle. |
| TS-02 | Relative platform folder mappings | Existing archives use human-owned folder names rather than RomM slugs or `roms/{platform}` | High | Map each platform to zero or one active normalized relative directory within the root. Never persist host paths or absolute container paths in a platform mapping. Prevent conflicting active mappings where ambiguity would make scan ownership unclear. |
| TS-03 | Central path resolution and containment | Folder browsing, scans, hashes, downloads, and streams must resolve the same bytes safely | High | Resolve `(root, relative mapping, relative item path)` through one backend boundary. Reject empty or malformed input where inappropriate, absolute POSIX paths, Windows drive paths, UNC paths, parent traversal, NULs, canonical escape, and symlink escape. Do not rely on the current generic handler behavior that intentionally permits contained lexical paths through symlinks. |
| TS-04 | Safe v2 folder browser | Administrators need to select real directories without typing paths or learning the container filesystem | Medium | Browse directories only, starting at the approved root, with breadcrumbs expressed as relative segments. Never reveal host paths, allow arbitrary path entry outside the root, follow escaping symlinks, enumerate files unnecessarily, or expose mutation controls. Handle unreadable, missing, stale, and empty folders without leaking server details. |
| TS-05 | Mapping test | A saved path must be validated before it becomes scan input | Medium | Provide a non-mutating test that reports containment, existence, readability, directory status, symlink safety, and useful discovery facts such as immediate candidate count. A test is advisory until save, so save must repeat authoritative validation to avoid time-of-check/time-of-use assumptions. |
| TS-06 | Non-mutating scan preview | Users need to see what RomM will index before committing database and metadata changes | High | Preview the selected mapping using the same enumeration rules as the real scan. Report candidate logical games and files, ignored entries, existing matches, likely additions/updates/missing records, warnings, and bounded errors. Preview writes neither catalog rows nor metadata/resources and never changes source bytes. Results must be bounded or paginated for large folders and explicitly become stale when mapping or filesystem state changes. |
| TS-07 | Read-only scan execution | Preview must lead to a useful catalog while preserving the archive | High | Existing recursive single-file and directory-based `Rom`/`RomFile` discovery, hashing, and metadata enrichment remain available. Scan reads external bytes and writes only database rows, resources, assets, cache, audit data, and temporary data under RomM-owned roots. |
| TS-08 | Central external-root storage policy | Hiding write buttons does not protect the archive from APIs, tasks, sockets, or future regressions | High | Before filesystem access, reject create, upload, overwrite, rename, move, copy, delete, extract, patch-output persistence, single-file-to-folder conversion, and directory creation when the target is under an external root. Apply the policy across endpoints, handlers, background tasks, scheduled cleanup, and socket workflows. Return a stable, actionable policy error. |
| TS-09 | Read-only content access | A library manager remains useful only if indexed games can be consumed | Medium | Preserve hashing, metadata reads, browser play where compatible, single-file streaming/download, and selected multi-file download. Temporary ZIPs, generated playlists, caches, and conversion artifacts must be outside the source root. Any path that requires writing beside a game is disabled or redirected to RomM-owned storage. |
| TS-10 | Catalog-only removal | Administrators need to correct the index without deleting valuable source material | High | Remove a `Rom`, platform mapping, or stale catalog record from the database independently of source deletion. For external roots, the API must not accept a source-delete option and the UI must say what is removed: catalog metadata and RomM-owned resources, never original files. Rescanning an unchanged active mapping may rediscover a removed game, which the UI and docs must explain. |
| TS-11 | Mapping lifecycle and audit history | Mapping changes alter what the catalog sees and require accountability | Medium | Record create, update, activation/deactivation, and removal with actor, timestamp, root identity, platform identity, old relative mapping, new relative mapping, and outcome. Treat paths as operationally sensitive: expose audit detail only to authorized administrators and never log host paths unnecessarily. Audit records live outside the archive and are not removed with the mapping. |
| TS-12 | Safe migration or compatibility bridge | Existing installations cannot be forced to reorganize or move their libraries | High | Detect supported legacy Structure A (`roms/{platform}`) and Structure B (`{platform}/roms`) associations, propose relative mappings, identify ambiguous/unmatched platforms, and require an explicit administrator review. Migration changes configuration/database state only. It never creates folders, renames, moves, copies, or deletes content. It is restartable and reports partial failures. |
| TS-13 | v2-only product surface | Maintaining two UIs would duplicate storage workflows and retain unsafe compatibility paths | High | Remove the UI version selector, local storage version state, v1 named views, v1 fallback, v1 pair dispatch, v1 layouts/views/components/console code, and v1-only route shims. Preserve and rewire shared services, stores, composables, generated types, auth, and v2 routes. Unknown routes and every supported workflow must resolve predictably in v2. |
| TS-14 | Archive-safety evidence | The central value proposition needs proof, not only intended behavior | High | Cover policy, path resolution, traversal, Windows/UNC input, symlink escape, browse, mapping, preview, scan, catalog removal, migration, and API bypass attempts. Include a container test with the external root mounted `:ro` plus before/after filesystem manifests proving no changes to names, directories, content, or metadata under test control. |
| TS-15 | Deployment and operator guidance | NAS safety depends on correct mounting and clear recovery procedures | Medium | Document the single `:ro` mount, writable RomM-owned mounts, root registration, mappings, preview and scan behavior, migration, audit, troubleshooting permissions/stale mappings/symlinks, backup expectations, and optional NAS `noatime` guidance. Never suggest making the archive writable to resolve an application error. |

## Differentiators

These are not generic ROM-manager expectations. They express why this fork is valuable to users with a long-maintained archive.

| ID | Feature | Value Proposition | Complexity | Recommendation |
|----|---------|-------------------|------------|----------------|
| DF-01 | Defense-in-depth immutability | The archive remains protected even if an endpoint is called directly or the mount is misconfigured | High | Make this the product's primary trust claim and a release gate, not a settings label. |
| DF-02 | Organization-preserving platform mapping | RomM adapts to names such as `Nintendo Switch`, `SNES Super Nintendo`, and `PC` without forcing RomM slugs or restructuring | High | Keep mapping identity separate from platform metadata identity and filesystem display names. |
| DF-03 | Preview-before-index workflow | Administrators can validate scope, ignored content, and likely catalog changes before a large or expensive scan | High | Use the same discovery engine for preview and execution, with an explicit summary and drill-down rather than a second approximate parser. |
| DF-04 | Explainable safety states | Users can tell whether a root, mapping, action, or error is read-only and why | Medium | Show immutable status, relative path, validation state, last test/preview time, and blocked-action explanation on the v2 administration surfaces. Avoid security theater such as a decorative lock icon without behavioral guarantees. |
| DF-05 | Audited mapping changes | Operators can reconstruct why a platform began scanning a different subtree | Medium | Provide a compact admin audit view or mapping-local history after the persistence and authorization contract is stable. |
| DF-06 | Evidence-backed migration | Existing RomM users can adopt mappings without trusting a destructive conversion script | High | Present a dry-run report and retain recovery information for database/config changes. Source content is never part of rollback because it is never changed. |
| DF-07 | Focused v2 administration design | New workflows feel like part of a browsable game library rather than a raw filesystem control panel | Medium | Derive hierarchy, spacing, state presentation, and navigation principles from the read-only Team4s review, then implement them with RomM's Vue v2 tokens and primitives. Do not copy React components or broaden milestone 1 into a full redesign. |

## Anti-Features

These features must explicitly not be built in milestone 1, either because they violate archive safety or because they expand the milestone before its foundational contract is proven.

| ID | Anti-Feature | Why Avoid | What to Do Instead |
|----|--------------|-----------|-------------------|
| AF-01 | Writable external-root mode or per-root writable toggle | One mistaken setting undermines the core promise and multiplies policy states | External roots are permanently `external_read_only`; future writable/import storage must be a separate root type and milestone. |
| AF-02 | File manager behavior | Rename, move, copy, delete, create-folder, upload, extraction, and archive organization directly threaten the source collection | The browser selects directories and reports state only. Manage source files outside RomM. |
| AF-03 | Per-platform Docker mounts | It burdens deployment, leaks container layout into domain configuration, and scales poorly | Mount one approved root and store platform-relative mappings. |
| AF-04 | Absolute or host paths in mappings | They are non-portable, expose infrastructure, and create traversal/containment risk | Persist only normalized paths relative to an approved root identity. |
| AF-05 | UI-only read-only enforcement | APIs, workers, sockets, and regressions could still mutate content | Enforce a central backend storage capability policy before I/O, with the mount as a second boundary. |
| AF-06 | Automatic restructuring during migration | Moving or creating source content violates the project promise and makes rollback dangerous | Generate and review mapping proposals, then migrate database/config state only. |
| AF-07 | Source-delete option during catalog removal | A checkbox or request field can turn routine cleanup into data loss | External-root removal is always catalog-only. Remove RomM-owned derived resources separately and label that scope. |
| AF-08 | Persistent scan-preview side effects | A preview that creates catalog rows, downloads art, changes missing flags, or fills source directories is not a preview | Read and classify only. If ephemeral server state is needed, keep it outside the root with a short lifetime and no catalog semantics. |
| AF-09 | Following symlinks because they appear below the root | The existing generic validator can lexically allow symlink paths; an external-root symlink may escape canonical containment | Reject escaping symlinks after canonical resolution. Decide and document whether contained symlinks are allowed, defaulting to reject if the contract remains ambiguous. |
| AF-10 | PC game component hierarchy | Base game, update, DLC, hotfix, and extras modeling depends on a stable immutable file contract and would obscure milestone verification | Continue using existing `Rom` plus `RomFile` behavior in milestone 1. Design components in a later milestone. |
| AF-11 | Manifests, immutable revisions, resumable orchestration, or Windows downloader | These introduce transfer protocols and state machines unrelated to the root boundary | Defer until storage-root and immutable-file contracts are validated. |
| AF-12 | Dynamic ZIP redesign or installation planning | Existing downloads are sufficient to prove read access and these projects add unrelated complexity | Preserve compatible read/download behavior and ensure generated artifacts stay outside the archive. |
| AF-13 | Complete redesign of all v2 screens | It expands risk and delays the safety boundary | Apply the derived visual direction only to new root, browser, mapping, preview, audit, and migration surfaces. |
| AF-14 | Continued v1 compatibility | It doubles test and implementation paths and retains named-view fallback complexity | Delete v1 in a bounded workstream after confirming every required route and shared dependency has a v2 owner. |

## Feature Dependencies

```text
External-root persistence (TS-01)
  -> central path resolver (TS-03)
     -> safe folder browser (TS-04)
     -> mapping validation/test (TS-05)
     -> scan preview (TS-06)
     -> read-only scan and content access (TS-07, TS-09)

Central storage policy (TS-08)
  -> safe scan execution (TS-07)
  -> catalog-only removal (TS-10)
  -> migration safety (TS-12)
  -> immutability evidence (TS-14)

Platform mapping persistence (TS-02)
  -> mapping test (TS-05)
  -> preview (TS-06)
  -> scan execution (TS-07)
  -> mapping audit (TS-11)
  -> migration/bridge (TS-12)

Complete v2 route and workflow inventory
  -> v2-only rewiring (TS-13)
  -> safe deletion of v1 (TS-13)

All storage and migration behavior
  -> deployment/operator documentation (TS-15)
  -> release-level immutability proof (TS-14)
```

The preview and real scan must share enumeration and resolution code. Building preview first against a separate implementation would create drift exactly where users rely on it for safety. Likewise, catalog-only removal must follow the central policy rather than becoming a special UI label around the current endpoint's optional filesystem deletion branch.

## Required Workflow Contracts

### Root and Mapping Setup

1. An administrator sees the configured external root as an opaque named root and immutable mode, not as an editable host path.
2. The administrator chooses a platform and browses relative directories within that root.
3. The browser rejects unsafe traversal and symlink states server-side on every request.
4. A mapping test reports whether the directory can be safely read and what RomM is likely to discover.
5. Save repeats validation, records the mapping, and writes an audit event.
6. No setup step creates the selected directory or any RomM layout beneath it.

### Preview and Scan

1. Preview is available only for a valid mapping and clearly identifies platform plus relative directory.
2. Preview summarizes candidate games/files, ignored entries, database deltas, warnings, and errors without metadata downloads or persistence.
3. The administrator explicitly starts a real scan after reviewing the preview.
4. The scan revalidates mapping containment and filesystem state instead of trusting preview results.
5. Source reads feed existing `Rom` and `RomFile` indexing; all produced state is stored outside the external root.
6. Completion distinguishes successful indexing, skipped/ignored content, stale or missing paths, and policy failures.

### Catalog Removal

1. The UI says `Remove from catalog` for external-root games and never offers `Delete files`.
2. The backend ignores no hidden destructive flag. It rejects any request to delete external source content.
3. Database records and eligible RomM-owned derived resources are removed according to an explicit policy.
4. The response and audit trail identify catalog effects without implying source deletion.
5. Documentation explains that a later scan can rediscover an unchanged source game.

### Mapping Change or Removal

1. A change is validated and previewable before activation.
2. The UI explains that changing a mapping affects future discovery and may mark current records missing, but does not touch files.
3. Old and new relative paths are audited with the actor and result.
4. Removing a mapping disables future scans for that association. Source content remains untouched.
5. Existing catalog disposition is explicit: retain until reconciled or remove through a separate catalog-only action. It must not be an accidental cascade.

### Legacy Migration

1. Detect existing platform associations and filesystem structure without modifying either.
2. Produce proposed relative mappings and flag collisions, missing folders, symlinks, unreadable paths, duplicate platform ownership, and associations that cannot be inferred.
3. Require administrator confirmation for proposals, especially ambiguous matches.
4. Persist root/mapping state and audit events transactionally or with restartable checkpoints.
5. Never invoke existing library bootstrap, platform folder creation, rename, upload, or deletion behavior.
6. Provide a result report and a database/config rollback path that does not involve source content.

## Permission and Visibility Requirements

| Capability | Administrator | Non-admin authenticated user | Notes |
|------------|---------------|------------------------------|-------|
| View root status and mappings | Yes | No by default | Do not expose infrastructure or mapping details through general platform schemas unless required. |
| Browse folders | Yes | No | Require platform/root administration scope and server-side authorization on every browse request. |
| Test/create/change/remove mappings | Yes | No | Reuse granular platform/config administration permissions where appropriate; audit the authenticated actor. |
| Run preview | Yes | No by default | Preview reveals filenames and directory structure. Treat this as sensitive administration data. |
| Run scan | Existing authorized roles | Existing behavior, subject to policy | External-root policy cannot be overridden by role. |
| Stream/download indexed content | Existing authorized roles | Existing visibility rules | Storage mode changes mutation capability, not ordinary content visibility. |
| Remove catalog entries | Existing authorized roles | Existing permission model | For an external root, no role can delete source content through RomM. |
| View mapping audit | Administrator | No | Consider path details sensitive even though they are relative. |

## MVP Recommendation

Prioritize the milestone as these product slices:

1. **Immutable storage contract:** root model, `external_read_only` capability policy, canonical resolver, and adversarial tests.
2. **Mapping administration:** relative mapping persistence, safe folder browser, mapping test, audit events, and v2 administration UI.
3. **Preview-to-scan workflow:** shared discovery engine, bounded preview, read-only execution, and clear results.
4. **Safe lifecycle:** catalog-only removal, mapping changes/removal, and legacy migration/bridge.
5. **Single frontend and release proof:** remove v1 and its routing/version compatibility, complete container and before/after evidence, then publish deployment and migration documentation.

Defer PC components, manifests, revision tracking, transfer orchestration, the Windows client, dynamic ZIP redesign, installation planning, writable/import storage, and broad visual redesign. None should enter milestone 1 acceptance criteria or data modeling.

## Roadmap Acceptance Signals

- An administrator can map `Nintendo Switch` or another existing relative folder without typing or storing an absolute path.
- Browser, test, preview, and scan agree on containment and discovered scope.
- A preview produces no database, resource, cache-with-catalog-semantics, or source changes.
- Direct API attempts to upload, delete, rename, convert, patch-write, extract, or create a directory under the external root fail at the application policy boundary even on a writable test mount.
- Normal scan, hash, stream, browser play, and download reads continue where compatible.
- Removing a catalog entry or mapping leaves the source tree byte-for-byte and name-for-name unchanged.
- Legacy layout migration creates mappings without source filesystem operations.
- Every mapping lifecycle change has an authorized actor and old/new audit record.
- The production frontend has no v1 toggle, named-view fallback, dispatcher, route, or v1-only compatibility surface.
- The container uses one external `:ro` games mount and separate writable RomM-owned storage.

## Sources and Evidence

All findings are based on the canonical repository and project scope. No Team4s source or service was modified.

- `.planning/PROJECT.md` (2026-08-04): authoritative milestone requirements, constraints, decisions, and exclusions. **Confidence: HIGH**.
- `CLAUDE.md`: v1 freeze/v2 ownership, architecture, API generation, testing, and repository constraints. **Confidence: HIGH**.
- `.planning/codebase/ARCHITECTURE.md`: existing scan, download, `Rom`/`RomFile`, handler, task, and dual-UI boundaries. **Confidence: HIGH**.
- `.planning/codebase/CONCERNS.md`: brownfield mutation and security-risk inventory used to avoid treating UI controls or mount errors as policy. **Confidence: HIGH**.
- `.planning/codebase/TESTING.md`: available unit, endpoint, integration, container-adjacent, frontend, and migration verification patterns. **Confidence: HIGH**.
- `backend/handler/filesystem/base_handler.py`: current generic path validation and filesystem mutation primitives. It shows that milestone-specific canonical symlink policy must be explicit. **Confidence: HIGH**.
- `backend/handler/filesystem/platforms_handler.py`: current fixed Structure A/Structure B detection, folder creation fallback, and `fs_slug`-based platform discovery that mappings must replace or bridge. **Confidence: HIGH**.
- `backend/models/platform.py`: current platform identity and `fs_slug` persistence; no external-root mapping or audit model is present. **Confidence: HIGH**.
- `backend/endpoints/sockets/scan.py` and `backend/handler/scan_handler.py`: current filesystem-platform scan orchestration and recursive index behavior to preserve behind the new mapping/resolution contract. **Confidence: HIGH**.
- `backend/endpoints/roms/__init__.py`, `backend/endpoints/roms/files.py`, `backend/endpoints/roms/upload.py`, `backend/endpoints/roms/manual.py`, `backend/endpoints/roms/screenshot.py`, and `backend/endpoints/roms/soundtrack.py`: current read paths plus optional source deletion, upload, conversion, and source-adjacent mutation paths requiring policy enforcement. **Confidence: HIGH**.
- `frontend/src/RomM.vue`, `frontend/src/plugins/router.ts`, `frontend/src/v2/router/routes.ts`, and `frontend/src/composables/useUiVersion.ts`: current UI-version gate, named-view routing, fallback, and v1/v2 compatibility seams targeted for removal. **Confidence: HIGH**.
- `docs/PC_GAME_COMPONENTS_AND_MANIFEST_DOWNLOADS_ANALYSIS.md`: confirms PC component and transfer concepts are later work and should not reshape milestone 1. **Confidence: HIGH for deferral scope**.

## Open Questions for Phase Specification

- Whether distinct platforms may intentionally map to the same directory. Default recommendation: reject overlapping active mappings unless a concrete multi-platform use case and deterministic ownership rule are specified.
- Whether contained symlinks are allowed. Default recommendation: reject all symlinks in external-root mappings and traversal until a narrower, testable policy is approved.
- Whether the external root is configured only by deployment or can be registered in the UI. Default recommendation for milestone 1: deployment defines the absolute mount, UI exposes only an opaque root identity and relative browsing.
- Exact preview delta semantics for renamed/moved candidates and missing records. Reuse the scanner's reconciliation rules rather than inventing preview-only matching.
- Whether mapping removal retains all indexed records or offers an explicit follow-up catalog cleanup. Default recommendation: retain records and make cleanup a separate catalog-only action to avoid surprising cascades.
- Retention and export policy for mapping audit events.

