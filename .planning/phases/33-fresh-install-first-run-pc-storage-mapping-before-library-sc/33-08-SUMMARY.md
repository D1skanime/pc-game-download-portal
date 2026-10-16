---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
plan: 08
subsystem: frontend
tags: [vue, typescript, vitest, storage-readiness, mapping-gates]

requires:
  - phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
    provides: setup-owned persisted folder assignments and mapping-bound scan authorization
provides:
  - shared GET-only readiness aggregation for all persisted platform mappings
  - Home and Scan guards driven by server-backed mapping health
  - focused regression coverage for multi-mapping, reload, direct invocation, and mutation/path boundaries
affects: [phase-33, home, scan, storage-mapping]

tech-stack:
  added: []
  patterns: [server-backed aggregate readiness, GET-only persisted identity checks, shared Home/Scan predicate]

key-files:
  created: []
  modified:
    - frontend/src/services/api/storage.ts
    - frontend/src/services/api/storage.test.ts
    - frontend/src/v2/views/Home.vue
    - frontend/src/v2/views/Home.test.ts
    - frontend/src/v2/views/Scan.vue
    - frontend/src/v2/views/Scan.test.ts

key-decisions:
  - Resolve readiness from server platform IDs and root health, ignoring only 404s for unmapped platforms and requiring every returned mapping to be healthy.
  - Keep Home and Scan mutation-free and reuse the same storage service aggregate, with no browser paths or hard-coded platform route.
  - Retain the existing large Home and Scan view files because their size predates this plan; splitting unrelated UI would expand scope without improving the readiness change.

patterns-established:
  - Storage readiness fetches one root snapshot, then GETs active mappings by persisted platform identity.
  - Scan access is hidden and direct invocation is guarded until aggregate readiness is true.

requirements-completed: [PGDP-33-01]

---
# Phase 33 Plan 08: Shared persisted-mapping readiness gates

**Home and Scan now expose library scanning only after every persisted mapping returned by the server is active, reachable, readable, and confirmed non-writable.**

## Performance

- Duration: approximately 14 min
- Started: 2026-10-16T19:31:00Z
- Completed: 2026-10-16T19:46:00Z
- Tasks: 2
- Files modified: 6

## Accomplishments

- Added getMappingsReadiness, a typed GET-only aggregate that fetches one root health snapshot, resolves all server platform mapping identities, ignores only missing mappings, and requires every saved mapping to satisfy the existing health predicate.
- Updated Home and Scan to use the aggregate predicate on initial load/reload, hide blocked controls, preserve retry/error states, and guard direct scan invocation.
- Added regression coverage for multiple mappings, partial/missing/unhealthy/writable states, reload/no-mapping states, mutation absence, and browser-path absence.

## Task Commits

Each task was committed atomically:

1. Task 1: Generalize the GET-only readiness client - 717d146b2 (test), 78944c364 (feat)
2. Task 2: Gate Home and Scan on persisted readiness - 816f897e2 (test), ae55b65b2 (feat)

## Verification

- docker compose run --rm --no-deps --entrypoint bash pgdp-dev -lc 'cd /app/frontend && npm run test -- src/services/api/storage.test.ts src/v2/views/Home.test.ts src/v2/views/Scan.test.ts' - PASS, 19 tests.
- docker compose run --rm --no-deps --entrypoint bash pgdp-dev -lc 'cd /app/frontend && npm run typecheck' - PASS.
- Source-only forbidden-string/path/mutation grep over Home.vue and Scan.vue - PASS.
- git diff --check - PASS.
- File sizes: storage service 190 lines, storage tests 201 lines, Home test 26 lines, Scan test 25 lines. Home.vue (688) and Scan.vue (1,558) were already large pre-existing views; the change is confined to their existing readiness blocks and splitting them would be unrelated scope.

## Deviations from Plan

### Auto-fixed Issues

1. [Rule 3 - Blocking] Used the existing Compose frontend service
- Found during: Task 1 verification
- Issue: The plan command names romm-dev, but this checkout exposes pgdp-dev.
- Fix: Ran the identical frontend test/typecheck commands through pgdp-dev.
- Files modified: None
- Verification: All 19 focused tests and typecheck passed.
- Committed in: Task commits above.

2. [Rule 3 - Blocking] Used the configured remote checkout's available tooling
- Found during: Task execution
- Issue: The verified Linux host has no host-side apply_patch or npm; edits were applied inside the verified checkout using the available remote Python stdin fallback, and tests ran in Compose.
- Fix: Preserved the same atomic file changes and ran all executable gates in the existing container.
- Files modified: Planned six frontend files only.
- Verification: Pre-commit formatting/checks, focused tests, typecheck, forbidden-string scan, and diff check passed.
- Committed in: Task commits above.

Total deviations: 2 auto-fixed (Rule 3: 2).
Impact on plan: No scope expansion; implementation and verification stayed inside the verified Linux checkout.

## Issues Encountered

None affecting delivered behavior. The initial RED test edit had a malformed Windows-path assertion; it was corrected before the RED gate commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The frontend now consumes persisted server mapping health consistently on Home and Scan. The shared dirty Compose overrides and backend/pgdp_test/ remain preserved for the next executor.

---
Phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
Completed: 2026-10-16

## Self-Check: PASSED

- Summary file exists in the verified Linux checkout.
- Task commits 717d146b2, 78944c364, 816f897e2, and ae55b65b2 are present.
- Protected dirty files remain untouched.
