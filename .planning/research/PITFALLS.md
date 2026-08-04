# Domain Pitfalls

**Domain:** Brownfield conversion of RomM to an immutable external NAS library with explicit platform mappings and v2-only UI
**Researched:** 2026-08-04
**Overall confidence:** HIGH for observed code risks, MEDIUM for race-hardening details that require phase-specific Linux prototyping

## Critical Pitfalls

### 1. Treating `:ro` as the application security boundary

**What goes wrong:** Mutating endpoints and background tasks remain logically available and fail only when the kernel rejects a write. A deployment mistake, remount, alternate development configuration, or path routed to writable storage makes those operations destructive again.

**Why it happens:** A read-only Docker bind appears to solve the requirement cheaply. However, the project explicitly needs independent application authorization, and upstream has many write paths beyond the obvious upload button.

**Consequences:** Archive modification becomes configuration-dependent, APIs return inconsistent low-level errors, previews may mutate in development, and safety claims cannot be proven independently of one Compose file.

**Prevention:** Enforce an operation-capability policy before filesystem access. External roots allow enumerate, stat, read, hash, stream, and download only. They deny create, upload, write, overwrite, rename, move, copy, delete, extract, patch, and mkdir. Keep `:ro` as defense in depth and test both layers separately.

**Detection:** Run prohibited operations against a deliberately writable test mount and assert policy denial plus zero calls to filesystem mutation primitives. Then run allowed reads against an actual `:ro` bind.

### 2. Gating endpoints while leaving internal bypasses

**What goes wrong:** UI controls and selected FastAPI routes are disabled, but an RQ task, watcher-triggered scan, helper, cleanup job, socket handler, migration, or direct handler call reaches a mutation method without policy evaluation.

**Why it happens:** Mutation is distributed. Observed examples include ROM deletion with `delete_from_fs`, firmware deletion, ROM uploads, directory creation, rename/promotion, resource cleanup, extraction/patch workflows, and direct `unlink`, `rmtree`, `replace`, `mkdir`, and `makedirs` calls.

**Consequences:** A supposedly read-only system still has destructive alternate paths. Hidden controls provide false confidence.

**Prevention:** Inventory operations by sink, not route. Centralize source path acquisition and require an operation intent at the filesystem boundary. Make source handlers expose no public mutation methods. Route every endpoint, task, socket, watcher, and migration through the same resolver/policy. Distinguish external source storage from RomM-owned resources and temporary storage so legitimate derived-data cleanup remains possible.

**Detection:** Static search for mutation primitives and all library-root imports, plus tests that monkeypatch sinks (`unlink`, `rmtree`, rename/replace, write-mode open, archive extraction) to fail if called for an external root. Repeat the inventory near milestone completion because new bypasses may appear during refactoring.

### 3. Reusing `FSHandler` for the external root without changing its contract

**What goes wrong:** Merely constructing a handler calls `self.base_path.mkdir(parents=True, exist_ok=True)`. `FSPlatformsHandler.get_platforms()` can also bootstrap a `roms` folder through `create_library_structure()` when it cannot detect the legacy layout.

**Why it happens:** The existing base class looks like the natural central filesystem abstraction, and its validation is useful, but it assumes RomM owns and may initialize the root.

**Consequences:** Startup, browsing, or an empty/unreadable mount attempts to create directories in the archive. On `:ro`, startup behavior becomes error-prone. On a mistakenly writable mount, the archive is changed silently.

**Prevention:** Create a non-mutating external-root resolver/reader with a constructor that only validates existence, directory type, ownership contract, and readability. Do not subclass a mutation-rich handler unless mutation methods and initialization are structurally unavailable. Bypass structure detection and bootstrapping for mapped roots.

**Detection:** Instantiate every external-root service against a missing path, an empty path, an unreadable path, and a writable sentinel directory. Assert no directory or file is created in any case.

### 4. Canonical containment that still permits symlink escape or TOCTOU

**What goes wrong:** Lexical checks reject `..`, but symlinks resolve outside the approved root. Alternatively, code validates a path and later reopens it after a component is replaced. Prefix-string checks also confuse sibling names such as `/library` and `/library-old`.

