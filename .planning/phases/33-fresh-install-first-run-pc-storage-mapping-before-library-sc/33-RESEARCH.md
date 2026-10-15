# Phase 33: Fresh-install first-run PC storage mapping before library scan - Research

**Researched:** 2026-10-15
**Domain:** First-run routing, PC storage mappings, library scan gating, and fresh-install UAT
**Confidence:** HIGH for repository behavior and test contracts; MEDIUM for the final UX transition because no Phase 33 context or requirement IDs exist yet

## User Constraints

- Work in the canonical Linux checkout `/home/d1sk/pc-game-download-portal` on `team4s-linux`.
- On a fresh installation, the first-run screen must open the storage/platform mapping workflow instead of the empty-library screen.
- The PC/Windows mapping (`Games/pc`) must be completed before a scan is offered.
- Analyze existing setup, library management, storage roots/mappings, scan routing, backend contracts, and UAT/test patterns.
- Write only the phase research artifact. Do not implement product code.

## Project Constraints (from AGENTS.md and CLAUDE.md)

- The Windows checkout is coordination and reference only. Planning artifacts and tests for this phase run in `/home/d1sk/pc-game-download-portal` through `ssh team4s-linux`. [VERIFIED: AGENTS.md; CLAUDE.md; remote preflight 2026-10-15]
- Preserve unrelated worktree changes. The canonical checkout had pre-existing changes in `.planning/ROADMAP.md` and `.planning/STATE.md`; this research file is additive. [VERIFIED: remote `git status --short` 2026-10-15]
- The active frontend is v2 under `frontend/src/v2/`; v1 is frozen. New behavior belongs in v2 surfaces and must reuse canonical shared stores, services, generated API types, and locale files. [VERIFIED: CLAUDE.md; `.claude/skills/frontend-v2-components/SKILL.md`]
- Backend endpoints remain thin and the backend owns the OpenAPI contract. Schema or route changes require generated frontend types and a frontend typecheck. [VERIFIED: `.claude/skills/backend-development/SKILL.md`; CLAUDE.md]
- New logic needs tests. Code and Markdown are English, and em-dashes are forbidden. [VERIFIED: CLAUDE.md]
- Do not use live Team4s services, NAS data, real credentials, ROMs, media, databases, or existing populated volumes for this fresh-install phase. [VERIFIED: AGENTS.md; Phase 32 context and validation]

## Summary

The current fresh-install path has two separate concepts that do not yet meet. The `/setup` wizard probes the legacy filesystem layout, displays detected platforms, creates the first administrator, and then routes to `home`. It does not register a canonical `StorageRoot` or create a `PlatformStorageMapping`. [VERIFIED: `frontend/src/v2/views/Auth/Setup.vue`; `frontend/src/v2/components/Auth/SetupStepPlatforms.vue`; `backend/endpoints/heartbeat.py`]

After setup, `Home.vue` treats an empty database/library as a normal empty state and offers a direct link to the scan view. The scan socket already rejects a scan when no active mapping commands exist, but this is a late error after the user has been offered scanning. [VERIFIED: `frontend/src/v2/views/Home.vue`; `backend/endpoints/sockets/scan.py`; `backend/tests/endpoints/sockets/test_scan.py`]

The canonical storage workflow already provides the required primitives: administrator-only root listing, legacy bootstrap that registers the protected PC subtree, safe root browsing, mapping test, create/update with optimistic versioning, preview, and audit/removal semantics. The recommended phase boundary is to route the first-run administrator into this existing workflow, ensure the canonical PC/Windows mapping is established for `Games/pc`, and make the scan affordance conditional on that prerequisite. Do not create a second mapping model, path resolver, or scan lifecycle. [VERIFIED: `backend/endpoints/storage.py`; `backend/handler/database/storage_handler.py`; `frontend/src/v2/components/Settings/StorageRootsSection.vue`; `frontend/src/v2/views/Storage/PlatformStorageMapping.vue`]

