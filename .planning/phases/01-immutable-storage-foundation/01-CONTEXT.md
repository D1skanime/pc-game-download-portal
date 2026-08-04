# Phase 1: Immutable Storage Foundation - Context

**Gathered:** 2026-08-04
**Status:** Ready for planning
**Source:** PRD Express Path from the user-provided Phase 1 specification

<domain>
## Phase Boundary

Phase 1 establishes only the persistent identity and safe resolution foundation for an immutable external game library. It introduces deployment-owned storage-root records, relative platform-storage mappings, canonical containment and symlink protection, root health inspection, the initial database migration, and adversarial unit coverage.

This phase does not cut scanners, watchers, downloads, lifecycle endpoints, or the frontend over to the new model. Central mutation policy is Phase 2, administration APIs are Phase 3, the UI design contract is Phase 4, read-path cutover is Phase 5, lifecycle and legacy migration behavior is Phase 6, v2 administration is Phase 7, v1 removal is Phase 8, and production NAS proof is Phase 9.

</domain>

<decisions>
## Implementation Decisions

### External library ownership

- D-01: The real games collection is an archive owned outside RomM. RomM adapts to its existing directory structure and never requires users to copy, move, rename, or reorganize it.
- D-02: Deployment mounts one shared NAS games root at a configured container path, for example `/volume1/Mediathek/Games:/romm/library:ro`.
- D-03: Every external library root uses the immutable mode `external_read_only`. Phase 1 provides no writable mode and no UI or configuration toggle that can enable writes.
- D-04: RomM-owned database state, resources, assets, configuration, cache, hashes, scan state, temporary files, and audit data remain outside the external root.
- D-05: The storage foundation must not create a root or any directory during initialization or health inspection. A missing or unreadable deployment mount fails closed with a controlled status.

### Storage-root model

- D-06: Add a persistent storage-root entity with at least ID, display name, container path, mode, active state, creation timestamp, and update timestamp.
- D-07: The container path is deployment-owned. Normal administration must not accept arbitrary absolute host or system paths.
- D-08: The schema must allow multiple storage roots in future, although the first deployment uses one NAS root.
- D-09: Root status reports reachable, readable, non-writable, last checked time, and a safe error without mutating the root.
- D-10: A root registered as `external_read_only` is expected to be non-writable. A writable observation is a warning or failed safety state, never permission to write.

### Platform-storage mapping model

- D-11: Each platform maps to an existing relative subdirectory of a storage root through a dedicated persistent entity.
- D-12: Store `storage_root_id` plus normalized `relative_path`; never store a NAS host path or a composed absolute container path in the mapping.
- D-13: Phase 1 permits at most one active mapping per platform.
- D-14: Multiple platforms may map to distinct directories below the same root.
- D-15: Ancestor, descendant, duplicate, and otherwise unsafe overlaps are rejected by default.
- D-16: Saving or validating a mapping must not create, move, rename, copy, or otherwise change filesystem content.
- D-17: Mapping targets must exist, be readable directories, and belong to an active root.

### Central safe resolution

- D-18: All external-library path resolution uses one central, non-mutating resolver rather than the current directory-creating `FSHandler` constructor behavior.
- D-19: Resolver input is a logical relative path only. Reject absolute POSIX paths, Windows drive paths, UNC paths, parent traversal, invalid empty segments, NUL/control input, and separator-confusable escape forms.
- D-20: Resolve root and target canonically and verify containment after symlink resolution. Lexical `startsWith` or string-prefix checks are not sufficient.
- D-21: Platform mappings resolve to directories only.
- D-22: Milestone 1 rejects symlinks by default. Supporting a verified in-root symlink later requires an explicit decision and dedicated race-safe tests.
- D-23: Path behavior must support spaces, dots, hyphens, umlauts, Unicode, long directory names, and nested subdirectories.
- D-24: Controlled domain errors distinguish invalid input, missing root, inactive root, missing target, non-directory target, unreadable target, unsafe symlink, escape attempt, and unsafe writable-root observation without leaking unrelated filesystem paths.

### Database and compatibility

- D-25: Use the existing SQLAlchemy 2 and Alembic conventions and preserve MariaDB, MySQL, and PostgreSQL portability.
- D-26: The migration adds the new schema only. It does not create, rename, move, copy, or delete library files or directories.
- D-27: Do not perform speculative legacy backfill in Phase 1. The legacy migration and fallback strategy is implemented in Phase 6 after read paths have a safe mapping contract.
- D-28: Use integer identities and relationship/index conventions consistent with the existing RomM models unless concrete repository constraints require another existing convention.

### Security and evidence

- D-29: Docker `:ro` is defense in depth, not the application policy. Phase 1 models immutability and proves non-mutating resolution even against a writable test fixture.
- D-30: Unit coverage includes valid root, normal and nested directories, spaces, umlauts, Unicode, empty path behavior, traversal, repeated traversal, absolute POSIX, drive, UNC, missing root, missing target, file target, inactive root, read-only status, writable-root warning, and symlink escape.
- D-31: Tests compare filesystem state before and after root registration, health inspection, and mapping validation to prove that Phase 1 creates no source files or directories.
- D-32: Access-time changes depend on NAS and mount policy. Documentation later recommends `noatime` or a NAS-specific equivalent when metadata-level immutability is required.

