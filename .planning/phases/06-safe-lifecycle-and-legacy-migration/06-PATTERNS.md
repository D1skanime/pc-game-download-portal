# Phase 6: Safe Lifecycle and Legacy Migration - Pattern Map

**Mapped:** 2026-08-12
**Files analyzed:** 16 expected new/modified files
**Analogs found:** 16 / 16

## Scope Constraints

Covers D-01 through D-23, CAT-01..04, and MIG-01..05. Phase 6 may change only RomM-owned database, configuration, audit, catalog, assets, and durable job state. It must never move, copy, rename, create, patch, upload, extract, overwrite, or delete source files/directories.

Automatic detection has exactly two literal grammars constructed from persisted `Platform.fs_slug`: `roms/{fs_slug}` and `{fs_slug}/roms`. Do not enumerate identities from folders or use aliases, bindings, versions, configured names such as `games`, case folding, fuzzy matching, or historical priority. Both candidates present means `manual_mapping_required`. Compatibility is expiring status only, never a source fallback.

## File Classification

| Expected File                                                      | Role         | Flow                 | Closest Analog                                       |
| ------------------------------------------------------------------ | ------------ | -------------------- | ---------------------------------------------------- |
| `backend/models/storage.py`                                        | model        | CRUD/state           | same file mapping/audit models                       |
| `backend/models/rom.py`                                            | model        | CRUD                 | same file missing/dependency models                  |
| `backend/alembic/versions/0111_safe_lifecycle_legacy_migration.py` | migration    | batch                | `0109_mapping_administration_contracts.py`           |
| `backend/handler/database/storage_handler.py`                      | service      | transactional CRUD   | same file lifecycle                                  |
| `backend/handler/database/roms_handler.py`                         | service      | CRUD/transform       | same file missing/reconnection                       |
| `backend/handler/storage/legacy_migration.py`                      | service      | bounded file-I/O     | `storage/preview.py` + `database/storage_handler.py` |
| `backend/handler/storage/read_context.py`                          | service      | file-I/O             | same file revision validation                        |
| `backend/endpoints/responses/storage.py`                           | schema       | request-response     | same file                                            |
| `backend/endpoints/storage.py`                                     | controller   | request-response/job | same file admin/preview routes                       |
| `backend/endpoints/roms/__init__.py`                               | controller   | request-response     | current delete route (anti-pattern)                  |
| `backend/tasks/manual/detect_legacy_storage.py`                    | job          | event/batch          | `tasks/manual/preview_mapping.py`                    |
| `backend/tests/handler/database/test_storage_lifecycle.py`         | test         | CRUD/concurrency     | `test_storage_handler.py`                            |
| `backend/tests/handler/storage/test_legacy_migration.py`           | test         | bounded file-I/O     | `test_preview.py`                                    |
| `backend/tests/endpoints/roms/test_catalog_removal.py`             | test         | request-response     | `tests/endpoints/test_storage.py`                    |
| `backend/tests/integration/test_legacy_migration.py`               | test         | integration/restart  | `test_mapped_scan.py`                                |
| `backend/tools/verify_storage_migrations.py` + test                | utility/test | cross-dialect        | same verifier/test                                   |

## Pattern Assignments

### Transactional lifecycle, overlap, and audit

**Analog:** `backend/handler/database/storage_handler.py:112-157,205-253,363-463`

```python
roots = session.scalars(
    select(StorageRoot).where(StorageRoot.active.is_(True))
    .order_by(StorageRoot.id).with_for_update()
).all()
mappings = session.scalars(
    select(PlatformStorageMapping).where(PlatformStorageMapping.active.is_(True))
    .order_by(PlatformStorageMapping.id)
    .with_for_update(of=PlatformStorageMapping)
).all()
```

Copy deterministic lock order: platform, active roots by ID, mappings by ID, then migration/catalog rows by ID. Reuse equal/ancestor/descendant rejection at lines 130-156, immutable snapshots/audit at 215-253, version check at 394-397, and one `@begin_session` transaction.

Extend `_set_inactive` (437-463) so mapping removal also marks retained platform catalog/file rows unreachable in the same transaction. Increment revision and audit, but preserve platform, games, metadata, saves, states, play history, catalog identity, and source (D-01..05).

One confirmed platform equals one independent transaction: lock/revalidate platform, root, overlaps, result versions, catalog matches and migration row; create/activate mapping, reconnect unique identities, audit and write rollback metadata; one commit or no partial state (D-13,14,17,18,20).