**Primary recommendation:** Add a first-run prerequisite state around the existing storage-root/mapping contracts, route `/setup` completion to the mapping workflow for the PC/Windows platform, and expose scan only after a valid active PC mapping is observable. Reuse `/storage/legacy/bootstrap`, `/storage/mappings/*`, and existing mapping UI behavior. [VERIFIED: inspected routes, API adapters, and tests]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| First-run prerequisite and redirect | Browser / Client | API / Backend | The router and setup view decide where the administrator lands, while the backend heartbeat/setup state remains authoritative for whether setup is complete. [VERIFIED: `frontend/src/plugins/router.ts`; `frontend/src/v2/views/Auth/Setup.vue`; `backend/endpoints/heartbeat.py`] |
| Storage-root health and safe path resolution | API / Backend | Database / Storage | Backend storage handlers validate absolute roots, reachability, readability, non-writability, symlink safety, and containment. [VERIFIED: `backend/handler/database/storage_handler.py`; `backend/handler/filesystem/storage_resolver.py`; `backend/endpoints/storage.py`] |
| Platform-to-folder mapping persistence | Database / Storage | API / Backend | `PlatformStorageMapping` is persisted by the database handler and exposed through typed storage endpoints. [VERIFIED: `backend/models/storage.py`; `backend/handler/database/storage_handler.py`; `backend/endpoints/responses/storage.py`] |
| PC/Windows identity translation | API / Backend | Browser / Client | Legacy bootstrap maps filesystem `pc` to an existing `win` platform when applicable and can create a platform with Windows identity. [VERIFIED: `backend/endpoints/storage.py`; `backend/utils/platform_slugs.py`] |
| Scan eligibility and command construction | API / Backend | Browser / Client | The socket builds mapping-bound commands and rejects requests with no active mappings; the browser should prevent the premature affordance. [VERIFIED: `backend/endpoints/sockets/scan.py`; `backend/handler/scan_command.py`; `frontend/src/v2/views/Scan.vue`] |
| Empty-library presentation | Browser / Client | API / Backend | `Home.vue` computes the empty state from loaded ROM/platform/collection data and currently links directly to scan. [VERIFIED: `frontend/src/v2/views/Home.vue`] |
| Acceptance evidence | Browser / Client and API / Backend | Deployment | Existing UAT combines focused automated tests, typecheck, Linux service smoke, and browser checks; fresh-install evidence must use disposable state. [VERIFIED: Phase 27 UAT; Phase 29 UAT; Phase 32 validation]

## Standard Stack

### Core

| Library / component | Version | Purpose | Why standard |
|---|---:|---|---|
| FastAPI | Project-managed, documented in repository stack | Setup, storage, platform, and generated OpenAPI endpoints. [VERIFIED: CLAUDE.md; `backend/endpoints/heartbeat.py`; `backend/endpoints/storage.py`] | Existing backend route and contract layer. [VERIFIED: repository architecture] |
| SQLAlchemy 2.0 | 2.0 family | Storage root, platform, mapping, and audit persistence. [VERIFIED: CLAUDE.md; `backend/models/storage.py`; `backend/handler/database/storage_handler.py`] | Existing ORM and transaction boundary. [VERIFIED: repository architecture] |
| Vue | `^3.4.27` | Setup, home, settings, and mapping views. [VERIFIED: `frontend/package.json`] | Existing v2 frontend framework. [VERIFIED: `frontend/package.json`] |
| Vue Router | `^4.3.2` | Setup/home/settings/mapping navigation and route guards. [VERIFIED: `frontend/package.json`; `frontend/src/plugins/router.ts`] | Existing route contract. [VERIFIED: `frontend/src/plugins/router.ts`] |
| Pinia | `^3.0.1` | Auth, heartbeat, platform, and related shared state. [VERIFIED: `frontend/package.json`; inspected v2 adapters/stores] | Existing state layer. [VERIFIED: repository source] |
| Vuetify plus project `R*` wrappers | `^3.9.2` | Existing v2 controls, alerts, cards, forms, and navigation. [VERIFIED: `frontend/package.json`; `.claude/skills/frontend-v2-components/SKILL.md`] | Project constitution requires primitives/wrappers when available. [VERIFIED: `.claude/skills/frontend-v2-components/SKILL.md`] |

### Supporting

| Tool | Version | Purpose | When to use |
|---|---:|---|---|
| Vitest | `^4.1.5` | Focused frontend tests for setup/home/routing/mapping behavior. [VERIFIED: `frontend/package.json`] | Run focused tests and the full frontend suite in `romm-dev`. [VERIFIED: Phase 32 validation; `frontend/package.json`] |
| pytest | Project-managed through `uv` | Backend endpoint, handler, and scan contract tests. [VERIFIED: CLAUDE.md; `.claude/skills/backend-development/SKILL.md`] | Run focused backend tests and collection in the dev container. [VERIFIED: Phase 32 validation] |
| OpenAPI generated TypeScript models | Repository-generated | Keep storage/setup response types aligned with backend schemas. [VERIFIED: CLAUDE.md; `frontend/src/__generated__/`] | Regenerate if the backend contract changes. [VERIFIED: CLAUDE.md] |

**Installation:** None. This phase should reuse the existing lockfiles, frontend packages, backend environment, and project containers. [VERIFIED: `frontend/package.json`; `pyproject.toml`; Phase 32 validation]

