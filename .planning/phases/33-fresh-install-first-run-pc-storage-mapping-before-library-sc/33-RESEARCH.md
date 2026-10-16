# Phase 33: Fresh-install PGDP first-run folder discovery and direct platform assignment - Research

**Researched:** 2026-10-16
**Domain:** PGDP first-run setup, direct Games-folder discovery, platform assignment, internal read-only mappings, and pre-scan gating
**Confidence:** HIGH for current repository behavior; MEDIUM for the replacement API contract

<user_constraints>
## User Constraints

- The stack mounts one main Games directory, for example ./Games:/app/romm/library:ro.
- First-run setup inspects direct subfolders inside that mounted Games directory.
- Known folder names are auto-associated with PGDP platforms.
- Unknown folder names are still listed and can be assigned directly to a PGDP platform in the same setup screen.
- The user should not be sent to a separate Storage Administration tab during first-run setup.
- The user should not see RomM branding or roms/{platform} terminology in this PGDP flow.
- The setup screen should explain the concrete action, show folder name, assigned PGDP platform, and inline editing/selection.
- Technical storage mappings may remain internal for safe scan/read authorization, but must not create a second user-facing mapping step.
- Verify the complete fresh install flow in the Linux dev stack and the in-app browser.

### Project execution constraints

- The canonical checkout is /home/d1sk/pc-game-download-portal on team4s-linux; Windows is coordination-only. [VERIFIED: AGENTS.md; CLAUDE.md; remote preflight 2026-10-16]
- Do not edit product code in this research task. Preserve unrelated dirty docker-compose.yml, docker-compose.override.yml, and backend/pgdp_test/ changes. [VERIFIED: remote status 2026-10-16]
- Update this existing research artifact in the verified Linux checkout. [VERIFIED: task scope]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research support |
|---|---|---|
| PGDP-33-01 | Fresh-install PGDP setup discovers direct folders under the mounted Games directory, auto-associates known names, lets the user assign unknown names to PGDP platforms inline, persists safe internal mappings, and exposes scanning only after assignments are server-confirmed ready. | Current setup, filesystem, platform, storage, scan, and validation contracts are mapped below. The previous implementation must be replanned because it routes to a separate mapping page and preserves legacy structure copy. [VERIFIED: .planning/ROADMAP.md; source inspection 2026-10-16] |
</phase_requirements>

## Project Constraints (from AGENTS.md and CLAUDE.md)

- Run all GSD planning, implementation, tests, and commits in the verified Linux checkout, never Windows. [VERIFIED: AGENTS.md; CLAUDE.md]
- New frontend behavior belongs in v2 and must reuse canonical services, generated OpenAPI types, stores, locale files, and R* primitives. v1 is frozen. [VERIFIED: CLAUDE.md; .claude/skills/frontend-v2-components/SKILL.md]
- Backend endpoints stay thin, delegate to handlers, enforce scopes, and remain the OpenAPI source of truth. Route/schema changes require generated frontend types and typecheck. [VERIFIED: .claude/skills/backend-development/SKILL.md]
- New logic needs tests. New user-visible strings belong in all 18 locales and must pass both locale validators. [VERIFIED: CLAUDE.md; .claude/skills/frontend-i18n/SKILL.md]
- Do not use RomM branding or legacy roms/{platform} wording in the replacement first-run surface. [VERIFIED: task constraints; current SetupStepPlatforms.vue]
- Do not add filesystem mutation. The external root is mounted read-only and the storage policy remains authoritative for safe list/read/scan access. [VERIFIED: docker-compose.yml; storage policy implementation]

## Summary