### Portable durable schema

**Analog:** `backend/models/storage.py:34-101,104-146`

Use additive bounded scalar fields, named checks/indexes/FKs, and scalar safe snapshots. Persist migration/result ID, platform/mapping/root IDs, exact relative path, observed versions, prior owned-state change set, state/version, actor/timestamps, expiry, nullable `first_used_at`, bounded operation and rollback timestamp. Never persist host paths or raw row dumps. Avoid partial indexes, advisory locks, dialect upserts and in-memory authority.

### First-use CAS and rollback

**Analog:** `backend/handler/storage/read_context.py:55-101`

```python
if (mapping.id != self.mapping_id
    or mapping.version != self.expected_revision
    or not mapping.active):
    raise StaleMappedReadError(self.mapping_id, self.expected_revision)
...
descriptor = _create_external_descriptor(...)
self.boundary()
return open_storage_access(descriptor, operation, logical_path)
```

Scan/hash/stream/play/download atomically compare-and-set first use before first source open, then revalidate exact mapping ID/revision. Rollback locks migration then mapping, requires unused/version match, restores only prior owned state, invalidates revision, audits and marks rolled back atomically. Use-first makes rollback 409; rollback-first makes read stale (D-15,16). Validate before each open, between bounded batches, before reconciliation/owned writes, response commitment, and each multi-file member. RQ cancellation is only latency reduction (D-02).

### Exact detection and bounded preview

**Grammar analog:** `backend/handler/filesystem/platforms_handler.py:75-83`, historical shape only. Do not read mutable `ROMS_FOLDER_NAME`; use literal `roms`.

**Traversal analog:** `backend/handler/storage/preview.py:11-93`

```python
PREVIEW_TIME_BUDGET_SECONDS = 5.0
PREVIEW_ENTRY_BUDGET = 10_000
MAX_PROBLEM_CATEGORIES = 10
...
with context.open(StorageOperation.LIST, directory) as listing:
    entries = listing.list()
```

Reuse dual budgets, lower-bound semantics, capped problems and LIST/STAT capabilities. Start only via explicit authenticated admin POST/manual RQ job, never startup/schedule/heartbeat/watcher (D-06). Return platform identity, reachability/readability, bounded count/bytes, proposed relative mapping, state/problems/timestamps/expiry. Exclude absolute paths, member lists, raw errors and rows. Empty/unreadable/unreachable/unsafe/both-present/active-mapping/overlap stay visible but unselectable (D-07..10,17,18,21,23).

Impact preview adds reconnectable/unmatched counts, bounded problems and planned owned DB effects. Bind confirmation to result/platform/root/path/live versions and expiry, then revalidate (D-12). Preview never scans or mutates catalog/source.

### Status-only legacy compatibility

No source-opening analog exists because Phase 5 closed fixed-layout authority. Status may expose `manual_mapping_required`, bounded reason and created/expires timestamps. It cannot resolve/open/scan/hash/stream/play/download or enqueue a legacy path. This is MIG-05 and D-21.

### Catalog-only removal and retained ownership

**Anti-pattern:** `backend/endpoints/roms/__init__.py:1995-2087`. Current input accepts `delete_from_fs` at 2010-17, deletes source at 2043-62, deletes ROM at 2072-75, then resources at 2077-82. Replace the external contract with typed Remove from catalog accepting IDs only, no source-delete field/branch (CAT-01,02,04; D-22).

**Too-broad DB analog:** `backend/handler/database/roms_handler.py:1737-1746` direct `delete(Rom)` can cascade retained value. Use an explicit ownership service and durable cleanup intent.

Preserve stable reconnectable identity, saves, states and play history. Remove active visibility/association plus explicitly disposable metadata/facets, notes, user props, collection/sibling links and catalog file rows only after retained ownership is detached. Delete only allowlisted RomM-owned resources/assets through trusted destination capabilities. Save/state files remain owned and addressable. `PlaySession.rom_id` currently uses `ON DELETE SET NULL` at `backend/models/play_session.py:41-59`; add durable reconnectable ownership rather than anonymous history. DB and asset cleanup are not ACID together, so persist idempotent cleanup intent with catalog transition, then retry allowlisted cleanup.

**Reconnection analog:** `backend/handler/database/roms_handler.py:2643-2677`

