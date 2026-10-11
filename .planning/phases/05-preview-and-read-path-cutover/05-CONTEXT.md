# Phase 5: Preview and Read-path Cutover - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Make bounded preview, manual and automated discovery, hashing, streaming, browser play, downloads, workers, and internal redirects resolve content through stable platform mappings. Every workflow must preserve the external archive byte-for-byte, write only to RomM-owned storage, and fail clearly when its expected mapping or source content is no longer valid. Mapping administration, catalog-removal semantics, migration, and final v2 UI implementation remain in their assigned phases.

</domain>

<decisions>
## Implementation Decisions

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

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project and Phase Contract

- `.planning/ROADMAP.md` - Defines the Phase 5 goal, SCAN-01 through SCAN-06 scope, success criteria, Phase 3 dependency, and later-phase boundaries.
- `.planning/STATE.md` - Records the immutable archive principle, current Phase 5 focus, and the concern that NAS watcher fidelity requires validation.
- `CLAUDE.md` - Defines repository architecture, backend conventions, generated API contract rules, testing expectations, and the frozen v1 boundary.

### Carried-forward Decisions

- `.planning/phases/02-read-only-policy-boundary/02-CONTEXT.md` - Locks explicit read capabilities, operation-bound access, independent RomM-owned writes, stable denials, path redaction, and fail-visible background behavior.
- `.planning/phases/04-v2-storage-design-specification/04-CONTEXT.md` - Locks bounded preview states, explicit refresh, stable local state presentation, mapping replacement behavior, and the platform-led workflow consumed by later UI work.

### Existing Architecture

- `.planning/codebase/ARCHITECTURE.md` - Maps filesystem handlers, scan orchestration, endpoints, tasks, and download paths involved in the cutover.
- `.planning/codebase/CONCERNS.md` - Identifies path containment, symlink, large-file, Range, download, scanner-volume, and production Nginx risks relevant to this phase.
- `.planning/codebase/INTEGRATIONS.md` - Defines mounted filesystem storage, Redis/RQ jobs, Nginx redirects, browser emulators, and external metadata integrations touched by read workflows.

No external specification or ADR was referenced during discussion.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `backend/handler/scan_handler.py`: existing platform, ROM, firmware, asset, and metadata scan orchestration that must receive mapping-bound source access.
- `backend/handler/filesystem/`: shared filesystem handlers and hashing utilities where Phase 2 operation-bound policy must replace legacy fixed-layout access.
- `backend/endpoints/roms/files.py` and `backend/endpoints/roms/__init__.py`: authenticated direct-file, multi-file, ZIP, and response flows that need mapping revision checks and preflight behavior.
- `backend/utils/nginx.py` and `backend/utils/zip_cache.py`: existing internal redirect and generated archive mechanisms; generated output remains RomM-owned.
- `backend/tasks/` and Redis/RQ infrastructure: existing queued and scheduled execution model where mapping ID and revision must be captured and validated.

### Established Patterns

- Backend flows from endpoints or tasks through application handlers into filesystem and database handlers; mapping and policy enforcement belongs at the common read boundary.
- Backend schemas and domain exceptions own stable contracts. HTTP, jobs, sockets, and the generated frontend contract translate those shared domain results for their channels.
- Metadata, artwork, caches, temporary archives, and other generated data already have RomM-owned destinations separate from source-library content.
- Scheduled and manual scanning already exist; watcher-triggered work must converge on the same pipeline rather than introduce a second discovery implementation.

### Integration Points

- Platform mapping contracts from Phase 3 provide the active mapping ID, revision, safe resolution, and health state for every Phase 5 consumer.
- Manual and socket scan entry points, scheduled tasks, and watcher hooks must enqueue the same mapping-bound scan command.
- Hash and metadata lookup paths consume source bytes through mapped, operation-specific handles.
- Streaming, EmulatorJS/Ruffle play, direct downloads, multi-file archives, and Nginx internal redirects must authorize the expected mapping revision immediately before source handoff.
- Preview results provide the `pending`, `partial`, and `complete` backend states consumed by the Phase 7 v2 administration experience.

</code_context>

<specifics>
## Specific Ideas

- Preview lower-bound language should say that at least the observed number of files and bytes were found and that full discovery occurs during a scan.
- Download preflight must scale by required source files: one ISO produces one quick preflight, while a title distributed across 100 required RAR parts produces 100 quick preflights.
- Quick preflight must not read or hash every byte before delivery; it validates identity, containment, availability, file type, readability, and authorization.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within the Phase 5 boundary.

</deferred>

---

_Phase: 5-preview-and-read-path-cutover_
_Context gathered: 2026-08-11_