The previous Phase 33 implementation is not the requested product flow. Setup.vue currently creates the administrator, logs in, calls POST /storage/legacy/bootstrap, and navigates to platform-storage-mapping, exposing the separate storage-mapping screen. [VERIFIED: frontend/src/v2/views/Auth/Setup.vue:131-177; frontend/src/services/api/storage.ts:40-46; frontend/src/plugins/router.ts:168-176] SetupStepPlatforms.vue only renders a legacy detected-structure summary and displays either roms/{platform} or {platform}/roms. [VERIFIED: frontend/src/v2/components/Auth/SetupStepPlatforms.vue:1-89] Prior verification records that all browser scenarios failed before Chromium launch and the roadmap remains incomplete. [VERIFIED: 33-VERIFICATION.md; 33-UAT.md]

The target is one setup-owned folder assignment surface. It lists direct children of the mounted Games root, shows a server-provided known association where safe, leaves unknown folders visible with an inline PGDP platform selector, and submits choices as part of setup. The browser never sends a host path or invents a platform ID. [ASSUMED: recommended contract derived from task constraints and existing storage boundary]

Keep StorageRoot and PlatformStorageMapping as internal authorization state, but compose them behind setup. Reuse the existing storage handler, resolver, health checks, mapping lifecycle, and scan readiness predicate. Do not route setup to PLATFORM_STORAGE_MAPPING, expose Storage Administration copy, call the legacy structure detector as truth, or create a second user-facing mapping step. [VERIFIED: backend/endpoints/storage.py; backend/handler/database/storage_handler.py; frontend/src/services/api/storage.ts; task constraints]

**Primary recommendation:** Replace the legacy setup platform summary with a setup-specific direct-folder discovery and assignment contract, save assignments after the new administrator is authenticated through one server-owned setup operation, then route to Home only when the server confirms the selected mappings are active and healthy. [ASSUMED: recommended architecture]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Direct child discovery | API / Backend | Browser / Client | Backend lists the mounted root through storage policy and rejects unsafe paths; browser renders returned entries. [VERIFIED: storage policy/resolver; backend/endpoints/storage.py:923-987] |
| Known-folder association | API / Backend | Browser / Client | Platform aliases, bindings, canonical slugs, and database identity are server-owned. [VERIFIED: backend/utils/platforms.py; backend/utils/platform_slugs.py; config manager] |
| Unknown-folder selection | Browser / Client | API / Backend | Browser owns draft editing; server validates the selected platform and folder again before persistence. [ASSUMED: v2 form split] |
| Assignment persistence | API / Backend | Database / Storage | Compose existing root/mapping persistence through handlers and one setup boundary. [VERIFIED: storage handler; ASSUMED: one setup composition operation] |
| First-run sequencing | Browser / Client | API / Backend | Setup owns wizard state/navigation; backend authorizes and confirms saved readiness. [VERIFIED: Setup.vue; heartbeat; router] |
| Scan eligibility | API / Backend | Browser / Client | Scan already fails closed without mappings; Home/Scan need the same read-only readiness UX gate. [VERIFIED: scan socket; Home; Scan; storage.ts] |
| Acceptance evidence | Linux dev stack and in-app browser | API / Backend | The task requires the complete disposable flow and prior UAT never reached browser assertions. [VERIFIED: task; 33-UAT.md] |

## Current-State Findings and Re-plan Implications

