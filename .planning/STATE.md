---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 06-01-PLAN.md
last_updated: "2026-08-12T20:09:21.826Z"
last_activity: 2026-08-12
progress:
  total_phases: 9
  completed_phases: 5
  total_plans: 44
  completed_plans: 36
  percent: 82
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-10)

**Core value:** RomM adapts to an existing game archive without requiring or permitting any change to the archive's files, directories, or organization.
**Current focus:** Phase 06 — safe-lifecycle-and-legacy-migration

## Current Position

Phase: 06 (safe-lifecycle-and-legacy-migration) — EXECUTING
Plan: 2 of 9
Status: Ready to execute
Last activity: 2026-08-12

Progress: [████████░░] 82%

## Performance Metrics

**Velocity:**

- Total plans completed: 24
- Average duration: 10 min
- Total execution time: 1.41 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
| ----- | ----- | ----- | -------- |
| 01    | 7     | -     | -        |

**Recent Trend:**

- Last 5 plans: 10 min, 16 min, 27 min, 18 min, 10 min
- Trend: Stable

_Updated after each plan completion_
| Phase 01 P05 | 11min | 2 tasks | 2 files |
| Phase 01 P06 | 10min | 2 tasks | 5 files |
| Phase 01 P07 | 6min | 2 tasks | 2 files |
| Phase 02 P01 | 7min | 2 tasks | 3 files |
| Phase 02 P02 | 7min | 2 tasks | 3 files |
| Phase 02 P03 | 13min | 2 tasks | 13 files |
| Phase 02 P04 | 16min | 2 tasks | 16 files |
| Phase 02 P05 | 15min | 2 tasks | 21 files |
| Phase 02 P06 | 27min | 3 tasks | 18 files |
| Phase 02 P07 | 10min | 2 tasks | 13 files |
| Phase 02 P08 | 16min | 2 tasks | 2 files |
| Phase 02 P09 | 27min | 2 tasks | 7 files |
| Phase 02 P10 | 18min | 3 tasks | 6 files |
| Phase 02 P11 | 10min | 3 tasks | 1 files |
| Phase 03 P01 | 25min | 2 tasks | 9 files |
| Phase 03 P02 | 9min | 2 tasks | 2 files |
| Phase 03 P03 | 22min | 2 tasks | 2 files |
| Phase 03 P04 | 6min | 2 tasks | 5 files |
| Phase 03 P05 | 10min | 2 tasks | 3 files |
| Phase 05 P08 | 8min | 2 tasks | 4 files |
| Phase 05 P07 | 5h | 3 tasks | 24 files |
| Phase 06 P01 | 31min | 2 tasks | 9 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 1]: External roots are permanently `external_read_only`; path resolution and policy precede all consumers.
- [Phase 4]: Team4s is a read-only design-principles reference only and is never modified or copied.
- [Phase 8]: V1 removal is bounded and passes its own v2 regression gate.
- [Phase 1]: Indexed root and mapping paths are bounded to 700 characters for portable utf8mb4 uniqueness.
- [Phase 1]: MySQL verifies 0108 from a clean 0107-compatible baseline because older migration DDL is not MySQL 8-compatible.
- [Phase 1]: Empty logical paths are accepted only by the explicit internal root contract; platform mappings remain non-empty.
- [Phase 1]: Lexical normalization preserves valid case and Unicode exactly while returning bounded errors for unsafe text.
- [Phase 01]: CI treats MariaDB, MySQL, and PostgreSQL as independent migration authorities.
- [Phase 01]: Mapping locks target only the mapping entity and load storage roots separately for PostgreSQL portability.
- [Phase 01]: Only explicitly named mapping uniqueness constraints translate to duplicate-domain errors.
- [Phase 01]: Raw MariaDB/MySQL mapping key names require DBAPI errno 1062; PostgreSQL structured constraint names remain authoritative.
- [Phase 02]: External policy allows only eight explicitly enumerated read operations and rejects non-enum values without coercion.
- [Phase 02]: Storage authority comes only from immutable trusted descriptors with explicit external identity or RomM-owned kind.
- [Phase 02]: External access authorizes before root open and retains only an already-open target descriptor.
- [Phase 02]: Each approved external read operation has a separate capability type without raw path or generic open authority.
- [Phase 02]: Composition binds every closed owned kind to a trusted configured path before handler construction.
- [Phase 02]: Legacy external handlers deny inherited mutations before filesystem access.
- [Phase 02]: Retain the composition-owned legacy external descriptor until Phase 5 mapping lookup. - Caller paths never classify storage.
- [Phase 02]: Stream direct external downloads from DOWNLOAD capabilities without X-Accel conversion. - External capabilities cannot become raw paths or redirect URIs.
- [Phase 02]: Authorize ZIP cache writes separately with the owned CACHE descriptor. - External reads never imply write authority.
- [Phase 02]: Transformation utilities accept only operation-bound capabilities, with no raw Path/string compatibility overloads.
- [Phase 02]: Export metadata is written to classified owned resources storage, never back into the external library.
- [Phase 02]: Sync and SSH filesystem operations authorize the composition-owned SYNC descriptor before I/O.
- [Phase 02]: StoragePolicyDenied bypasses broad job and sync recovery handlers and remains terminal.