**Version verification:** The manifest versions above were inspected in the canonical checkout. Host `node`, `npm`, and `uv` are unavailable, so package and backend gates must use the project container path already established by Phase 32. [VERIFIED: remote runtime probe 2026-10-15; Phase 32 validation]

## Architecture Patterns

### System Architecture Diagram

```text
Fresh install
    |
    v
Router heartbeat: SHOW_SETUP_WIZARD?
    | yes
    v
/setup -> create first admin
    |
    v
First-run mapping prerequisite
    |
    +--> GET /storage/roots --------------------+
    |                                            |
    +--> POST /storage/legacy/bootstrap --------+--> StorageRoot + PC/Windows mapping
    |                                            |
    +--> GET /storage/mappings/platforms/{id}   |
    |                                            |
    +--> browse -> test -> POST /storage/mappings
                                                 |
                                                 v
                                  Active mapping + healthy read-only root
                                                 |
                                                 v
                         Home/library state exposes Scan action
                                                 |
                                                 v
                         Socket scan -> mapping_scan_commands
                                      |
                    no commands -> scan:done_ko and no enqueue
                    valid commands -> mapping-bound scan execution
```

[VERIFIED: `frontend/src/plugins/router.ts`; `frontend/src/v2/views/Auth/Setup.vue`; `frontend/src/v2/components/Settings/StorageRootsSection.vue`; `frontend/src/v2/views/Storage/PlatformStorageMapping.vue`; `backend/endpoints/storage.py`; `backend/endpoints/sockets/scan.py`]

### Recommended Project Structure

```text
frontend/src/v2/views/Auth/Setup.vue                 # first-run orchestration and handoff
frontend/src/v2/views/Home.vue                       # empty-library gating and CTA
frontend/src/v2/views/Settings/LibraryManagement.vue # existing storage/mapping entry
frontend/src/v2/components/Settings/StorageRootsSection.vue
frontend/src/v2/views/Storage/PlatformStorageMapping.vue
frontend/src/services/api/storage.ts                 # typed storage API adapter
backend/endpoints/heartbeat.py                       # setup state and legacy filesystem probe
backend/endpoints/storage.py                         # storage root/mapping contract
backend/handler/database/storage_handler.py          # persistence, locking, versioning
backend/endpoints/sockets/scan.py                    # mapping-bound scan routing
backend/tests/endpoints/test_heartbeat.py
backend/tests/endpoints/test_storage.py
backend/tests/endpoints/sockets/test_scan.py
backend/tests/integration/test_mapped_scan.py
frontend/src/v2/views/Storage/PlatformStorageMapping.test.ts
```

[VERIFIED: repository paths and inspected source files]

### Pattern 1: Treat mapping as a prerequisite, not a scan error

**What:** The browser should determine whether the required PC/Windows mapping is available through the existing storage contract and route to mapping when it is not. The backend remains fail-closed through `mapping_scan_commands` and must continue rejecting unmapped scan requests. [VERIFIED: `backend/endpoints/sockets/scan.py`; `backend/tests/endpoints/sockets/test_scan.py`]

**When to use:** On setup completion and any empty-library entry point where a scan CTA would otherwise be rendered. [VERIFIED: `frontend/src/v2/views/Auth/Setup.vue`; `frontend/src/v2/views/Home.vue`]

**Example:**

```ts
// Use existing route and storage API contracts. Keep mapping identity server-owned.
if (!hasActivePcMapping.value) {
  router.push({
    name: ROUTES.PLATFORM_STORAGE_MAPPING,
    params: { platformId: pcPlatformId.value },
  });
  return;
}
router.push({ name: ROUTES.SCAN });
```

[VERIFIED pattern basis: `frontend/src/v2/views/Storage/PlatformStorageMapping.vue`; `frontend/src/services/api/storage.ts`; `frontend/src/plugins/router.ts`]

### Pattern 2: Use the legacy bootstrap as the bridge to canonical PC storage

**What:** `POST /storage/legacy/bootstrap` registers the protected PC subtree in the canonical mapping model. It resolves filesystem `pc` against `win`/`pc` platform identities and returns the root plus mapping records. [VERIFIED: `backend/endpoints/storage.py`; `frontend/src/services/api/storage.ts`]

Phase 33 resolves this as an explicit mapping-first handoff: authenticated Setup is the only caller of this mutating endpoint, invokes it once, then routes to the existing mapping page. Home, Scan, and recovery checks do not call it. [DECIDED for D-01; Plan 02]

### Pattern 3: Preserve storage safety and optimistic concurrency

