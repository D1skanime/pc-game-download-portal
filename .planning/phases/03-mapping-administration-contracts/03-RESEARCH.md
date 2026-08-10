# Phase 3: Mapping Administration Contracts - Research

**Researched:** 2026-08-10
**Domain:** Safe storage administration APIs, optimistic persistence, filesystem containment, and immutable audit history
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within Phase 3 scope.
</user_constraints>

<phase_requirements>

## Phase Requirements

| ID                    | Description                                                                                 | Research Support                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| MAP-01                | Assign a platform to an existing relative subdirectory of an active root.                   | Reuse normalization and strict contained directory resolution before persistence.                           |
| MAP-02                | At most one active mapping per platform while allowing future multiple roots.               | Replace the unconditional platform unique constraint with an active-row lifecycle enforced transactionally. |
| MAP-03                | Mapping operations never mutate source storage.                                             | Keep all lifecycle work in SQL and reuse read-only resolver operations with mutation-tripwire tests.        |
| MAP-04                | Multiple platforms may use distinct directories below one root.                             | Retain root plus relative path identity and reject only equal or ancestor/descendant paths.                 |
| MAP-05                | Reject unsafe overlapping mappings.                                                         | Extend canonical overlap checks to active rows and return conflicting IDs only.                             |
| MAP-06                | Missing mapping is explicit and never falls back.                                           | Add `PlatformMappingMissingError` and endpoint translation to HTTP 409.                                     |
| API-01                | Admins can list roots and inspect safe status.                                              | Thin protected endpoint calls a handler that clones/serializes live health without persisting it.           |
| API-02                | Admins can browse contained relative directories.                                           | Add resolver-level bounded keyset browsing with opaque signed-shape cursor validation.                      |
| API-03                | Typed read/create/change/test/preview/remove endpoints.                                     | Add dedicated request/response schemas and storage administration router.                                   |
| API-04                | Non-admins cannot mutate and anonymous callers cannot enumerate.                            | Use `@protected_route` plus `assert_admin` on every storage administration route.                           |
| AUD-01                | Lifecycle mutations record actor, timestamp, platform, action, and old/new values.          | Add append-only `StorageMappingAudit` rows in the same transaction as mutations.                            |
| AUD-02                | Audit output never exposes host or unrelated paths.                                         | Store structured allowlisted snapshots, not exception text or container paths.                              |
| TEST-02               | API tests cover listing, browsing, lifecycle, authorization, traversal, tests, and preview. | Add endpoint, handler, resolver, migration, OpenAPI, and mutation-tripwire coverage.                        |
| </phase_requirements> |

## Summary

Phase 1 already provides the correct storage identity and filesystem safety primitives in `backend/models/storage.py`, `backend/handler/database/storage_handler.py`, and `backend/handler/filesystem/storage_resolver.py`. Phase 2 adds the trusted operation-bound read-only policy. Phase 3 should extend those modules instead of introducing a second storage subsystem. [VERIFIED: repository inspection]

The central schema change is lifecycle-aware mapping persistence. `PlatformStorageMapping` currently has no `active` or explicit `version` column and uses unconditional unique constraints, so it cannot retain inactive history while freeing paths. Add `active: bool` and `version: int`, retain rows on removal by deactivation, add an append-only audit table, and enforce one active mapping plus active-only overlap checks in one locked transaction. Because portable partial unique indexes are not available uniformly across the supported databases, the handler lock and validation are the primary invariant, with portable supporting indexes and explicit concurrency tests. [VERIFIED: `backend/models/storage.py`, migration 0108, MariaDB/MySQL/PostgreSQL support policy]

Use one admin-only `/api/storage` router with separate read, test, preview, and mutation contracts. Root health and browse results must be computed live and returned without writing observation state. Cursor pagination should be deterministic over normalized entry names and audit `(created_at, id)` keys. Every outward failure should pass through one allowlisted error schema so raw `OSError`, SQL text, absolute paths, and conflicting mapping paths cannot escape. [VERIFIED: CONTEXT D-01 through D-16 and existing endpoint layering]

**Primary recommendation:** Build Phase 3 as a schema-first backend slice: lifecycle and audit migration, transactional handler operations, read-only filesystem browsing, typed admin router, then generated OpenAPI and adversarial API tests.

## Architectural Responsibility Map

