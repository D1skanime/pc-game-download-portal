# Phase 5: Preview and Read-path Cutover - Research

**Researched:** 2026-08-11
**Domain:** Mapping-bound filesystem discovery and immutable content delivery
**Confidence:** HIGH for repository architecture and locked behavior, MEDIUM for exact upstream Phase 3 interfaces because that phase artifact and implementation are absent

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

### Bounded Preview

- **D-01:** Bound every preview by both elapsed time and number of inspected entries. Stop when either budget is exhausted.
- **D-02:** Report only observed file count, directory count, and aggregate observed size. Never extrapolate totals from a partial traversal.
- **D-03:** When a budget is reached, label observed values as safe lower bounds, such as "at least 420 files and 38 GB observed," and return `partial` rather than implying completeness.
- **D-04:** An unreadable individual entry does not abort the preview. Continue within the remaining budget, return `partial`, and summarize a bounded set of problem categories without exposing technical paths.
- **D-05:** Preserve the most recent preview result with its timestamp. Starting another preview requires an explicit action; while it runs, keep the previous result visible and mark it stale.

### Scan Trigger Consistency

- **D-06:** Manual, scheduled, and watcher-triggered scans use the same mapping resolution, safety checks, scan pipeline, and persistence behavior. Only trigger metadata, priority, and scan scope may differ.
- **D-07:** Watchers accelerate discovery but do not guarantee completeness. Scheduled and manual scans remain authoritative, especially for NAS-backed mappings.
- **D-08:** Debounce and coalesce watcher events per mapping. While a scan is active, retain at most one pending follow-up scan for newly observed events.
- **D-09:** If the active mapping is unreachable at scan start, fail visibly and leave the existing catalog unchanged. Never interpret an unreachable mapping as an empty archive. A later scheduled or manual scan may try again.

### Queued Mapping Identity

- **D-10:** Every queued read job captures the logical mapping ID and its immutable revision at enqueue time. It must not capture or rely on a freely reusable absolute path.
- **D-11:** Validate the expected mapping revision before the first filesystem access. Long-running work also validates at safe processing boundaries, without requiring a database lookup before every individual file read.
- **D-12:** A removed, disabled, or replaced mapping makes the queued job stale. Fail immediately with a stable machine-readable error and bounded mapping ID, expected revision, and state details. Never redirect the job to the current revision.
- **D-13:** Retrying stale work creates a new job against the currently confirmed mapping revision. Preserve the original job, identity, and failure history.

### Content-read Integrity and Failure Behavior

- **D-14:** Use stable error classes across hashing, streaming, browser play, downloads, workers, and redirects. At minimum distinguish stale mapping, unreachable storage, missing content, and denied access. Translate the same domain errors appropriately for HTTP, job, and UI channels.
- **D-15:** Never expose absolute host paths, internal container paths, or raw filesystem errors in public responses.
- **D-16:** If a source changes, is replaced, or becomes unreachable during a stream or download, abort the transfer. Never reopen and concatenate bytes from different source versions. A retry is a new explicit request.
- **D-17:** Immediately before producing a file handle, response, or internal web-server redirect, resolve and authorize the expected mapping revision for the specific operation.
- **D-18:** Before a multi-file download begins, quickly preflight every required source file for mapping identity, revision, safe resolution, existence, regular-file type, readability, and download authorization.
- **D-19:** Download preflight is metadata and access validation, not a full content read or mandatory rehash. A single ISO needs one preflight; a game made of 100 required RAR parts needs 100 preflights.
- **D-20:** If any required source fails preflight, reject the complete download before output starts. Do not silently produce a partial game archive.

### Agent's Discretion

Exact preview time and entry limits, stale-result retention duration, debounce windows, scan priorities, safe-boundary frequency, error-code spelling, bounded diagnostic counts, and internal module organization are left to research and planning, provided they preserve D-01 through D-20.

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within the Phase 5 boundary.
</user_constraints>

<phase_requirements>

## Phase Requirements