- [Phase 03]: Lifecycle mutations lock platform, active roots, and mappings in deterministic order before optimistic version checks and state changes.
- [Phase 03]: Create always inserts history; explicit reactivation revalidates active conflicts and audit cursors bind every filter.
- [Phase 02]: Fixed unsaved identities keep dual-mount verification independent from health resolution.
- [Phase 02]: Database-only ROM deletion does not request external filesystem mutation authority.

- [Phase 02]: Runtime external authority is created only by trusted composition, and external access accepts bound descriptors only.
- [Phase 02]: Private factory imports and aliased calls are independently discovered; typed StorageRoot branches and container_path access are function-name independent. - Close the final independent AST authority-discovery gap while preserving explicit Phase 1 non-authority resolvers.
- [Phase 03]: Active mapping conflicts use portable supporting indexes plus ordered handler locking; audit history is stored as relationship-free scalar snapshots.
- [Phase 03]: 0109 downgrade fails before DDL when lifecycle history cannot be represented by 0108.
- [Phase 03]: Directory cursors bind version, root identity, normalized parent, and the final visible binary sort key.
- [Phase 03]: Live root health is a pure value snapshot; registration compatibility adapts it explicitly onto the ORM row.

- [Phase 03]: Storage read routes require users.read plus explicit admin authority before lookup or filesystem observation.
- [Phase 03]: Root and browse contracts serialize explicit allowlists and translate storage failures to bounded static messages.
- [Phase 03]: Mapping mutations derive immutable actor attribution from authenticated requests and require explicit optimistic versions.
- [Phase 03]: Mapping conflicts expose only stable codes, allowlisted identifiers, and current versions where applicable.
- [Phase 03]: Preview is a bounded non-mutating directory summary whose cursor binds mapping identity, version, path, and final binary name key.
- [Phase 05]: External exporter destinations are classified with StoragePolicy OVERWRITE before database lookup, serialization, or filesystem work.
- [Phase 05]: Exporter immutability evidence covers manual, scheduled, and watcher commands with byte-exact source manifests.
- [Phase 05]: External mapped downloads use application-held descriptors; Nginx receives only completed RomM-owned cache paths.
- [Phase 05]: ZIP cache identity binds mapping ID, revision, logical path, member name, size, and timestamp without host paths.
- [Phase 05]: Independent verification passed all 26 requirements and decision checks with no product gaps or human verification items.
- [Phase 06]: Detached saves, states, and play sessions retain ownership through a stable catalog identity. — Preserves durable user history without keeping mutable ROM rows alive.
- [Phase 06]: Legacy migration state stores bounded logical identifiers and guarded downgrade state. — Supports restart-safe recovery without persisting host paths or raw snapshots.

### Blockers/Concerns

- [Phase 1]: Point-in-time resolution rejects configured-root and target-component symlinks; descriptor-relative no-follow opens and residual long-read race enforcement remain Phase 2 consumer-policy work.
- [Phase 5]: Confirm NAS watcher fidelity; scheduled and manual scans remain authoritative by default.
- [Phase 9]: Confirm NAS protocol, mount options, atime behavior, and a safe activation window before real-NAS rollout.

## Deferred Items

| Category | Item                                               | Status                      | Deferred At    |
| -------- | -------------------------------------------------- | --------------------------- | -------------- |
| Product  | PC components and file revisions                   | Deferred to later milestone | Initialization |
| Delivery | Manifests, resumable downloads, and Windows client | Deferred to later milestone | Initialization |
| UX       | Broader redesign beyond new storage surfaces       | Deferred to later milestone | Initialization |

## Session Continuity

Last session: 2026-08-12T20:08:16.350Z
Stopped at: Completed 06-01-PLAN.md
Resume file: None