**What:** Root registration requires an absolute path and checks reachability, readability, non-writability, and symlink safety. Mapping creation normalizes a relative path, rejects overlap and duplicate platform mappings, and update/removal uses an expected mapping version. [VERIFIED: `backend/handler/database/storage_handler.py`; `backend/handler/filesystem/storage_resolver.py`; `backend/endpoints/responses/storage.py`]

**When to use:** Every first-run mapping action, including the fixed PC path and any later administrator edit. [VERIFIED: `frontend/src/v2/views/Storage/PlatformStorageMapping.vue`; `backend/endpoints/storage.py`]

### Anti-Patterns to Avoid

- **Route setup directly to `/scan`:** It bypasses the storage prerequisite and produces a late socket failure. [VERIFIED: `frontend/src/v2/views/Auth/Setup.vue`; `frontend/src/v2/views/Home.vue`; `backend/endpoints/sockets/scan.py`]
- **Treat `/setup/library` as a mapping contract:** It only reports legacy filesystem structure and counts, not `StorageRoot` or `PlatformStorageMapping` records. [VERIFIED: `backend/endpoints/heartbeat.py`; `frontend/src/services/api/setup.ts`]
- **Use a browser-supplied absolute path:** The storage API accepts a root ID plus safe relative path; backend root registration and resolution own filesystem safety. [VERIFIED: `frontend/src/services/api/storage.ts`; `backend/handler/database/storage_handler.py`]
- **Create a second PC platform identity in the frontend:** Legacy bootstrap already handles `pc` to `win` resolution and platform creation. [VERIFIED: `backend/endpoints/storage.py`]
- **Make the scan CTA merely disabled without a recovery route:** The user must have a direct path to complete mapping and understand why scanning is unavailable. [VERIFIED: `frontend/src/v2/views/Home.vue`; mapping UI behavior in `frontend/src/v2/views/Storage/PlatformStorageMapping.vue`]
- **Use v1 settings or raw Vuetify controls for new v2 behavior:** v1 is frozen and v2 wrappers/primitives are required where available. [VERIFIED: CLAUDE.md; `.claude/skills/frontend-v2-components/SKILL.md`]

## Don't Hand-Roll

| Problem | Do not build | Use instead | Why |
|---|---|---|---|
| Root/path safety | Client-side absolute-path validation or a second resolver | `StorageRoot`, `storage_resolver`, `resolve_directory`, and `/storage/roots/*` | Backend enforces containment, symlink, health, and read-only policy. [VERIFIED: storage handler and resolver] |
| PC/Windows identity mapping | Frontend slug conversion or duplicate platform creation | `POST /storage/legacy/bootstrap` and existing platform lookup rules | Existing backend handles `pc`, `win`, bindings, versions, and platform creation. [VERIFIED: `backend/endpoints/storage.py`] |
| Mapping persistence | Local storage, config-file mutation, or a new table | `PlatformStorageMapping` and `/storage/mappings` endpoints | Existing model supports uniqueness, overlap checks, versions, and audit behavior. [VERIFIED: `backend/models/storage.py`; `backend/handler/database/storage_handler.py`] |
| Scan lifecycle | New first-run scan event or queue path | Existing `mapping_scan_commands`, `execute_mixed_scans`, and socket events | Existing scan routing already freezes mapping identity and fails closed when absent. [VERIFIED: `backend/endpoints/sockets/scan.py`; `backend/handler/scan_command.py`] |
| Empty-state presentation | A parallel first-run page with duplicated library logic | Existing `Home.vue` empty state plus a prerequisite-aware CTA/redirect | Keeps library state and navigation in one home surface. [VERIFIED: `frontend/src/v2/views/Home.vue`] |
| API types | Hand-written frontend response interfaces for changed backend schemas | Generated OpenAPI types and existing adapters | Backend is the source of truth. [VERIFIED: CLAUDE.md; `.claude/skills/backend-development/SKILL.md`]

**Key insight:** The repository already has a security-conscious mapping system and a fail-closed scan boundary. Phase 33 is primarily an orchestration and first-run UX gap, not a storage or scanner implementation gap. [VERIFIED: inspected storage and scan contracts]

## Common Pitfalls

### Pitfall 1: Setup completion still lands on Home before mapping

**What goes wrong:** The new administrator sees the empty-library screen and a scan CTA before the PC mapping exists. [VERIFIED: `Setup.vue` routes to `home` for avatar flow and `login` otherwise; `Home.vue` renders empty CTA]

**Why it happens:** Setup step 1 is a legacy structure/platform probe, not canonical storage setup. [VERIFIED: `Setup.vue`; `setup.ts`; `heartbeat.py`]

