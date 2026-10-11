# Phase 17: Browser Download Manager - Research

**Researched:** 2026-09-17
**Domain:** Browser-only, manifest-bound PC download manager
**Confidence:** MEDIUM

## User Constraints

### Locked Scope

- Replace the desktop-client handoff with a browser-only workflow. [VERIFIED: task brief]
- Reuse the immutable selected-component manifest from Phase 14 and direct single-file transfer contract from Phase 15. [CITED: .planning/phases/14-immutable-download-manifests/14-VERIFICATION.md] [CITED: .planning/phases/15-direct-resumable-transfer/15-03-SUMMARY.md]
- Support whole-game and explicit component selection, including explicit required archive sets, without guessing dependencies from the source tree. [VERIFIED: task brief]
- Add server-side transfer-session and history semantics, bounded queue concurrency, a standard browser-download baseline, and an optional File System Access enhancement. [VERIFIED: task brief]
- Do not mutate NAS/source paths, expose source paths, create ZIPs, split archives, extract archives, or retain the desktop handoff as a required workflow. [CITED: CLAUDE.md] [CITED: docs/superpowers/specs/2026-09-15-cross-platform-pc-downloader-design.md]

### Planner Decision Required

- Define the authoritative rule for a custom archive set. The current data model has component kinds but no dependency or required-set relation, and Phase 14 accepts any non-empty subset of eligible base, update, DLC, and extra components. The planner must add an explicit persisted/archive-profile rule or a product-level acknowledgement rule. It must not infer installer dependencies from directories or filenames. [CITED: backend/handler/database/download_manifests_handler.py] [CITED: backend/models/rom.py]

## Phase Requirements

| ID      | Description                                                                                                                            | Research Support                                                                                                                                                                                                                                                  |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UXDL-01 | v2 securely hands a whole-game or selected-component download to the installed desktop client.                                         | This phase changes the consumer to the browser manager while preserving the selected-manifest contract. [CITED: .planning/REQUIREMENTS.md]                                                                                                                        |
| SAFE-01 | Manifest preparation and every transfer leave the NAS and source library read-only and unchanged.                                      | Existing descriptor-backed manifest transfer is reused, with session/history records stored only in RomM's database. [CITED: backend/endpoints/download_manifests.py] [CITED: backend/handler/filesystem/roms_handler.py]                                         |
| TEST-01 | Automated coverage proves resume, source changes, bad checksums, disk-full recovery, 4 GiB-plus values, and Windows/Linux path safety. | Browser tests add manager semantics, while established Phase 15/16 suites remain the authoritative direct-transfer and cross-platform-path evidence. [CITED: .planning/REQUIREMENTS.md] [CITED: .planning/phases/16-cross-platform-desktop-client/16-PATTERNS.md] |

## Summary

Phase 17 should add a v2 browser manager above the existing Phase 14/15 contract, not another file-serving implementation. The existing POST creates an owner-scoped immutable manifest from `null` for the whole eligible game or a non-empty exact component list. Its member URLs contain only opaque IDs, safe destinations, `BigInteger` sizes, SHA-256, and quoted strong snapshots. The direct endpoint authorizes every member request, performs fresh hash verification before streaming, and permits only strict single-range resumption with the exact `If-Match` snapshot. [CITED: backend/endpoints/download_manifests.py] [CITED: backend/endpoints/responses/download_manifest.py] [CITED: backend/handler/filesystem/roms_handler.py]

Use two explicitly different browser modes. The baseline invokes normal same-origin attachment downloads one original member at a time and records `HANDED_TO_BROWSER`, not a proven completion. Browser-native resume cannot be relied upon because an automatic `Range` request cannot be made to include the contract's exact `If-Match` value, and the server deliberately rejects any range without it. [CITED: backend/endpoints/download_manifests.py] The optional File System Access mode uses a user-selected writable directory, `fetch()` streaming, exact Range/If-Match resume, and a streamed SHA-256 verifier. It is progressive enhancement only because `showDirectoryPicker()` is secure-context, user-activation gated, and not Baseline across major browsers. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker] [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch]

**Primary recommendation:** Build a manifest-backed browser queue with database sessions as an auditable, non-authoritative journal, native browser download as the universal handoff, and File System Access plus streaming SHA-256 verification as the opt-in resumable mode.

