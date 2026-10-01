# Phase 22: Bulk Automation for PC Game and DLC Matching - Research

**Researched:** 2026-10-01
**Domain:** Scheduled read-only PC discovery, metadata automation, and administrator exception review
**Confidence:** HIGH

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** A correctly named main-game folder may be matched and applied without confirmation when the Steam result is unambiguous. The enrichment fetches Steam text, IGDB metadata, and available provider media through the existing non-destructive paths.
- **D-02:** No result or an ambiguous result is never applied automatically; it becomes a review-queue item.
- **D-03:** After a main game has a trusted Steam identity, its local DLC and expansion components may use a tolerant title comparison against the official related-item list, but only one plausible result may be applied.
- **D-04:** Missing, tied, or otherwise unsafe DLC relations remain pending review. Existing manual selections and protected provider data are never overwritten by a background run.
- **D-05:** The administration UI provides one centralized queue with the suggested candidate, cover, platform, and reason for confidence or failure.
- **D-06:** Operators can accept, search/correct, or skip an item, and can use multi-selection when applying the same safe decision to comparable queued items.
- **D-07:** New PC folders are discovered by a configurable periodic background scan, with a 15-minute production default and a development/UAT interval as low as 10 seconds, rather than a filesystem watcher. Newly discovered eligible games then enter the automatic matching flow.
- **D-08:** The UI exposes processing progress and outstanding review items. Background work never writes to, renames, moves, or deletes source-library content.

### Claude's Discretion

- Choose bounded confidence scoring, job persistence, retry behavior, and the smallest API/UI seams that reuse the existing scan, Steam, IGDB, component, and media reconciliation contracts.
- Define safe batch-action eligibility so each application is still traceable and cannot silently apply an ambiguous candidate.

### Deferred Ideas (OUT OF SCOPE)

None. Discussion stayed within phase scope.

## Summary

The repository already has the two foundations needed for this phase: a mapping-bound scheduled quick scan and guarded PC scan enrichment for Steam, IGDB, and provider media. Source access stays inside the immutable mapping capability, while persistence happens only in RomM-owned storage. [VERIFIED: codebase, `backend/tasks/scheduled/scan_library.py`, `backend/endpoints/sockets/scan.py`, `backend/handler/scan_handler.py`]

What is missing is durable automation state. `PcMetadataMatchHandler` deliberately returns review-only candidates, while existing automatic DLC code applies only one unambiguous IGDB or parent-listed Steam relation. There is no database-backed queue, retry policy, batch review contract, or centralized UI. [VERIFIED: codebase, `backend/handler/metadata/pc_match_handler.py`, `backend/handler/scan_handler.py`, repository search]

**Primary recommendation:** implement a dedicated, idempotent PC automation handler and durable queue rows, invoked after the existing mapped scheduled scan. Reuse the existing manual PC selection endpoints and `MatchRomDialog` for correction, and reuse the existing guarded metadata/media persistence paths rather than duplicating merge logic. [VERIFIED: codebase, `backend/endpoints/roms/pc_metadata.py`, `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`]

## Architectural Responsibility Map

| Capability                           | Primary Tier       | Secondary Tier     | Rationale                                                                                                                                                                                      |
| ------------------------------------ | ------------------ | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Periodic folder discovery            | API / Backend      | Database / Storage | RQ scheduled task invokes mapping-safe quick scans. [VERIFIED: codebase, `backend/tasks/scheduled/scan_library.py`]                                                                            |
| Main-game and DLC decision           | API / Backend      | External providers | Provider calls, identity checks, and persistence policy cannot be trusted to the browser. [VERIFIED: codebase, `backend/handler/metadata/pc_match_handler.py`]                                 |
| Pending review lifecycle             | Database / Storage | API / Backend      | A durable row is needed for retries, skip state, version checks, pagination, and traceability. [ASSUMED]                                                                                       |
| Queue, correction, and safe batch UI | Browser / Client   | API / Backend      | v2 renders state and sends explicit requests; server validates each target. [VERIFIED: codebase, `frontend/src/v2/views/Settings/Administration.vue`, `backend/endpoints/roms/pc_metadata.py`] |
| Progress and counts                  | Browser / Client   | API / Backend      | Existing task polling shows job state; queue needs a dedicated count/list contract. [VERIFIED: codebase, `frontend/src/v2/components/Settings/TasksSection.vue`, `backend/endpoints/tasks.py`] |

## Standard Stack