```python
if not (crc_hash and md5_hash and sha1_hash):
    return None
matches = session.scalars(
    select(Rom).where(
        Rom.platform_id == platform_id,
        Rom.missing_from_fs.is_(True),
        Rom.crc_hash == crc_hash,
        Rom.md5_hash == md5_hash,
        Rom.sha1_hash == sha1_hash,
    ).limit(2)
).all()
return matches[0] if len(matches) == 1 else None
```

Prefer unique exact normalized logical identity; moved content may use complete CRC32+MD5+SHA1 uniqueness. Never basename/display/provider/partial hash/alias/first match. Ambiguous/missing remains unreachable (D-03,19).

### Thin API and job contracts

**Analog:** `backend/endpoints/storage.py:206-216,284-298,467-518,521-645`. Copy admin-before-observation, protected scopes, typed models, safe allowlisted 409s, request actor identity, and POST-enqueue/GET-status. Preview enqueue at 467-494 binds ID+revision and timeout/TTL; detection binds only IDs/versions, never paths. Removal retains expected-version input and returns bounded retention/unreachable/cancellation consequences (D-04).

### Alembic and dialect proof

**Analog:** `backend/tools/verify_storage_migrations.py`, its tests, and migration 0109. Extend it for pristine and seeded-0110 upgrade, downgrade and re-upgrade on MariaDB, MySQL and PostgreSQL. Prove durable state across API/worker restart, rollback after failure at every flush, and downgrade preflight before MySQL/MariaDB DDL. Do not assume transactional DDL. Use barriers, not sleeps, for migrate/migrate, migrate/create, remove/read, rollback/first-use and confirm/lifecycle races.

## Test Assignments

- `test_storage_lifecycle.py`: follow `test_storage_handler.py:399-520`; assert version/overlap/rollback, retained catalog/saves/states/history, unreachable state, stale jobs and no source mutation.
- `test_legacy_migration.py`: follow `test_preview.py` and resolver tests; cover exactly two grammars, both-present, aliases, variants, bindings, `games`, empty/unreadable/symlink/traversal, budgets, expiry/replay and mutation sentinels.
- `test_catalog_removal.py`: seed every dependency, owned asset, save/state and play session; assert exact disposable/retained sets, reconnectability, cleanup retry and identical writable/read-only source manifests.
- Endpoint/OpenAPI: follow `tests/endpoints/test_storage.py:300-430,560-610`; auth before observation, safe errors, stale 409, independent confirmations, no `delete_from_fs`, host path or row dump.
- Integration: follow `tests/integration/test_mapped_scan.py`; detection-impact-confirm-restart-read, rollback/use race, reconnection, stale queued work and manual status with no fallback. Capture source path/type/mode/size/hash/symlink before/after; atime remains Phase 9.

## Shared Patterns

- Safe errors: `backend/endpoints/storage.py:168-216,284-298`; stable code/message/allowlisted IDs only.
- Source immutability: all external reads through `MappingReadContext` and operation capabilities; detection LIST/STAT only; cleanup trusted owned destinations only.
- Revision authority: `read_context.py:55-101`; missing/inactive/changed/unhealthy fails closed and never redirects.
- Overlap/concurrency: `storage_handler.py:112-157,363-397`; ordered locks, optimistic versions, last-moment validation.

## No Analog Found

No exact analog exists for retained save/state ownership after catalog removal, durable rollback-before-first-use CAS, or expiring status-only compatibility. Compose the transaction, revision, preview, audit and cleanup-intent patterns above. Never fill this gap with a legacy source fallback.

## Decision Coverage

| Decisions | Coverage                                                              |
| --------- | --------------------------------------------------------------------- |
| D-01..05  | soft lifecycle, retention, revision invalidation, source immutability |
| D-06..10  | explicit job, exact grammars, bounded safe results                    |
| D-11..16  | owned-state-only, per-platform atomicity, rollback/use CAS            |
| D-17..21  | active/overlap locks, unique match, retry, manual status, no fallback |
| D-22      | retained saves/states/history, allowlisted owned cleanup              |
| D-23      | only `roms/{fs_slug}` and `{fs_slug}/roms`                            |

## Metadata

**Search scope:** backend models/handlers/endpoints/tasks/alembic/tools/tests, Phases 3-5 artifacts, codebase maps.
**Extraction date:** 2026-08-12