**How to avoid:** Make the first-run handoff observe the canonical mapping prerequisite and route directly to the existing platform storage mapping workflow before exposing scan. [VERIFIED: existing route/API contracts]

**Warning signs:** Fresh disposable database has no rows in storage-root/mapping tables, but browser shows Scan as the primary action. [VERIFIED: storage model/API behavior]

### Pitfall 2: `pc` and `win` are treated as unrelated platforms

**What goes wrong:** A mapping is created for a duplicate or wrong platform ID, so the scan command for the actual PC platform remains absent. [VERIFIED: `backend/endpoints/storage.py` platform resolution logic; `scan.py` mapping lookup]

**Why it happens:** Filesystem slug and canonical platform slug are not always identical. [VERIFIED: `backend/utils/platform_slugs.py`; storage bootstrap]

**How to avoid:** Use the bootstrap response and persisted platform ID, then query the active mapping by that ID. Do not infer the ID from a hard-coded frontend slug. [VERIFIED: `frontend/src/services/api/storage.ts`; storage endpoint response]

### Pitfall 3: Mapping the wrong relative level

**What goes wrong:** The mapping points at `Games` or `Games/roms` when the intended PC subtree is `Games/pc`, so preview and scan see the wrong directory. [VERIFIED: user requirement; `StorageRoot` relative-path contract; mapping UI]

**Why it happens:** The storage root and mapping relative path are separate fields, and legacy structure A uses `roms/{platform}` while the requested fresh-install contract names the operator path `Games/pc`. [VERIFIED: user request; `FSPlatformsHandler`; storage schemas]

**How to avoid:** Make the desired root and relative path explicit in the plan and assert the persisted mapping identity/path in backend and UAT checks. [VERIFIED: storage schemas and API]

### Pitfall 4: Scan is hidden but no route completes the prerequisite

**What goes wrong:** The user cannot scan, but is left at an empty page with no mapping CTA or with an admin-only error. [VERIFIED: `StorageRootsSection.vue`; mapping permissions in `storage.py`]

**Why it happens:** Storage roots and mappings require administrator scopes, while the empty-home path is generic. [VERIFIED: storage route decorators; `StorageRootsSection.vue`]

**How to avoid:** Route the first-run administrator directly to the mapping workflow and provide an actionable error/retry path for unhealthy or missing roots. [VERIFIED: `PlatformStorageMapping.vue`; `StorageRootsSection.vue`]

### Pitfall 5: Tests prove only the late backend rejection

**What goes wrong:** The scan socket test passes while the first-run browser still offers the wrong screen. [VERIFIED: existing scan rejection test and absence of setup/home mapping test]

**How to avoid:** Add tests at the routing/setup boundary, the storage prerequisite boundary, and the scan fail-closed boundary, then cover the complete disposable fresh-install path in UAT. [VERIFIED: existing test layout and Phase 32 validation pattern]

## Code Examples

### Existing typed mapping API shape

```ts
const roots = await storageApi.getRoots();
const mapping = await storageApi.getMapping(platformId);
await storageApi.testMapping({
  platform_id: platformId,
  storage_root_id: rootId,
  relative_path: "pc",
});
await storageApi.createMapping({
  platform_id: platformId,
  storage_root_id: rootId,
  relative_path: "pc",
});
```

[VERIFIED pattern: `frontend/src/services/api/storage.ts`; `frontend/src/v2/views/Storage/PlatformStorageMapping.vue`]

### Existing backend scan gate

```python
commands = mapping_scan_commands(
    platform_ids,
    trigger=ScanTrigger.MANUAL,
    scope=ScanScope.ROM if roms_ids else ScanScope.PLATFORM,
    scan_type=scan_type,
    platform_fs_slugs=platform_fs_slugs,
)
if not commands:
    await socket_handler.socket_server.emit(
        "scan:done_ko",
        "No active storage mapping was found for the requested platform selection.",
        to=sid,
    )
    return
```

[VERIFIED pattern: `backend/endpoints/sockets/scan.py`; `backend/tests/endpoints/sockets/test_scan.py`]

### Existing first-run route guard

```ts
if (heartbeat.value.SYSTEM.SHOW_SETUP_WIZARD) {
  return currentRoute !== "setup" ? next({ name: ROUTES.SETUP }) : next();
}
```

[VERIFIED pattern: `frontend/src/plugins/router.ts`]

## State of the Art