| ID                    | Description                                                                                                                        | Research Support                                                                                                                                                                                                |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SCAN-01               | Scanner jobs resolve a platform through its active storage mapping instead of deriving `library/roms/<platform>`.                  | Introduce one mapping-bound scan command and source gateway used by all triggers. `[VERIFIED: .roadmap-staging/REQUIREMENTS.md; backend/endpoints/sockets/scan.py; backend/handler/filesystem/roms_handler.py]` |
| SCAN-02               | The scanner only reads source metadata and bytes and persists discoveries to RomM-owned database and storage locations.            | Separate operation-bound source handles from database, resource, asset, and cache destinations. `[VERIFIED: .roadmap-staging/REQUIREMENTS.md; 02-CONTEXT.md D-05 through D-08]`                                 |
| SCAN-03               | Watcher events resolve safely through storage mappings and cannot escape or mutate an external root.                               | Replace global-root string splitting with per-mapping event normalization, debounce, and one-pending-follow-up state. `[VERIFIED: .roadmap-staging/REQUIREMENTS.md; backend/watcher.py]`                        |
| SCAN-04               | An administrator can preview reachability, readability, non-writability, bounded counts, and observed size without catalog writes. | Add a preview application service and typed result persisted outside catalog records. `[VERIFIED: .roadmap-staging/REQUIREMENTS.md; 05-CONTEXT.md D-01 through D-05]`                                           |
| SCAN-05               | Large-directory preview is bounded or asynchronous and communicates partial or pending results clearly.                            | Enqueue preview with dual budgets and retain the prior timestamped result while pending. `[VERIFIED: .roadmap-staging/REQUIREMENTS.md; 04-CONTEXT.md D-05 and D-15]`                                            |
| SCAN-06               | Queued scan work retains or validates mapping identity so a concurrent mapping change cannot redirect it silently.                 | Queue mapping ID plus immutable revision, validate at start and safe boundaries, and preserve stale failure history. `[VERIFIED: .roadmap-staging/REQUIREMENTS.md; 05-CONTEXT.md D-10 through D-13]`            |
| </phase_requirements> |

## Summary

Plan this phase as a boundary-first cutover, not as a collection of endpoint patches. The current scanner, watcher, hashing, streaming, browser-stream broker, direct downloads, ZIP cache, mod_zip response, and Nginx redirect paths repeatedly reconstruct absolute source locations from `LIBRARY_BASE_PATH` plus platform slugs or persisted `full_path` strings. The safest task order is: define mapping identity and common domain errors, define mapping-bound scan/read commands, implement preview and trigger convergence, then migrate every byte consumer and finally delete or gate legacy fixed-layout reads. `[VERIFIED: backend/handler/filesystem/roms_handler.py; backend/endpoints/streaming.py; backend/endpoints/roms/files.py; backend/endpoints/roms/__init__.py; backend/utils/zip_cache.py; backend/watcher.py]`

The essential invariant is that persisted catalog paths remain logical paths relative to the platform mapping. They must not become durable absolute paths or capabilities. Each operation resolves the logical path through the expected mapping revision immediately before access and receives only an operation-bound handle. Long-running scans and hashes revalidate at coarse safe boundaries, while response and redirect creation revalidates immediately before handoff. `[VERIFIED: 02-CONTEXT.md D-13 and D-14; 05-CONTEXT.md D-10 through D-18]`

Phase 3 is a hard integration dependency, but no Phase 3 directory or implementation exists in this checkout. The planner must begin with a contract-integration checkpoint that names the actual mapping repository, revision type, lifecycle states, resolver, and health API produced by Phase 3. Do not invent a competing storage model in Phase 5. `[VERIFIED: .planning/ROADMAP.md; repository directory inventory on 2026-08-11]`

**Primary recommendation:** Implement a single `MappingReadContext(mapping_id, expected_revision)` application contract that issues operation-specific source handles and is consumed by preview, the unified scan command, hashing, downloads, play, workers, and redirect adapters. `[VERIFIED: 02-CONTEXT.md D-13 and D-14; 05-CONTEXT.md D-06, D-10, D-17]`

## Architectural Responsibility Map

| Capability                                     | Primary Tier  | Secondary Tier           | Rationale                                                                                                                                       |
| ---------------------------------------------- | ------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Preview orchestration and result contract      | API / Backend | Database / Storage       | Admin API starts work; RomM-owned persistence retains prior timestamped results. `[VERIFIED: D-05]`                                             |
| Bounded directory traversal                    | API / Backend | Database / Storage       | The filesystem gateway owns safe listing/stat operations; no catalog mutation occurs. `[VERIFIED: D-01 through D-04]`                           |
| Manual, scheduled, watcher scan command        | API / Backend | Database / Storage       | All triggers converge before filesystem and catalog work. `[VERIFIED: D-06]`                                                                    |
| Watch event normalization and coalescing       | API / Backend | External mounted storage | Events are hints scoped to mappings; authoritative scans reconcile state. `[VERIFIED: D-07 and D-08]`                                           |
| Mapping revision validation                    | API / Backend | Database / Storage       | The backend loads trusted mapping state and fails stale work before access. `[VERIFIED: D-10 through D-12]`                                     |
| Hashing and archive reads                      | API / Backend | External mounted storage | Hash code consumes operation-bound handles; results persist in RomM-owned DB. `[VERIFIED: SCAN-02; backend/handler/filesystem/roms_handler.py]` |
| Direct download and browser play authorization | API / Backend | CDN / Static             | Backend authorizes and resolves; Starlette or Nginx transfers bytes. `[VERIFIED: backend/endpoints/roms/files.py; backend/utils/nginx.py]`      |
| ZIP generation/cache                           | API / Backend | Database / Storage       | Sources are preflighted reads; generated ZIPs stay under `ZIP_CACHE_PATH`. `[VERIFIED: backend/utils/zip_cache.py; D-18 through D-20]`          |