## Architectural Responsibility Map

| Capability                                  | Primary Tier     | Secondary Tier     | Rationale                                                                                                                                                                                                             |
| ------------------------------------------- | ---------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Component/archive-set selection             | API / Backend    | Browser / Client   | The server must validate selected IDs and any required-set policy before creating one immutable manifest. [CITED: backend/handler/database/download_manifests_handler.py]                                             |
| Immutable manifest and source authorization | API / Backend    | Database / Storage | Existing ownership, visibility, lifecycle, snapshot, and descriptor checks remain server authority. [CITED: backend/endpoints/download_manifests.py]                                                                  |
| Transfer session and append-only history    | API / Backend    | Database / Storage | Durable records must be owner-scoped and path-free; browser-reported progress is observational only. [ASSUMED]                                                                                                        |
| Queue, progress UI, pause/cancel            | Browser / Client | API / Backend      | The browser owns active fetches and UI state; API receives bounded journal events only. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch]                                               |
| Standard file delivery                      | Browser / Client | API / Backend      | Normal attachment navigation is the compatible fallback; its completion cannot be cryptographically established in page JavaScript. [ASSUMED]                                                                         |
| Resumable writing and final SHA-256         | Browser / Client | API / Backend      | The enhanced mode controls Range/If-Match and writes only below a user-approved directory. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/File_System_API] [CITED: backend/endpoints/download_manifests.py] |

## Standard Stack

### Core

