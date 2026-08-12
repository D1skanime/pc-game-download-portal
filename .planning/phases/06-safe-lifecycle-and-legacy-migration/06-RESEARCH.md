# Phase 6: Safe Lifecycle and Legacy Migration - Research

**Researched:** 2026-08-12
**Confidence:** HIGH

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

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
- **D-22:** Game-level Remove from catalog preserves RomM-owned saves, states, and play history for later reconnection. It removes active catalog visibility and association only. The planner must define the exact retained ownership and identity contract and may delete only explicitly disposable catalog records and RomM-owned assets. Source content remains untouched.
- **D-23:** Automatic legacy detection accepts only the two historically verified canonical grammars `roms/{Platform.fs_slug}` and `{Platform.fs_slug}/roms`. Configured or custom folder names such as `games` require manual mapping and are never auto-detected.

### the agent's Discretion

- Exact bounded count/size budgets and asynchronous execution mechanism for detection and impact previews.
- Matching algorithm for reconnecting catalog identities, provided only unambiguous matches reconnect and source content is never mutated.
- Internal rollback token/state representation and audit schema, provided D-14 through D-16 remain enforceable across supported databases.
- User-facing copy details for the future Phase 7 UI, within the behavioral contract above.

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within phase scope.
</user_constraints>

<phase_requirements>

## Phase Requirements

| IDs                   | Research support                                                                                                 |
| --------------------- | ---------------------------------------------------------------------------------------------------------------- |
| CAT-01..CAT-04        | Explicit catalog-only API, exact owned deletion boundary, mapping invalidation, policy regression.               |
| MIG-01..MIG-05        | Exact detection, portable transaction/rollback, restart persistence, status-only compatibility with no fallback. |
| </phase_requirements> |

## Summary

Mapping removal already sets `active=False`, increments `version`, and audits in one transaction. Phase 5 consumers bind `mapping_id + expected_revision` and fail closed when either changes. [VERIFIED: backend/handler/database/storage_handler.py, backend/handler/storage/read_context.py] Phase 6 should extend this aggregate to mark platform catalog/file rows unreachable, provide explicit catalog-only removal, and persist migration, rollback and first-use state.

Historical RomM recognizes exactly two layouts relative to the library root: `roms/<platform-fs-slug>` and `<platform-fs-slug>/roms`; Structure A historically has global priority. [VERIFIED: backend/handler/filesystem/platforms_handler.py, backend/endpoints/heartbeat.py, git history] Phase 6 must construct only these candidates from persisted `Platform.fs_slug` rows, never enumerate platform identities from folders or apply bindings, aliases or fuzzy matching.

**Primary recommendation:** one deterministic locked transaction per platform, durable rollback state, and an atomic first-use marker before source open. Detection remains bounded, administrator-started, read-only and non-authoritative.

## Architectural Responsibility Map

| Capability             | Primary tier   | Secondary                  | Reason                                                     |
| ---------------------- | -------------- | -------------------------- | ---------------------------------------------------------- |
| Catalog removal        | API/backend    | DB/owned storage           | authorize and define exact owned cleanup                   |
| Mapping lifecycle      | backend        | DB                         | revision, reachability, identity and audit change together |
| Work cancellation      | backend jobs   | DB/RQ                      | revision is durable authority                              |
| Detection/preview      | backend        | external read-only storage | bounded capability reads                                   |
| Migration/rollback/use | DB             | all consumers              | row locks and compare-and-set                              |
| UI confirmation        | Phase 7 client | API                        | Phase 6 supplies typed contracts only                      |

## Exact Canonical Legacy Layout

| Priority | Exact relative constructor | Identity source                  |
| -------- | -------------------------- | -------------------------------- |
| 1        | `roms/{Platform.fs_slug}`  | persisted canonical platform row |
| 2        | `{Platform.fs_slug}/roms`  | persisted canonical platform row |