## Project Constraints (from AGENTS.md and CLAUDE.md)

- Read and follow `CLAUDE.md`; backend work follows endpoint to handler to database/filesystem layering. `[VERIFIED: AGENTS.md; CLAUDE.md]`
- Keep endpoints thin, use custom domain exceptions, use managed database sessions, and place tests beside new logic under the mirrored backend test layout. `[VERIFIED: .claude/skills/backend-development/SKILL.md]`
- Backend response or route changes require generated frontend types and frontend typechecking during implementation, even though Phase 5 must not refactor frozen v1. `[VERIFIED: CLAUDE.md]`
- New logic and endpoints require tests; linting uses `trunk fmt && trunk check`; never bypass hooks. `[VERIFIED: CLAUDE.md]`
- All text is English, no em-dashes, no secrets, and comments explain only non-obvious current behavior. `[VERIFIED: CLAUDE.md]`
- Any eventual PR must disclose AI assistance, target `master`, use the PR template, and link the issue. `[VERIFIED: CLAUDE.md]`

## Standard Stack

### Core

| Library    | Version      | Purpose                                            | Why Standard                                                                                                                                                   |
| ---------- | ------------ | -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python     | `>=3.13`     | Traversal, typed domain layer, async orchestration | Existing backend runtime. `[VERIFIED: pyproject.toml]`                                                                                                         |
| FastAPI    | 0.134.x      | Admin preview/read API and error translation       | Existing backend API framework. `[VERIFIED: pyproject.toml; uv.lock fastapi 0.134.0]`                                                                          |
| Starlette  | 1.0.1        | File responses and response adapters               | Existing direct delivery primitive. `[VERIFIED: pyproject.toml; uv.lock]`                                                                                      |
| RQ         | 2.9.0 locked | Mapping-bound scan and preview jobs                | Existing queue, result retention, scheduled/manual worker infrastructure. `[VERIFIED: uv.lock; backend/tasks/]`                                                |
| watchfiles | 1.1.0 locked | Filesystem change hints                            | Existing watcher dependency supports grouping changes with `debounce` and `step`. `[VERIFIED: uv.lock]` `[CITED: https://watchfiles.helpmanual.io/api/watch/]` |
| pytest     | 9.0.3 locked | Unit and integration validation                    | Existing backend test runner. `[VERIFIED: uv.lock]`                                                                                                            |

### Supporting

| Library                                 | Version            | Purpose                              | When to Use                                                                                                                                                            |
| --------------------------------------- | ------------------ | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python `os.scandir`                     | stdlib 3.13        | Bounded iterative preview            | Use for entry-at-a-time counting and metadata, with explicit iterator closure and caught `OSError`. `[CITED: https://docs.python.org/3.13/library/os.html#os.scandir]` |
| Existing filesystem policy/capabilities | Phase 2 contract   | Operation-specific safe access       | Use for every external `LIST`, `STAT`, `SCAN`, `HASH`, `STREAM`, and `DOWNLOAD`. `[VERIFIED: 02-CONTEXT.md D-01 through D-14]`                                         |
| Existing Nginx adapters                 | repository utility | Large files, Range requests, mod_zip | Retain as delivery adapters after mapping preflight, never as authorization boundaries. `[VERIFIED: backend/utils/nginx.py]`                                           |

No new package is required. Use the repository stack and Phase 1 through Phase 3 contracts. `[VERIFIED: repository dependency and architecture scan]`

## Architecture Patterns

### System Architecture Diagram

```text
Admin preview request ----> Preview service ----> MappingReadContext(LIST/STAT)
                               |                         |
                               | budgets reached         +--> external mapping (read only)
                               +--> pending/partial/complete
                               +--> RomM-owned preview result store

Manual trigger ----+
Scheduler ----------+--> Mapping-bound ScanCommand(mapping_id, revision, scope, trigger)
Watcher hint -------+        | validate revision at start and safe boundaries
                             +--> MappingReadContext(SCAN/HASH) --> external bytes
                             +--> DB/resources/assets/cache (RomM-owned writes only)

HTTP/play/worker request --> authorize catalog object --> expected mapping identity
                             --> preflight/MappingReadContext(operation)
                                  | failure: stable bounded domain error
                                  +--> one open handle OR authorized redirect
                                         +--> Starlette / broker / Nginx / mod_zip
```