| Capability             | Primary Tier       | Secondary Tier     | Rationale                                                                     |
| ---------------------- | ------------------ | ------------------ | ----------------------------------------------------------------------------- |
| Live root status       | API / Backend      | Filesystem         | Endpoint authorizes; resolver performs read-only point-in-time observation.   |
| Directory browsing     | Filesystem         | API / Backend      | Resolver owns containment and enumeration; API bounds and serializes results. |
| Mapping lifecycle      | Database / Storage | API / Backend      | Transactional invariants and audit rows must commit atomically.               |
| Optimistic concurrency | Database / Storage | API / Backend      | Compare version under row lock, then expose a typed HTTP 409.                 |
| Audit history          | Database / Storage | API / Backend      | Append-only persistence and keyset query live in the data layer.              |
| Authorization          | API / Backend      | Database / Storage | Existing middleware and permission resolver establish admin identity.         |
| OpenAPI contract       | API / Backend      | Browser / Client   | Pydantic responses are authoritative; frontend types are generated later.     |

## Project Constraints (from AGENTS.md and CLAUDE.md)

- Work only in `/home/d1sk/romm` on `team4s-linux`; keep branch `codex/pc-module-analysis` and do not use worktrees. [VERIFIED: `CLAUDE.md`]
- Keep endpoint to handler to database/filesystem layering; no business logic or raw queries in endpoints. [VERIFIED: `.claude/skills/backend-development/SKILL.md`]
- Python 3.13+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic 2, pytest, and `uv` are the established backend stack. [VERIFIED: `pyproject.toml`]
- Migrations must upgrade and downgrade on MariaDB, MySQL, and PostgreSQL and must be hand-reviewed. [VERIFIED: `CLAUDE.md`, `.github/workflows/migrations.yml`]
- New logic and endpoints require tests. API changes require regenerated frontend OpenAPI types and frontend typecheck. [VERIFIED: `CLAUDE.md`]
- Use English in code, comments, identifiers, planning files, and commits. Do not use em dashes. Never use `--no-verify`. [VERIFIED: `CLAUDE.md`]
- Preserve the Phase 1 immutable external-root model and Phase 2 trusted descriptor/operation boundary. [VERIFIED: Phase 1 and Phase 2 contexts and verifications]

## Standard Stack

### Core

| Library    | Version     | Purpose                                              | Why Standard                                                                         |
| ---------- | ----------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------ |
| FastAPI    | `~=0.134.0` | Typed routes, auth dependencies, OpenAPI             | Already owns all `/api` contracts. [VERIFIED: `pyproject.toml`]                      |
| Pydantic   | `~=2.11`    | Request, response, and bounded error schemas         | Existing authoritative OpenAPI schema layer. [VERIFIED: `pyproject.toml`]            |
| SQLAlchemy | `~=2.0`     | Models, row locks, atomic mutation and audit         | Existing ORM and handler architecture. [VERIFIED: `pyproject.toml`, storage handler] |
| Alembic    | `~=1.16`    | Portable lifecycle and audit schema migration        | Existing migration chain and multi-dialect CI. [VERIFIED: `pyproject.toml`]          |
| pytest     | `~=9.0`     | Unit, integration, authorization, and endpoint tests | Existing backend test framework. [VERIFIED: `pyproject.toml`]                        |

### Supporting

| Library                    | Version     | Purpose                                     | When to Use                                                                                                                                                     |
| -------------------------- | ----------- | ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hypothesis                 | `~=6.0`     | Adversarial relative path and cursor inputs | Resolver and cursor validation properties. [VERIFIED: existing storage tests]                                                                                   |
| fastapi-pagination         | `~=0.15`    | Existing generic pagination                 | Reuse only where its contract can express required stable cursors; do not force offset pages onto browse/audit. [VERIFIED: `pyproject.toml`, `backend/main.py`] |
| stdlib `base64` and `json` | Python 3.13 | Opaque cursor payload encoding              | Cursor is continuation state, not a security authority; validate decoded shape and query binding.                                                               |

### Alternatives Considered

| Instead of                  | Could Use                 | Tradeoff                                                                                                                                                                                  |
| --------------------------- | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Integer `version`           | `updated_at` precondition | Timestamps can lose precision or serialize differently across dialects; integer versions are explicit and OpenAPI-friendly.                                                               |
| Lifecycle row with `active` | Hard delete mapping       | Hard delete satisfies removal but loses inactive traceability and makes D-11 meaningless; use deactivation plus audit.                                                                    |
| Custom keyset response      | Offset pagination         | Offset pages can skip or duplicate entries during concurrent change and are not stable continuations.                                                                                     |
| Structured audit columns    | JSON old/new blob         | JSON is flexible but makes filtering and allowlist enforcement weaker; use fixed scalar snapshot columns or a tightly typed portable JSON wrapper only if existing conventions demand it. |

