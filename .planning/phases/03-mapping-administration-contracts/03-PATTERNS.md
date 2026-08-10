# Phase 3: Mapping Administration Contracts - Pattern Map

**Mapped:** 2026-08-10
**Files analyzed:** 14
**Analogs found:** 14 / 14

## File Classification

| New/Modified File                                                   | Role               | Data Flow        | Closest Analog                         | Match      |
| ------------------------------------------------------------------- | ------------------ | ---------------- | -------------------------------------- | ---------- |
| `backend/models/storage.py`                                         | model              | CRUD             | existing storage models                | exact      |
| `backend/alembic/versions/0109_mapping_administration_contracts.py` | migration          | transform        | `0108_immutable_storage_foundation.py` | exact      |
| `backend/exceptions/storage_exceptions.py`                          | utility            | request-response | existing storage hierarchy             | exact      |
| `backend/handler/filesystem/storage_resolver.py`                    | service            | file-I/O         | existing resolver                      | exact      |
| `backend/handler/database/storage_handler.py`                       | service            | CRUD             | existing `DBStorageHandler`            | exact      |
| `backend/endpoints/responses/storage.py`                            | model              | request-response | `responses/permission.py`, `base.py`   | role-match |
| `backend/endpoints/storage.py`                                      | controller         | request-response | `endpoints/permissions.py`             | role-match |
| `backend/main.py`                                                   | config             | request-response | router registration block              | exact      |
| `backend/tests/models/test_storage.py`                              | test               | CRUD             | existing storage model tests           | exact      |
| `backend/tests/handler/database/test_storage_handler.py`            | test               | CRUD             | existing lock/overlap/tripwire tests   | exact      |
| `backend/tests/handler/filesystem/test_storage_resolver.py`         | test               | file-I/O         | existing property/adversarial tests    | exact      |
| `backend/tests/endpoints/test_storage.py`                           | test               | request-response | permission endpoint tests              | role-match |
| `backend/tools/verify_storage_migrations.py`                        | utility            | batch            | existing multi-dialect verifier        | exact      |
| `frontend/src/__generated__/`                                       | generated contract | transform        | existing OpenAPI pipeline              | generated  |

## Pattern Assignments

### Models and migration

**Targets:** `backend/models/storage.py`, `backend/alembic/versions/0109_mapping_administration_contracts.py`

**Analogs:** `backend/models/storage.py` lines 30-95 and `backend/alembic/versions/0108_immutable_storage_foundation.py` lines 8-100.

```python
class StorageRoot(BaseModel):
    __tablename__ = "storage_roots"
    __table_args__ = (
        CheckConstraint(
            f"mode = '{EXTERNAL_READ_ONLY_MODE}'",
            name="ck_storage_roots_external_read_only_mode",
        ),
        UniqueConstraint("container_path", name="uq_storage_roots_container_path"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
```

```python
import sqlalchemy as sa
from alembic import op

revision = "0108_storage_foundation"
down_revision = "0107_roms_dedup_cover_index"

op.create_table(
    "storage_roots",
    sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.PrimaryKeyConstraint("id", name="pk_storage_roots"),
)
op.create_index(
    "ix_platform_storage_mappings_storage_root_id",
    "platform_storage_mappings",
    ["storage_root_id"],
)
```

Add bounded constants, typed `active` and integer `version`, portable indexes, and `StorageMappingAudit`. Audit actor/mapping/platform attribution must be immutable scalar snapshots where deletion must not erase history. Migration 0109 backfills existing mappings to active version 1 before non-null enforcement, removes both unconditional unique constraints, creates audit storage, and reverses in dependency order. Do not rely on PostgreSQL-only partial indexes.

**Gap:** No existing append-only model captures fixed old/new storage snapshots. Follow RESEARCH.md Pattern 6 and expose listing only.

### Storage exceptions

**Target/analog:** `backend/exceptions/storage_exceptions.py` lines 1-18.

```python
class StorageResolutionError(Exception):
    code = "storage_resolution_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class InvalidRelativePathError(StorageResolutionError):
    code = "invalid_relative_path"

    def __init__(self):
        super().__init__("Storage path must be a safe relative path")
```

Preserve class-level codes and bounded defaults. Add missing-mapping, stale-version, active-duplicate, invalid-cursor, and safe filesystem variants. Store allowlisted IDs as attributes. Do not copy the current overlap message at lines 84-90 outward because it embeds a relative path. No relative/container path, raw `OSError`, or SQL may enter a response.

### Filesystem resolver

**Target/analog:** `backend/handler/filesystem/storage_resolver.py`.