These are grammars, not an alias table. [VERIFIED: platforms_handler.py] If both exist for one platform, return `manual_mapping_required`; historical priority cannot override D-21. Configured or custom folder names, including `games`, require manual mapping and are never automatically detected. [VERIFIED: locked D-23]

## Standard Stack

| Component        | Version            | Purpose                                                           |
| ---------------- | ------------------ | ----------------------------------------------------------------- |
| SQLAlchemy       | project 2.0 family | transaction and row locks [VERIFIED: pyproject.toml]              |
| Alembic          | ~1.16              | additive schema after 0110 [VERIFIED: pyproject.toml, migrations] |
| FastAPI/Pydantic | ~0.134.0 / ~2.11   | typed admin/OpenAPI contract [VERIFIED: pyproject.toml]           |
| Redis/RQ         | ~6.2 / ~2.7        | bounded asynchronous detection [VERIFIED: pyproject.toml, tasks]  |
| pytest           | ~9.0               | unit/API/integration evidence [VERIFIED: pyproject.toml]          |

No new runtime dependency is needed. [VERIFIED: repository architecture]

## Architecture Patterns

```text
admin -> auth/admin -> typed expected version/result
 -> lock Platform -> active roots by id -> mappings by id
 -> validate exact candidate and overlaps
 -> lock migration/catalog rows by id
 -> mapping + reachability + audit + rollback state
 -> commit one platform

consumer -> validate mapping/revision -> mark first use atomically
 -> validate again -> open capability -> safe boundaries -> owned output
```

### Atomic per-platform migration

Use existing `@begin_session` and lock order. Mapping activation, reconnection, audit and rollback snapshot flush before one commit; exceptions roll back that platform without affecting earlier independently confirmed platforms. [VERIFIED: decorators/database.py, storage_handler.py; CITED: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html]

### Cancellation and revision

Inactive state plus a new revision invalidates queued work at first validation. Running work checks before every source open, between bounded scan/hash batches, before catalog reconciliation, and before response/output commitment. [VERIFIED: read_context.py, scan_handler.py] Current scan has outer pre/post boundaries, so implementation must add inner boundaries around owned writes. Already-open descriptors cannot be promised asynchronous revocation. RQ stop is optional latency reduction, never correctness authority. [ASSUMED]

### Rollback before first use

Persist migration ID, platform/mapping, prior owned state/change set, state/version, actor/timestamps, and nullable `first_used_at` with bounded operation kind. Rollback locks migration/mapping, requires unused, restores owned state, invalidates mapping revision, audits and marks rolled back atomically. [ASSUMED] Every productive consumer compare-and-sets first use before open, then revalidates. Rollback-first makes the read stale; use-first makes rollback return 409. [ASSUMED]

### Unambiguous reconnection

Reconnect only a one-to-one exact normalized logical path/file identity. For moved content, use existing complete CRC32+MD5+SHA1 uniqueness. [VERIFIED: roms_handler.get_matching_missing_rom] Never use basename, display name, provider ID, partial hash, alias or first result. [ASSUMED]

### Bounded detection and impact

Reuse the existing 10,000-entry and 2-second budget per exact candidate, observed lower-bound counts, partial state and capped problems. [VERIFIED: handler/storage/preview.py] Run only via explicit admin job, persist a safe result, and bind confirmation to result/platform/root/path/live versions. Recommended expiry is 24 hours. [ASSUMED]

## Catalog Removal and Owned Boundary