**Installation:** No new runtime packages are required. [VERIFIED: repository dependencies]

## Architecture Patterns

### System Architecture Diagram

```text
Authenticated request
  -> protected `/api/storage` route
  -> `assert_admin(request)`
  -> request schema validation
  -> storage administration handler
       -> read path: DB root/mapping lookup -> resolver health/browse/test -> safe response
       -> write path: ordered DB locks -> normalize/resolve/conflict check
            -> version precondition decision
               -> stale: typed 409 with current version
               -> current: mapping mutation + audit append in one transaction
  -> allowlisted Pydantic response/error
  -> OpenAPI -> generated frontend types
```

### Recommended Project Structure

```text
backend/
├── alembic/versions/0109_mapping_administration_contracts.py
├── endpoints/storage.py
├── endpoints/responses/storage.py
├── exceptions/storage_exceptions.py
├── handler/database/storage_handler.py
├── handler/filesystem/storage_resolver.py
├── models/storage.py
├── main.py
└── tests/
    ├── endpoints/test_storage.py
    ├── handler/database/test_storage_handler.py
    ├── handler/filesystem/test_storage_resolver.py
    ├── models/test_storage.py
    └── tools/test_verify_storage_migrations.py
frontend/src/__generated__/   # regenerate from OpenAPI, do not hand edit
```

### Pattern 1: Live health without persistence

Load roots from the database, copy each health-visible value into a response-oriented snapshot, run `check_storage_root_health` against that snapshot, and serialize it. Do not flush health observations during GET. This prevents a read route from mutating `updated_at` or creating audit noise while satisfying D-01. Stored `last_checked_at` may be included under a clearly named stored field, but current status and current checked time must come from the live probe. [VERIFIED: D-01, D-13, current mutating health helper]

### Pattern 2: Contained bounded directory enumeration

Add a resolver function that first calls `resolve_storage_root`, normalizes the requested parent with `allow_root=True`, rejects symlink components, then enumerates only immediate child directories. For every child use `lstat`, reject symlinks, and expose only `name`, the POSIX relative path, and `navigable`. Sort by a deterministic binary/case-sensitive key with a stable tie-breaker, retain the smallest `limit + 1` entries after the cursor with `heapq.nsmallest`, and emit an opaque cursor bound to root ID and parent path. Cap both page size and scanned directory entries in the Pydantic/service contract. [VERIFIED: D-02 through D-04 and existing resolver behavior]

Do not call `Path.iterdir()` and then materialize an unbounded list before slicing. `os.scandir()` cannot stop after the first `limit + 1` entries while also promising global deterministic sort order. Instead stream entries through a bounded `heapq.nsmallest(limit + 1, generator, key=...)`, retaining O(limit) entries, and stop with a typed `directory_scan_limit_exceeded` error if the hard scan ceiling is crossed. This explicitly rejects an oversized directory rather than silently returning an incomplete page. A filesystem directory has no snapshot transaction, so cursor stability is deterministic continuation only for unchanged content, not a promise against concurrent NAS changes.

### Pattern 3: Non-mutating test and preview

Factor validation into a pure/read-only handler path returning a typed result. `test_mapping` performs platform/root lookup, normalization, active-root validation, canonical containment, readability, and active conflict detection, but does not add, update, delete, flush, or audit. Phase 3 preview is resolved as a bounded directory-level candidate summary: mapping/platform/root identifiers, mapping version, normalized relative path, examined-entry count, candidate file count, candidate directory count, `truncated`, and a continuation cursor. It returns no candidate names or paths and invokes neither scanner nor catalog persistence. The same scan ceiling and bounded-memory top-k rule as browsing applies. [RESOLVED: D-05, D-08, Phase 3 boundary, TEST-02]

### Pattern 4: Versioned transactional lifecycle

Add `version` starting at 1 and increment it on update, deactivate, or reactivate. Mutation requests carry `expected_version`. Under a transaction, lock the target mapping and the active root set in the same global order already used by `DBStorageHandler`. Compare the precondition before mutation. On mismatch, rollback and return `mapping_version_conflict` with mapping ID and current version only. Never retry automatically. [VERIFIED: D-09, D-12, existing ordered locks]

