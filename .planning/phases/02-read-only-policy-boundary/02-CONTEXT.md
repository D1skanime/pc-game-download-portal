# Phase 2: Read-only Policy Boundary - Context

**Gathered:** 2026-08-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish one deny-by-default server-side operation policy for every access to an external root. The phase permits the defined read operations, rejects every mutation before filesystem access, separates external source storage from RomM-owned writable storage, and proves that all existing mutation paths are governed or cannot address an external root. Mapping administration APIs, consumer cutover, lifecycle migration, UI work, and real NAS activation remain outside this phase.

</domain>

<decisions>
## Implementation Decisions

### Operation Model

- **D-01:** Use explicit, fine-grained operation capabilities rather than broad read/write groups.
- **D-02:** The external-root allowlist is closed. It contains only `LIST`, `STAT`, `READ`, `SCAN`, `HASH`, `STREAM`, `DOWNLOAD`, and the explicitly named safe resolution capability.
- **D-03:** Unknown and newly introduced operations fail closed until explicitly classified and allowed.
- **D-04:** Policy decisions use the requested operation and a trusted storage classification. Caller-supplied path text must never determine the storage class.

### Mixed Workflows and Destinations

- **D-05:** Authorize source reads and destination writes independently. A read grant must never imply permission to write.
- **D-06:** Temporary and generated output may be written only to explicitly classified RomM-owned storage, never merely to any path outside an external root.
- **D-07:** Model copying from an external source as an authorized external read plus a separate authorized RomM-owned write. An external root can never be the copy destination.
- **D-08:** Extraction, patching, conversion, and similar transformations may use external bytes only as input. All generated or modified bytes must land in RomM-owned storage; in-place processing and write-back are forbidden.

### Denial Contract

- **D-09:** Use one typed policy-denial error with a stable machine-readable code. API, job, and internal callers translate the same domain error for their channel.
- **D-10:** Direct API denials return HTTP 403 with the stable error code.
- **D-11:** Background jobs and internal workflows fail immediately and visibly. They must not skip the denied step, silently fall back, redirect to another path, or report partial work as success.
- **D-12:** Externally visible denial details are limited to the operation, storage class, and logical root or mapping identifier. Do not expose absolute paths, relative paths, filesystem details, or unrelated mappings.

### Enforcement and Proof

- **D-13:** Enforce policy at the lowest common filesystem boundary. Endpoints, handlers, and jobs must not access an external root through raw resolved paths.
- **D-14:** Successful authorization returns an operation-bound capability or handle, not a freely reusable absolute path. The capability exposes only the approved operation.
- **D-15:** Maintain a complete inventory of existing mutation paths. Every path must use the policy or be structurally and testably restricted to RomM-owned storage. Any unclassified path blocks phase completion.
- **D-16:** Run the same denial matrix against a writable fixture and a container-mounted read-only fixture. Tripwires must prove that a denial occurs before `stat`, `open`, enumeration, or mutation reaches the target filesystem.

### Agent's Discretion

The exact Python names, module boundaries, capability representation, error-code spelling, and test organization are left to research and planning, provided they preserve D-01 through D-16.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project and Phase Contract

- `.planning/ROADMAP.md` - Defines the Phase 2 goal, requirements identifiers, success criteria, dependencies, and later-phase boundaries.
- `.planning/STATE.md` - Records the immutable external-root decision and project-level safety concerns. It currently references a missing `.planning/PROJECT.md`; do not assume unavailable project content.
- `CLAUDE.md` - Defines repository architecture, backend conventions, verification requirements, and contribution constraints.

### Existing Architecture

- `.planning/codebase/ARCHITECTURE.md` - Maps filesystem handlers, endpoints, tasks, scans, downloads, and application-layer integration points.
- `.planning/codebase/CONCERNS.md` - Records known security and filesystem risks relevant to the policy boundary.
- `.planning/codebase/TESTING.md` - Defines existing backend test patterns and infrastructure.
- `backend/handler/filesystem/base_handler.py` - Current shared filesystem API, including constructor-side directory creation, raw path returns, reads, writes, copies, moves, and deletes that the new boundary must account for.
- `backend/exceptions/fs_exceptions.py` - Existing filesystem exception conventions that the typed policy denial must remain distinguishable from.

No external specification or ADR was referenced during discussion.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- Phase 1 planned storage resolver and storage models: supply trusted external-root and mapping identities once Phase 1 is implemented.
- `FSHandler` locking and async file helpers: existing operational behavior can inform capability adapters, but its constructor and mutation methods are unsafe for direct external-root use.
- Existing pytest filesystem fixtures and handler tests: provide patterns for writable-tree manifests, mutation tripwires, and asynchronous tests.

### Established Patterns

- Backend flow is endpoint to application handler to filesystem/database handler; policy belongs at the common filesystem boundary while domain errors are translated at outer layers.
- Backend exceptions and response schemas own stable contracts; API errors must remain bounded and must not leak host paths.
- Background work runs through RQ tasks and scheduled/manual task modules, so enforcement cannot depend only on HTTP middleware.

### Integration Points

- `backend/handler/filesystem/` contains the common read and mutation surface.
- `backend/endpoints/roms/` contains download, upload, manual, soundtrack, screenshot, and patch workflows with mixed source/destination behavior.
- `backend/handler/scan_handler.py`, `backend/endpoints/sockets/scan.py`, and `backend/tasks/` are non-HTTP consumers that require the same policy contract.
- Download ZIP/cache and resource paths must be classified as RomM-owned destinations rather than inferred safe because they are outside an external root.

</code_context>

<specifics>
## Specific Ideas

- Treat safe access as an operation-bound capability rather than returning a raw absolute path.
- Prove application-level denial independently of mount permissions by combining writable and read-only fixtures with pre-access tripwires.

</specifics>

<deferred>
## Deferred Ideas

None. Discussion stayed within the Phase 2 boundary.

</deferred>

---

_Phase: 2-read-only-policy-boundary_
_Context gathered: 2026-08-09_