| Library / API                                      |                       Version | Purpose                                                          | Why Standard                                                                                                                                                                                                                                                                                          |
| -------------------------------------------------- | ----------------------------: | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Existing FastAPI, SQLAlchemy, Alembic              |            repository-managed | Sessions, owner-scoped endpoints, durable history, and migration | This is the repository's established endpoint, handler, model, and migration architecture. [CITED: CLAUDE.md] [CITED: .claude/skills/backend-development/SKILL.md]                                                                                                                                    |
| Vue 3, TypeScript, Vuetify wrappers, Pinia, Vitest |            repository-managed | v2 manager, queue state, component tests                         | v2 is the active UI and requires canonical shared resources and R* primitives. [CITED: CLAUDE.md] [CITED: .claude/skills/frontend-v2-components/SKILL.md]                                                                                                                                             |
| Fetch, ReadableStream, AbortController             |              browser standard | Enhanced streaming, progress, pause/cancel, exact resume headers | Fetch exposes the response body as a stream and AbortController cancels it. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch]                                                                                                                                           |
| File System Access API                             | browser standard, progressive | User-selected directory and streamed local writes                | Directory access requires explicit user permission and `showDirectoryPicker()` is not broadly Baseline, so it cannot be the only mode. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker] [CITED: https://developer.mozilla.org/en-US/docs/Web/API/File_System_API] |

### Supporting

| Library               |                                               Version | Purpose                                                       | When to Use                                                                                                                                                                                                                                                                |
| --------------------- | ----------------------------------------------------: | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `hash-wasm` [ASSUMED] | 4.12.0, published 2024-11-19 [VERIFIED: npm registry] | Incremental SHA-256 while writing large enhanced-mode streams | Use only after human package verification. Web Crypto `digest()` requires the entire input in memory and is unsuitable for 100-GB-class files. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest] [CITED: https://github.com/Daninet/hash-wasm] |

**Installation:**

```bash
cd frontend && npm install hash-wasm
```

Do not install this package until a human verifies its provenance because slopcheck was unavailable during research. [ASSUMED]

## Package Legitimacy Audit

| Package               | Registry    | Age                | Downloads     | Source Repo                  | slopcheck   | Disposition                                         |
| --------------------- | ----------- | ------------------ | ------------- | ---------------------------- | ----------- | --------------------------------------------------- |
| `hash-wasm` [ASSUMED] | npm, 4.12.0 | created 2020-04-10 | not collected | github.com/Daninet/hash-wasm | unavailable | Flagged, human verification required before install |

**Packages removed due to slopcheck [SLOP] verdict:** none.

**Packages flagged as suspicious [SUS]:** none. slopcheck was unavailable, therefore the package remains `[ASSUMED]` and the plan must insert `checkpoint:human-verify` before installation. [ASSUMED]

## Architecture Patterns

### System Architecture Diagram

```text
v2 PC game/detail view
  -> explicit whole-game or component/archive-set selection
  -> POST /api/roms/{rom_id}/download-manifests
  -> immutable manifest (opaque member IDs, destinations, sizes, SHA-256, snapshots)
  -> POST /api/download-transfer-sessions
  -> browser queue
       -> Baseline: user-initiated attachment navigation per member
       -> Enhanced: showDirectoryPicker() -> fetch member -> stream writer + SHA-256
  -> GET /api/download-manifests/{manifest_id}/files/{member_id}
       -> owner/visibility/lifecycle check -> fresh hash verification -> descriptor lease
       -> 200 fresh or strict 206 Range + exact If-Match
  -> bounded browser journal events -> session/item history UI
```

The existing direct endpoint is the only source-file delivery boundary. Session routes must never accept a source path, a replacement member URL, an arbitrary byte range, a digest, or an authorization bypass. [CITED: backend/endpoints/download_manifests.py] [CITED: backend/endpoints/responses/download_manifest.py]

### Recommended Project Structure

```text
backend/
├── models/download_transfer.py                 # path-free session, item, event models
├── handler/database/download_transfers_handler.py
├── endpoints/responses/download_transfer.py
├── endpoints/download_transfers.py
├── alembic/versions/0122_download_transfer_sessions.py
└── tests/{models,handler/database,endpoints}/test_download_transfers*.py
frontend/src/
├── services/api/downloadTransfers.ts           # typed session API
├── v2/components/GameDetails/DownloadManager.vue
├── v2/components/GameDetails/DownloadSelectionDialog.vue
├── v2/composables/useBrowserDownloadQueue/
├── v2/utils/downloadManifestPath.ts            # pure destination validation
└── v2/workers/downloadHash.worker.ts           # enhanced streamed SHA-256 only
```

The exact migration revision must be based on the live Alembic head, which is currently `0121_download_manifest_member_identity_and_topology`; do not assume it remains unchanged when execution starts. [CITED: backend/alembic/versions/0121_download_manifest_member_identity_and_topology.py]

### Pattern 1: Create once, queue immutable members

**What:** On a user click, validate the selection and create one manifest. Create the transfer session from that manifest ID. Persist copied member evidence in session items only if it improves historical readability; the session must retain the manifest relation and never become an alternate delivery grant. [CITED: backend/handler/database/download_manifests_handler.py] [ASSUMED]

**When to use:** Every whole-game and custom component/archive-set request. [VERIFIED: task brief]

### Pattern 2: Separate authoritative transfer outcomes from browser observations

**What:** Model session items as `QUEUED`, `HANDED_TO_BROWSER`, `DOWNLOADING`, `PAUSED`, `VERIFYING`, `VERIFIED`, `FAILED`, `CANCELLED`, and `STALE`. Append ordered events with bounded error codes and `BigInteger` observed bytes. Only `VERIFIED` is eligible after the enhanced path finishes SHA-256 equality; baseline navigation never creates that claim. [ASSUMED]

**When to use:** This prevents a client-controlled POST from claiming source bytes were received or verified. It also keeps a browser cancel distinct from a source change or manifest expiry. [ASSUMED]

### Pattern 3: Strict enhanced resume

**What:** Store per-item local enhanced state only after validating its manifest ID, opaque file ID, destination, expected size, SHA-256, and exact quoted snapshot. Resume with `Range: bytes=<verified-local-offset>-` and `If-Match: <snapshot>`, accept only `206` with an exact matching `Content-Range`, and never append a `200`. Map `412 source_changed` and `409/410` manifest states to terminal stale/reprepare states. [CITED: backend/endpoints/download_manifests.py] [CITED: docs/superpowers/specs/2026-09-15-cross-platform-pc-downloader-design.md]

### Pattern 4: Progressive File System Access

**What:** Offer the user a mode selector before queue start. The enhanced branch calls `showDirectoryPicker({ mode: "readwrite" })` directly from the initiating click, checks/requests permission again before writing, validates every POSIX destination segment, walks only child directory handles, and refuses automatic overwrite. The baseline branch remains available if the API is absent, denied, or cancelled. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker] [CITED: https://developer.mozilla.org/en-US/docs/Web/API/File_System_API] [ASSUMED]

### Anti-Patterns to Avoid

- **A ZIP fallback for selected components:** It defeats original-file transfer and the established no-packaging boundary. [CITED: .planning/phases/15-direct-resumable-transfer/15-03-SUMMARY.md]
- **Calling `crypto.subtle.digest()` on a complete large file:** It requires the whole input in memory. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest]
- **Calling a native browser download complete from page code:** A page cannot prove that browser-managed attachment delivery finalized and matches the manifest. [ASSUMED]
- **Treating a transfer session or browser event as authorization:** Each member request must retain the existing manifest owner, ROM visibility, lifecycle, and fresh source verification checks. [CITED: backend/endpoints/download_manifests.py]
- **Reusing generic ROM ZIP/bulk download actions:** Existing gallery bulk actions target `/api/roms/download`; this phase must add an isolated PC manifest flow rather than alter generic downloads. [CITED: frontend/src/services/api/rom.ts]