Creation has no prior version, but must lock platform/root/mapping rows and reject a second active mapping. If an inactive row is reused, treat reactivation as its own action with its current `expected_version`, increment version, and append audit. Do not silently overwrite an inactive historical row during create.

The public lifecycle is resolved as follows: create always creates a genuinely new active row and never revives or overwrites inactive history. Reactivation is available only through the explicit mapping activation operation, addressed by mapping ID and guarded by its current `expected_version`; it re-runs all active-only platform and overlap validation, increments version, and writes an `activate` audit row. [RESOLVED: D-09, D-11, D-12, D-13]

### Pattern 5: Active-only uniqueness and overlap

The current unique constraints prevent inactive history from releasing a platform or path. Migration 0109 must remove both unconditional unique constraints. Enforce active-only platform uniqueness and equal/ancestor/descendant conflicts within the locked handler transaction. Keep deterministic lock ordering across all active roots and mappings to preserve the Phase 1 concurrency guarantee. Translate any remaining integrity failures by named constraints only and never return DB messages. [VERIFIED: current model/migration/handler tests]

Because MariaDB, MySQL, and PostgreSQL differ in partial/filtered unique index support, do not base correctness on a PostgreSQL-only `WHERE active` index. A portable helper identity column would add dialect and null-semantics complexity. The existing lock-first strategy is the repository-consistent primary guard, backed by cross-dialect concurrent tests.

Migration 0109 downgrade must be fail-closed when Phase 3 history cannot be represented by the 0108 schema. Before any DDL, abort if an audit row exists, any mapping is inactive, any mapping version differs from 1, or active rows would violate the restored 0108 unique constraints. The failure must leave the complete 0109 schema and data intact. A pristine upgraded 0108 dataset may downgrade and re-upgrade. The verifier seeds and mutates a real lifecycle dataset on MariaDB, MySQL, and PostgreSQL, asserts the preflight rejection without partial DDL, then separately proves the pristine downgrade/re-upgrade path. [RESOLVED: portable reversibility and audit preservation]

### Pattern 6: Append-only same-transaction audit

Add `StorageMappingAudit` with its own ID and creation timestamp, mapping ID and platform ID snapshots, action, immutable actor user ID value, bounded actor display-name snapshot, and fixed old/new fields for root ID, relative path, mapping version, and active state. Do not foreign-key actor with `ON DELETE CASCADE`; attribution must survive user deletion. Mapping ID should also be a scalar snapshot rather than a cascade dependency. Insert the audit row in the same session before transaction commit. [VERIFIED: D-13 through D-16]

Prevent updates/deletes through the public handler surface and test that audit listing is the only supported operation. Database-level triggers are not recommended because they cannot reliably receive the authenticated display-name snapshot through the existing application transaction.

### Pattern 7: Keyset audit pagination