| Existing behavior | Required Phase 33 direction | Evidence |
|---|---|---|
| Setup probes legacy structure and then finishes into auth/home. | Setup completion must enter a canonical mapping prerequisite before scan is offered. | [VERIFIED: `Setup.vue`; `heartbeat.py`; user request] |
| Home always uses an empty-library scan CTA when no ROMs/platforms/collections are loaded. | Empty state must be mapping-aware and provide mapping workflow first on fresh install. | [VERIFIED: `Home.vue`] |
| Storage administration is reachable under Library Management and can bootstrap legacy storage. | Reuse it as the first-run workflow or extract only a shared prerequisite decision around it. | [VERIFIED: `LibraryManagement.vue`; `StorageRootsSection.vue`] |
| Scan backend rejects missing mappings at socket execution time. | Retain this defense and add earlier browser routing/visibility. | [VERIFIED: `scan.py`; scan test] |

**Deprecated/outdated:** None identified in the inspected contracts. The legacy filesystem setup probe is still used by the setup wizard, but it is not a substitute for canonical mapping state. [VERIFIED: `heartbeat.py`; `setup.ts`; storage endpoints]

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Frontend framework | Vitest `^4.1.5`, Vue Test Utils, existing project config. [VERIFIED: `frontend/package.json`] |
| Backend framework | pytest through project `uv` environment. [VERIFIED: CLAUDE.md; `.claude/skills/backend-development/SKILL.md`] |
| Frontend quick run | `docker compose run --rm --no-deps romm-dev bash -lc 'cd /app/frontend && npm run test -- <focused-file>'` [VERIFIED: Phase 32 validation container path; package script] |
| Frontend full suite | `docker compose run --rm --no-deps romm-dev bash -lc 'cd /app/frontend && npm run test'` [VERIFIED: Phase 32 validation] |
| Frontend typecheck | `docker compose run --rm --no-deps romm-dev bash -lc 'cd /app/frontend && npm run typecheck'` [VERIFIED: Phase 32 validation] |
| Backend quick run | `docker compose run --rm --no-deps romm-dev bash -lc 'cd /app/backend && uv run pytest <focused-tests>'` [VERIFIED: CLAUDE.md; Phase 32 validation] |
| Backend collection | `docker compose run --rm --no-deps romm-dev bash -lc 'cd /app/backend && uv run pytest tests --collect-only -q'` [VERIFIED: Phase 32 validation] |

### Phase Behavior to Test Map

| Behavior | Test type | Suggested automated evidence | File status |
|---|---|---|---|
| Setup completion routes to mapping prerequisite rather than home/scan on a clean install. | Frontend unit/router | Focused setup/router test exercising `finishWizard` and the mapping prerequisite decision. | New Wave 0 test likely needed. [VERIFIED: no existing setup view test found] |
| Existing setup library probe remains compatible with empty fresh storage. | Backend endpoint | `backend/tests/endpoints/test_heartbeat.py` setup-library tests plus empty-structure handler tests. | Exists. [VERIFIED: listed tests] |
| PC filesystem identity resolves to Windows/canonical platform identity. | Backend endpoint/handler | Extend storage bootstrap tests and assert returned `platform_id`, `platform_fs_slug`, and mapping path. | Existing storage tests exist; exact fresh PC case needs explicit coverage. [VERIFIED: `backend/tests/endpoints/test_storage.py`; storage endpoint] |
| `Games/pc` mapping is tested and persisted only after safety validation. | Backend endpoint/integration | Focused storage endpoint tests for root, relative path, test, create, duplicate, overlap, and unhealthy root. | Existing mapping tests exist; fresh-install path needs composition. [VERIFIED: `backend/tests/endpoints/storage/test_mapping_preview.py`; `backend/tests/endpoints/test_storage.py`] |
| Empty home does not offer scan before the active PC mapping exists. | Frontend unit | Mount Home with empty ROM state and missing mapping; assert mapping CTA/route and no scan CTA. | New Wave 0 test likely needed. [VERIFIED: `Home.vue`; no Home test found in targeted test inventory] |
| Scan remains fail-closed when mapping is absent. | Backend socket unit | `backend/tests/endpoints/sockets/test_scan.py::test_scan_handler_rejects_unmapped_library_without_enqueuing`. | Exists. [VERIFIED: test file] |
| A valid mapping produces mapping-bound scan commands and reaches execution. | Backend integration | `backend/tests/integration/test_mapped_scan.py`, `backend/tests/integration/test_scan_source_immutability.py`, and scan handler tests. | Exists. [VERIFIED: test files] |
| Browser first-run journey reaches mapping, completes it, then offers scan. | Disposable UAT | Fresh empty database/volumes, synthetic operator paths, login, mapping, reload, scan visibility, and no premature scan. | New Phase 33 UAT evidence required. [VERIFIED: Phase 27/29/32 UAT patterns] |

### Sampling Rate