| Finding | Evidence | Consequence |
|---|---|---|
| Compose mounts ./Games directly to /app/romm/library:ro. | [VERIFIED: docker-compose.yml:29] | Treat /app/romm/library as Games. Never append ROMS_FOLDER_NAME or require a roms child. |
| There is no backend/endpoints/setup.py; /setup/library is in heartbeat.py. | [VERIFIED: file check; backend/endpoints/heartbeat.py:194-305] | Plan changes in the actual route or extract a focused setup handler without inventing a nonexistent module. |
| /setup/library uses legacy structure detection; get_platforms() can attempt to create a default roms directory when structure detection fails. | [VERIFIED: heartbeat.py; platforms_handler.py:112-141] | Do not use it for PGDP direct-folder discovery. Use a read-only direct-child listing path. |
| SetupStepPlatforms.vue is a legacy summary, not an assignment editor. | [VERIFIED: SetupStepPlatforms.vue:40-89] | Replace it with rows showing folder name, PGDP assignment, and inline edit/select state. |
| bootstrapLegacy persists one pc mapping and routes to mapping administration. | [VERIFIED: storage.py:750-933; Setup.vue:165-177] | Replace/narrow the visible setup composition; keep low-level storage handlers. |
| Generic mapping create requires a positive database platform ID; supported unmatched entries can have id -1. | [VERIFIED: storage schemas; platform.py; utils/platforms.py] | Submit platform slugs/server identities and resolve/create a real platform before mapping. Never submit -1. |
| Root browse uses root ID plus safe relative parent; mapping APIs use root ID plus relative path. | [VERIFIED: storage.ts:76-105; storage.py:923-1035] | Reuse safety internally; return no host paths to the browser. |
| Readiness requires active mapping/root, reachable, readable, and non_writable === true. | [VERIFIED: storage.ts:50-73] | Use this rule for setup completion and Home/Scan. Define multi-row semantics explicitly. |
| Prior browser UAT failed because the runner lacked libglib-2.0.so.0; host probing now reports Docker and libglib available. | [VERIFIED: 33-UAT.md; remote probe 2026-10-16] | Add browser-runner preflight and use the requested in-app browser for final evidence. |

## Proposed Setup Contract

The following is a recommended composition over existing storage primitives, not a new storage model. [ASSUMED: recommendation]

### Discovery response

Use a setup read response equivalent to:

~~~ts
type SetupFolderDiscovery = {
  root_label: "Games";
  folders: Array<{
    name: string;
    relative_path: string;
    association: "known" | "unknown";
    suggested_platform: { slug: string; display_name: string } | null;
  }>;
  platform_options: Array<{ slug: string; display_name: string }>;
};
~~~

Exact schema names remain a planning decision, but the response must be server-owned, bounded, direct-child-only, and free of host paths and RomM/roms terminology. [ASSUMED: response shape]

Discovery should enumerate only direct directories below LIBRARY_BASE_PATH, through the existing safe list policy, with no writes. It should reject unsafe symlinks and return relative names such as pc only as internal data. [VERIFIED: resolver/storage routes; ASSUMED: hidden-entry policy requires explicit tests]

Known matching should be deterministic and server-side: exact canonical filesystem slug first, then configured binding/version aliases, then a safe supported-platform match. Ambiguous or unrecognized names remain unknown; do not infer from contents or ROM counts. [VERIFIED: platform/config utilities; ASSUMED: precedence]

### Assignment submission

After admin creation and authentication, submit draft assignments from the same Setup view through one protected setup operation. The server re-lists direct children, validates each as an existing direct directory below Games, resolves each selected PGDP platform, creates/reuses its database identity without source mutation, and creates/reconciles internal root/mappings through db_storage_handler. [ASSUMED: recommended composition; existing handler operations verified]

Preferred shape: a setup-specific POST /setup/folders/assign accepting {folder_name, platform_slug} rows and returning persisted assignments plus readiness. This keeps the multi-row first-run operation atomic and prevents the browser needing a mapping screen. [ASSUMED: recommendation] A fallback is sequential generic mapping calls, but that risks partial persistence and spreads first-run orchestration across administration APIs. [ASSUMED: tradeoff]

The save must be idempotent, reject duplicate platform assignments and unsafe overlaps, and return server IDs/health. It must not accept absolute paths, a client-supplied root outside the deployment-owned path, or placeholder platform IDs. [VERIFIED: existing storage rules; ASSUMED: multi-row contract]

### First-run state machine