### Recommended Project Structure

```text
backend/
├── exceptions/storage_read.py          # stable domain error taxonomy
├── handler/storage/read_context.py     # mapping revision validation and operation handles
├── handler/storage/preview.py          # dual-budget traversal and result persistence
├── handler/scan_command.py             # common trigger-neutral command
├── endpoints/storage/                  # thin preview API and schemas
├── tasks/manual/ and scheduled/        # enqueue identity-bearing commands
└── tests/
    ├── handler/storage/
    ├── handler/test_scan_command.py
    ├── endpoints/storage/
    └── integration/test_mapped_read_paths.py
```

Names are recommendations subject to the actual Phase 3 module layout. `[ASSUMED]`

### Pattern 1: Identity-bearing command

```python
@dataclass(frozen=True, slots=True)
class MappingJobIdentity:
    mapping_id: int
    expected_revision: str

@dataclass(frozen=True, slots=True)
class ScanCommand:
    identity: MappingJobIdentity
    trigger: ScanTrigger
    scope: ScanScope
    scan_type: ScanType
```

Serialize only bounded logical identity and options into RQ. At execution, load exactly that mapping revision and reject removed, disabled, or replaced state. RQ supports explicit timeouts and result/failure retention, which should preserve stale failure history instead of transparently retrying against a new mapping. `[VERIFIED: D-10 through D-13]` `[CITED: https://python-rq.org/docs/]`

### Pattern 2: Dual-budget iterative preview

```python
deadline = monotonic() + limits.max_seconds
stack = [mapping_root_handle]
while stack and observed_entries < limits.max_entries and monotonic() < deadline:
    directory = stack.pop()
    for entry in directory.scandir():
        observed_entries += 1
        # Count only successfully observed metadata.
        # Catch and classify individual OSError values without retaining paths.
```

Check both budgets at the outer and inner loop so a single huge directory cannot overrun the entry limit. Do not follow symlinks, do not sort the entire tree, and do not retain `DirEntry` values after traversal because their metadata may become stale. `[VERIFIED: D-01 through D-04; Phase 1 symlink contract]` `[CITED: https://docs.python.org/3.13/library/os.html#os.DirEntry]`

### Pattern 3: Preflight then single-source handoff

Resolve each logical required file using the expected revision and `DOWNLOAD` or `STREAM`, validate containment, regular-file type, readability, and caller authorization, then either keep the issued handle for application streaming or convert the already-authorized target into an Nginx internal location. Never validate one path and later reconstruct another from `file.full_path`. `[VERIFIED: D-17 through D-20; backend/endpoints/roms/files.py currently reconstructs `/library/{full_path}`]`

### Pattern 4: One pending watcher follow-up per mapping

Key debounce and active/pending state by mapping ID, not platform slug or global path. When events arrive during an active scan, merge their scope into one pending command carrying the revision observed at enqueue time. After the active scan ends, enqueue that single follow-up if still relevant. Scheduled/manual scans remain the reconciliation source. `[VERIFIED: D-07 and D-08; backend/watcher.py currently schedules per fs_slug]`

### Anti-Patterns to Avoid

- **Absolute path in queue args or job metadata:** it bypasses revision semantics and can silently redirect after replacement. `[VERIFIED: D-10 through D-12]`
- **Resolving only at route entry:** a later `FileResponse`, broker call, ZIP build, or Nginx redirect can use stale state. Resolve immediately before handoff. `[VERIFIED: D-17]`
- **One preflight for a multi-file title:** every required file is a separate possible failure and must pass before output starts. `[VERIFIED: D-18 through D-20]`
- **Watcher equals truth:** NAS and polling behavior can miss or coalesce events; scheduled/manual scans are authoritative by decision. `[VERIFIED: D-07]`
- **Missing mapping equals empty tree:** current missing-file reconciliation can mark catalog records absent; unreachable mapping must fail before any catalog mutation. `[VERIFIED: D-09; backend/handler/scan_handler.py]`
- **Preview reuses full scanner:** scanning performs metadata/database work and can create records, violating preview isolation. `[VERIFIED: SCAN-04; backend/handler/scan_handler.py]`

## Don't Hand-Roll