- **Per task commit:** Run the focused frontend or backend test for the changed contract. [VERIFIED: repository test conventions]
- **Per wave merge:** Run focused storage/setup/scan tests, frontend typecheck, and relevant frontend tests in `romm-dev`. [VERIFIED: Phase 32 validation]
- **Phase gate:** Run the full frontend suite, backend collection/focused integration tests, disposable fresh-install UAT, and browser checks before `$gsd-verify-work`. [VERIFIED: Phase 27, 29, and 32 validation/UAT patterns]

### Wave 0 Gaps

- [x] Setup view/router test for clean-install handoff to the PC mapping workflow. [VERIFIED: targeted frontend test inventory]
- [x] Home empty-state test for mapping prerequisite versus scan CTA. [VERIFIED: targeted frontend test inventory]
- [x] Fresh-install backend/storage fixture that asserts `Games/pc`, Windows identity resolution, active mapping persistence, and preview. [VERIFIED: existing storage tests do not expose this complete journey]
- [x] Disposable UAT script or documented command matrix that proves no scan is offered before mapping and that only the intended temporary state is removed. [VERIFIED: Phase 32 validation pattern]

## Security Domain

### Applicable ASVS Categories

| ASVS category | Applies | Standard control |
|---|---|---|
| V2 Authentication | Yes | Preserve the existing setup/admin creation and authenticated storage route guards. [VERIFIED: `heartbeat.py`; `storage.py`] |
| V3 Session Management | Yes | Preserve existing login, CSRF refresh, heartbeat, and router guard flow. [VERIFIED: `Setup.vue`; `router.ts`] |
| V4 Access Control | Yes | Storage roots/mappings require administrator scopes and scan requests require server-side task permission. [VERIFIED: `storage.py`; `scan.py`] |
| V5 Input Validation | Yes | Use Pydantic schemas, normalized relative paths, root containment, overlap checks, and backend error codes. [VERIFIED: `storage.py`; `storage_handler.py`; `responses/storage.py`] |
| V6 Cryptography | Indirect | Do not add new cryptography; preserve existing auth/session secret handling and synthetic-secret-only UAT. [VERIFIED: CLAUDE.md; Phase 32 validation]

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard mitigation |
|---|---|---|
| Path traversal or root escape | Tampering / Elevation | Backend `normalize_relative_path`, `resolve_directory`, approved root IDs, and containment checks. [VERIFIED: storage resolver/handler] |
| Unsafe symlink or writable source | Tampering | Root health and mapping test require read-only, reachable, safe storage. [VERIFIED: storage handler/resolver] |
| Unauthorized mapping or scan | Elevation | Protected routes, admin assertions, scope checks, and server-side socket authorization. [VERIFIED: storage.py; scan.py] |
| Stale concurrent mapping edit | Tampering | Expected mapping version and conflict responses. [VERIFIED: storage schemas/handler] |
| Premature scan affordance | Denial of service / integrity | Browser gates the action on mapping state while backend remains fail-closed. [VERIFIED: Home.vue; scan.py] |

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Linux canonical checkout | All research and writes | Yes | `team4slinux`, `/home/d1sk/pc-game-download-portal` | None. [VERIFIED: preflight 2026-10-15] |
| Docker | Disposable/UAT and project tooling | Yes | 29.6.2 | None. [VERIFIED: remote probe] |
| Node/npm | Frontend test/typecheck | Not on host PATH | None | Use `romm-dev` container, as Phase 32 does. [VERIFIED: remote probe; Phase 32 validation] |
| uv | Backend test tooling | Not on host PATH | None | Use `romm-dev` container. [VERIFIED: remote probe; Phase 32 validation] |
| Host Python | Repository inspection only | Available, 3.10.12 | Below project Python 3.13+ | Use containerized project environment for tests. [VERIFIED: remote probe; CLAUDE.md] |
| MariaDB/Redis test services | Backend integration/UAT | Not independently verified in this research | — | Start only disposable project services under the phase UAT contract; do not use live services. [VERIFIED: AGENTS.md; Phase 32 validation]

**Missing dependencies with no fallback:** None for planning. [VERIFIED: containerized gate path]

**Missing dependencies with fallback:** Host Node/npm/uv/Python version are replaced by the existing `romm-dev` container toolchain. [VERIFIED: Phase 32 validation]

## Resolved Decisions

1. **Bootstrap versus mapping page:** Setup is the only mutating bootstrap path. After authenticated admin creation, `Setup.vue` calls the existing `POST /storage/legacy/bootstrap` exactly once, validates the returned mapping, and navigates to the existing PC/Windows mapping page. Home, Scan, and recovery surfaces never call bootstrap. This preserves an observable mapping workflow while keeping mutation ownership in setup. [DECIDED for D-01, D-03, D-04]