~~~text
Fresh empty DB + Games:/app/romm/library:ro
  -> GET setup direct-folder discovery
  -> known folders preselected; unknown folders visible with inline selector
  -> user reviews/edits rows on Setup
  -> create admin -> login -> CSRF/current-user/heartbeat refresh
  -> POST setup assignment composition
       -> validation failure: remain on Setup, preserve draft, retry
       -> valid mappings: GET readiness for selected platforms
            -> not ready: actionable Setup error
            -> ready: Home may expose Scan
~~~

Setup is the only first-run assignment surface. Home and Scan may offer later recovery, but must not call setup mutation or route the fresh user through Storage Administration. [ASSUMED: navigation rule]

## Standard Stack

| Component | Version | Purpose | Source |
|---|---:|---|---|
| FastAPI | Project-managed | Setup/platform HTTP contracts | [VERIFIED: CLAUDE.md; heartbeat/platform endpoints] |
| SQLAlchemy | 2.0 family | Platform/root/mapping persistence | [VERIFIED: CLAUDE.md; storage models/handler] |
| Vue | ^3.4.27 | Setup surface | [VERIFIED: frontend/package.json] |
| Vue Router | ^4.3.2 | Setup/Home navigation | [VERIFIED: frontend/package.json; router] |
| Pinia | ^3.0.1 | Auth/heartbeat/platform state | [VERIFIED: frontend/package.json; platform store] |
| Vuetify and project R* wrappers | ^3.9.2 | Accessible controls/layout | [VERIFIED: frontend/package.json; v2 component skill] |
| Vitest | ^4.1.5 | Frontend contracts | [VERIFIED: frontend/package.json] |
| pytest/uv | Project-managed | Backend contracts | [VERIFIED: CLAUDE.md; backend skill] |
| Playwright plus in-app browser | Project-managed/requested | Disposable fresh-install UAT | [VERIFIED: playwright config; task constraints] |

**Installation:** Reuse lockfiles and Compose services. Do not add a second mapping library or filesystem abstraction. [VERIFIED: manifests; existing storage implementation]

## Architecture Patterns

### Pattern 1: Server-owned direct-folder discovery

List direct folders with the existing storage policy/resolver and return server-derived association suggestions. Do not call FSPlatformsHandler.get_platforms(), because it can bootstrap a legacy directory. [VERIFIED: platforms_handler.py; storage policy; ASSUMED: setup response]

### Pattern 2: Setup-owned inline assignment table

Each row displays the concrete folder name and PGDP platform. Known rows are preselected; unknown rows require an inline v2 select; edits remain draft state until submit. [ASSUMED: UX recommendation] Keep async state in Setup.vue or a setup composable and keep row rendering presentational. [VERIFIED: current orchestrator pattern; component skill]

~~~ts
type FolderAssignmentDraft = {
  folderName: string;
  platformSlug: string | null;
  association: "known" | "unknown";
};
const canSubmit = computed(() =>
  assignments.value.every((row) => row.platformSlug !== null),
);
~~~

The draft is not authorization. Backend revalidates direct-child containment, platform identity, duplicates, overlap, root health, and read-only status. [VERIFIED: storage boundary; ASSUMED: draft shape]

### Pattern 3: Internal mapping persistence behind setup

Compose existing root/mapping persistence after login and CSRF refresh, then return readiness. Do not navigate to platform-storage-mapping during first run. [VERIFIED: current auth sequence; task constraints; ASSUMED: composition]

### Pattern 4: One readiness predicate

Home, direct Scan, and setup completion use active mapping/root, reachable, readable, and non_writable === true. [VERIFIED: frontend/src/services/api/storage.ts:50-73] Extend deliberately if multiple assignments are required. [ASSUMED: multi-row rule]

### Anti-Patterns

