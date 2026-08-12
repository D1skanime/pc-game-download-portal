# Phase 6: Safe Lifecycle and Legacy Migration - Context

**Gathered:** 2026-08-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver source-safe catalog and mapping lifecycle behavior plus an explicit, administrator-started bridge from exact canonical legacy RomM platform layouts to storage roots and relative mappings. The phase may change RomM-owned database, configuration, audit, catalog, and owned assets only. It must never move, copy, rename, create, patch, or delete source library files or directories. The v2 administration UI remains Phase 7; Phase 6 provides the backend contracts, migration behavior, and evidence it will consume.

</domain>

<decisions>
## Implementation Decisions

### Mapping Removal and Reconnection

- **D-01:** Removing a platform mapping retains cataloged games, metadata, saves, play history, and catalog identity. Affected games remain visible but are marked unreachable.
- **D-02:** New scan, preview, hash, stream, play, download, and related jobs are blocked after removal. Running and queued work aborts at the next safe boundary rather than finishing against a removed mapping.
- **D-03:** A later valid mapping for the same platform automatically reconnects unambiguous matching source files to existing catalog identities without recreating metadata or history.
- **D-04:** Mapping removal uses a clear normal confirmation that explains catalog retention, source immutability, and job cancellation. It does not require typing the platform name.
- **D-05:** Mapping removal changes only RomM-owned configuration and audit state. It never mutates source files or directories.

### Legacy Library Detection

- **D-06:** Legacy detection runs only when explicitly started by an authorized administrator. It never runs automatically at startup or on a schedule.
- **D-07:** Detection examines only exact known canonical RomM legacy platform paths such as `library/roms/<platform>`. It does not search arbitrary directories or infer meaning from similar names.
- **D-08:** Names such as `ps3_old`, `playstation3_backup`, or other aliases are ignored unless a future locked compatibility contract identifies them as an exact canonical historical path.
- **D-09:** Each result shows a safe compact summary: platform identity, reachability/readability state, bounded file count, estimated size, and proposed relative mapping. It exposes no absolute host/container path and no complete file list.
- **D-10:** Empty, unreadable, or unreachable canonical folders remain visible as bounded problems but cannot be selected for migration.

### Migration Confirmation and Rollback

- **D-11:** Migration changes only RomM-owned database and configuration state. It never moves, copies, renames, creates, or deletes source library content.
- **D-12:** Before confirmation, show a per-platform impact preview containing the proposed mapping, count of reconnectable catalog entries, unmatched entries, bounded problems, and planned database effects without internal row dumps or absolute paths.
- **D-13:** Each platform is confirmed and migrated independently. Failure for one platform does not roll back already completed migrations for other platforms.
- **D-14:** A platform migration is atomic: mapping creation/activation, catalog reconnection, audit, and rollback metadata either commit together or leave no partial state.
- **D-15:** Direct rollback is available only until the new mapping is first used productively by scan, hash, stream, play, or download work.
- **D-16:** Rollback restores only prior RomM-owned database/configuration state. It never reverses or changes source files because migration never modifies them.

### Conflicts and Edge Cases

- **D-17:** If a platform already has an active mapping, legacy migration for that platform is blocked. RomM never automatically replaces, merges, or prefers the legacy source.
- **D-18:** Duplicate, equal, ancestor, or descendant overlaps with any active mapping block migration. RomM never shrinks or rewrites existing mappings automatically.
- **D-19:** Unambiguous catalog matches reconnect. Missing or ambiguous catalog entries remain preserved and visible as unreachable rather than blocking the whole migration or being deleted.
- **D-20:** A crash, database error, stale version, or other failure during one platform migration causes a complete transaction rollback. The administrator can safely retry afterward.
- **D-21:** Unsafe or ambiguous layouts produce a clear manual-mapping requirement. The system never guesses and never enables a hidden legacy fallback.

### the agent's Discretion

