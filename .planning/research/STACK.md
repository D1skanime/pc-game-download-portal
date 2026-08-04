# Technology Stack

**Project:** RomM PC Library, milestone 1 secure NAS integration
**Researched:** 2026-08-04
**Confidence:** HIGH for repository facts and implementation seams, MEDIUM for exact schema naming until phase planning

## Recommendation

Keep the existing Python/FastAPI and Vue v2 modular monolith. Add storage roots, platform mappings, path resolution, storage policy, audit records, and preview APIs as native backend layers, then expose them through the existing generated OpenAPI client and v2 component system. Do not add a storage abstraction framework, a second API, or a new frontend framework. The difficult part is enforcing one security invariant consistently, not acquiring new infrastructure.

## Recommended Stack

### Existing core, retained

| Technology | Repository version | Purpose in milestone 1 | Why |
|---|---:|---|---|
| Python | 3.13 | Policy, path resolution, scanners, APIs, migrations | Already owns every filesystem and scan path. `pathlib`, `os`, and `stat` are sufficient for canonical containment and symlink checks. |
| FastAPI | 0.134.x | Admin root/mapping/browser/preview APIs | Preserves authentication, permission decorators, Pydantic validation, and the authoritative OpenAPI contract. |
| SQLAlchemy | 2.0.x | Storage root, mapping, and audit persistence | Existing repository pattern and portable across MariaDB, MySQL, and PostgreSQL. |
| Alembic | 1.16.x | Additive schema migration and legacy-layout bridge | Existing cross-dialect migration mechanism and CI path. |
| Pydantic | 2.11.x | Strict relative-path request and response schemas | Reject malformed mappings before resolution and generates frontend types. |
| Redis and RQ | Redis protocol, RQ 2.7.x | Existing scan jobs and progress only | Reuse scan orchestration. Root and mapping truth belongs in SQL, not Redis. |
| Vue | 3.4+ | v2-only administration workflow | Active frontend and established component/composable conventions. |
| TypeScript | 5.7 | Generated contracts and v2 state | Prevents handwritten API-shape drift. |
| Vite | 8 | Frontend build after v1 deletion | Existing build and test toolchain. |
| Vuetify, v2 `R*` primitives and tokens | Vuetify 3.9+ | Folder browser, mapping forms, preview states | Preserve RomM interaction/accessibility patterns while applying the derived Team4s visual principles. |
| Pinia and Vue Router | Pinia 3, Router 4.3+ | Admin state and v2 routes | Existing app state and routing; remove named-view duality rather than replacing routing. |
| pytest, Hypothesis, Vitest, Storybook, Playwright | Repository pinned | Security and UI verification | Already support filesystem property tests, API tests, component states, and full workflows. |
| Docker Compose and read-only bind mount | Existing deployment | OS-level archive protection | Mount the single approved NAS root at `/romm/library:ro`; application policy remains an independent control. |

### New domain components, no new dependency required

| Component | Recommended implementation | Responsibility |
|---|---|---|
| Storage root model | SQLAlchemy model with immutable kind `external_read_only`, stable container mount path, timestamps | Represents approved roots. Do not persist NAS host paths in mappings. For milestone 1, reject kind changes rather than model a writable state. |
| Platform mapping model | One active mapping per platform and root, normalized POSIX-style relative path, uniqueness constraint | Decouples platform identity from upstream `fs_slug` and fixed `roms/{platform}` layouts. |
| Mapping audit model | Append-only actor, timestamp, action, old value, new value | Makes mapping changes independently reviewable. Store structured scalar values rather than dialect-specific assumptions where portability is uncertain. |
| Path resolver | Small central backend service using `pathlib.Path`, `os.lstat`/`stat`, explicit normalization and operation intent | Converts `(root_id, relative_path)` to a contained canonical path and is the only gateway to source bytes. |
| Storage policy | Central enum/value object for operation classes and root capabilities | Allows read, enumerate, stat, hash, stream, and download. Denies create, upload, write, overwrite, rename, move, copy, delete, extract, patch, and mkdir before filesystem access. |
| Root browser/preview endpoints | Thin FastAPI endpoints calling resolver, policy, scanner, and DB handlers | Lists directories only, tests a mapping, and returns a non-mutating scan preview. No generic arbitrary-path endpoint. |
| v2 admin feature | `frontend/src/v2/` feature components plus existing `R*` primitives, API service, i18n, and generated types | Provides root status, constrained directory navigation, mapping validation, and explicit preview results. |

## Implementation Approach

### 1. Establish the immutable root contract first