- Route setup to Storage Administration. [VERIFIED: current Setup; task constraints]
- Render roms/{platform} or RomM branding. [VERIFIED: current component; task constraints]
- Use legacy structure detection for direct Games truth. [VERIFIED: heartbeat; platforms handler]
- Let browser create platform IDs or send absolute paths. [VERIFIED: platform/storage schemas]
- Save rows through a hidden admin screen, creating partial failure and violating the same-screen requirement. [ASSUMED: UX risk]
- Disable Scan without an actionable recovery path. [VERIFIED: frontend patterns; current Home/Scan gating]

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Root containment/symlink safety | Client checks or second resolver | Existing storage resolver/policy | Server owns root authority and bounded errors. [VERIFIED: resolver/policy] |
| Mapping lifecycle | Setup table/localStorage mappings | Existing root/mapping models and handler | Existing duplicate, overlap, audit, and version semantics. [VERIFIED: storage model/handler/routes] |
| Platform matching | Frontend alias table/ID map | Server platform catalog, config bindings, slug utilities | Metadata/aliases are server-owned. [VERIFIED: platform utilities/config] |
| Scan authorization | Setup boolean or ROM count | Mapping-bound scan commands plus readiness | Backend remains fail-closed. [VERIFIED: scan socket/handler; storage API] |
| Form validation | Zod/Yup/raw v-form | RForm and native rules | Required by v2 patterns. [VERIFIED: frontend patterns] |

**Key insight:** The user-facing concept is a folder assignment; the safe implementation concept is a mapping. Expose the former and keep the latter behind one setup boundary. [ASSUMED: architecture conclusion]

## Common Pitfalls

### Pitfall 1: Legacy structure leakage

**What goes wrong:** Direct Games is interpreted as roms/{platform} or {platform}/roms. [VERIFIED: current component/heartbeat]
**Why:** Compatibility code still uses ROMS_FOLDER_NAME and structure detection. [VERIFIED: platforms handler]
**Avoid:** Direct-child discovery and fixtures with no roms child. [ASSUMED: test recommendation]
**Warning signs:** roms/, RomM, or mkdir appears in the PGDP setup path. [VERIFIED: current source/policy]

### Pitfall 2: Placeholder IDs leak

Supported unmatched platforms can have id -1, while mapping schemas require positive IDs. [VERIFIED: utils/platforms.py; storage schemas] Resolve/create server-side from stable slugs. [ASSUMED: contract]

### Pitfall 3: Unknown folders disappear or are guessed

Return every safe direct folder, mark uncertain names unknown, require explicit selection, and never silently omit or fuzzy-assign. [ASSUMED: product safety recommendation]

### Pitfall 4: Partial save/retry duplicates

Prefer one idempotent composition operation, existing conflict/overlap checks, and preserved draft on failure. [VERIFIED: existing mapping conflicts; ASSUMED: composition]

### Pitfall 5: One mapping gates multiple rows

The current code checks only Windows. Decide whether all submitted assignments or only PC gates initial Scan, then use one rule everywhere. [VERIFIED: Home/Scan/storage API; NEEDS DECISION]

### Pitfall 6: Source-level tests substitute for browser proof

Prior UAT failed before Chromium assertions. Add a runner preflight, disposable Linux stack, and in-app-browser evidence before completion. [VERIFIED: 33-UAT.md; 33-VERIFICATION.md; task]

## Runtime State Inventory

| Category | Items found | Action required |
|---|---|---|
| Stored data | Existing platform, root, mapping, and audit records are internal state. [VERIFIED: storage models/handler] | No source migration; fresh disposable DB must prove intended records and idempotent retry. [ASSUMED: test action] |
| Live service config | Not accessed; Compose defines disposable services and has unrelated dirty changes. [VERIFIED: AGENTS; git status] | Do not touch live services or unrelated Compose edits. |
| OS-registered state | None relevant to this code-only setup flow found. [ASSUMED: scope inspection] | None. |
| Secrets/env vars | Library base path, database, and auth/CSRF inputs are deployment configuration. [VERIFIED: backend config/Compose] | Keep host paths/credentials out of browser payloads/evidence. |
| Build artifacts/packages | Dependencies are container-mounted; host node/npm/uv unavailable. [VERIFIED: remote probe] | Run gates through Compose and in-app browser. |