**Why it happens:** Upstream `FSHandler.validate_path()` intentionally allows paths containing symlinks through lexical containment to support configured links. That behavior conflicts with this milestone. Even `Path.resolve()` plus `relative_to()` is a point-in-time check, not necessarily a safe open.

**Consequences:** Folder browsing, scanning, hashing, streaming, or downloading can read outside the approved NAS root. If a mutation bypass exists, the same issue can target external files.

**Prevention:** Reject absolute POSIX paths, Windows drive paths, UNC forms, NULs, backslashes under a POSIX canonical format, and every parent segment. Resolve root and candidate canonically and require `candidate.relative_to(root)`. Walk components with `lstat` and reject symlinks for external roots. For high-value read paths, phase-specific research should prototype descriptor-relative Linux opening with no-follow semantics and ensure the opened object matches the validated identity.

**Detection:** Test symlinks at the first, middle, and leaf component, relative and absolute targets, loops, broken links, sibling-prefix paths, and component replacement between validation and access. Do not mock path resolution in these tests.

### 5. Conflating catalog deletion with source deletion

**What goes wrong:** Removing a ROM or mapping invokes the current `delete_from_fs` branch, or scanner reconciliation interprets an unmapped/missing path as permission to delete bytes. Resource cleanup may also be pointed at source paths by an incorrect path classification.

**Why it happens:** Upstream `/roms/delete` explicitly supports database deletion and optional filesystem deletion in one operation, then deletes RomM-owned resources. Existing UI language and service methods may preserve that combined mental model.

**Consequences:** Correcting the index can delete original games. Mapping removal can cascade into source mutation or accidental broad catalog loss.

**Prevention:** Define catalog removal as a domain command that deletes SQL state and, where intended, derived RomM-owned resources only. Remove the source-deletion request shape and frontend option for this fork, rather than defaulting a dangerous flag to false. Mapping removal must be non-cascading toward source bytes and explicit about catalog impact. Path objects must carry storage ownership so resource cleanup cannot accept a source path.

**Detection:** Endpoint tests should assert catalog rows change, source manifests remain identical, and only expected RomM-owned derived paths are removed. Include mapping removal with populated catalog data and interrupted/retried operations.

## High-Risk Brownfield Pitfalls

### 6. Keeping fixed-layout assumptions inside scanner and watcher code

**What goes wrong:** The main scan uses mappings, but the watcher still computes platform identity by splitting a path at `LIBRARY_BASE_PATH`, choosing a structure depth from `has_structure_path_b`, and looking up `Platform.fs_slug`. Scheduled scans or helper functions may still derive `roms/{platform}` or `{platform}/roms`.

**Why it happens:** The watcher and scanner evolved around the two upstream layouts. Mapping only the admin API leaves secondary entry points unchanged.

**Consequences:** Events rescan the wrong platform, directories with spaces or deeper mappings are ignored, a mapped parent/child overlap causes ambiguous ownership, and deletion events can trigger inappropriate reconciliation.

**Prevention:** Make mapping lookup the sole platform-to-source relationship. Watcher event routing should canonicalize the event under the root, find the active mapping by path containment with an unambiguous longest-match rule or, preferably, prohibit overlapping active mappings. Consider disabling source watching by default for a remote read-only NAS because inotify/watchfiles behavior across NAS mounts is filesystem- and mount-dependent. Scheduled/manual scans must remain correct without watcher events.

**Detection:** Exercise root-level, mapping-level, nested, excluded, deleted, renamed, and overlapping paths. Validate behavior with the actual NAS protocol/mount type before promising watcher responsiveness.

### 7. Calling a preview “dry-run” while reusing mutating scan orchestration

**What goes wrong:** Preview calls the normal scanner inside a rolled-back transaction, but it still writes caches, downloads metadata/assets, creates resources, emits sockets, schedules jobs, updates missing flags, or removes stale records.

**Why it happens:** Reusing the full scan entry point minimizes code but DB rollback covers only one class of side effect.

**Consequences:** An administrator’s mapping test changes application state or derived files, and the immutability evidence is misleading.

**Prevention:** Factor pure discovery and classification from persistence/enrichment. Preview should enumerate candidates and diagnostics only, with an explicit side-effect-free result type. Do not enqueue RQ work or invoke provider/resource handlers.