### Core

| Library / subsystem                   | Purpose                         | Why use it                                                                                                                                                           |
| ------------------------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RQ plus `rq-scheduler`                | Recurring background work       | Existing `PeriodicTask` startup, de-duplication, task metadata, and queue priority conventions. [VERIFIED: codebase, `backend/tasks/tasks.py`, `backend/startup.py`] |
| FastAPI, SQLAlchemy, Alembic          | Queue API, model, and migration | Repository-standard layered backend and portable persistence stack. [VERIFIED: codebase, `CLAUDE.md`, `.claude/skills/backend-development/SKILL.md`]                 |
| Vue 3, Pinia, v2 primitives, vue-i18n | Accessible review UI            | v2 is active UI and canonical shared APIs/stores/types must be reused. [VERIFIED: codebase, `CLAUDE.md`, `.claude/skills/frontend-v2-components/SKILL.md`]           |

### Supporting Existing Seams

| Component                       | Phase 22 use                                                                                                                                                                                                                                              |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ScanLibraryTask`               | Keep mapped scheduled quick scans, change production default to `*/15 * * * *` when enabled, and invoke PC automation only for eligible discovered records. [VERIFIED: codebase, `backend/tasks/scheduled/scan_library.py`, `backend/config/__init__.py`] |
| `PcMetadataMatchHandler`        | Add bounded decision methods, not direct persistence. Existing candidate collection and DLC validation remain the source of truth. [VERIFIED: codebase, `backend/handler/metadata/pc_match_handler.py`]                                                   |
| PC database application helpers | Reuse parent/component version-bound persistence after a safe decision. [VERIFIED: codebase, `backend/handler/database/roms_handler.py`, `backend/endpoints/roms/pc_metadata.py`]                                                                         |
| `MatchRomDialog`                | Open for queue correction instead of building a second matching workflow. [VERIFIED: codebase, `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`]                                                                                                   |
| Tasks API/store/section         | Reuse for periodic-job status; add a separate queue API for items and counts. [VERIFIED: codebase, `frontend/src/services/api/task.ts`, `frontend/src/stores/tasks.ts`]                                                                                   |

### Alternatives Considered

| Instead of                 | Could Use                         | Decision                                                                                                                                                                                       |
| -------------------------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Periodic scan              | Filesystem watcher                | Rejected by D-07. The repository has a watcher, but NAS/Docker reliability requires periodic discovery. [VERIFIED: codebase, `backend/watcher.py`, `22-CONTEXT.md`]                            |
| Durable queue              | Redis-only task metadata          | Rejected. Job metadata is transient task status and cannot safely represent per-item review, skip, correction, retry, and audit state. [ASSUMED]                                               |
| New manual matching screen | Existing dialog and selection API | Rejected because it duplicates provider search and guarded persistence. [VERIFIED: codebase, `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`, `backend/endpoints/roms/pc_metadata.py`] |

**Installation:** No external package is required. [VERIFIED: codebase]

## Package Legitimacy Audit

No new package is introduced, so the package legitimacy gate is not applicable. [VERIFIED: codebase]

## Architecture Patterns

### System Architecture Diagram

```text
Read-only external PC library
          |
          v
Periodic RQ scheduled rescan (configured interval)
          |
          v
Mapped scan capability and existing PC discovery
          |
          v
PC automation decision handler
  main: exactly one valid Steam identity
  DLC: exactly one valid parent-listed relation
          |
    +-----+------------------+
    |                        |
safe result              no result/tie/failure
    |                        |
    v                        v
existing guarded          durable pending queue row
metadata/media apply              |
    |                              v
RomM-owned DB/resources     protected v2 review queue
                                    |
                         accept | correct | skip | safe batch
```

The scheduled flow must retain `MappedScanCommand` and `MappingReadContext`. These authorize `StorageOperation.SCAN` before scan reads, then allow only RomM-owned persistence after the source boundary. [VERIFIED: codebase, `backend/endpoints/sockets/scan.py`]

### Recommended Project Structure

```text
backend/
├── alembic/versions/                 # portable review queue migration
├── models/                            # queue state and queue item model
├── handler/metadata/pc_automation.py # bounded decisions and orchestration
├── endpoints/roms/pc_automation.py   # thin protected queue routes
└── tasks/scheduled/scan_library.py    # scheduled scan configuration/invocation