## Code Examples

~~~ts
// Recommended browser payload: stable names, not root paths or database IDs.
type SetupAssignmentRequest = {
  folder_name: string;
  platform_slug: string;
};
~~~

The server must revalidate both fields against the mounted root and supported catalog. [ASSUMED: request contract]

~~~ts
const ready = Boolean(
  mapping.active &&
  root?.active &&
  root.health.reachable &&
  root.health.readable &&
  root.health.non_writable === true,
);
~~~

This is the existing readiness implementation to reuse. [VERIFIED: frontend/src/services/api/storage.ts:50-73]

## State of the Art

| Old approach | Recommended approach | Impact |
|---|---|---|
| Legacy structure summary and roms/{platform} copy. [VERIFIED: current UI] | Direct Games folder rows with PGDP assignment. [ASSUMED: re-plan] | Makes unknown folders actionable and removes wrong terminology. |
| One PC bootstrap followed by Storage Administration. [VERIFIED: current Setup] | Setup owns discovery, inline assignment, save, and completion. [ASSUMED: re-plan] | Removes the second first-run step. |
| One known mapping readiness gate. [VERIFIED: current Home/Scan] | Same predicate over the selected assignment set. [ASSUMED: multi-row extension] | Prevents premature scan exposure. |

**Deprecated/outdated for this flow:** detected_structure/structure copy in PGDP setup, visible legacy bootstrap handoff, and platform-storage-mapping as first-run destination. Compatibility consumers and later administration may retain their contracts. [VERIFIED: current code; ASSUMED: scope]

## Open Questions