- Exact canonical legacy platform-name table, provided it is derived from verified historical RomM behavior and follows D-07/D-08.
- Exact bounded count/size budgets and asynchronous execution mechanism for detection and impact previews.
- Matching algorithm for reconnecting catalog identities, provided only unambiguous matches reconnect and source content is never mutated.
- Internal rollback token/state representation and audit schema, provided D-14 through D-16 remain enforceable across supported databases.
- User-facing copy details for the future Phase 7 UI, within the behavioral contract above.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone scope and requirements

- `.planning/ROADMAP.md` - Phase 6 goal, dependency on Phase 5, success criteria, and fixed boundary.
- `.planning/REQUIREMENTS.md` - CAT-01 through CAT-04 and MIG-01 through MIG-05 acceptance requirements.
- `.planning/PROJECT.md` - Core immutable-archive value and project constraints.

### Upstream lifecycle and read contracts

- `.planning/phases/03-mapping-administration-contracts/03-CONTEXT.md` - Mapping lifecycle, optimistic versioning, audit, removal, and authorization decisions.
- `.planning/phases/03-mapping-administration-contracts/03-VERIFICATION.md` - Verified backend administration contract and database portability evidence.
- `.planning/phases/05-preview-and-read-path-cutover/05-CONTEXT.md` - Mapping-bound work identity, cancellation/staleness behavior, and read-only consumer decisions.
- `.planning/phases/05-preview-and-read-path-cutover/05-VERIFICATION.md` - Verified mapping-aware read paths, source immutability, and legacy-authority closure.
- `docs/design/v2-storage-administration.md` - Phase 7-facing storage workflow and removal presentation contract.

### Repository rules and architecture

- `CLAUDE.md` - Backend, generated API, testing, Trunk, language, and repository-wide rules.
- `.planning/codebase/ARCHITECTURE.md` - Current backend/data-flow boundaries.
- `.planning/codebase/TESTING.md` - Test organization and integration conventions.
- `.planning/codebase/CONCERNS.md` - Known storage, path, portability, and production risks.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `backend/handler/database/storage_handler.py`: version-checked deactivate, remove, reactivate, overlap validation, and immutable audit snapshots.
- `backend/endpoints/storage.py`: protected administrator lifecycle endpoints and bounded error translation.
- `backend/handler/storage/read_context.py`: mapping/revision-bound work validation and missing/stale mapping failures.
- `backend/models/storage.py`: root, mapping, preview, and audit identities that migration must extend without host-path persistence.

### Established Patterns

- Mapping lifecycle operations use optimistic `expected_version`, row locks, one transaction, and immutable audit entries.
- Missing or changed mapping identity fails closed across jobs and direct content reads.
- External-source operations are deny-by-default and RomM-owned writes require a distinct trusted destination capability.
- Public responses expose friendly identities and bounded status, never NAS host paths or raw filesystem errors.
- Cross-database behavior is proven against MariaDB/MySQL/PostgreSQL rather than assumed from SQLite behavior.

### Integration Points

- Extend the database/storage service for atomic migration and rollback state rather than bypassing existing lifecycle methods.
- Connect job cancellation/denial to mapping revision and active-state checks established in Phase 5.
- Provide typed administrator detection, impact-preview, migrate, rollback, and status contracts through the existing storage router.
- Reuse existing catalog identities and mark reachability without deleting catalog/source content.
- Add Alembic changes only where required for durable migration/audit/rollback state and verify upgrade/downgrade portability.

</code_context>

<specifics>
## Specific Ideas

- A Game Boy mapping such as `NAS Games / GB GameBoy / DE - Version` must not be replaced by a detected legacy `library/roms/gb` folder. The migration is blocked until the administrator deliberately resolves the existing mapping.
- If `PlayStation -> roms` is active, a proposed `Game Boy -> roms/gb` migration is blocked because the paths overlap.
- Similar folders such as `ps3_old` and `playstation3_backup` are ignored rather than treated as migration candidates.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

_Phase: 06-safe-lifecycle-and-legacy-migration_
_Context gathered: 2026-08-12_