| Problem                     | Don't Build                                               | Use Instead                                                       | Why                                                                                                                                                                                |
| --------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| External path containment   | String-prefix or `Path.resolve()` checks at each consumer | Phase 1 resolver plus Phase 2 operation handles                   | Existing `validate_path` and `/library/{full_path}` constructions are not mapping revision contracts. `[VERIFIED: Phase 1/2 contexts; backend/handler/filesystem/base_handler.py]` |
| Queue lifecycle             | Custom threads or in-memory job history                   | Existing RQ queues, scheduler, job meta, and failure retention    | Workers and scheduled/manual execution already use RQ. `[VERIFIED: backend/tasks/; backend/handler/redis_handler.py]`                                                              |
| File transfer               | Python Range parser or custom proxy                       | Existing Starlette and Nginx/mod_zip adapters after authorization | Production paths already delegate Range and archive delivery. `[VERIFIED: backend/utils/nginx.py; backend/endpoints/roms/__init__.py]`                                             |
| Watch aggregation           | New watcher daemon                                        | Existing watchfiles input plus mapping-keyed coalescer            | watchfiles already groups events and exposes debounce controls. `[VERIFIED: pyproject.toml]` `[CITED: https://watchfiles.helpmanual.io/api/watch/]`                                |
| Error responses per channel | Ad hoc strings from caught `OSError`                      | Shared domain exceptions plus HTTP/job/socket translators         | Locked stable error classes and path redaction apply everywhere. `[VERIFIED: D-14 and D-15]`                                                                                       |

## Common Pitfalls

### Pitfall 1: Catalog corruption on transient storage loss

**What goes wrong:** an unreachable mapping is treated as no files, then existing games are marked missing. **How to avoid:** resolve and health-check the expected mapping before starting a scan transaction or any missing-item reconciliation; abort visibly without catalog mutation. **Warning sign:** `mark_missing_*` executes after an empty filesystem list caused by an I/O error. `[VERIFIED: D-09; backend/handler/scan_handler.py]`

### Pitfall 2: TOCTOU between preflight and transfer

**What goes wrong:** source replacement after metadata validation can mix or substitute bytes. **How to avoid:** use a single opened handle where the application transfers bytes; for Nginx handoff, re-resolve immediately before redirect and test production races explicitly. If the platform contract cannot bind the same object across Nginx handoff, document the residual limitation for Phase 9 rather than claiming stronger integrity. `[VERIFIED: D-16 and D-17; .planning/STATE.md Phase 1 concern]`

### Pitfall 3: Unbounded work inside one directory

**What goes wrong:** checking budgets only between directories lets a huge flat folder run indefinitely. **How to avoid:** increment and check per inspected entry and check monotonic time within the inner loop. `[VERIFIED: D-01]`

### Pitfall 4: Preview numbers imply completeness

**What goes wrong:** UI/API calls observed size an estimate or extrapolates. **How to avoid:** schema should carry `status`, observed counters, budget reason, timestamp, and bounded problem summary; copy derives "at least" from `partial`. `[VERIFIED: D-02 through D-05]`

### Pitfall 5: ZIP output begins before all sources are valid

**What goes wrong:** mod_zip or in-memory ZIP emits headers and early entries before a later part fails. **How to avoid:** materialize a bounded list of authorized source descriptors only after every required file passes preflight; then start output. `[VERIFIED: D-18 through D-20; backend/endpoints/roms/__init__.py]`

### Pitfall 6: Generated output accidentally targets external storage

**What goes wrong:** covers, persisted soundtrack art, gamelist exports, ZIPs, or temporary work write beside source content. **How to avoid:** explicitly authorize destination as RomM-owned, and disable or redirect scan-time local exporters whose configured destination is the external mapping. `[VERIFIED: 02-CONTEXT.md D-05 through D-08; backend/handler/scan_handler.py includes scan-time exports]`

### Pitfall 7: Browser play is missed

**What goes wrong:** direct downloads are cut over, but EmulatorJS/Ruffle URLs or streaming broker requests still use legacy `full_path`. **How to avoid:** inventory both file endpoints and broker/player URL issuance; require a grep gate for every `LIBRARY_BASE_PATH`, `/library/`, and source `full_path` construction in read consumers. `[VERIFIED: backend/endpoints/streaming.py; backend/endpoints/roms/]`

## Code Examples

### Stable domain error translation

```python
class MappingReadError(Exception):
    code: str

class StaleMappingError(MappingReadError):
    code = "stale_mapping"

class StorageUnreachableError(MappingReadError):
    code = "storage_unreachable"

class SourceContentMissingError(MappingReadError):
    code = "content_missing"

class StorageAccessDeniedError(MappingReadError):
    code = "access_denied"
```

Public detail should include only code, bounded mapping ID, expected revision, and safe state. Raw exceptions are logged through a redacting adapter, not returned by `scan:done_ko` or FastAPI. `[VERIFIED: D-12, D-14, D-15]`