## Don't Hand-Roll

| Problem                                | Don't Build                                       | Use Instead                                           | Why                                                                                                                                                                                                    |
| -------------------------------------- | ------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Source authorization and Range parsing | A browser or new route that resolves file paths   | Existing manifest-member endpoint                     | It already enforces opaque identity, owner/visibility masking, snapshot checks, `u64` single-range parsing, source rehashing, and descriptor leasing. [CITED: backend/endpoints/download_manifests.py] |
| Browser directory permission           | A fake local path text field                      | `showDirectoryPicker()` when available                | The API obtains a user-approved directory handle under browser permission controls. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker]                               |
| Large streamed SHA-256                 | A bespoke JavaScript cryptographic implementation | A reviewed incremental SHA-256 library in a worker    | Native Web Crypto digest is not streaming; cryptographic code must not be improvised. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest] [ASSUMED]                          |
| Modal, progress, permissions, feedback | Raw Vuetify/HTML and inline role checks           | `RDialog`, `RProgressLinear`, `useCan`, `useSnackbar` | These are required v2 patterns and preserve universal input and theming behavior. [CITED: .claude/skills/frontend-v2-patterns/SKILL.md] [CITED: .claude/skills/frontend-v2-components/SKILL.md]        |

## Common Pitfalls

### Pitfall 1: Native resume silently becomes invalid

**What goes wrong:** A browser resumes an attachment with `Range` but cannot be directed to send the saved snapshot in `If-Match`; the server correctly returns `412`. [CITED: backend/endpoints/download_manifests.py]

**How to avoid:** Declare baseline browser attachment mode non-resumable and do not show a resume control there. Offer resume only where the enhanced fetch path controls both headers. [ASSUMED]

### Pitfall 2: Incorrect component selection changes the archive set

**What goes wrong:** A UI checkbox list implies dependencies that the data model cannot prove, or silently expands a custom request. [CITED: backend/handler/database/download_manifests_handler.py]

**How to avoid:** Add a server-authoritative archive-set policy and display its required components before manifest creation. Block or require a clear acknowledgement for incomplete sets, according to the user-approved rule. [ASSUMED]

### Pitfall 3: Browser history overstates completion

**What goes wrong:** Client POSTs can fabricate byte counts or completion, producing misleading audit data. [ASSUMED]

**How to avoid:** Store client-reported values as observations, preserve event origin/mode, and reserve `VERIFIED` for the enhanced local SHA-256 match. [ASSUMED]

### Pitfall 4: File System Access is treated as universal

**What goes wrong:** A browser without the experimental/limited picker cannot start the workflow. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker]

**How to avoid:** Feature-detect the picker, retain baseline attachment downloads, and make lack/denial an informative state rather than an error that blocks download. [ASSUMED]

### Pitfall 5: UI breaks v2 contracts

**What goes wrong:** A download manager creates raw controls, hard-coded strings/colors, or mouse-only queue controls. [CITED: .claude/skills/frontend-v2-components/SKILL.md] [CITED: .claude/skills/frontend-v2-input/SKILL.md] [CITED: .claude/skills/frontend-i18n/SKILL.md]