Add schema and configuration for exactly one external root in this milestone. Deployment supplies the fixed container path, recommended `/romm/library`, using a read-only bind mount. Keep database, resources, assets, cache, temporary data, hashes, and audit data on existing RomM-owned writable paths. Do not call the current `FSHandler.__init__` unchanged for an external root because it executes `mkdir(parents=True, exist_ok=True)` and therefore has a mutating constructor contract.

Make immutability structural: the API accepts no writable flag, the database only permits `external_read_only`, and update code rejects root-kind or mount-path mutation. Docker `:ro` is defense in depth, not the policy implementation.

### 2. Centralize resolution before adapting consumers

Create one resolver used by browser, preview, scan, hash, stream, and download code. Its input is a stored root identity plus a normalized relative mapping or catalog path, never a caller-supplied absolute path.

Resolution should:

1. Reject empty values where not meaningful, NULs, absolute POSIX paths, Windows drive paths, UNC paths, backslashes if the canonical stored format is POSIX, and every `..` segment.
2. Normalize `.` and duplicate separators, then persist one canonical relative representation.
3. Resolve the approved root and candidate with strict existence appropriate to browsing/scanning.
4. Require `candidate.relative_to(root)` after canonical resolution.
5. Walk path components with `lstat` or equivalent and reject symlinks for external-root mappings and source traversal. This is stricter and safer than upstream `FSHandler.validate_path`, which intentionally permits configured symlink paths lexically.
6. Return a typed resolved-path object carrying root identity and read-only capability, not a bare string that later code can reinterpret.

Avoid lexical prefix checks such as `str(candidate).startswith(str(root))`. Avoid `Path.resolve()` alone followed by later reopening through an unchecked path, which leaves room for time-of-check/time-of-use replacement. Phase planning should evaluate descriptor-relative opening (`openat` style with no-follow semantics) for the strongest Linux guarantee, especially for streaming and hashing.

### 3. Put policy ahead of every filesystem action

Introduce an operation enum and a single policy check near the filesystem boundary. Endpoint visibility is not enforcement. Existing handlers include directory creation, rename, deletion, upload, extraction, patching, and resource writes, so every call path touching library content must pass an operation intent.

Separate source-library handlers from RomM-owned writable storage handlers. Read-only source handlers must not inherit public mutation methods or constructor behavior that creates directories. Catalog removal should delete SQL rows and derived RomM-owned artifacts only, never call a source unlink/rmtree path.

### 4. Replace layout inference with explicit mappings

Upstream `FSPlatformsHandler` infers Structure A (`roms/{platform}`) or Structure B (`{platform}/roms`) and may bootstrap directories. Bypass that behavior for external roots. A platform mapping should point directly to an existing relative directory such as `Nintendo Switch` or `PC`; scanners receive the resolver result instead of deriving a path from `Platform.fs_slug`.

Keep `fs_slug` temporarily for compatibility with existing records and metadata behavior, but stop treating it as the external directory contract. Build an additive migration/bridge that can translate a detected legacy layout into proposed mappings without moving or creating content. Require validation and preview before activation where ambiguity exists.

### 5. Add narrow APIs and regenerate contracts

Recommended API surface:

- read root status and capability;
- list immediate child directories under a root-relative cursor;
- create, change, or remove one platform mapping;
- test a mapping with containment/readability diagnostics;
- preview a scan with counts, candidate paths, exclusions, and conflicts, with no DB or source mutations.

Use opaque root IDs and relative paths. Never return host paths. Mask filesystem details in ordinary errors and log security diagnostics server-side. Protect every endpoint with the existing admin permission system. After schemas stabilize, run `npm run generate`; frontend code imports generated models only.

### 6. Make the frontend v2-only as a bounded cleanup

Delete the frozen v1 view/component/layout/console trees only after dependency analysis identifies shared modules still imported by v2. Simplify `RomM.vue` to mount the v2 application unconditionally, remove `useUiVersion`, settings persistence/toggle, the `default` versus `v2` named-view route composition, v1 theme scoping, and v1-only fallbacks. Keep shared services, Pinia stores, generated types, socket client, player utilities, and any component still used by v2 until it is migrated.

Build new storage UI under `frontend/src/v2/` with existing primitives and input rules. The folder browser should navigate server-issued relative entries, never concatenate trusted absolute paths in the browser. Provide loading, empty, unreadable, invalid, escaped-symlink, mapped, and preview-result states. Use Team4s only for visual principles such as hierarchy, spacing, typography, cards, and state presentation.

## Alternatives Considered