**Detection:** Snapshot database tables, Redis keys/queues, RomM-owned filesystem trees, socket emissions, outbound calls, and source manifests before and after preview. Assert all remain unchanged except request logs.

### 8. Migrating by moving content or overloading `Platform.fs_slug`

**What goes wrong:** A migration tries to normalize existing directories, stores absolute paths, or silently repurposes `fs_slug` as the new mapping. Ambiguous Structure A/B libraries get auto-converted incorrectly.

**Why it happens:** Upstream already persists `fs_slug`, and Alembic migrations are expected to finish automatically at startup.

**Consequences:** Host/container coupling, lost legacy meaning, irreversible data changes, wrong platform associations, and cross-database migration failures.

**Prevention:** Use additive root, mapping, and audit tables. Keep `fs_slug` during the compatibility bridge. Detect legacy candidates without filesystem writes, validate containment/existence, and require explicit resolution for ambiguity. Use portable SQLAlchemy/Alembic constructs, bounded column lengths, deterministic uniqueness, and reversible migrations across MariaDB/MySQL/PostgreSQL.

**Detection:** Test empty, Structure A, Structure B, mixed/ambiguous, missing-directory, duplicate, Unicode, space-containing, and already-partially-migrated databases. Run upgrade and downgrade on MariaDB and PostgreSQL, then verify repeated startup is idempotent.

### 9. Making an “immutable” root mutable through configuration or ORM updates

**What goes wrong:** The first API supports changing mount path or storage kind because generic CRUD makes it easy. An update can turn an audited mapping into a reference to a different tree without changing the mapping record.

**Why it happens:** Immutability is treated as a UI convention rather than a data invariant.

**Consequences:** Audit history no longer proves which bytes a mapping referred to, and policy may change under existing catalog records.

**Prevention:** For milestone 1, expose no writable toggle and reject root kind/mount-path changes after creation. Prefer deployment-defined stable mount coordinates. If replacement is required operationally, create a new root identity and remap explicitly with audit records.

**Detection:** Model and API tests for direct ORM updates, PATCH payload smuggling, migration defaults, and concurrent mapping/root changes.

## Frontend and Design Pitfalls

### 10. Deleting v1 directories before identifying v2’s hidden dependencies

**What goes wrong:** Wholesale deletion breaks v2 because it still imports shared or v1 components. Observed v2-sensitive seams include `SoundtrackMiniPlayer`, `PairDispatcher` importing the v1 Pair view, `NotReady` switching back to v1, UI version settings, named router views, passthrough layouts, and theme/bootstrap logic.

**Why it happens:** Repository guidance labels broad directories as frozen v1, but coexistence introduced compatibility imports and routing behavior outside those directories.

**Consequences:** Blank routes, broken auth/setup/pair deep links, circular imports, missing overlays/theme tokens, player regressions, and build-only failures.

**Prevention:** Build an import/reachability inventory from v2 entry points before deletion. First make every shipped route have a real v2 target, replace dispatchers/fallbacks, and simplify routing from named views to one ordinary component tree. Then remove toggle persistence and v1 assets. Delete in bounded batches with typecheck/build/tests after each batch.

**Detection:** Search for `useUiVersion`, named `v2` router views, imports from v1 roots, `fallbackComponent`, `Passthrough`, and v1 route components. Test direct navigation and refresh for every route, especially setup, login, reset, register, pair, players, settings, and 404.

### 11. Removing UI controls but leaving API surface and permissions inconsistent

**What goes wrong:** Upload/delete/rename controls disappear in v2, yet generated services, API routes, permission labels, keyboard actions, context menus, or direct URLs remain capable of mutation.

**Why it happens:** v1 removal and storage safety are treated as unrelated visual cleanup.

**Consequences:** Advanced users or stale clients can call dangerous routes. Permission semantics no longer match the product.

**Prevention:** Decide endpoint disposition explicitly: remove source-mutating routes where incompatible, or retain only operations proven to target RomM-owned storage. Regenerate OpenAPI types and remove dead services/actions. Review gamepad, keyboard, selection-bar, and context-menu paths, not just visible admin pages.

**Detection:** Contract diff, route inventory, frontend service search, permission matrix tests, and direct authenticated HTTP attempts against every former operation.

### 12. Copying Team4s implementation or visual identity instead of deriving principles

