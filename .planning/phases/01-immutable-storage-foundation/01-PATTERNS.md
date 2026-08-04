# Phase 01: Immutable Storage Foundation - Pattern Map

**Mapped:** 2026-08-04
**Files analyzed:** 12
**Analogs found:** 12 / 12

## Phase Boundary

Backend models, handlers, resolver, errors, migration, and tests only. No API, frontend, consumer cutover, legacy backfill, or mutation policy. Current Alembic head is `0107_roms_dedup_cover_index`; create `0108_*.py`, not research's stale `0063_*.py`.

## File Classification

| File | Role | Flow | Analog |
|---|---|---|---|
| `backend/models/storage.py` | model | CRUD | `backend/models/music.py` |
| `backend/models/platform.py` | model | CRUD | same file |
| `backend/handler/database/storage_handler.py` | service | CRUD/file-I-O | `platforms_handler.py` |
| `backend/handler/database/__init__.py` | provider | request-response | same file |
| `backend/handler/filesystem/storage_resolver.py` | service | file-I-O | `base_handler.py` (anti-analog) |
| `backend/exceptions/storage_exceptions.py` | utility | errors | `fs_exceptions.py` |
| `backend/alembic/env.py` | config | schema discovery | same file |
| `backend/alembic/versions/0108_*.py` | migration | schema CRUD | `0102_music_playlists.py` |
| `backend/tests/models/test_storage.py` | test | schema | `test_music_playlists_handler.py` |
| `backend/tests/handler/database/test_storage_handler.py` | test | CRUD | `test_music_playlists_handler.py` |
| `backend/tests/handler/filesystem/test_storage_resolver.py` | test | file-I-O | `test_base_handler.py` |
| `backend/tests/conftest.py` | test config | cleanup | same file |

## Pattern Assignments

### Models

**Source:** `backend/models/music.py:1-11,19-33,43-60`

```python
class MusicPlaylist(BaseModel):
    __tablename__ = "music_playlists"
    __table_args__ = (UniqueConstraint("user_id", "name", name="unique_music_playlist_user_name"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
```

Use typed `Mapped` declarations, `TYPE_CHECKING`, named constraints, relationships, integer identities, and inherited timestamps (`models/base.py:63-71`). For storage use restrictive root deletion, a string/check allowing only `external_read_only`, unique root path, unique platform mapping, unique root-relative path, and a root-id index. Persist independent reachable/readable/non-writable/check-time/bounded-error fields. In `platform.py`, add only a scalar inverse relationship; retain `fs_slug`.

### Database handler and registry

**Source:** `backend/handler/database/platforms_handler.py:26-53`

```python
class DBPlatformsHandler(DBBaseHandler):
    @begin_session
    def add_platform(self, platform, session: Session = None):
        platform = session.merge(platform)
        session.flush()
        return platform
```

Use `@begin_session`; health-inspect before root persistence. For mappings, first lock every active `StorageRoot` row with `SELECT FOR UPDATE` in ascending ID order, then load all active mappings and their roots, canonically resolve every physical target, and reject equality or either-direction ancestry across root identities and within one root. The stable root row set serializes conflicting first inserts even when no mapping exists; deterministic ordering avoids deadlocks. Recheck before insert/flush; database uniqueness remains the exact same-root/path race backstop. Phase 1 root registration occurs during deployment initialization before mapping writes, so concurrent active-root creation is outside this bounded handler contract. Accept absolute paths only for deployment-owned roots. Beware `merge` resetting defaults (`tests/handler/database/test_platforms_handler.py:5-30`). Register one singleton following `handler/database/__init__.py:1-33`.

### Resolver

**Anti-analog:** `backend/handler/filesystem/base_handler.py:153-159,187-230`

```python
class FSHandler:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
```

Never inherit or instantiate this mutating class. Validate raw text before path construction: reject controls/NUL, backslash, POSIX absolute, Windows drive/device/UNC, traversal, repeated/empty segments, and empty mapping paths. Preserve Unicode/case. Reject symlink root and every component using `lstat`; strict-resolve root/target; enforce `target.relative_to(root)`; require readable directory. Translate OS failures into bounded errors. Health may stat/enumerate and observe `os.access`, but never create, write, lock, rename, copy, or delete. Writable is unsafe. A returned path is only point-in-time safe.

### Exceptions

**Source:** `backend/exceptions/fs_exceptions.py:16-31`. Create a storage base error and subclasses for invalid input, missing/inactive root, missing/non-directory/unreadable target, symlink, escape, and writable-root safety. Messages contain safe IDs/logical values, not raw OS paths. No HTTP mapping.

### Alembic

Import storage models in `backend/alembic/env.py:7-28`. Follow `0102_music_playlists.py:33-109,143-150`: portable explicit columns, named constraints, server-default timestamps, roots before mappings, reverse order on downgrade. Use `down_revision = "0107_roms_dedup_cover_index"`. Do not copy `0062` native-enum branching/empty downgrade. No backfill or filesystem access.

### Tests

Use `pytest.raises(IntegrityError)` from `test_music_playlists_handler.py:1-55` for DB constraints. Resolver test structure follows `test_base_handler.py:90-126`, but asserts typed errors.

Cover valid nested/space/dot/hyphen/Unicode/long names; empty/repeated separators, traversal; POSIX/drive/UNC/device/backslash/control inputs; missing/inactive root, missing/file/unreadable target, writable warning; root/intermediate/leaf/in-root/escaping/broken/loop symlinks; sibling-prefix containment; canonical exact and ancestry overlap within one root and across distinct or nested roots. Include two coordinated sessions attempting conflicting first inserts before any mapping exists, and require one commit plus one bounded overlap rejection after the root-lock recheck.

Snapshot relative name, kind, size, mode, mtime, and link target before/after registration, health, resolution, and mapping. Exclude atime. Add mutation tripwires for mkdir, write-open, tempfile, rename/move/copy, unlink/remove. Mock unreadability if running as root.

Update `tests/conftest.py:90-105` to delete mappings before platforms and roots after mappings; add shared fixtures only when broadly reused.

## Shared Patterns and Pitfalls

- `@begin_session`, atomic validation/insert, then flush.
- Explicit `back_populates` and loading behavior.
- Typed domain errors with safe messages.
- `base_handler.py` and `platforms_handler.py:92-119` are negative patterns because they create directories.
- No endpoints, absolute mapping paths, writable mode, string-prefix containment, symlinks, consumer changes, `fs_slug` backfill, or atime assertions.
- Verify migration upgrade, downgrade one revision, and re-upgrade on MariaDB/PostgreSQL.

## No Analog Found

None. The resolver analog is deliberately negative; use `01-RESEARCH.md` for its standard-library security core.

## Metadata

**Search scope:** backend models, handlers, exceptions, Alembic, tests
**Primary analogs read:** 12
**Pattern extraction date:** 2026-08-04