**Lexical validation** (lines 27-50):

```python
def normalize_relative_path(raw: str, *, allow_root: bool = False) -> str:
    if raw == "":
        if allow_root:
            return ""
        raise InvalidRelativePathError
    if "\\" in raw or raw.startswith("/"):
        raise InvalidRelativePathError
    if PureWindowsPath(raw).drive:
        raise InvalidRelativePathError
    segments = raw.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise InvalidRelativePathError
    return raw
```

**Symlink and containment** (lines 123-157):

```python
def _reject_component_symlinks(root: Path, relative_path: str) -> Path:
    candidate = root
    for segment in relative_path.split("/"):
        candidate = candidate / segment
        metadata = candidate.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise UnsafeSymlinkError
    return candidate

try:
    resolved_target.relative_to(root)
except ValueError as error:
    raise StorageEscapeError from error
```

Extract a health snapshot/value path from `check_storage_root_health` (lines 53-88) so GET does not dirty ORM state. Browse through existing root validation, use `os.scandir()`, `lstat`, reject symlinks, enumerate immediate directories only, sort deterministically, cap limit, and return only name, normalized relative path, and navigable.

**Gap:** No query-bound filesystem cursor exists. Use versioned bounded base64/JSON continuation state bound to root ID and normalized parent. It is never authorization.

### Database handler

**Target/analog:** `backend/handler/database/storage_handler.py`.

**Deterministic locks** (lines 85-119):

```python
roots = session.scalars(
    select(StorageRoot)
    .where(StorageRoot.active.is_(True))
    .order_by(StorageRoot.id)
    .with_for_update()
).all()
mappings = session.scalars(
    select(PlatformStorageMapping)
    .options(selectinload(PlatformStorageMapping.storage_root))
    .with_for_update(of=PlatformStorageMapping)
).all()
```

**Transaction reuse:** `backend/decorators/database.py` lines 10-20.

```python
def begin_session(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if kwargs.get("session") is not None:
            return func(*args, **kwargs)
        with sync_session.begin() as s:
            kwargs["session"] = s
            return func(*args, **kwargs)
```

Extend `DBStorageHandler`, never create parallel persistence. Filter conflicts to active mappings, preserve deterministic platform/root/mapping lock order, compare `expected_version` under lock, increment on update/deactivate/reactivate, and append audit in the same session. Test and preview reuse validation without add, flush, mutation, or audit. Translate named integrity failures only, matching lines 40-50 and 147-154.

**Gap:** No filter-bound audit keyset helper exists. Implement `created_at DESC, id DESC` continuation bound to normalized filters.

### Response schemas

**Target:** `backend/endpoints/responses/storage.py`

**Analogs:** `backend/endpoints/responses/base.py` lines 8-18 and `permission.py` lines 95-113, 159-188.

```python
UTCDatetime = Annotated[datetime, PlainSerializer(_serialize_utc_datetime)]

class BaseModel(PydanticBaseModel):
    pass

class PermissionScopeSchema(BaseModel):
    kind: Literal["global", "platform", "collection", "rom"] = "global"
    id: int | None = None

class PermissionGroupSchema(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}
```

Create explicit root-health, browse-page, mapping, mapping-test, preview, audit-page, and safe-conflict models. Use `Field` bounds for limits, cursor, relative path, actor snapshot, and messages, plus `Literal` or `StrEnum` for stable values. Never expose `container_path` or unrestricted ORM serialization.

### Storage endpoints and registration

**Targets:** `backend/endpoints/storage.py`, `backend/main.py`

**Analog:** `backend/endpoints/permissions.py` lines 1-30, 61-65, 98-118.

```python
from decorators.auth import protected_route
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_admin
from utils.router import APIRouter

router = APIRouter(prefix="/permissions", tags=["permissions"])

@protected_route(router.get, "/catalog", [Scope.USERS_READ])
def get_permission_catalog(request: Request) -> PermissionCatalogSchema:
    assert_admin(request)
    return PermissionCatalogSchema(...)
```

```python
@protected_route(
    router.post, "/groups", [Scope.USERS_WRITE], status_code=status.HTTP_201_CREATED
)
def create_permission_group(
    request: Request, body: PermissionGroupCreate
) -> PermissionGroupSchema:
    assert_admin(request)
    group = db_permission_handler.create_group(...)
    return _group_schema(group)
```

Use one `/storage` router. Apply both coarse `@protected_route` and `assert_admin(request)` before any lookup or I/O. Endpoints only validate, capture immutable actor identity, delegate, translate typed domain errors to the safe detail, and serialize. Keep read, browse, test, preview, create/update, deactivate/reactivate, and audit contracts distinct.