frontend/src/
├── services/api/pcAutomation.ts       # typed queue API
├── stores/pcAutomation.ts             # paginated queue state
└── v2/components/Settings/            # review queue feature composite
```

Exact filenames are discretionary. Endpoints validate and serialize, handlers own business logic, models own state, and frontend work stays in v2. [VERIFIED: codebase, `.claude/skills/backend-development/SKILL.md`, `.claude/skills/frontend-v2-components/SKILL.md`]

### Pattern 1: Bounded decision before persistence

**What:** Transform provider data into `applied`, `pending`, `skipped`, or `retryable_failure`. The durable record contains target kind, parent ROM ID, nullable component ID, expected version/incarnation, normalized query, candidate/provider IDs, cover URL, reason, and decision fingerprint.

**When:** For a new eligible PC parent and unresolved DLC/expansion component only. Do not run on manual or protected state.

```python
# Source: persistence pattern in roms_handler.py
decision = await pc_automation.decide_parent(rom)
if decision.is_safe_single_match:
    applied = db_rom_handler.apply_pc_igdb_enrichment(
        rom.id, rom.updated_at, decision.patch
    )
    if applied is None:
        queue.record_stale_target(decision)
else:
    queue.upsert_pending(decision)
```

Reuse actual existing selection/application functions to preserve provenance and Phase 21 media reconciliation. [VERIFIED: codebase, `backend/endpoints/roms/pc_metadata.py`, `backend/handler/database/roms_handler.py`, `backend/handler/metadata/steam_merge.py`]

### Pattern 2: Fail closed, with cardinality separate from similarity

**What:** Main-game automation succeeds only if exactly one valid Steam candidate remains. DLC automation succeeds only if the candidate is in the parent's official Steam DLC list, Steam identifies it as DLC for that parent, and exactly one candidate passes the tolerant similarity filter.

**When:** Every automatic attempt, including a retry. Similarity can filter candidates but never resolve a tie.

The current DLC implementation uses `SequenceMatcher` with `STEAM_DLC_MIN_SIMILARITY = 0.9` and returns a candidate only where the validated list length is one. Preserve the cardinality rule even if title preprocessing improves. [VERIFIED: codebase, `backend/handler/metadata/pc_match_handler.py`]

### Pattern 3: Idempotent upsert and bounded retry

**What:** Use target kind plus parent ROM ID plus nullable component ID as the outstanding-row identity. Repeat scans update evidence and `last_seen_at`, not create duplicates. Store attempt fingerprint, last-attempt time, failure class, and bounded retry/backoff state.

**Why:** A 15-minute scan will rediscover the same pending entry; append-only rows would overwhelm a 1,000-game workflow. [ASSUMED]

### Pattern 4: Batch only one explicit proven-safe decision

**What:** The batch API gets queue IDs and one candidate fingerprint. It reloads every row, confirms pending status, same candidate identity and target category, rechecks each version, and applies each result independently for traceability.

**Why:** Browser selection cannot authorize a fuzzy or stale bulk change. The backend must reject mixed, tied, ambiguous, missing, or manually protected rows. [ASSUMED]

### Anti-Patterns to Avoid

- Applying the first Steam result. Existing matching is deliberately fail closed. [VERIFIED: codebase, `backend/handler/metadata/pc_match_handler.py`]
- Copying a bulk-only metadata merge. This risks overwriting manual fields or selected media. Reuse Phase 21 guarded merge/reconciliation. [VERIFIED: codebase, `21-CONTEXT.md`, `backend/handler/metadata/steam_merge.py`]
- Storing only query text for review. Candidate and target fingerprints are needed to detect stale actions. [ASSUMED]
- Implementing provider policy in a Vue component or endpoint. The repository puts business rules in handlers. [VERIFIED: codebase, `.claude/skills/backend-development/SKILL.md`]
- Using the filesystem watcher. D-07 chooses periodic scans. [VERIFIED: `22-CONTEXT.md`]

## Don't Hand-Roll

| Problem                  | Do not build                       | Use instead                                             | Why                                                                                                                                                                                                         |
| ------------------------ | ---------------------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scheduler                | Process-local timer/polling thread | Existing RQ `PeriodicTask`                              | Startup, de-duplication, priorities, and status patterns already exist. [VERIFIED: codebase, `backend/tasks/tasks.py`]                                                                                      |
| Steam/IGDB transport     | New direct HTTP client calls       | Existing provider handlers and `PcMetadataMatchHandler` | Existing code owns locale fallback, enabled checks, normalization, and failure isolation. [VERIFIED: codebase, `backend/handler/metadata/steam_handler.py`, `backend/handler/metadata/pc_match_handler.py`] |
| Source filesystem access | Raw path traversal                 | Mapping-bound scan command                              | Read-only authorization and containment are already enforced. [VERIFIED: codebase, `backend/endpoints/sockets/scan.py`]                                                                                     |
| Manual correction        | Second matching UI                 | `MatchRomDialog` and current PC metadata routes         | Existing review, filters, media selection, and persistence should stay canonical. [VERIFIED: codebase, `frontend/src/v2/components/Dialogs/MatchRomDialog.vue`]                                             |

## Common Pitfalls

### Pitfall 1: Current cron configuration cannot prove a 10-second UAT interval

**What goes wrong:** Production `*/15 * * * *` is compatible with the existing cron configuration, but the current rescan task exposes only a cron string. A six-field 10-second cron must not be assumed to work without a scheduler-specific integration test.

**How to avoid:** Keep production default `*/15 * * * *`. Add an explicit development-only interval override or direct UAT task invocation, with a test. [VERIFIED: codebase, `backend/config/__init__.py`, `backend/tasks/tasks.py`; [ASSUMED] for installed scheduler cron grammar]

### Pitfall 2: Scheduled scan currently omits Steam

**What goes wrong:** `ScanLibraryTask.source_mapping` currently selects existing providers but does not list `MetadataSource.STEAM`. Phase 21 Steam enrichment depends on the selected metadata source set.

**How to avoid:** Explicitly include enabled Steam in scheduled PC scan coverage and test it. [VERIFIED: codebase, `backend/tasks/scheduled/scan_library.py`, `backend/handler/scan_handler.py`]

### Pitfall 3: Repeated provider calls and duplicate queue rows

**What goes wrong:** Re-running scans every 15 minutes may repeatedly call providers for unchanged ambiguous/no-match records and create duplicate exceptions.

**How to avoid:** Upsert by target identity and retry only after bounded backoff or a target/configuration change. [ASSUMED]

### Pitfall 4: Parent/component target confusion

**What goes wrong:** Applying a base component candidate rather than the parent ROM can make metadata appear only in downloads rather than overview/details.

**How to avoid:** Main automation always targets the parent `Rom`; components are processed only after trusted parent identity. [VERIFIED: codebase, `backend/endpoints/roms/pc_metadata.py`, `backend/handler/scan_handler.py`]

### Pitfall 5: Stale review action overwrites later state

**What goes wrong:** A scan or manual operator action can change a ROM after queue display.

**How to avoid:** Every single and batch mutation carries expected row version/incarnation, reloads server-side, and marks stale rows pending rather than applying. Existing PC persistence already has version-bound application methods. [VERIFIED: codebase, `backend/handler/database/roms_handler.py`, `backend/endpoints/roms/pc_metadata.py`]

### Pitfall 6: Rendering all exceptions at once

**What goes wrong:** A 1,000-item queue would make cards, gamepad focus, and browser performance poor.

**How to avoid:** Server pagination with stable sort, v2 virtualization/load-more, URL query for filters/sort, and page-local selection. [VERIFIED: codebase, `.claude/skills/frontend-v2-patterns/SKILL.md`, `.claude/skills/frontend-v2-components/SKILL.md`]

## State of the Art

| Old approach                                            | Current approach                                                                    | Impact                                                                                                                                                                     |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Admin scans then manually matches every parent and DLC  | Phase 21 supplies guarded Steam/IGDB scan enrichment and manual candidate selection | Phase 22 can auto-apply only proven cases and centralize exceptions. [VERIFIED: codebase, `21-CONTEXT.md`, `backend/endpoints/roms/pc_metadata.py`]                        |
| Daily scheduled rescan at 03:00, no Steam in source map | Configurable periodic scan plus deliberate Steam selection                          | Phase 22 must update default/configuration and preserve explicit enablement. [VERIFIED: codebase, `backend/config/__init__.py`, `backend/tasks/scheduled/scan_library.py`] |

## Project Constraints (from AGENTS.md and CLAUDE.md)

- Work only in canonical `/home/d1sk/romm`, preserve unrelated dirty changes, and do not access Team4s, NAS, Docker Compose, or external source paths for this phase.
- Source-library access is read-only. Background work may scan/read but never write, rename, move, or delete source contents.
- Use endpoint-to-handler-to-model layering, protected routes, OpenAPI schemas as the frontend contract, and regenerate types after contract changes.
- New UI remains under v2, uses v2 primitives, strict TypeScript, accessibility/input conventions, `useSnackbar`, and vue-i18n.
- Add focused tests; support MariaDB, MySQL, and PostgreSQL migrations; run Trunk and never bypass hooks.
- All code, comments, artifacts, commits, and non-locale text use English. Do not commit secrets or use em dashes.

## Assumptions Log

| #   | Claim                                                                                       | Section   | Risk if Wrong                                         |
| --- | ------------------------------------------------------------------------------------------- | --------- | ----------------------------------------------------- |
| A1  | Durable queue rows are preferable to RQ metadata.                                           | Summary   | Existing persistence seam might be more suitable.     |
| A2  | Installed scheduler seconds support is unproven.                                            | Pitfall 1 | UAT interval design could differ.                     |
| A3  | Target identity upsert plus retry/backoff is needed.                                        | Pattern 3 | Queue retention behavior may need product refinement. |
| A4  | Batch requests should require identical candidate fingerprint and per-target version check. | Pattern 4 | Batch UX may require a stricter grouping contract.    |
| A5  | Exact queue authorization scope needs comparison against existing PC metadata routes.       | Security  | Wrong scope harms access consistency.                 |

## Open Questions

1. **How should the 10-second UAT interval be represented?**
   - Known: production uses a configurable periodic scan; current rescan configuration is cron-based. [VERIFIED: codebase, `backend/config/__init__.py`, `22-CONTEXT.md`]
   - Recommendation: plan a development-only interval override or direct task invocation with an automated scheduler test, while keeping production at `*/15 * * * *`.
2. **Which authorization scope owns queue review?**
   - Known: task status uses `tasks.run`; current manual PC metadata routes have their own protection. [VERIFIED: codebase, `backend/endpoints/tasks.py`, `backend/endpoints/roms/pc_metadata.py`]
   - Recommendation: reuse the narrowest existing manual PC metadata write scope and test access denials.
3. **What does skip mean after a target changes?**
   - Recommendation: make it terminal for the same target incarnation, with an explicit requeue action. [ASSUMED]

## Environment Availability

| Dependency               | Required By                   |                                Available | Fallback                           |
| ------------------------ | ----------------------------- | ---------------------------------------: | ---------------------------------- |
| Python and `uv`          | Backend/task tests            |                                      Yes | None                               |
| Node and npm             | v2 UI tests                   |                                      Yes | None                               |
| Redis/RQ scheduler       | Production periodic execution |   Project-configured, runtime not probed | Mocked focused tests, isolated UAT |
| MariaDB/MySQL/PostgreSQL | Queue migration               | Supported by project, runtime not probed | Existing migration CI/isolated DB  |
| Steam/IGDB credentials   | Live enrichment UAT           |   Configuration-dependent, not inspected | Provider-mocked tests              |

## Validation Architecture

### Test Framework

| Property           | Value                                                                                                                                                                                         |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend            | pytest, pytest-asyncio, fakeredis, VCR fixtures [VERIFIED: `.claude/skills/backend-development/SKILL.md`]                                                                                     |
| Frontend           | Vitest and Vue typecheck [VERIFIED: `CLAUDE.md`]                                                                                                                                              |
| Backend quick run  | `cd backend && uv run pytest tests/handler/metadata/test_pc_match_handler.py tests/handler/test_scan_handler.py tests/tasks/test_scan_library.py tests/endpoints/roms/test_pc_metadata.py -q` |
| Frontend quick run | `cd frontend && npm run test -- --run src/v2/components/Settings/<queue-tests>.test.ts`                                                                                                       |
| Phase gate         | `trunk fmt && trunk check`, focused suites, `cd frontend && npm run typecheck && npm run test`, isolated UAT                                                                                  |

### Requirements to Test Map

| Behavior                                                                      | Test Type           | Coverage                                                            |
| ----------------------------------------------------------------------------- | ------------------- | ------------------------------------------------------------------- |
| Exactly one Steam parent applies Steam, IGDB, and provider media              | Handler/integration | New automation scan tests with mocked providers                     |
| No/multiple parent candidate queues one item and applies nothing              | Handler/model       | New decision plus idempotent upsert tests                           |
| Exactly one valid tolerant parent-listed DLC relation applies, ties queue     | Unit/handler        | Extend `test_pc_match_handler.py` and scan handler tests            |
| Manual/protected metadata and media remain unchanged                          | Handler/database    | Extend PC enrichment persistence tests                              |
| Scheduled scan has 15-minute production config and includes Steam             | Task                | Extend `test_scan_library.py`                                       |
| Development/UAT 10-second mechanism is explicit                               | Task/config         | New config/task integration test                                    |
| List, accept, correct, skip, and safe batch reject stale/mixed/ambiguous rows | Endpoint/model      | New endpoint tests under `backend/tests/endpoints/roms/`            |
| v2 queue handles progress, empty/loading/error, paging, correction, and batch | Vitest/browser UAT  | New v2 queue tests and isolated UAT                                 |
| Source files never mutate                                                     | Integration         | Extend `backend/tests/integration/test_scan_source_immutability.py` |

### Wave 0 Gaps

- [ ] Queue model/migration fixtures for parents and components.
- [ ] Decision matrix fixtures for safe, no-match, ambiguous, tied DLC, provider failure, stale target, and manual-protected records.
- [ ] Scheduled Steam source mapping and 10-second development override tests.
- [ ] Paginated queue, mutation, and batch endpoint tests.
- [ ] v2 review component tests with keyboard/gamepad/accessibility coverage.

## Security Domain

| ASVS Category         | Applies       | Control                                                                                                                 |
| --------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------- |
| V2 Authentication     | Yes           | Existing protected routes. [VERIFIED: `.claude/skills/backend-development/SKILL.md`]                                    |
| V3 Session Management | Yes           | Existing RomM auth/session middleware, no new session design. [VERIFIED: `.claude/skills/backend-development/SKILL.md`] |
| V4 Access Control     | Yes           | Reuse least-privilege manual metadata scope and enforce it for every queue operation. [ASSUMED]                         |
| V5 Input Validation   | Yes           | Typed schemas, bounded pagination, server-side target reload, fingerprint and version validation. [ASSUMED]             |
| V6 Cryptography       | No new crypto | Never persist provider secrets in queue data. [VERIFIED: `CLAUDE.md`]                                                   |

| Threat                              | STRIDE                 | Mitigation                                                                                                                                 |
| ----------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Forged queue ID/fingerprint         | Tampering              | Reload rows and candidates server-side; do not trust client metadata. [ASSUMED]                                                            |
| Stale action overwrites manual data | Tampering              | Version/incarnation checks and existing manual/provenance protection. [VERIFIED: `backend/endpoints/roms/pc_metadata.py`, `21-CONTEXT.md`] |
| Background scan mutates library     | Tampering              | Mapping-bound scan capability and byte-exact immutability tests. [VERIFIED: `backend/endpoints/sockets/scan.py`, `CLAUDE.md`]              |
| Provider outage erases data         | Availability/Tampering | Queue retryable failure with no empty patch application. [VERIFIED: `21-CONTEXT.md`, `backend/handler/metadata/pc_match_handler.py`]       |

## Sources

### Primary (HIGH confidence)

- `22-CONTEXT.md` - locked decisions.
- `backend/tasks/scheduled/scan_library.py`, `backend/tasks/tasks.py`, `backend/startup.py`, and `backend/config/__init__.py` - scheduler and configuration.
- `backend/endpoints/sockets/scan.py` and `backend/handler/scan_handler.py` - mapped scans and PC enrichment.
- `backend/handler/metadata/pc_match_handler.py`, `steam_handler.py`, and `steam_merge.py` - matching, localization, and guarded patch behavior.
- `backend/endpoints/roms/pc_metadata.py` and `backend/handler/database/roms_handler.py` - current review and version-bound persistence.
- `frontend/src/v2/views/Settings/Administration.vue`, `components/Settings/TasksSection.vue`, and `components/Dialogs/MatchRomDialog.vue` - active v2 administration patterns.
- `CLAUDE.md` and relevant `.claude/skills` - project constraints.

### Secondary (MEDIUM confidence)

- No external documentation was necessary. This phase extends existing repository subsystems and installs no dependency.

### Tertiary (LOW confidence)

- No web-search-only source used.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH, all core subsystems already exist.
- Architecture: HIGH for integration seams; MEDIUM for durable queue shape and seconds-level UAT mechanism.
- Pitfalls: HIGH for existing source safety, Steam source omission, and fail-closed DLC behavior; MEDIUM for retry policy.

**Research date:** 2026-10-01
**Valid until:** 2026-10-31