**How to avoid:** Use R* primitives, locale keys in all locales, semantic tokens, native control order or `useGridNav`, and both dark/light and mouse/touch/key/pad test passes. [CITED: .claude/skills/frontend-v2-components/SKILL.md] [CITED: .claude/skills/frontend-v2-input/SKILL.md] [CITED: .claude/skills/frontend-v2-theming/SKILL.md]

## Code Examples

### Exact enhanced resume request

```ts
// Source: backend/endpoints/download_manifests.py
const response = await fetch(member.download, {
  credentials: "same-origin",
  headers:
    offset > 0
      ? { Range: `bytes=${offset}-`, "If-Match": member.snapshot }
      : {},
  signal: controller.signal,
});

// A resumed response must be exactly 206 and match offset/total before append.
```

The production implementation must validate response status and `Content-Range` before opening a writable stream. Fetch resolves for HTTP errors, so response status must be checked explicitly. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch]

### Feature-gated directory acquisition

```ts
// Source: https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker
if ("showDirectoryPicker" in window) {
  const root = await window.showDirectoryPicker({ mode: "readwrite" });
  // Validate manifest destinations, then walk child handles below root only.
}
```

The picker call must remain directly associated with the user's initiating action. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker]

## State of the Art

| Old Approach                                        | Current Approach                                                                            | Impact                                                                                                                                                                           |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Desktop/Tauri handoff with native local persistence | Browser-only queue, with browser attachment baseline and optional File System Access writer | Phase 17 needs a new browser-local state model and cannot claim desktop guarantees in baseline mode. [VERIFIED: task brief]                                                      |
| Generic `downloadRom` or ZIP-oriented bulk download | PC immutable manifest member delivery                                                       | Selection, identity, integrity evidence, and direct source-read safety are preserved. [CITED: frontend/src/services/api/rom.ts] [CITED: backend/endpoints/download_manifests.py] |

## Assumptions Log

| #   | Claim                                                                                                                                | Section               | Risk if Wrong                                                      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | --------------------- | ------------------------------------------------------------------ |
| A1  | Transfer session/history must distinguish client observations from server-authoritative source authorization and local verification. | Architecture Patterns | Audit semantics could be misleading.                               |
| A2  | Baseline attachment downloads should be non-resumable and only recorded as handed off.                                               | Summary               | Product behavior may need a different supported-browser policy.    |
| A3  | A persisted archive-profile/required-set model is the preferred way to express dependencies.                                         | User Constraints      | Scope and migration shape may change.                              |
| A4  | `hash-wasm` is appropriate after human verification for worker-based incremental SHA-256.                                            | Standard Stack        | Supply-chain approval or another approved library may be required. |

## Open Questions (RESOLVED)

1. **What is an explicit required archive set?**
   - What we know: Phase 14 permits whole game or any exact eligible subset, and the phase scope requires explicit required archive sets. [CITED: backend/handler/database/download_manifests_handler.py] [VERIFIED: task brief]
   - What's unclear: Whether base is mandatory for updates/DLC/extras, whether a user can define profiles, and whether incomplete selection is blocked or acknowledged.
   - Recommendation: Lock this product rule before planning the migration/API/UI work. [ASSUMED]
2. **Is checksum verification required in baseline mode?**
   - What we know: The baseline browser manages attachment completion outside page JavaScript, while Web Crypto's digest is non-streaming. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest]
   - What's unclear: Whether baseline may be labeled unverified or whether enhanced mode must be required for checksum-proven completion.
   - Recommendation: Require enhanced mode for `VERIFIED`; keep baseline available as an explicitly unverified handoff. [ASSUMED]