### Preflight list before ZIP output

```python
authorized = []
for required_file in required_files:
    authorized.append(
        await read_context.preflight_regular_file(
            logical_path=required_file.logical_path,
            operation=StorageOperation.DOWNLOAD,
            principal=principal,
        )
    )
return build_download_response(authorized)
```

The response constructor must receive authorized descriptors or handles, never raw catalog paths. `[VERIFIED: D-17 through D-20]`

## State of the Art

| Old Approach                                            | Current Approach                                                | Impact                                                                                                   |
| ------------------------------------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Global `LIBRARY_BASE_PATH` plus fixed `roms/<platform>` | Trusted root plus active relative platform mapping              | Every consumer must resolve through mapping identity. `[VERIFIED: SCAN-01; backend filesystem handlers]` |
| Queue platform IDs/slugs                                | Queue mapping ID plus immutable revision and scope              | Mapping replacement becomes an explicit stale failure. `[VERIFIED: D-10 through D-13]`                   |
| Watcher splits paths around global base                 | Watch root and normalize events per mapping                     | No cross-mapping or escape-by-string parsing. `[VERIFIED: SCAN-03; backend/watcher.py]`                  |
| Route constructs `/library/{full_path}`                 | Authorize mapping revision immediately before internal redirect | Nginx remains a transport, not an authority. `[VERIFIED: D-17; backend/utils/nginx.py]`                  |
| ZIP builder opens `Path(LIBRARY_BASE_PATH) / full_path` | Preflight all inputs, then read via authorized descriptors      | Complete rejection precedes output. `[VERIFIED: D-18 through D-20; backend/utils/zip_cache.py]`          |

## Assumptions Log

| #   | Claim                                                                                                                                                | Section           | Risk if Wrong                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------------- |
| A1  | Recommended module and class names can fit the eventual Phase 3 package layout.                                                                      | Project Structure | Medium, planner must adapt names to the actual Phase 3 implementation.                         |
| A2  | Preview results should persist in a dedicated RomM-owned database record keyed by mapping, rather than Redis only.                                   | Architecture      | Medium, retention requirements may favor existing Phase 3 storage fields or Redis.             |
| A3  | A safe scan-boundary check after each platform and before missing-item reconciliation is sufficient in addition to checks before long per-ROM reads. | Architecture      | High, planner must refine boundaries based on Phase 3 revision API and scan transaction shape. |

## Open Questions (RESOLVED)

1. **Phase 3 contract dependency:** Phase 3 artifacts and runtime contracts are absent in this checkout. Phase 5 Plan 05-01 is therefore a blocking integration gate. It records the exact landed repository, revision, lifecycle, resolver, operation handle, health, and error identifiers. No later plan may run while any item is `BLOCKED`, and provisional module names in this research are conditional examples only. `[VERIFIED: repository inventory; ROADMAP Phase 5 depends on Phase 3]`

2. **Preview persistence:** Store the latest completed preview as durable RomM-owned database state associated with the mapping identity and timestamp. Redis/RQ stores only running-job coordination and failure history. Starting a new preview leaves the completed result intact and marks it stale until the new job commits a replacement result. If Phase 3 already owns a mapping status record, Plan 05-01 records its exact extension point; otherwise Phase 5 adds the dedicated persistence model and portable migration. `[RESOLVED per D-05]`

3. **Same-version delivery:** A path-only `X-Accel-Redirect` cannot bind Nginx's later open to the inode authorized by the application. External mapped sources therefore use application-controlled streaming from one already-authorized open descriptor for GET, HEAD, and Range. On read failure or identity invalidation, the response aborts and never reopens or appends. X-Accel remains allowed only for RomM-owned generated files or an immutable snapshot whose identity is fixed before response creation. Race tests replace a source after authorization and prove no mixed-version body. `[RESOLVED per D-16, D-17, and current backend/utils/nginx.py behavior]`

4. **Scanner export destinations:** The runtime owners are `backend/endpoints/sockets/scan.py`, `backend/utils/gamelist_exporter.py`, and `backend/utils/pegasus_exporter.py`; configuration is read by `backend/config/config_manager.py`. Both exporters currently support local file output. Phase 5 must require an explicitly RomM-owned destination capability for gamelist and Pegasus writes and reject any destination inside an external mapping before filesystem access. Source metadata reads remain mapping-bound. Tests enable both exports for manual, scheduled, and watcher-trigger metadata and compare source manifests before and after. `[RESOLVED from repository inspection]`

## Environment Availability