1. **Must every discovered folder be assigned, or can the user skip one? (RESOLVED)** Every direct child returned by discovery is a required assignment row. The client must not silently omit or skip a row; the assignment endpoint rejects incomplete submissions, so both the known pc row and the unknown My Games row are explicitly assigned before setup can continue. [RESOLVED: locked phase contract in 33-02/33-04]
2. **Does initial readiness require every assigned mapping or only PC? (RESOLVED)** Initial readiness requires every submitted assignment and the shared root to be active, reachable, readable, and non-writable. Home/Scan remains unavailable until the all-mapping predicate passes, including after reload. [RESOLVED: locked phase contract in 33-02/33-08]
3. **Atomic setup endpoint or sequential generic mapping calls? (RESOLVED)** Use the setup composition endpoint POST /api/setup/folders/assign as the single atomic/idempotent reconciliation boundary. It re-lists and validates all rows server-side, persists the complete assignment set, and returns mapping identities and readiness; the browser does not sequence generic mapping mutations. [RESOLVED: locked phase contract in 33-02/33-04]
4. **Exact alias table? (RESOLVED)** Platform association is server-owned and deterministic: canonical PGDP slug first, then configured binding/version alias, then one unambiguous supported match. Ambiguous or unsupported names remain unknown and require explicit platform selection; no client alias table is permitted. [RESOLVED: locked phase contract in 33-02/33-04]

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---:|---|---|
| Linux canonical checkout | All GSD work | Yes | team4s-linux; Linux confirmed 2026-10-16 | None; Windows forbidden. [VERIFIED: preflight] |
| Docker | Disposable dev stack | Yes | 29.6.2 | None. [VERIFIED: remote docker] |
| Node/npm | Direct frontend commands | No | - | Compose dev container. [VERIFIED: remote probe] |
| uv | Direct backend commands | No | - | Compose dev container. [VERIFIED: remote probe] |
| Trunk | Lint/format | No | - | Container if available; otherwise explicit blocker. [VERIFIED: prior UAT/remote probe] |
| Python | Inspection only | Yes | 3.10.12 | Not substitute for project Python 3.13+. [VERIFIED: remote probe; CLAUDE] |
| Browser libraries | UAT | Host libglib present; prior one-shot runner failed | libglib-2.0.so.0 host present | In-app browser plus launch preflight. [VERIFIED: remote ldconfig; prior UAT; task] |

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Frontend | Vitest ^4.1.5 and Playwright. [VERIFIED: package/config] |
| Backend | pytest via project uv environment. [VERIFIED: CLAUDE; pyproject] |
| Config | frontend/vitest.config.ts, frontend/playwright.config.ts, backend pytest configuration. [VERIFIED: repository files] |
| Quick frontend | Compose dev service, focused Vitest path. [VERIFIED: existing phase commands/Compose] |
| Quick backend | Compose dev service, focused pytest path. [VERIFIED: existing phase commands/Compose] |
| Full gate | typecheck, frontend tests/build, backend focused/integration tests, Trunk, disposable UAT, in-app browser. [VERIFIED: pre-pr skill; phase validation] |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test type | Automated coverage |
|---|---|---|---|
| PGDP-33-01 | Direct child discovery lists known/unknown folders with no source mutation or roms creation. | Backend | Extend setup/heartbeat and storage tests; add source immutability fixture. [VERIFIED: existing locations; ASSUMED: new cases] |
| PGDP-33-01 | Known rows preselect; unknown rows remain visible and inline-selectable; copy has folder and PGDP platform, no RomM/legacy path. | Frontend | Add SetupStepPlatforms component tests and update Setup.test.ts. [VERIFIED: current files; ASSUMED: new tests] |
| PGDP-33-01 | Save uses server-owned slugs/IDs, retries preserve draft, and no Storage Administration route occurs. | Frontend/backend | Focused setup tests and endpoint tests. [VERIFIED: current patterns; ASSUMED: new cases] |
| PGDP-33-01 | Persist/reconcile internal mappings, reject unsafe/duplicate/overlap, and return health/readiness. | Backend integration | Run against reachable disposable DB, not host-loopback-only fixture. [VERIFIED: prior backend blocker; ASSUMED: new contract] |
| PGDP-33-01 | Home/Scan stay unavailable until readiness. | Unit + browser | Existing storage/Home/Scan tests plus browser assertion. [VERIFIED: existing test files] |
| PGDP-33-01 | Complete fresh install works in Linux dev stack/in-app browser after reload, both themes, responsive layouts, and mouse/touch/keyboard/gamepad. | Disposable UAT | Extend Phase 33 matrix; prior run failed before Chromium. [VERIFIED: phase artifacts; task] |

### Sampling Rate

- Per task: focused Vitest or pytest for the changed contract. [ASSUMED: recommendation]
- Per wave: typecheck plus focused backend/API collection and generated OpenAPI check. [VERIFIED: project skill]
- Phase gate: full relevant gates, disposable Linux UAT, and in-app browser evidence before verification. [VERIFIED: task; pre-pr skill]

### Wave 0 Gaps

- Define/test direct-folder discovery and safe direct-child listing. [ASSUMED: gap]
- Define/test assignment request/response, transaction, idempotence, and platform resolution. [ASSUMED: gap]
- Replace summary test with inline assignment coverage. [VERIFIED: current component; ASSUMED: gap]
- Add known/unknown/empty/nested/hidden/symlink synthetic fixtures and source immutability assertions. [ASSUMED: gap]
- Repair/prove browser prerequisites and execute requested in-app browser path. [VERIFIED: prior UAT; task]

## Security Domain

| ASVS area | Applies | Control |
|---|---:|---|
| V2 Authentication | Yes | Preserve admin creation, login, CSRF, and protected assignment sequence. [VERIFIED: Setup/auth decorators] |
| V3 Session | Yes | Refresh session/current user before assignment mutation. [VERIFIED: Setup] |
| V4 Access Control | Yes | Admin/users-write for assignment; if discovery is public, allow only no-admin setup state. [VERIFIED: protected routes; ASSUMED: final scope] |
| V5 Input Validation | Yes | Direct-child validation; reject traversal/absolute/UNC/drive paths and symlink escape; validate platform slug; reject duplicates/overlap. [VERIFIED: resolver/schemas; ASSUMED: payload] |
| V6 Cryptography | No new crypto | Reuse existing session/CSRF/audit; no custom token/hash. [ASSUMED: no new crypto] |