Order audit rows by `created_at DESC, id DESC`. Encode the final tuple plus normalized filter fingerprint in the cursor. The continuation predicate is `(created_at < t) OR (created_at = t AND id < id_cursor)`. Validate cursor version, types, filter binding, and length. Invalid cursors return a bounded `invalid_cursor` response. [CITED: https://docs.sqlalchemy.org/en/20/core/operators.html#using-conjunctions-and-negations]

### Pattern 8: One safe error envelope

Define a Pydantic error detail with `code`, bounded `message`, and allowlisted optional identifiers such as `platform_id`, `mapping_id`, `conflicting_platform_id`, `conflicting_mapping_id`, and `current_version`. Translate domain exceptions in the endpoint or a narrowly scoped exception translator. Never serialize `str(OSError)`, `IntegrityError`, input absolute paths, root `container_path`, or another mapping's relative path. [VERIFIED: D-04, D-10, D-12, AUD-02]

### Anti-Patterns to Avoid

- Persisting live GET health checks, which mutates state on reads and changes `updated_at`.
- Returning ORM models directly, which risks exposing `container_path` and relationships.
- Reusing generic `HTTPException(detail=str(error))`, which can leak paths or SQL details.
- Using offset pagination for browse/audit, which violates stable cursor semantics.
- Hard deleting mapping rows, which loses inactive lifecycle traceability.
- Checking overlap outside the transaction or in a different lock order, which reintroduces races/deadlocks.
- Treating client cursors as trusted. Decode, bound, validate, and bind them to the requested root/parent/filter.
- Running scanner reconciliation inside mapping changes. Rescan remains explicit and later.

## Don't Hand-Roll

| Problem                | Don't Build                                          | Use Instead                                                                     | Why                                                                                      |
| ---------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Path containment       | String-prefix path checks                            | Existing `normalize_relative_path`, `resolve_storage_root`, `resolve_directory` | Handles Windows forms, traversal, symlinks, canonical sibling prefixes, and readability. |
| Transactions           | Ad hoc session creation                              | `@begin_session` and existing handler session injection                         | Keeps mutation and audit atomic.                                                         |
| Authentication         | Header or role parsing in routes                     | `@protected_route` and `assert_admin`                                           | Preserves hybrid auth and 401/403 behavior.                                              |
| API typing             | Dict response payloads                               | Pydantic request/response models                                                | Keeps OpenAPI authoritative and generated clients accurate.                              |
| Database errors        | Vendor message parsing beyond known constraint names | Named constraints plus bounded domain exceptions                                | Prevents SQL/path leakage and supports multiple dialects.                                |
| Catalog reconciliation | Implicit rescan on save/remove                       | Explicit later rescan flow                                                      | Phase boundary and D-06 require catalog preservation.                                    |

**Key insight:** The difficult parts are already represented by repository primitives. Phase 3 should compose them under authenticated, transactional, and path-safe contracts rather than create parallel abstractions.

## Runtime State Inventory

This phase includes a schema migration but no legacy data rewrite.

| Category            | Items Found                                                                  | Action Required                                                                                                                                                |
| ------------------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stored data         | Existing `storage_roots` and `platform_storage_mappings` from migration 0108 | Add non-null `active` and `version` with portable server defaults, then create audit table. Existing mappings become active version 1. No catalog rows change. |
| Live service config | Storage root `container_path` values are deployment-owned database state     | Preserve values exactly; never expose or backfill them.                                                                                                        |
| OS-registered state | None for this API/schema phase                                               | None, verified from phase boundary and repo deployment model.                                                                                                  |
| Secrets/env vars    | No new secret or environment variable required                               | None. Cursor opacity is not authorization.                                                                                                                     |
| Build artifacts     | Generated frontend OpenAPI types                                             | Regenerate after route/schema changes; do not hand-edit generated files.                                                                                       |

## Common Pitfalls

### Pitfall 1: Active-only uniqueness race

**What goes wrong:** Two administrators create mappings for the same platform or overlapping paths concurrently.
**Why it happens:** Application validation runs before either transaction commits.
**How to avoid:** Preserve deterministic root/platform/mapping lock ordering and run validation immediately before flush. Add real concurrent MariaDB and PostgreSQL tests.
**Warning signs:** Both requests return success or a raw vendor integrity error escapes.

### Pitfall 2: Read endpoint writes health state

**What goes wrong:** Root listing changes timestamps, causes transaction contention, or appears as an administration mutation.
**Why it happens:** `check_storage_root_health` currently mutates its passed ORM object.
**How to avoid:** Probe a detached/snapshot object or return a dedicated value object.
**Warning signs:** GET emits UPDATE SQL or changes root `updated_at`.

### Pitfall 3: Directory cursor is not query-bound

**What goes wrong:** A cursor from one root or parent is replayed against another location.
**Why it happens:** Cursor contains only the last name.
**How to avoid:** Include schema version, root ID, normalized parent, and last sort key; reject mismatches.
**Warning signs:** Changing `root_id` while retaining cursor produces a valid page.

### Pitfall 4: Path leakage through conflict details

**What goes wrong:** Overlap or filesystem failures disclose NAS or another mapping path.
**Why it happens:** Current `StorageMappingOverlapError` embeds root ID and relative path in its message.
**How to avoid:** Redesign outward errors around allowlisted identifiers and generic bounded messages; assert forbidden sentinel paths are absent from JSON and logs captured by endpoint tests.
**Warning signs:** API tests assert raw exception text.

### Pitfall 5: Audit foreign keys erase history

**What goes wrong:** Deleting a user/platform/mapping cascades audit records or makes them unreadable.
**Why it happens:** Audit modeled as ordinary child relationships.
**How to avoid:** Store immutable scalar identity snapshots, with no cascade dependency for actor or mapping.
**Warning signs:** Audit rows disappear after fixture cleanup or entity deletion.

### Pitfall 6: Timestamp-only concurrency

**What goes wrong:** Equal timestamp precision or dialect serialization permits a stale write.
**Why it happens:** `updated_at` is used as a wire precondition.
**How to avoid:** Use an integer `version` column and return it on every mapping response/conflict.
**Warning signs:** Tests need database-specific timestamp rounding.

## Code Examples

### Typed version precondition

```python
class MappingUpdateRequest(BaseModel):
    storage_root_id: int = Field(gt=0)
    relative_path: str = Field(min_length=1, max_length=STORAGE_MAPPING_PATH_MAX_LENGTH)
    expected_version: int = Field(gt=0)
```

### Safe error detail

```python
class StorageConflictDetail(BaseModel):
    code: str
    message: str = Field(max_length=200)
    mapping_id: int | None = None
    conflicting_mapping_id: int | None = None
    conflicting_platform_id: int | None = None
    current_version: int | None = None
```

### Portable optimistic update under lock

```python
mapping = session.scalar(
    select(PlatformStorageMapping)
    .where(PlatformStorageMapping.id == mapping_id)
    .with_for_update()
)
if mapping.version != expected_version:
    raise StorageMappingVersionConflict(mapping.id, mapping.version)
mapping.version += 1
```

### Stable audit continuation predicate

```python
statement = statement.where(
    or_(
        StorageMappingAudit.created_at < cursor.created_at,
        and_(
            StorageMappingAudit.created_at == cursor.created_at,
            StorageMappingAudit.id < cursor.id,
        ),
    )
).order_by(StorageMappingAudit.created_at.desc(), StorageMappingAudit.id.desc())
```

Sources: existing SQLAlchemy 2 query style in `backend/handler/database/`; official operator documentation at https://docs.sqlalchemy.org/en/20/core/operators.html.

## State of the Art

| Old Approach                              | Current Approach                            | When Changed | Impact                                         |
| ----------------------------------------- | ------------------------------------------- | ------------ | ---------------------------------------------- |
| Unconditional unique mapping rows         | Active lifecycle rows with explicit version | Phase 3      | Allows inactive history and safe reactivation. |
| Stored root health interpreted as current | Live read-only probe on retrieval           | D-01         | Prevents stale NAS status.                     |
| Unbounded directory listing               | Bounded deterministic cursor pages          | D-02         | Controls response and memory size.             |
| Generic exception strings                 | Stable allowlisted error envelope           | D-04/D-12    | Prevents path and SQL leakage.                 |
| Mapping write only                        | Separate test, preview, and save operations | D-05         | Makes administrator intent explicit.           |

**Deprecated/outdated:** The current `save_mapping` create-only method and unconditional unique constraints are foundation behavior, not the Phase 3 lifecycle contract. Preserve their validated core while replacing their public lifecycle semantics.

## Assumptions Log

| #   | Claim                                                                                                                  | Section | Risk if Wrong |
| --- | ---------------------------------------------------------------------------------------------------------------------- | ------- | ------------- |
|     | None. All implementation recommendations derive from locked context, repository code, or cited official documentation. |         |               |

## Resolved Planning Decisions

1. **Preview payload depth:** The Phase 3 preview is the bounded, non-mutating directory-level candidate summary defined in Pattern 3. It does not call scanner/catalog code and does not return candidate names or paths. Scanner-aware preview expansion remains Phase 5.
2. **Inactive row reactivation semantics:** Create never reuses an inactive row. Reactivation is an explicit mapping-ID operation with `expected_version`, complete active-conflict validation, version increment, and one atomic `activate` audit row.

## Environment Availability

| Dependency         | Required By             | Available | Version           | Fallback                                                                                                                    |
| ------------------ | ----------------------- | --------- | ----------------- | --------------------------------------------------------------------------------------------------------------------------- |
| SSH Linux checkout | All work                | Yes       | `/home/d1sk/romm` | None needed                                                                                                                 |
| Python host        | Inspection only         | Yes       | 3.10.12           | Run project code in `romm-dev` container with Python 3.13 environment                                                       |
| Docker             | Tests and migrations    | Yes       | 29.6.2            | None needed                                                                                                                 |
| `uv` on host       | Direct backend commands | No        | None              | Use existing `romm-dev` container commands                                                                                  |
| Trunk on host      | Formatting/lint         | No        | None              | Download the official launcher exactly as pinned by `trunk-io/trunk-action@75699af...`; `.trunk/trunk.yaml` pins CLI 1.25.0 |
| Node on host       | OpenAPI generation      | No        | None              | Use frontend container or project-supported Node environment                                                                |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** Host `uv`, Trunk, and Node are absent. Plans must use the established containers or explicitly provision project-supported tooling.

## Validation Architecture

### Test Framework

| Property           | Value                                                                                                                                                                                                |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Framework          | pytest 9.x, pytest-asyncio, pytest-xdist, Hypothesis                                                                                                                                                 |
| Config file        | `backend/pytest.ini`, root `pyproject.toml`, `backend/tests/conftest.py`                                                                                                                             |
| Quick run command  | `docker exec romm-dev sh -lc 'cd /app/backend && uv run pytest tests/endpoints/test_storage.py tests/handler/database/test_storage_handler.py tests/handler/filesystem/test_storage_resolver.py -q'` |
| Full suite command | `docker exec romm-dev sh -lc 'cd /app/backend && uv run pytest -vv'`                                                                                                                                 |

### Phase Requirements to Test Map

| Req ID  | Behavior                                           | Test Type                  | Automated Command                           | File Exists?                            |
| ------- | -------------------------------------------------- | -------------------------- | ------------------------------------------- | --------------------------------------- |
| MAP-01  | Existing contained directory can be assigned       | handler/API                | focused storage suite                       | Existing handler test, extend in Wave 0 |
| MAP-02  | One active mapping, inactive history allowed       | model/concurrency          | focused storage suite                       | Missing, Wave 0                         |
| MAP-03  | No source mutation on all lifecycle calls          | mutation tripwire          | focused storage suite                       | Partial, extend in Wave 0               |
| MAP-04  | Distinct siblings under one root succeed           | handler                    | focused storage suite                       | Partial, extend in Wave 0               |
| MAP-05  | Equal/ancestor/descendant overlaps return safe 409 | handler/API/concurrency    | focused storage suite                       | Partial handler, missing API            |
| MAP-06  | Missing mapping yields typed conflict              | handler/API                | focused storage suite                       | Missing, Wave 0                         |
| API-01  | Admin live root listing                            | endpoint                   | `pytest tests/endpoints/test_storage.py -q` | Missing, Wave 0                         |
| API-02  | Bounded contained browse and cursor validation     | resolver/endpoint/property | endpoint and resolver tests                 | Missing, Wave 0                         |
| API-03  | Read/create/update/test/preview/remove             | endpoint                   | endpoint storage tests                      | Missing, Wave 0                         |
| API-04  | 401/403 admin matrix                               | endpoint                   | endpoint storage tests                      | Missing, Wave 0                         |
| AUD-01  | Same-transaction complete lifecycle audit          | model/handler              | model and handler tests                     | Missing, Wave 0                         |
| AUD-02  | No path leakage                                    | endpoint adversarial       | endpoint storage tests                      | Missing, Wave 0                         |
| TEST-02 | Required API matrix                                | endpoint/integration       | full focused suite                          | Missing, Wave 0                         |

### Sampling Rate

- **Per task commit:** Run the directly affected storage test file.
- **Per wave merge:** Run the complete focused storage suite.
- **Phase gate:** Run full backend pytest; run the migration verifier for MariaDB, MySQL, and PostgreSQL lifecycle/preflight cycles; run handler concurrency on MariaDB and PostgreSQL with `--handler-tests --handler-test-repetitions 10`; download the official Trunk launcher exactly as `.github/workflows/trunk-check.yml`'s pinned `trunk-io/trunk-action@75699af9e26881e564e9d832ef7dc3af25ec031b` does (`curl -fsSL https://trunk.io/releases/trunk` into `mktemp -d`) and execute `trunk check --all`; then regenerate OpenAPI and run frontend typecheck.

### Wave 0 Gaps

- [ ] `backend/tests/endpoints/test_storage.py` for auth, typed responses, lifecycle, preview, cursor, and path leakage.
- [ ] Extend `backend/tests/handler/filesystem/test_storage_resolver.py` for bounded browse and cursor properties.
- [ ] Extend `backend/tests/handler/database/test_storage_handler.py` for version conflicts, lifecycle, active-only overlap, atomic audit, and concurrent writes.
- [ ] Extend `backend/tests/models/test_storage.py` for new columns, indexes, defaults, and audit immutability.
- [ ] Extend `backend/tools/verify_storage_migrations.py` and its tests for 0109 across MariaDB, MySQL, and PostgreSQL.
- [ ] Add OpenAPI assertions that forbidden fields such as `container_path` never appear in public storage/audit schemas.

## Security Domain

### Applicable ASVS Categories

| ASVS Category           | Applies             | Standard Control                                                                   |
| ----------------------- | ------------------- | ---------------------------------------------------------------------------------- |
| V2 Authentication       | Yes                 | Existing HybridAuthBackend and protected routes                                    |
| V3 Session Management   | Yes                 | Existing Redis session and CSRF middleware, unchanged                              |
| V4 Access Control       | Yes                 | `@protected_route` plus `assert_admin` on every route                              |
| V5 Input Validation     | Yes                 | Pydantic bounds plus existing path normalization and containment                   |
| V6 Cryptography         | No new cryptography | Cursor opacity does not confer authority; do not invent signing as an auth control |
| V7 Error Handling       | Yes                 | Stable allowlisted codes and bounded messages                                      |
| V8 Data Protection      | Yes                 | No container/NAS/unrelated paths in responses or audit                             |
| V12 Files and Resources | Yes                 | Existing resolver, symlink rejection, read-only policy boundary                    |

### Known Threat Patterns for FastAPI and Filesystem Administration

| Pattern                                  | STRIDE                             | Standard Mitigation                                                                            |
| ---------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------- |
| Path traversal and alternate path syntax | Tampering / Information Disclosure | Normalize lexical path, reject absolute/backslash/drive/dot forms, canonical containment check |
| Symlink escape or swap                   | Tampering / Information Disclosure | Reject symlink at root and each component; revalidate on every request                         |
| Enumeration by unauthenticated caller    | Information Disclosure             | Authentication and explicit admin assertion before root lookup or filesystem access            |
| Raw OS/DB error leak                     | Information Disclosure             | Allowlisted typed errors; never serialize raw exception text                                   |
| Stale administrative overwrite           | Tampering                          | Version precondition under row lock, HTTP 409, no retry                                        |
| Concurrent overlap race                  | Tampering                          | Deterministic locks and final in-transaction active overlap check                              |
| Audit repudiation                        | Repudiation                        | Same-transaction append-only actor and before/after snapshots                                  |
| Unbounded browse or cursor abuse         | Denial of Service                  | Hard page cap, cursor length cap, immediate child enumeration, bounded messages                |

## Sources

### Primary (HIGH confidence)

- `CLAUDE.md` and `.claude/skills/backend-development/SKILL.md`, repository rules and architecture.
- `backend/models/storage.py`, `backend/handler/database/storage_handler.py`, `backend/handler/filesystem/storage_resolver.py`, implemented storage foundation.
- `backend/alembic/versions/0108_immutable_storage_foundation.py`, current persisted schema.
- `backend/decorators/auth.py` and `backend/handler/auth/dependencies.py`, established auth and admin checks.
- `backend/main.py` and `backend/endpoints/responses/`, router and OpenAPI composition.
- `backend/tests/handler/database/test_storage_handler.py`, `backend/tests/handler/filesystem/test_storage_resolver.py`, `backend/tests/models/test_storage.py`, established adversarial and concurrency tests.
- `.github/workflows/trunk-check.yml`, `.trunk/trunk.yaml`, and pinned `trunk-io/trunk-action@75699af9e26881e564e9d832ef7dc3af25ec031b`, reproducible official Trunk launcher and CLI 1.25.0 gate.
- `.planning/phases/01-immutable-storage-foundation/01-VERIFICATION.md` and `.planning/phases/02-read-only-policy-boundary/02-VERIFICATION.md`, verified upstream foundations.
- https://fastapi.tiangolo.com/tutorial/handling-errors/, official typed HTTP error behavior.
- https://docs.pydantic.dev/latest/concepts/models/, official model validation behavior.
- https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html, official SQLAlchemy 2 selection and locking patterns.
- https://alembic.sqlalchemy.org/en/latest/ops.html, official Alembic operations reference.

### Secondary (MEDIUM confidence)

- None. External ecosystem discovery was unnecessary because the phase uses the locked repository stack.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, versions and usage verified in `pyproject.toml` and source.
- Architecture: HIGH, based on locked context and existing Phase 1/2 implementation.
- Pitfalls: HIGH, derived from current constraints, tests, and multi-dialect support requirements.

**Research date:** 2026-08-10
**Valid until:** 2026-09-09
