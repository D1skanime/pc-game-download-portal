# Phase 9: Operational Immutability Proof - Context

**Gathered:** 2026-08-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove, in a production-like Docker environment, that every supported external-library workflow preserves the complete source fixture while RomM writes only to separate owned storage. The proof includes the application, worker, nginx, browser, restart, and migration paths, and it ships with an operator guide for safe NAS deployment. It uses controlled fixtures only and must not deploy, restart services, access a real NAS mount, or change Team4s.

</domain>

<decisions>
## Implementation Decisions

### Production-like Proof Stack

- **D-01:** Build the proof around a production-like Docker stack containing the RomM application, background worker, nginx, required database and queue services, a read-only fixture library mount, and distinct writable RomM-owned storage.
- **D-02:** Mount the fixture library read-only with Docker `:ro`. Database data, resources, assets, cache, configuration, temporary data, scan state, and all other RomM-owned output must use separate writable mounts or volumes.
- **D-03:** Exercise the actual nginx internal-redirect download/stream path and the actual worker queue path, not development-only substitutes.
- **D-04:** Include restart persistence in the stack proof. Restart only the isolated test stack created for Phase 9, never Team4s or unrelated host services.

### Complete Immutability Evidence

- **D-05:** Capture a full source manifest immediately before and after every supported workflow. Each manifest records every relative path, exact name, entry type and directory structure, file size, content hash, and filesystem timestamps.
- **D-06:** Compare complete manifests with an exact, machine-verifiable diff. A workflow passes only when content, names, structure, sizes, hashes, and non-access timestamps are unchanged. Access-time invariance must be demonstrated under the documented `noatime` or NAS-equivalent configuration.
- **D-07:** Produce separate before/after evidence for mapping creation, mapping change, mapping removal, folder browsing and mapping tests, preview, scanning and hashing, metadata matching, streaming and browser play, single-file and multi-file downloading, restart persistence, legacy migration and rollback where supported, game catalog removal, and platform mapping removal.
- **D-08:** Evidence must cover multiple mappings and Unicode, nested, empty, and multi-file fixture shapes. It must make any source mutation or incomplete manifest a hard failure, including unexpected files, directories, sidecars, locks, caches, archives, or temporary output.
- **D-09:** Keep evidence deterministic and reviewable in CI. The planner may choose the exact manifest serialization and artifact layout, but it may not weaken the required fields, per-workflow boundaries, or exact comparison.

### Browser End-to-end Coverage

- **D-10:** Use browser end-to-end tests for the supported operator and user workflows, not API-only substitutes. Cover mapping and browsing, scan initiation and completion, streaming or browser play, downloading, legacy migration, game catalog removal, and platform mapping removal.
- **D-11:** Browser tests must drive the production-like nginx-backed application while worker jobs run through the separate worker service. They must verify visible success, safe failure states where relevant, and the corresponding unchanged source manifest.
- **D-12:** Include the Phase 8 deferred v2 browser smoke scope so authentication, pairing where applicable, v2 boot, navigation, and supported routes are exercised without any v1 fallback.

### Operator Guide and Safeguards

- **D-13:** Write one complete operator guide covering the one-root Docker `:ro` mount, separate writable storage, root registration, folder browsing, platform mapping and changes, scan and preview behavior, streaming and downloading, migration, catalog-only removal, restart behavior, troubleshooting, security boundaries, and known limitations.
- **D-14:** The guide must explain defense in depth: Docker `:ro` is mandatory, and the application policy must still deny mutations before filesystem access. It must also explain traversal and symlink behavior without exposing or encouraging unsafe bypasses.
- **D-15:** Include explicit `noatime` guidance and NAS-specific equivalents, explain why ordinary reads can otherwise update access time, and distinguish access-time controls from the independent content immutability guarantees.
- **D-16:** Include a maintenance-window checklist that requires authorization and workload review before any real NAS mount change. The checklist must require backups or recovery readiness, mount verification, read-only validation, writable-storage separation, manifest/evidence review, rollback steps, and post-window confirmation.
- **D-17:** State explicit Team4s safeguards: do not edit Team4s source or configuration, do not restart or stop Team4s services or the host, do not touch active encode workloads, and do not use Team4s paths, mounts, containers, or data as Phase 9 test fixtures.
- **D-18:** Phase 9 planning and execution use synthetic or repository-controlled fixtures only. Access to a real NAS mount remains prohibited unless a later, separately authorized maintenance window explicitly permits it.

### Folded Todos

- **Enforce immutable external game libraries:** Fold `.planning/todos/pending/2026-08-04-enforce-external-library-read-only.md` into Phase 9. Its remaining operational proof and documentation obligations are satisfied through the production-like `:ro` stack, complete before/after manifests, catalog-only removal coverage, negative mutation guarantees, and `noatime` operator guidance.

### the agent's Discretion