Register like `backend/main.py` lines 48 and 196:

```python
from endpoints.permissions import router as permissions_router
app.include_router(permissions_router, prefix="/api")
```

Import/include `storage_router` once. Regenerate OpenAPI types, never hand-edit generated files.

### Tests

**Targets:** storage model, handler, resolver, endpoint, and migration verifier tests.

**Analogs:**

- `test_storage_resolver.py` lines 34-111: traversal and safe-message matrices.
- Same file lines 132-161: manifest and mutation tripwires.
- `test_storage_handler.py` lines 83-169: no-mutation, overlaps, rollback, sibling success.
- Same file lines 195-214: bounded persistence error.
- `test_storage.py` lines 35-82: defaults and column inspection.
- `test_permissions_me.py` lines 23-45: anonymous 401 and role responses.
- `test_permissions_admin.py` lines 44-53: non-admin 403 matrix, lines 62-102: CRUD calls.
- `verify_storage_migrations.py` lines 20-53, 93-110, 149-181: MariaDB/MySQL/PostgreSQL upgrade/downgrade/re-upgrade.

```python
@pytest.mark.parametrize("candidate", ["games", "games/child", "games/child/deeper"])
def test_overlap_equal_ancestor_descendant_and_rollback(...):
    with pytest.raises(StorageMappingOverlapError):
        db_storage_handler.save_mapping(...)

assert unrelated_root not in str(exc_info.value)
assert len(str(exc_info.value)) <= 200
```

```python
def test_requires_auth(client):
    assert client.get("/api/permissions/me").status_code == 401

def test_non_admin_forbidden(client, viewer_access_token):
    h = {"Authorization": f"Bearer {viewer_access_token}"}
    assert client.get("/api/permissions/groups", headers=h).status_code == 403
```

Test observable contracts: 401 before enumeration, 403 for non-admin on every route, stable 409 codes, current version on stale write, no sentinel path leakage, cursor replay rejection across roots/parents/filters, active-only conflicts, sibling success, atomic audit, immutable actor snapshots, catalog preservation, and mutation tripwires. Add real MariaDB/PostgreSQL concurrent coverage. For migration 0109, baseline/downgrade against 0108, seed existing mappings, assert active/version backfill, audit schema, and removed unconditional constraints across all three dialects.

## Shared Patterns

### Authentication

Use `protected_route` plus `assert_admin` from `backend/handler/auth/dependencies.py` lines 93-101. This preserves anonymous 401 versus authenticated 403.

### Transactions

Use `@begin_session`, caller-provided sessions, deterministic lock order, and one atomic mapping-plus-audit transaction. Endpoints do not open sessions.

### Safe errors

Domain exceptions own codes and bounded defaults. A storage-local translator builds allowlisted Pydantic detail from typed attributes. Raw exception strings are never serialized.

### Containment

Normalize before I/O, reject absolute/Windows/control/dot forms, validate active read-only roots, reject component symlinks, resolve strictly, assert containment, then check readability.

### OpenAPI

Backend route/schema annotations are authoritative. Register in `main.py`, regenerate `frontend/src/__generated__/`, and typecheck. Generated output is not manually edited.

## No Analog Found

| Concern                         | Role             | Data Flow        | Reason                                                                      |
| ------------------------------- | ---------------- | ---------------- | --------------------------------------------------------------------------- |
| Query-bound directory cursor    | utility          | file-I/O         | No cursor binds root ID and parent path with bounded validation.            |
| Filter-bound audit cursor       | utility/service  | CRUD             | Generic pagination lacks the required descending tuple and filter binding.  |
| Append-only mapping audit       | model            | CRUD             | No model captures immutable actor and fixed before/after snapshots.         |
| Typed storage conflict envelope | model/controller | request-response | Existing string HTTP errors are less strict than Phase 3 path-safety rules. |

Use `03-RESEARCH.md` patterns for these gaps and keep them storage-local.

## Planner Boundaries

- Backend/OpenAPI only, no v2 UI or scanner cutover.
- Test and preview are read-only and non-audited.
- Removal deactivates mapping configuration, never source or catalog data.
- Only active mappings block reuse and overlap.
- No response/audit exposes container, NAS, another mapping path, raw OS errors, or SQL.
- Filesystem cursors promise deterministic continuation for unchanged content, not a NAS snapshot.

## Metadata

**Analog search scope:** backend models, migrations, exceptions, database/filesystem handlers, endpoints/responses, tests, tools, and `main.py`

**Primary analogs read:** 14 files

**Pattern extraction date:** 2026-08-10