Current `POST /api/roms/delete` mixes DB deletion, optional source deletion and owned resource cleanup. [VERIFIED: endpoints/roms/**init**.py] Replace the external contract with catalog removal that has no `delete_from_fs`.

| Item                                                                      | Action                                                                                                                 |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Rom/RomFile, metadata/facets, notes, user props, collection/sibling links | explicit catalog-owned delete [VERIFIED: model FKs]                                                                    |
| owned cover/manual/screenshot/soundtrack/resources                        | owned RESOURCES/ASSETS capability only [VERIFIED: filesystem composition]                                              |
| saves/states/play history                                                 | preserve for later reconnection under the planner-defined retained ownership/identity contract [VERIFIED: locked D-22] |
| external source                                                           | never mutate [VERIFIED: policy and D-05/D-11]                                                                          |
| shared caches                                                             | scoped invalidation only [VERIFIED: current delete route]                                                              |

DB commit and filesystem cleanup are not one ACID transaction. Write an idempotent owned-cleanup intent with catalog deletion, commit, then process only allowlisted owned paths and retry failures. [ASSUMED]

## Cross-Dialect and Persistence

- Preserve platform, roots-by-ID, mappings-by-ID, then migration/catalog-by-ID lock order. [VERIFIED: storage_handler.py]
- Use portable indexes plus handler locks, not partial indexes/advisory locks/dialect upserts. [VERIFIED: 0109, Phase 3 verification]
- Use additive bounded scalar columns, named checks/indexes/FKs and scalar audit snapshots. [VERIFIED: storage schema]
- Test MariaDB, MySQL and PostgreSQL upgrade/downgrade/re-upgrade. PostgreSQL DDL is transactional; Alembic marks MySQL/MariaDB DDL non-transactional, so downgrade guards run before DDL. [CITED: https://alembic.sqlalchemy.org/en/latest/api/ddl.html]
- Mappings/migrations/usage live only in DB, never process memory, and restart tests prove normal deployment persistence. [ASSUMED]

## Explicit Time-Bounded Compatibility

Implement no source fallback. Phase 5 closed fixed-layout authority and D-21 forbids reopening it. [VERIFIED: Phase 5 verification] MIG-05 is met by status only: `manual_mapping_required`, created/expires timestamps and bounded warning. It can direct admin action but cannot resolve/open/scan/hash/stream/play/download a legacy path. [ASSUMED]

## Don't Hand-Roll and Pitfalls

| Problem          | Required approach                          |
| ---------------- | ------------------------------------------ |
| transaction      | SQLAlchemy session transaction             |
| containment      | existing resolver and operation capability |
| concurrency      | row locks plus optimistic versions         |
| cancellation     | revision plus safe boundaries              |
| matching         | exact identity/complete-hash uniqueness    |
| DB/files cleanup | owned cleanup intent                       |
| rollback token   | durable server migration row/version       |

Pitfalls: outer-only scan validation can write after removal; marking use after open races rollback; historical Structure A priority guesses when both exist; FK cascades can destroy user value; MySQL/MariaDB DDL cannot be assumed rollbackable; a temporary fallback silently restores legacy authority. [VERIFIED: cited code/docs, except race/outbox details ASSUMED]

## Validation Architecture

| Req          | Wave 0 test                                                                |
| ------------ | -------------------------------------------------------------------------- |
| CAT-01/02    | `backend/tests/endpoints/roms/test_catalog_removal.py`                     |
| CAT-03       | `backend/tests/handler/database/test_storage_lifecycle.py`                 |
| CAT-04       | existing policy denial/inventory tests                                     |
| MIG-01/03/05 | `backend/tests/handler/storage/test_legacy_migration.py`                   |
| MIG-02/04    | `backend/tests/integration/test_legacy_migration.py` plus dialect verifier |

## Resolved Research Questions

1. **Game-level catalog removal retention, RESOLVED by D-22.**
   - Preserve RomM-owned saves, states, and play history for later reconnection.
   - Remove active catalog visibility and association.
   - The planner must define exact retained ownership and identity and every explicitly disposable catalog record and RomM-owned asset.
   - External source content remains untouched.

2. **Automatic legacy grammar scope, RESOLVED by D-23.**
   - Auto-detect only `roms/{Platform.fs_slug}` and `{Platform.fs_slug}/roms`.
   - Configured/custom names, including `games`, require manual mapping.
   - No alias, configured-name, or fuzzy fallback is permitted.