### Frontend and later work

- D-33: The fork is v2-only, but Phase 1 contains no frontend feature work and does not remove v1. The bounded v1 removal remains Phase 8.
- D-34: Team4s is a read-only design-principles reference only. It is never modified, copied as React code, restarted, or made a build/runtime dependency.
- D-35: PC components, manifests, resumable downloads, Windows client work, upload, source organization, ZIP redesign, and install planning are outside Phase 1.

### Agent Discretion

- Exact model and module filenames within the established backend conventions.
- Whether root health is persisted directly on the root row or through a separate status record, provided the stored result remains safe, bounded, and testable.
- Exact enum persistence strategy, provided it remains portable across supported databases and returns a stable API string later.
- Exact domain exception hierarchy and repository method names.
- Transaction and eager-loading details consistent with existing database handlers.
- Whether the empty relative path represents the root itself for internal resolution. Platform mappings must still resolve to an explicitly valid directory according to the final model contract.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and requirements

- `.planning/PROJECT.md` - Core value, milestone boundary, constraints, and durable decisions.
- `.planning/REQUIREMENTS.md` - Phase 1 requirements ROOT-01 through ROOT-04, PATH-01 through PATH-05, and TEST-01.
- `.planning/ROADMAP.md` - Phase boundary, dependencies, success criteria, and later-phase ownership.
- `.planning/STATE.md` - Current position and unresolved research concerns.

### Existing architecture

- `.planning/codebase/ARCHITECTURE.md` - Current layers, scanner flow, filesystem handlers, data model, and architectural constraints.
- `.planning/codebase/CONCERNS.md` - Existing filesystem, scanner, symlink, mutation, and migration risks.
- `.planning/codebase/CONVENTIONS.md` - Repository implementation and testing conventions.
- `.planning/codebase/TESTING.md` - Existing test organization and commands.
- `.planning/research/ARCHITECTURE.md` - Recommended storage boundary, sequencing, and data flow.
- `.planning/research/STACK.md` - Stack decision and non-mutating resolver recommendation.
- `.planning/research/PITFALLS.md` - Concrete failure modes and required prevention.
- `.planning/research/SUMMARY.md` - Synthesized milestone recommendations and open questions.

### Repository rules and prior analysis

- `CLAUDE.md` - Mandatory repository rules, backend skill routing, tests, language, and verification.
- `.claude/skills/backend-development/SKILL.md` - Backend models, migrations, handlers, schemas, and test conventions.
- `docs/PC_GAME_COMPONENTS_AND_MANIFEST_DOWNLOADS_ANALYSIS.md` - Existing storage safety boundary and current filesystem architecture evidence.

### Current implementation seams

- `backend/config/__init__.py` - Current base paths and deployment configuration.
- `backend/config/config_manager.py` - Current fixed library layout assumptions.
- `backend/models/platform.py` - Existing platform persistence and relationships.
- `backend/models/base.py` - Shared SQLAlchemy model conventions.
- `backend/handler/filesystem/base_handler.py` - Current validation and directory-creating constructor behavior that external roots must not reuse unchanged.
- `backend/handler/filesystem/platforms_handler.py` - Current platform directory discovery and creation behavior.
- `backend/handler/filesystem/roms_handler.py` - Current fixed-layout resolution consumed by later phases.
- `backend/handler/database/platforms_handler.py` - Existing platform database-handler patterns.
- `backend/alembic/versions/` - Cross-dialect migration conventions and current revision head.
- `backend/tests/handler/filesystem/test_base_handler.py` - Existing filesystem boundary tests.
- `backend/tests/handler/filesystem/test_platforms_handler.py` - Existing platform filesystem tests.
- `backend/tests/models/` - Model test patterns.

</canonical_refs>

<specifics>
## Specific Ideas

- The target deployment mount is one shared root: `/volume1/Mediathek/Games:/romm/library:ro`.
- Example relative mappings include `Nintendo Switch`, `PlayStation 2`, `SNES Super Nintendo`, `GB GameBoy`, `GBC GameBoy Color`, and `Xbox`.
- The effective container path is derived on the server from storage root plus relative mapping and is never accepted from a mapping request.
- A root health check must demonstrate that inspection itself does not call `mkdir`, create a probe file, or write a lock.
- Descriptor-relative and no-follow techniques should be investigated for residual time-of-check/time-of-use risk, but Phase 1 planning must distinguish achievable containment guarantees from production NAS validation deferred to Phase 9.

</specifics>

<deferred>
## Deferred Ideas

- Central operation policy and mutation-path enforcement: Phase 2.
- Storage-root and mapping administration APIs, browsing, and audit: Phase 3.
- Team4s-informed RomM v2 design contract: Phase 4.
- Preview, scanner, watcher, hashing, streaming, and download cutover: Phase 5.
- Catalog-only removal and legacy migration: Phase 6.
- V2 administration UI: Phase 7.
- Complete v1 removal: Phase 8.
- Production-like nginx, worker, real NAS, atime, and full immutability evidence: Phase 9.
- PC components, manifests, resume, and Windows downloader: later milestones.

</deferred>

---
*Phase: 01-immutable-storage-foundation*
*Context gathered: 2026-08-04 via PRD Express Path*