| Dependency                           | Required By                      | Available                                         | Version                                                  | Fallback                                                                                                    |
| ------------------------------------ | -------------------------------- | ------------------------------------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Python/uv project environment        | Backend tests and implementation | ✓                                                 | Python constraint 3.13+, locked environment in `uv.lock` | Docker development environment. `[VERIFIED: pyproject.toml; CLAUDE.md]`                                     |
| Redis/RQ                             | Preview and scans                | Configured dependency, live service not probed    | RQ 2.9.0 locked                                          | Development Valkey service in compose. `[VERIFIED: uv.lock; docker-compose.yml]`                            |
| watchfiles                           | Watch hints                      | ✓ dependency                                      | 1.1.0 locked                                             | Scheduled/manual scans remain authoritative. `[VERIFIED: uv.lock; D-07]`                                    |
| Nginx with internal redirect/mod_zip | Production download paths        | Configured in repository, live service not probed | repository image configuration                           | Starlette response path for test/dev where already supported. `[VERIFIED: backend/utils/nginx.py; docker/]` |

No missing dependency blocks planning. Phase 3 contracts, not a tool installation, are the integration prerequisite. `[VERIFIED: .planning/ROADMAP.md]`

## Validation Architecture

### Test Framework

| Property           | Value                                                                                   |
| ------------------ | --------------------------------------------------------------------------------------- |
| Framework          | pytest 9.0.3, pytest-asyncio 1.3.0 locked `[VERIFIED: uv.lock]`                         |
| Config file        | `pyproject.toml`                                                                        |
| Quick run command  | `cd backend; uv run pytest tests/handler/storage tests/handler/test_scan_command.py -x` |
| Full suite command | `cd backend; uv run pytest`                                                             |

### Phase Requirements to Test Map

| Req ID       | Behavior                                                                          | Test Type               | Automated Command                                                                      | File Exists?                                                                                                   |
| ------------ | --------------------------------------------------------------------------------- | ----------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| SCAN-01      | Manual/scheduled/watcher scans resolve only their active mapping                  | integration             | `uv run pytest tests/integration/test_mapped_scan.py -x`                               | ❌ Wave 0                                                                                                      |
| SCAN-02      | Scan reads source and writes only DB/RomM-owned destinations                      | adversarial integration | `uv run pytest tests/integration/test_scan_source_immutability.py -x`                  | ❌ Wave 0                                                                                                      |
| SCAN-03      | Watch events are contained, debounced, and coalesced per mapping                  | unit/integration        | `uv run pytest tests/test_watcher.py -x`                                               | Existing watcher coverage needs extension `[VERIFIED: backend/tests/test_sync_watcher.py; backend/watcher.py]` |
| SCAN-04      | Preview reports health and observed counts without catalog writes                 | endpoint/integration    | `uv run pytest tests/endpoints/storage/test_mapping_preview.py -x`                     | ❌ Wave 0                                                                                                      |
| SCAN-05      | Time/entry budgets produce pending/partial/complete and retain stale prior result | unit/endpoint           | `uv run pytest tests/handler/storage/test_preview.py -x`                               | ❌ Wave 0                                                                                                      |
| SCAN-06      | Changed/removed/disabled revision makes queued work stale                         | queue integration       | `uv run pytest tests/tasks/test_mapping_revision_jobs.py -x`                           | ❌ Wave 0                                                                                                      |
| D-14 to D-20 | Read errors are stable/redacted; all files preflight before output                | endpoint/integration    | `uv run pytest tests/endpoints/roms/test_files.py tests/endpoints/roms/test_rom.py -x` | Existing files need extension `[VERIFIED: backend/tests/endpoints/roms/]`                                      |

### Required Adversarial Matrix

- Mapping replacement before job start, during scan, before hash open, before response creation, and before Nginx redirect. `[VERIFIED: D-10 through D-17]`
- Removed, disabled, unreachable, missing file, permission denial, symlink, non-regular file, and raw `OSError` redaction. `[VERIFIED: D-12 through D-15; Phase 1/2 context]`
- Flat huge directory and deep tree, budget reached by time and by entries, unreadable entries, Unicode names, zero-byte files, and no catalog writes. `[VERIFIED: D-01 through D-05]`
- ISO, 100-part title, one failed final part, mutation between preflight and transfer, Range/HEAD, disconnect, and Nginx redirect parity. `[VERIFIED: D-16 through D-20; .planning/codebase/CONCERNS.md]`
- Watch burst while idle, burst while active, two mappings concurrently, NAS-style missed events, and scheduled reconciliation. `[VERIFIED: D-07 and D-08]`

### Sampling Rate