| Threat | STRIDE | Mitigation |
|---|---|---|
| Traversal/absolute injection | Tampering/Elevation | Server validates names/slugs and resolves safe relative paths. [VERIFIED: storage resolver] |
| Symlink escape | Tampering/Disclosure | Reject unsafe symlinks and prove containment. [VERIFIED: resolver] |
| Writable/unhealthy root | Tampering | Require active, reachable, readable, non-writable health. [VERIFIED: storage API] |
| Wrong unknown-folder guess | Integrity | Unknown remains explicit and requires selection. [ASSUMED: safety] |
| Partial multi-row save | Integrity/DoS | Prefer atomic idempotent composition and preserve drafts on failure. [ASSUMED: recommendation] |

## Sources

### Primary (HIGH confidence)

- AGENTS.md and CLAUDE.md - execution boundary, canonical checkout, stack, and project rules.
- .planning/ROADMAP.md, 33-UAT.md, 33-VERIFICATION.md, 33-VALIDATION.md - current goal, incomplete prior phase, and browser failure.
- docker-compose.yml - direct Games read-only mount.
- frontend/src/v2/views/Auth/Setup.vue, SetupStepPlatforms.vue, services/api/setup.ts, services/api/storage.ts - current frontend contracts.
- backend/endpoints/heartbeat.py, storage.py, endpoints/responses/storage.py - actual setup and mapping contracts.
- backend/handler/filesystem/platforms_handler.py, storage_resolver.py, storage_policy.py - filesystem behavior and safety.
- backend/utils/platforms.py, platform_slugs.py, config manager - platform catalog/alias behavior.
- backend/endpoints/sockets/scan.py, frontend/src/v2/views/Home.vue, Scan.vue - scan readiness.
- Project skill files for v2 components/patterns/i18n/backend/pre-verification conventions. [VERIFIED: skill files]

### Secondary (MEDIUM confidence)

- None required. This is codebase/product-contract research; no new library documentation was needed. [VERIFIED: scope]

### Tertiary (LOW confidence)

- None.

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | Setup-specific composition endpoint is preferable to sequential generic mapping calls. | Medium: endpoint scope/transaction planning. |
| A2 | Setup submits stable platform slugs; server creates/reuses positive database IDs. | High: wrong identity contract can duplicate/fail mappings. |
| A3 | Every non-hidden folder requires assignment unless explicit Skip state is added. | Medium: completion UX. |
| A4 | Initial readiness requires all submitted assignments. | Medium: Home/Scan semantics. |
| A5 | Matching precedence is exact canonical slug, configured alias, then safe supported match; ambiguous remains unknown. | High: wrong precedence can misassociate folders. |
| A6 | Hidden/system filtering follows a bounded helper and is locked by tests. | Medium: visible folder set. |
| A7 | No OS registration/live service config belongs to this phase. | Low: scope expansion. |
| A8 | In-app browser can provide final evidence after preflight. | High: prior browser failure. |

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, repository manifests and skills verify it.
- Current architecture: HIGH, setup/storage/platform/scan paths were inspected in the canonical Linux checkout.
- Replacement architecture: MEDIUM, the single-screen contract follows explicit constraints but requires decisions A1-A6.
- Validation: MEDIUM, test locations/failures are verified but browser execution is deferred to implementation/UAT.

**Research date:** 2026-10-16
**Valid until:** 2026-10-23 for browser/runtime availability; 2026-11-15 for stable repository architecture.

## RESEARCH COMPLETE