**What goes wrong:** React components, proprietary structure, exact branding, CSS, or product-specific interaction assumptions leak into RomM. Alternatively, superficial visual imitation violates v2 tokens, accessibility, gamepad navigation, and responsive rules.

**Why it happens:** A concrete reference is easier to copy than to translate into RomM’s Vue design system.

**Consequences:** Legal/provenance risk, two component systems, inconsistent theming, inaccessible folder navigation, and maintenance burden.

**Prevention:** Keep Team4s read-only. Record abstract observations only: hierarchy, density, spacing, typography roles, navigation, cards, and state presentation. Implement with RomM v2 tokens and `R*` primitives, preserving universal input and zero-literal theming rules. Do not make Team4s a build or runtime dependency.

**Detection:** Review diffs for copied code/assets/identifiers, new React dependencies, literal colors, raw interactive elements, and missing keyboard/gamepad/focus behavior. Document design provenance as principles, not copied artifacts.

## Testing Pitfalls

### 13. Testing denial only on a read-only mount

**What goes wrong:** A mutation test passes because the OS returned `EROFS`, even though application policy was never called.

**Prevention:** Run policy-denial tests on writable fixtures and assert rejection occurs before the sink. Run separate container tests for the mount control.

### 14. Mocking away the filesystem behavior under test

**What goes wrong:** Mocked `resolve`, `is_symlink`, or directory enumeration cannot reveal symlink chains, normalization differences, races, permissions, or NAS behavior.

**Prevention:** Use real temporary trees and links for resolver tests. Reserve mocks for verifying that forbidden sinks and external providers were not called.

### 15. Using content hashes as the entire immutability proof

**What goes wrong:** Hashes remain stable while names, permissions, ownership, timestamps, directory entries, or symlink targets change. Reads may alter access times.

**Prevention:** Capture names, relative paths, file types, sizes, hashes, modes, ownership where available, timestamps with documented atime expectations, and link targets. Recommend `noatime` or appropriate `relatime` behavior and distinguish archive-content immutability from access metadata.

### 16. Missing dialect, concurrency, and restart cases

**What goes wrong:** Mapping uniqueness works on one database only, concurrent updates create two active mappings, audit writes split from mapping changes, or a queued scan uses a mapping changed after enqueue.

**Prevention:** Use DB constraints plus transactions, audit in the same transaction, and define job semantics around mapping version or root/mapping snapshot. Test MariaDB and PostgreSQL, concurrent requests, worker retries, and restart/idempotency.

## Operational Sequencing Pitfalls

### 17. Mounting the real NAS before the safety boundary is proven

**What goes wrong:** Brownfield code touches production data while mutation paths and startup mkdir behavior are still being refactored. The active Team4s encode workload may also be disrupted by unrelated service or mount changes.

**Prevention:** Develop with synthetic fixtures, then a disposable writable sentinel archive, then a disposable read-only bind, and only then schedule the real NAS mount when operations permit. Never restart Team4s services or alter `/home/d1sk/team4s`.

**Detection:** Deployment checklist requires completed mutation inventory, passing writable-fixture policy tests, container read-only evidence, backup/rollback plan, and an approved operational window.

### 18. Deploying schema, workers, and frontend in an incompatible order

**What goes wrong:** Old workers consume jobs using fixed-layout assumptions after mappings are active, or a new frontend calls APIs before migrations/backend deployment. Queued jobs survive application replacement in Redis.

**Prevention:** Define a compatibility window. Pause scan scheduling and drain or invalidate incompatible queued scan jobs, deploy additive schema/backend first, create/validate mappings without activating them, deploy v2 frontend, activate mapping-based reads, then retire fixed-layout code and v1. Do not restart unrelated services.

**Detection:** Preflight checks database revision, worker image/version, queue contents, active scans, mapping readiness, mount state, and generated frontend/backend contract compatibility.

### 19. Confusing unreadable, unavailable, empty, and deleted storage

**What goes wrong:** A transient NAS outage or permissions error is interpreted as an empty library, causing catalog missing flags or cleanup. Upstream already contains defensive cleanup logic for suspiciously empty DB/resource states, but external-root availability needs its own state.