- **Per task commit:** targeted test file with `-x`
- **Per wave merge:** mapped scan, preview, watcher, and ROM endpoint suites
- **Phase gate:** full backend suite plus `trunk check`; production Nginx and real NAS evidence remains Phase 9. `[VERIFIED: CLAUDE.md; .planning/ROADMAP.md]`

### Wave 0 Gaps

- [ ] Add shared external read-only mapping fixtures and revision replacement helpers.
- [ ] Add a source-tree before/after manifest fixture covering name, type, size, and digest.
- [ ] Add fake operation handles that fail if accessed after revision invalidation.
- [ ] Add RQ/fakeredis helpers that preserve and inspect stale failure metadata.
- [ ] Add a response-capture fixture proving no headers/body are emitted before multi-file preflight completes.

## Security Domain

### Applicable ASVS Categories

| ASVS Category         | Applies | Standard Control                                                                                                                                                         |
| --------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| V2 Authentication     | yes     | Existing protected routes and socket server-side session checks. `[VERIFIED: backend/decorators/auth.py; backend/endpoints/sockets/scan.py]`                             |
| V3 Session Management | yes     | Existing Redis-backed session/auth infrastructure, unchanged by this phase. `[VERIFIED: CLAUDE.md; .planning/codebase/INTEGRATIONS.md]`                                  |
| V4 Access Control     | yes     | Existing scopes plus operation-specific Phase 2 capability and per-file authorization. `[VERIFIED: .claude/skills/backend-development/SKILL.md; 02-CONTEXT.md]`          |
| V5 Input Validation   | yes     | Typed IDs/options, Phase 1 relative-path resolver, regular-file checks, no caller absolute paths. `[VERIFIED: Phase 1/2 contexts; D-18]`                                 |
| V6 Cryptography       | limited | Existing hash implementations identify content but are not an authorization or race-prevention mechanism. `[VERIFIED: backend/handler/filesystem/roms_handler.py; D-19]` |

### Known Threat Patterns

| Pattern                            | STRIDE                 | Standard Mitigation                                                                                     |
| ---------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------- |
| Mapping swap redirects queued work | Tampering              | Immutable expected revision, fail stale, explicit new retry. `[VERIFIED: D-10 through D-13]`            |
| Path traversal/symlink escape      | Elevation/Disclosure   | Phase 1 resolver and Phase 2 operation handle at every access. `[VERIFIED: Phase 1/2 contexts]`         |
| Public raw filesystem error        | Information Disclosure | Stable bounded error mapper with no paths or raw exception text. `[VERIFIED: D-14 and D-15]`            |
| Mixed-version stream               | Tampering              | One open source per response, abort on change/error, never reopen-and-append. `[VERIFIED: D-16]`        |
| Partial multi-file archive         | Tampering/Repudiation  | Authorize and preflight every required source before headers or output. `[VERIFIED: D-18 through D-20]` |
| Watch event flood                  | Denial of Service      | Per-mapping debounce, coalescing, and at most one pending follow-up. `[VERIFIED: D-08]`                 |

## Sources

### Primary (HIGH confidence)

- `05-CONTEXT.md`, `02-CONTEXT.md`, and `04-CONTEXT.md` - locked product, security, preview, and UI-state decisions.
- `.roadmap-staging/REQUIREMENTS.md` and `.planning/ROADMAP.md` - requirement text and phase contract.
- `CLAUDE.md` and `.claude/skills/backend-development/SKILL.md` - repository and backend rules.
- `backend/handler/scan_handler.py`, `backend/endpoints/sockets/scan.py`, `backend/watcher.py` - discovery and trigger paths.
- `backend/handler/filesystem/`, `backend/endpoints/roms/`, `backend/endpoints/streaming.py`, `backend/utils/nginx.py`, `backend/utils/zip_cache.py` - current read consumers and delivery adapters.
- [Python 3.13 os documentation](https://docs.python.org/3.13/library/os.html#os.scandir) - traversal and `DirEntry` behavior.
- [RQ documentation](https://python-rq.org/docs/) - queue timeout, retention, and retry controls.
- [watchfiles watch API](https://watchfiles.helpmanual.io/api/watch/) - debounce and event grouping behavior.

### Secondary (MEDIUM confidence)

- `.planning/codebase/ARCHITECTURE.md`, `CONCERNS.md`, and `INTEGRATIONS.md` - repository mapping and risk inventory verified against current code where cited.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, versions verified from `uv.lock` and existing repository use.
- Architecture: HIGH for current paths and locked pattern, MEDIUM for names until Phase 3 lands.
- Pitfalls: HIGH, derived from locked decisions and concrete current consumers.

**Research date:** 2026-08-11
**Valid until:** 2026-09-10, or immediately after Phase 3 changes its mapping/revision contract