2. **Canonical persisted root/path pair:** The canonical representation is the StorageRoot for configured deployment folder `Games` plus `PlatformStorageMapping.relative_path = "pc"`; its effective target is `Games/pc`. The implementation must reconcile any old bootstrap representation of root `Games/pc` plus empty relative path into this exact pair, without source mutation. Filesystem `pc` resolves to the canonical Windows platform identity returned by the server. [DECIDED for D-02, verified against storage schemas and bootstrap tests]

3. **Readiness authority:** The browser may offer Scan only after a read-only GET-backed check confirms an active mapping, active root, reachable root, readable root, and `non_writable === true`. The backend `mapping_scan_commands` and socket rejection remain authoritative. ROM counts, legacy `/setup/library` discovery, local storage, and optimistic UI state are not readiness authorities. [DECIDED for D-03, D-04]

These decisions are implemented and tested by Plans 01-03, with disposable browser evidence in Plan 04.

## Sources

### Primary, HIGH confidence

- `AGENTS.md`, `CLAUDE.md`, and `.claude/skills/*` in `/home/d1sk/pc-game-download-portal`, project constraints and stack. [VERIFIED: remote inspection 2026-10-15]
- `frontend/src/v2/views/Auth/Setup.vue`, `frontend/src/v2/components/Auth/SetupStepPlatforms.vue`, and `frontend/src/services/api/setup.ts`, first-run behavior and legacy library probe. [VERIFIED: source inspection]
- `frontend/src/v2/views/Home.vue`, empty-library state and current scan CTA. [VERIFIED: source inspection]
- `frontend/src/v2/views/Settings/LibraryManagement.vue`, `frontend/src/v2/components/Settings/StorageRootsSection.vue`, and `frontend/src/v2/views/Storage/PlatformStorageMapping.vue`, existing mapping workflow. [VERIFIED: source inspection]
- `frontend/src/services/api/storage.ts`, typed storage API routes. [VERIFIED: source inspection]
- `frontend/src/plugins/router.ts`, setup guard and mapping/scan routes. [VERIFIED: source inspection]
- `backend/endpoints/heartbeat.py`, setup library contract and setup platform behavior. [VERIFIED: source inspection]
- `backend/endpoints/storage.py`, storage-root/bootstrap/mapping contracts and permissions. [VERIFIED: source inspection]
- `backend/models/storage.py`, `backend/handler/database/storage_handler.py`, and `backend/handler/filesystem/storage_resolver.py`, persistence and safety rules. [VERIFIED: source inspection]
- `backend/endpoints/sockets/scan.py` and `backend/handler/scan_command.py`, mapping-bound scan routing and fail-closed behavior. [VERIFIED: source inspection]
- `backend/tests/endpoints/test_heartbeat.py`, `backend/tests/endpoints/test_storage.py`, `backend/tests/endpoints/sockets/test_scan.py`, `backend/tests/integration/test_mapped_scan.py`, and `frontend/src/v2/views/Storage/PlatformStorageMapping.test.ts`, test patterns. [VERIFIED: source inspection]
- `.planning/phases/27-*/27-UAT.md`, `.planning/phases/29-*/29-UAT.md`, and `.planning/phases/32-*/32-VALIDATION.md`, disposable UAT and containerized gate patterns. [VERIFIED: source inspection]

### Secondary, MEDIUM confidence

- No external web or library documentation was needed for this repository-bound research. Framework and package versions are from the canonical manifest and project instructions, not training-memory claims. [VERIFIED: `frontend/package.json`; CLAUDE.md]

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | [RESOLVED] Setup owns the sole bootstrap mutation; Home/Scan readiness is GET-only. | Resolved Decisions, Plans 01-03 | None remaining within Phase 33 scope. |
| A2 | [RESOLVED] Games is the persisted root and pc is the relative path, producing effective Games/pc. | Resolved Decisions, Plan 01, 33-VALIDATION.md | Deployment config must expose the configured Games folder; UAT fails if the exact pair is not observable. |

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, based on project manifests and repository instructions. [VERIFIED: `frontend/package.json`; CLAUDE.md]
- Architecture: HIGH for current behavior, contracts, and the Phase 33 first-run handoff. [VERIFIED: inspected source; Phase 33 decision set and roadmap requirement PGDP-33-01 are now resolved]
- Pitfalls: HIGH for storage/scan safety and current routing mismatch, MEDIUM for the exact `Games/pc` deployment interpretation. [VERIFIED: source and test inspection]

**Research date:** 2026-10-15
**Valid until:** 2026-11-14, unless storage/setup contracts or Phase 33 context changes sooner.