**Prevention:** Model root health explicitly. Fail closed on unavailable/unreadable roots, preserve catalog state, and prevent reconciliation/cleanup until availability is confirmed. Require a stable successful scan before destructive catalog cleanup, even though source deletion is prohibited.

**Detection:** Tests for mount absent at startup, mount disappearing mid-scan, permission denial, stale file handles, partial enumeration, timeout, and recovery without catalog loss.

## Phase-Specific Warnings

| Phase topic | Likely pitfall | Required mitigation |
|---|---|---|
| Root/schema foundation | Generic CRUD weakens immutability | Immutable kind/path contract, additive portable migration, transactional audit |
| Resolver and policy | Lexical containment or inherited mkdir/write behavior | Separate non-mutating service, real symlink tests, operation intent at boundary |
| Mapping APIs | Absolute-path leakage, overlap, concurrency | Relative canonical form, no host paths, uniqueness/overlap rules, DB transaction |
| Scanner integration | Secondary paths retain layout assumptions | Trace manual, scheduled, socket, watcher, hash, stream, and download entry points |
| Preview/browser | Dry-run side effects and arbitrary path oracle | Pure discovery, admin-only narrow API, sanitized errors, server-issued relative cursors |
| Catalog removal | Old `delete_from_fs` semantics survive | Remove source-delete contract and prove only DB/owned resources change |
| Migration bridge | Auto-conversion moves or misbinds content | Proposal-only detection, explicit ambiguity handling, no source writes |
| v1 removal | Hidden v2 imports and deep-link gaps | Import graph, route matrix, staged deletion, typecheck/build/E2E after each batch |
| Design application | Copying Team4s or bypassing v2 rules | Principle-only review, native Vue primitives/tokens, accessibility/input verification |
| Deployment | Real NAS exposed too early or stale workers run | Synthetic-to-disposable-to-real progression, queue/worker preflight, approved window |

## Sources

- `/home/d1sk/romm/.planning/PROJECT.md` and `.planning/research/STACK.md` (HIGH)
- `/home/d1sk/romm/.planning/codebase/{ARCHITECTURE,CONCERNS,CONVENTIONS,INTEGRATIONS,STACK,STRUCTURE,TESTING}.md` (HIGH)
- `backend/handler/filesystem/base_handler.py` and `platforms_handler.py`, constructor mutation, validation, layout bootstrap (HIGH)
- `backend/endpoints/roms/__init__.py`, combined catalog/source deletion behavior (HIGH)
- `backend/endpoints/roms/upload.py`, `patch.py`, `files.py`, `manual.py`, `screenshot.py`, and `soundtrack.py`, mutation and temporary-storage paths (HIGH)
- `backend/watcher.py`, fixed-layout event parsing and `fs_slug` lookup (HIGH)
- `backend/handler/scan_handler.py`, `backend/handler/filesystem/roms_handler.py`, and scan socket/scheduled tasks, read-path integration seams (HIGH)
- `backend/tasks/scheduled/cleanup_orphaned_resources.py` and `backend/tasks/manual/cleanup_missing_roms.py`, cleanup semantics (HIGH)
- `frontend/src/RomM.vue`, `frontend/src/plugins/router.ts`, `frontend/src/v2/router/routes.ts`, `PairDispatcher.vue`, `NotReady.vue`, and UI settings, dual-UI coupling (HIGH)
- Repository pytest/Vitest/Storybook/Playwright configuration and codebase testing map (HIGH)
- `/home/d1sk/team4s`, inspected only as a read-only design-principle reference, never as a code source or dependency (HIGH)

## Research Flags

- **Resolver phase:** Prototype Linux descriptor-relative, no-follow access and document what protection remains against component replacement during long reads. Confidence: MEDIUM until exercised on the production mount type.
- **Watcher phase:** Verify watchfiles/inotify behavior and event fidelity on the actual NAS protocol and mount options. Scheduled/manual correctness must not depend on watcher support. Confidence: MEDIUM.
- **Migration phase:** Decide whether mapping overlap is forbidden or resolved deterministically, and specify catalog behavior when a mapping changes. Confidence: MEDIUM.
- **Operations phase:** Confirm the NAS mount technology, atime policy, UID/GID/read permissions, timeout behavior, and safe deployment window around the active encode workload. Confidence: MEDIUM.