The exact fixture dataset, manifest file format, Docker project naming, CI artifact packaging, Playwright spec grouping, and operator-guide filename are open to the researcher and planner, provided every locked workflow, evidence field, service path, and safeguard above remains explicit and testable.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope and Locked Requirements

- `.planning/ROADMAP.md` - Phase 9 goal, dependencies, production-like evidence scope, and operational success criteria.
- `.planning/REQUIREMENTS.md` - TEST-04 through TEST-06 and DOC-01 through DOC-03 acceptance requirements.
- `.planning/PROJECT.md` - Immutable archive value, storage-separation constraints, canonical host rules, and Team4s restrictions.
- `.planning/todos/pending/2026-08-04-enforce-external-library-read-only.md` - Folded defense-in-depth, negative-test, catalog-removal, and `noatime` obligations.

### Carried-forward Phase Contracts

- `.planning/phases/05-preview-and-read-path-cutover/05-CONTEXT.md` - Mapping-aware scan, hash, stream, download, preview, worker, and source-safety decisions.
- `.planning/phases/06-safe-lifecycle-and-legacy-migration/06-CONTEXT.md` - Catalog removal, mapping removal, legacy migration, rollback, and source-preservation contracts.
- `.planning/phases/07-v2-storage-administration-experience/07-CONTEXT.md` - Browser-visible mapping, browsing, testing, preview, and removal workflows.
- `.planning/phases/08-bounded-v1-removal/08-CONTEXT.md` - v2-only route contract and browser smoke coverage deferred to Phase 9.

### Repository Architecture and Test Patterns

- `CLAUDE.md` - Canonical checkout, Docker, testing, frontend v2, language, and repository-wide constraints.
- `.planning/codebase/TESTING.md` - pytest, Playwright, fixture, integration, and browser assertion conventions.
- `.planning/codebase/STACK.md` - Runtime service and deployment stack inventory.
- `.planning/codebase/ARCHITECTURE.md` - Scan, worker, streaming, download, nginx, database, and filesystem integration paths.
- `backend/docker-compose.policy-test.yml` - Existing writable-versus-read-only policy probe stack to extend or supersede.
- `backend/tests/integration/test_scan_source_immutability.py` - Existing source-manifest seed and scan immutability proof.
- `frontend/playwright.config.ts` - Current authenticated Playwright harness and production-build browser configuration.
- `frontend/e2e/fixtures/auth.ts` - Existing browser authentication and navigation fixtures.
- `docker/nginx/templates/default.conf.template` - Production nginx proxy, internal library redirect, and cached download routes.
- `examples/docker-compose.example.yml` - Existing operator-facing Compose baseline.
- `docs/design/v2-storage-administration.md` - Storage administration behavior and safety presentation contract.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `backend/docker-compose.policy-test.yml` already contrasts writable and read-only external fixtures while keeping owned output separate.
- `backend/tests/integration/test_scan_source_immutability.py` already builds a deterministic path, type, size, and SHA-256 source manifest that can be expanded to full timestamps and all workflows.
- `frontend/e2e/` and `frontend/playwright.config.ts` provide authenticated browser fixtures, semantic assertions, tracing, and production-build execution patterns.
- `backend/handler/storage/legacy_migration.py`, `backend/endpoints/storage.py`, and `frontend/src/services/api/storage.ts` expose the migration and mapping paths required by the browser proof.

### Established Patterns

- External reads resolve through database mapping identity and centralized storage policy; RomM-owned writes require a separate trusted destination.
- Durable scans execute through Redis/RQ workers, while production downloads and streams can use nginx internal redirects.
- Browser tests reuse authenticated storage state and rely on auto-waiting assertions rather than sleeps.
- Existing integration tests use controlled filesystem fixtures, but Phase 9 must broaden their partial manifest into a complete per-workflow evidence contract.

### Integration Points

- Add an isolated production-like Compose proof stack without changing the developer stack, host services, Team4s, or a real NAS mount.
- Route browser actions through the v2 UI, nginx, FastAPI, database identity, storage resolver/policy, and worker queue as applicable.
- Capture and compare manifests around each workflow boundary, while keeping generated reports and all runtime output in owned writable storage.
- Extend operator documentation from the production Compose example and storage design contract with maintenance-window, `:ro`, `noatime`, troubleshooting, and Team4s safety procedures.

</code_context>

<specifics>
## Specific Ideas

The proof should resemble a real deployment closely enough that passing only an in-process test is insufficient. A source fixture is mounted read-only, the worker performs queued work, nginx serves production read paths, the browser drives user-visible workflows, and every workflow is enclosed by complete, exact before/after manifests.

</specifics>

<deferred>
## Deferred Ideas

None. The immutability todo and Phase 8 browser smoke debt are intentionally folded into Phase 9, and the discussion stayed within the phase boundary.

</deferred>

---

_Phase: 09-operational-immutability-proof_
_Context gathered: 2026-08-27_
