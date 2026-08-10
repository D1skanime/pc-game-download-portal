# Phase 3: Mapping Administration Contracts - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 delivers authenticated backend and OpenAPI contracts for live-safe storage-root inspection, contained directory browsing, one active relative mapping per platform, non-mutating mapping tests, optimistic mapping administration, and path-safe audit history. The v2 administration UI, scanner cutover, migration, and broader catalog lifecycle work remain in later phases.

</domain>

<decisions>
## Implementation Decisions

### Root Status and Directory Browser

- **D-01:** Every storage-root retrieval performs a live read-only health check for reachability, readability, and non-writability. Stored timestamps remain part of the response, but stale stored status is not presented as current.
- **D-02:** Directory browsing returns bounded pages using a stable cursor. It never returns an unbounded directory listing or silently truncates results.
- **D-03:** Each directory entry exposes only its name, normalized relative path, and whether it can be navigated. Counts, estimated sizes, timestamps, absolute paths, and filesystem metadata are excluded.
- **D-04:** Root and browse failures use stable machine-readable codes plus bounded safe messages. Responses never expose absolute paths, NAS paths, unrelated mappings, or raw filesystem errors.

### Mapping Lifecycle

- **D-05:** Mapping test and mapping persistence are separate operations. Testing validates root, normalized path, containment, readability, and conflicts without modifying the mapping, catalog, audit history, or source tree.
- **D-06:** Changing a mapping preserves all existing catalog entries and requires an explicit later rescan to reconcile them. The change does not delete or rewrite indexed games automatically.
- **D-07:** Removing a mapping removes only active mapping configuration and creates the required audit record. Catalog records and every source file remain untouched; the platform becomes explicitly unmapped.
- **D-08:** Any browse, test, preview, or scan-related call that requires a mapping returns a typed `platform_mapping_missing` conflict when none exists. No legacy directory derivation, unrelated-directory fallback, or empty-success response is allowed.

### Conflicts and Concurrency

- **D-09:** Mapping updates and state changes use optimistic concurrency based on an explicit version or `updated_at` precondition. Stale writes never overwrite newer administrator changes.
- **D-10:** Overlap errors expose a stable conflict type and the affected platform/mapping identifiers, but never disclose another mapping's relative or absolute path.
- **D-11:** Only active mappings participate in duplicate and ancestor/descendant overlap checks. Inactive mapping history remains available for traceability but does not reserve a path.
- **D-12:** Concurrency, duplicate, and overlap conflicts return HTTP 409 with stable machine codes and the current mapping version where applicable. The server never retries or merges a stale administrator command automatically.

### Audit Contract

- **D-13:** Audit creation, update, removal, activation, and deactivation. Read-only root checks, directory browsing, mapping tests, and previews do not create audit records.
- **D-14:** Old and new audit values contain root ID, normalized relative path, mapping version, and active status. Container paths, NAS host paths, unrelated paths, and raw errors are forbidden.
- **D-15:** The actor is stored as an immutable user ID plus a bounded safe display-name snapshot so records remain attributable after user renaming or deletion.
- **D-16:** Audit history is administrator-only, cursor-paginated, ordered newest first, and filterable by platform ID, mapping ID, and action.

### the agent's Discretion

Exact route names, Pydantic schema names, cursor encoding, version column representation, audit table/module names, and safe error-code spelling are left to research and planning, provided D-01 through D-16 and the established FastAPI/OpenAPI conventions are preserved.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope and Requirements

- `.planning/PROJECT.md` - Core archive-safety value, project constraints, active requirements, and deferred capabilities.
- `.planning/ROADMAP.md` - Phase 3 goal, fixed boundary, dependencies, success criteria, and requirement allocation.
- `.planning/REQUIREMENTS.md` - MAP-01 through MAP-06, API-01 through API-04, AUD-01 through AUD-02, and TEST-02 contracts.

### Trusted Storage Foundation

- `.planning/phases/01-immutable-storage-foundation/01-CONTEXT.md` - Storage-root, mapping, normalization, overlap, and persistence decisions.
- `.planning/phases/02-read-only-policy-boundary/02-CONTEXT.md` - Trusted descriptor, operation-bound access, bounded denial, and closed-inventory decisions that Phase 3 must preserve.
- `.planning/phases/02-read-only-policy-boundary/02-VERIFICATION.md` - Verified Phase 2 trust boundary and security evidence.

### Existing Architecture Maps

- `.planning/codebase/ARCHITECTURE.md` - Endpoint-to-handler layering and OpenAPI-generated frontend contract pattern.
- `.planning/codebase/STACK.md` - FastAPI, Pydantic, SQLAlchemy, database portability, and test/container toolchain.
- `.planning/codebase/INTEGRATIONS.md` - Existing authentication, authorization, database, and operational integration points.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `backend/models/storage.py`: Existing `StorageRoot` and `PlatformStorageMapping` schema, immutable external mode, root/path uniqueness, and platform relationship.
- `backend/handler/database/storage_handler.py`: Root registration, live health validation, normalized mapping persistence, row locks, cross-root overlap checks, and typed persistence errors.
- `backend/handler/filesystem/storage_resolver.py`: Relative-path normalization, containment, symlink rejection, directory resolution, and live root-health probes.
- `backend/decorators/auth.py` and `backend/handler/auth/dependencies.py`: Established protected-route, scope, visibility, and permission enforcement.
- `backend/utils/router.py` and `backend/endpoints/responses/`: Established FastAPI/OpenAPI and Pydantic response conventions.

### Established Patterns

- Endpoints remain thin and delegate database/filesystem behavior to handlers.
- Backend response schemas are authoritative; generated frontend types must be regenerated after contract changes.
- Storage identity must originate from trusted persisted/composed descriptors, never caller path text.
- Database changes remain portable across MariaDB, MySQL, and PostgreSQL and translate named constraint failures into typed domain errors.

### Integration Points

- New storage administration routes attach to the existing `/api` router and protected-route scope model.
- Mapping operations extend `DBStorageHandler` rather than introducing parallel persistence access.
- Directory browsing and tests reuse the Phase 1 resolver and Phase 2 operation-bound access boundary.
- Audit persistence links mapping changes to authenticated request identity without placing audit output inside the external root.

</code_context>

<specifics>
## Specific Ideas

- Root status must be current at retrieval time even if NAS checks add latency.
- Browser payloads intentionally remain minimal and path-safe.
- Administrator intent is explicit: testing never saves, changing never rescans automatically, and removing never deletes catalog or source data.
- Conflicts are recoverable through reload-and-retry by the client, not server-side automatic merging.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 3 scope.

</deferred>

---

_Phase: 03-mapping-administration-contracts_
_Context gathered: 2026-08-10_