3. **What retention policy applies to transfer history?**
   - What we know: Existing manifest TTL defaults to 24 hours, but there is no transfer-session model yet. [CITED: backend/config/**init**.py] [CITED: backend/models/download_manifest.py]
   - What's unclear: Session expiry, event retention, user delete/export controls, and whether a cleanup task is needed.
   - Recommendation: Decide retention and ownership before adding tables, then test cascade/cleanup behavior. [ASSUMED]

## Resolution Summary

- Required archive sets are persisted, explicit relationships. Phase 17 must
  provide an authorized authoring or import path and a safe assignment path for
  existing components. Empty set tables must not change existing component
  eligibility.
- Standard attachment delivery is retained as an explicitly unverified browser
  handoff. Only enhanced streaming may be marked locally verified after the
  manifest SHA-256 matches.
- Completed, cancelled, failed, and expired session records and bounded events
  are retained for 90 days. A RomM-owned cleanup path deletes them afterward;
  an active session with an expired manifest transitions fail closed.

## Environment Availability

| Dependency                            | Required By                 |  Available | Version           | Fallback                      |
| ------------------------------------- | --------------------------- | ---------: | ----------------- | ----------------------------- |
| Node.js                               | frontend build/tests        |        yes | v24.19.0          | none                          |
| npm                                   | frontend dependency/install |        yes | 11.17.0           | none                          |
| uv                                    | backend tests/migration     |        yes | 0.12.3            | none                          |
| slopcheck                             | package legitimacy gate     |         no | -                 | human verification checkpoint |
| Browser supporting File System Access | enhanced mode               | not probed | browser-dependent | standard attachment baseline  |

## Validation Architecture

### Test Framework

| Property               | Value                                                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Backend framework      | pytest with repository fixtures [CITED: .claude/skills/backend-development/SKILL.md]                                                  |
| Frontend framework     | Vitest via `npm run test` [CITED: CLAUDE.md]                                                                                          |
| Quick backend command  | `cd backend && uv run pytest tests/endpoints/test_download_transfers.py tests/handler/database/test_download_transfers_handler.py -q` |
| Quick frontend command | `cd frontend && npm run test -- DownloadManager DownloadSelectionDialog`                                                              |
| Full commands          | `cd backend && uv run pytest`; `cd frontend && npm run typecheck && npm run test && npm run build` [CITED: CLAUDE.md]                 |

### Phase Requirements to Test Map

| Req ID  | Behavior                                                                                                                                                                                                                                   | Test Type                                 | Automated Command                                 | File Exists?               |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------- | ------------------------------------------------- | -------------------------- |
| UXDL-01 | Whole-game/custom/archive-set selection produces exactly one matching manifest/session queue                                                                                                                                               | backend endpoint plus Vue component       | focused pytest and Vitest                         | Wave 0                     |
| SAFE-01 | Session creation/events and transfer initiation neither mutate source nor disclose paths; no ZIP route is added                                                                                                                            | endpoint/integration source-tree evidence | focused pytest                                    | Wave 0                     |
| TEST-01 | Existing strict 206/412/416, source change, bad checksum, disk/permission, 5/80/120 GiB, and cross-platform path tests remain green; browser enhanced path adds response/header, cancellation, queue cap, and destination-validation tests | backend plus Vitest                       | Phase 15/16 focused suites plus new manager tests | partial, Phase 15/16 exist |

### Wave 0 Gaps

- [ ] `backend/tests/models/test_download_transfer.py`, model constraints, owner cascade, append-only event ordering, `BigInteger` counters.
- [ ] `backend/tests/handler/database/test_download_transfers_handler.py`, session/member ownership, manifest status, archive-set enforcement, transition rules.
- [ ] `backend/tests/endpoints/test_download_transfers.py`, auth/visibility masking, payload bounds, raw-path disclosure, source-unchanged evidence.
- [ ] `frontend/src/v2/components/GameDetails/DownloadManager.test.ts`, native vs enhanced mode, selection preservation, errors, queue limit, progress, keyboard/gamepad behavior.
- [ ] `frontend/src/v2/utils/downloadManifestPath.test.ts`, traversal, slash variants, Windows roots/names, Unicode/collision, and duplicate destination rejection.
- [ ] Browser-capability test seam that mocks directory handles, writable streams, fetch 200/206/412/416, and `AbortController`; no test contacts a NAS or Team4s. [CITED: CLAUDE.md]

## Security Domain

### Applicable ASVS Categories

| ASVS Category         | Applies | Standard Control                                                                                                                                                                                      |
| --------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| V2 Authentication     | yes     | Existing `ROMS_READ`, owner-scoped manifests, and same-origin authenticated API routes. [CITED: backend/endpoints/download_manifests.py]                                                              |
| V3 Session Management | yes     | Transfer session is metadata only, never an authorization credential; each member request rechecks owner and visibility. [CITED: backend/endpoints/download_manifests.py]                             |
| V4 Access Control     | yes     | `assert_rom_visible`, masked 404 for foreign/hidden data, strict server-owned selection. [CITED: backend/endpoints/download_manifests.py]                                                             |
| V5 Input Validation   | yes     | Pydantic `extra="forbid"`, bounded statuses/counters, UUID format, and revalidated destination paths. [CITED: backend/endpoints/responses/download_manifest.py] [ASSUMED]                             |
| V6 Cryptography       | yes     | Existing SHA-256 evidence and strong snapshot; reviewed incremental SHA-256 for enhanced local verification, never custom cryptography. [CITED: backend/handler/filesystem/roms_handler.py] [ASSUMED] |

### Known Threat Patterns

| Pattern                         | STRIDE                 | Standard Mitigation                                                                                                                                                                                          |
| ------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Source-path disclosure          | Information disclosure | Accept only opaque manifest/session identities; preserve existing masked 404 and path-free serialization. [CITED: backend/endpoints/download_manifests.py]                                                   |
| Resume mixes changed bytes      | Tampering              | Exact snapshot `If-Match`, strict 206 `Content-Range`, and terminal stale state on 412/409/410. [CITED: backend/endpoints/download_manifests.py]                                                             |
| Browser event forges completion | Tampering              | Treat event bytes/status as observation; only enhanced local hash equality may mark verified. [ASSUMED]                                                                                                      |
| Malicious destination           | Tampering              | Validate each manifest destination before FSA handle traversal; do not accept local path strings or source paths. [ASSUMED]                                                                                  |
| Resource exhaustion             | Denial of service      | Cap browser active files, preserve existing server transfer limiter, and bound event payload/rate/history. [CITED: backend/config/**init**.py] [CITED: backend/handler/filesystem/roms_handler.py] [ASSUMED] |

## Project Constraints (from AGENTS.md)

- Use `/home/d1sk/romm` on `team4s-linux` as the canonical checkout and preserve unrelated worktree changes. [CITED: AGENTS.md] [CITED: CLAUDE.md]
- New frontend work belongs in `frontend/src/v2/`; v1 remains frozen. [CITED: CLAUDE.md]
- Backend owns the API schema. Regenerate frontend types and typecheck after API changes. [CITED: CLAUDE.md] [CITED: .claude/skills/backend-development/SKILL.md]
- Use tests with code, Trunk checks, locale parity/sorting for strings, v2 primitives/tokens/universal input, and browser verification before UI handoff. [CITED: CLAUDE.md] [CITED: .claude/skills/frontend-i18n/SKILL.md] [CITED: .claude/skills/frontend-v2-input/SKILL.md]
- Do not deploy, use a real NAS mount, access Team4s, restart Team4s, or alter Team4s in this phase. [CITED: AGENTS.md]
- All project documentation is English and must not use em dashes. [CITED: CLAUDE.md]

## Sources

### Primary

- [CITED: backend/endpoints/download_manifests.py] Existing manifest creation, owner/visibility checks, strict range protocol, source verification, and response headers.
- [CITED: backend/handler/filesystem/roms_handler.py] Existing snapshot construction, path-safe member evidence, descriptor lease, and server concurrency limiter.
- [CITED: .planning/phases/14-immutable-download-manifests/14-VERIFICATION.md] Manifest identity, exact selection, and source safety evidence.
- [CITED: .planning/phases/15-direct-resumable-transfer/15-03-SUMMARY.md] Direct no-ZIP range delivery evidence.
- [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker] User activation, secure-context, permission, and compatibility constraints.
- [CITED: https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest] Native digest's whole-input memory restriction.

### Secondary

- [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch] Response streaming, error-status handling, and abort behavior.
- [CITED: https://github.com/Daninet/hash-wasm] Maintainer documentation for incremental WebAssembly hashing, worker support, and resumable hash state.

## Metadata

**Confidence breakdown:**

- Standard stack: MEDIUM, existing project and browser APIs are verified; the SHA-256 package awaits human legitimacy verification.
- Architecture: HIGH for reuse of Phase 14/15 transfer authority; MEDIUM for new session/history semantics pending product decisions.
- Pitfalls: HIGH for strict Range/If-Match and File System Access availability; MEDIUM for browser-native completion behavior.

**Research date:** 2026-09-17

**Valid until:** 2026-10-17