| Category | Recommended | Alternative | Why not |
|---|---|---|---|
| Filesystem abstraction | Focused resolver plus policy service | pyfilesystem2/fsspec | Adds a broad virtual filesystem API, including mutation concepts, without improving the local Linux containment boundary. |
| Root configuration | Stable container path plus SQL identity/capability | Store NAS host path per mapping | Leaks deployment details, prevents portable containers, and violates the relative-mapping requirement. |
| Platform mapping | Dedicated relation | Overload `Platform.fs_slug` | Conflates metadata slug, legacy layout, and user-owned folder name, making migration and audit difficult. |
| Read-only enforcement | App policy plus Docker `:ro` | Docker mount only | Produces late OS errors and leaves behavior dependent on deployment correctness. |
| Audit | Append-only SQL records | Application logs only | Logs are difficult to query, relate, and retain as domain history. |
| Preview | Reuse scanner discovery in a dry-run result type | Scan then roll back DB transaction | Filesystem and job side effects are not reliably undone by a DB rollback. |
| Frontend | Existing Vue v2 stack | React components copied from Team4s | Breaks repository architecture and imports another product's implementation rather than deriving design principles. |
| v1 removal | Delete dual composition and verify shared imports | Leave hidden v1 routes | Retains compatibility code, dependencies, and test surface contrary to the fork contract. |

## Verification Stack

Use layered evidence, with denial and absence-of-side-effect assertions as first-class outcomes:

- Unit/property tests for normalization, POSIX absolute paths, drive paths, UNC paths, traversal encodings, separator variants, long paths, missing nodes, and symlink chains.
- Resolver integration tests using real temporary directories, including symlinks at every component and replacement attempts where practical.
- API tests for admin authorization, path-error sanitization, uniqueness, audit history, and preview non-mutation.
- Scanner/hash/download/stream tests proving reads still work through the resolver.
- Mutation inventory tests proving every prohibited operation is denied before a filesystem mutation function is called.
- Container test with the library bind-mounted read-only and all RomM-owned paths separately writable.
- Before/after filesystem evidence using a recursive manifest of names, types, sizes, content hashes, permissions, and link targets. Account for access-time behavior by recommending `noatime` or `relatime`; do not claim byte immutability proves metadata immutability.
- Migration tests on MariaDB and PostgreSQL, plus local upgrade and downgrade verification.
- Vitest/Storybook for new v2 states, Playwright for mapping and preview workflows, and build/typecheck checks after all v1 imports and named views are removed.

## Installation

No new runtime package is recommended.

```bash
# Existing backend environment
cd backend && uv sync --all-extras --dev

# Existing frontend environment
cd frontend && npm install
```

## Sources

Repository evidence inspected in the canonical `/home/d1sk/romm` checkout:

- `.planning/PROJECT.md`, milestone scope, constraints, and key decisions (HIGH)
- `.planning/codebase/STACK.md`, `ARCHITECTURE.md`, `STRUCTURE.md`, `CONCERNS.md`, `CONVENTIONS.md`, `INTEGRATIONS.md`, and `TESTING.md` (HIGH)
- `CLAUDE.md`, stack, v2-only direction, contract, testing, and contribution rules (HIGH)
- `backend/handler/filesystem/base_handler.py`, current rooted validation plus mutating constructor and write surface (HIGH)
- `backend/handler/filesystem/platforms_handler.py`, fixed-layout inference and directory bootstrap behavior (HIGH)
- `backend/models/platform.py` and `backend/models/rom.py`, current platform and physical-path persistence (HIGH)
- `backend/config/__init__.py` and `backend/config/config_manager.py`, current library root configuration (HIGH)
- `backend/handler/scan_handler.py` and `backend/handler/filesystem/roms_handler.py`, scan and filesystem integration seams (HIGH)
- `frontend/src/RomM.vue`, `frontend/src/plugins/router.ts`, and `frontend/src/v2/router/routes.ts`, UI-version gate and named-view architecture (HIGH)
- `pyproject.toml`, `frontend/package.json`, `docker/Dockerfile`, `docker-compose.yml`, and `env.template`, pinned toolchain and deployment patterns (HIGH)
- `/home/d1sk/team4s`, read-only design-principle reference only, not a technology source or code dependency (HIGH)

## Roadmap Consequence

Order implementation by invariant dependency: schema and immutable root contract, resolver and policy, mapping and audit APIs, read-path integration, preview/browser v2 workflow, legacy-layout bridge, then bounded v1 deletion and end-to-end immutability proof. Do not begin UI mapping work against provisional handwritten types, and do not adapt scanner/download consumers before the resolver and policy contracts are independently tested.
