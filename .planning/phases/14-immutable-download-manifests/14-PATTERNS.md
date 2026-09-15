# Phase 14: Immutable Download Manifests - Pattern Map

**Mapped:** 2026-09-15
**Files analyzed:** 9 anticipated new/modified files
**Analogs found:** 9 / 9

## File Classification

| New/Modified File                                         | Role                      | Data Flow        | Closest Analog                                                | Match Quality |
| --------------------------------------------------------- | ------------------------- | ---------------- | ------------------------------------------------------------- | ------------- |
| `backend/models/download_manifest.py`                     | model                     | CRUD             | `backend/models/client_token.py` and `backend/models/rom.py`  | role-match    |
| `backend/endpoints/responses/download_manifest.py`        | config/schema             | request-response | `backend/endpoints/responses/rom.py`                          | role-match    |
| `backend/handler/database/download_manifests_handler.py`  | service                   | CRUD             | `backend/handler/database/client_tokens_handler.py`           | role-match    |
| `backend/handler/database/__init__.py`                    | config/provider           | request-response | existing handler singleton registrations                      | exact         |
| `backend/endpoints/download_manifests.py`                 | route/controller          | request-response | `backend/endpoints/roms/pc_component_resources.py`            | role-match    |
| `backend/main.py`                                         | config/route registration | request-response | router registration at `backend/main.py:171-199`              | exact         |
| `backend/alembic/versions/0118_add_download_manifests.py` | migration                 | CRUD             | `backend/alembic/versions/20260831_add_pc_rom_components.py`  | role-match    |
| `backend/tests/models/test_download_manifest.py`          | test                      | CRUD             | `backend/tests/models/test_rom.py`                            | role-match    |
| `backend/tests/endpoints/test_download_manifests.py`      | test                      | request-response | `backend/tests/endpoints/roms/test_pc_component_resources.py` | role-match    |

## Pattern Assignments

### `backend/models/download_manifest.py` (model, CRUD)

**Analogs:** `backend/models/client_token.py:15-35` for user ownership and expiry, and `backend/models/rom.py:232-309` for component/member immutability evidence.

**Ownership and expiry columns** (`backend/models/client_token.py:15-35`):

```python
class ClientToken(BaseModel):
    __tablename__ = "client_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    user: Mapped[User] = relationship(lazy="joined", back_populates="client_tokens")
```

**Hash-backed component member evidence** (`backend/models/rom.py:287-309`):

```python
class RomComponentManifestMember(BaseModel):
    __tablename__ = "rom_component_manifest_members"

    __table_args__ = (
        UniqueConstraint(
            "component_id", "relative_path",
            name="uq_rom_component_manifest_members_component_relative_path",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("rom_components.id", ondelete="CASCADE")
    )
    relative_path: Mapped[str] = mapped_column(String(length=PC_COMPONENT_PATH_MAX_LENGTH))
    size_bytes: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    sha256: Mapped[str] = mapped_column(String(length=64), nullable=False)
```

**Apply:** Persist a manifest header owned by `user_id`, its explicit status enum (`VALID`, `EXPIRED`, `REVOKED`, `SOURCE_CHANGED`), creation/expiry timestamps, plus members that reference the trusted `RomComponentManifestMember`/component identity internally. Copy the explicit uniqueness and `BigInteger`/64-character SHA-256 choices. Persist destination, captured size, digest, and a separately captured strong `snapshot` string, never a filesystem path. Do not make a member's future delivery URL or any server path a persisted client input.

### `backend/endpoints/responses/download_manifest.py` (response schemas, request-response)

**Analog:** `backend/endpoints/responses/rom.py:299-307, 429-441`.

```python
class PcComponentManifestMemberSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    relative_path: str
    size_bytes: int
    sha256: str

class PcComponentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: UTCDatetime | None = None
    relative_path: str
    kind: RomComponentKind
    manifest_members: list[PcComponentManifestMemberSchema]
```

**Apply:** Request models use `ConfigDict(extra="forbid")`, selected component IDs use `Field(ge=1)`, and response schemas remain backend-authoritative Pydantic models. The public member schema exposes only opaque `file_id`/member ID, safe `destination`, `size` (Python `int`, backed by SQL `BigInteger`), `sha256`, quoted strong `snapshot`, and relative `download`. It must not include `Rom.fs_path`, `Rom.fs_name`, `StorageRoot.container_path`, mapped path, or host structure.

### `backend/handler/database/download_manifests_handler.py` (service, CRUD)

**Analog:** `backend/handler/database/client_tokens_handler.py:16-108`.

```python
class DBClientTokensHandler(DBBaseHandler):
    @begin_session
    def add_token(self, token: ClientToken, session: Session = None) -> ClientToken:
        return session.merge(token)

    @begin_session
    def get_token(self, token_id: int, user_id: int | None = None,
                  session: Session = None) -> ClientToken | None:
        stmt = select(ClientToken).where(ClientToken.id == token_id)
        if user_id is not None:
            stmt = stmt.where(ClientToken.user_id == user_id)
        return session.scalar(stmt)

    @begin_session
    def delete_token(self, token_id: int, user_id: int | None = None,
                     session: Session = None) -> int:
        stmt = delete(ClientToken).where(ClientToken.id == token_id)
        if user_id is not None:
            stmt = stmt.where(ClientToken.user_id == user_id)
        return session.execute(stmt.execution_options(
            synchronize_session="evaluate"
        )).rowcount
```

**Apply:** Keep creation, ownership-scoped retrieval, status evaluation/revocation, and selection resolution in a dedicated DB handler with `@begin_session`, rather than querying from the route. Retrieval used by the Phase 14 API must constrain `user_id`; a future Phase 15 delivery check must use the same ownership-scoped lookup. Evaluate expiration as `EXPIRED`, not `SOURCE_CHANGED`. The handler must reject absent, duplicate, unsafe, unresolved, or empty selected components before inserting any usable manifest.

### `backend/handler/database/__init__.py` (provider registration, request-response)

**Analog:** `backend/handler/database/__init__.py:1-53`.

```python
from .client_tokens_handler import DBClientTokensHandler

db_client_token_handler = DBClientTokensHandler()
db_rom_handler = DBRomsHandler()
```

**Apply:** Import the new `DBDownloadManifestsHandler` and expose one `db_download_manifest_handler` singleton. Keep module import and singleton naming consistent with existing endpoint dependencies.

### `backend/endpoints/download_manifests.py` (route/controller, request-response)

**Analog:** `backend/endpoints/roms/pc_component_resources.py:31-52, 237-268`.

```python
def _dlc_component(request: Request, rom_id: int, component_id: int):
    rom = db_rom_handler.get_rom(rom_id)
    if not rom:
        raise RomNotFoundInDatabaseException(rom_id)
    assert_rom_visible(request, rom)
    component = db_rom_handler.get_pc_component_by_id(rom_id, component_id)
    if component is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return rom, component

@protected_route(
    router.get,
    "/{id}/pc-components/{component_id}/manifest-members/{member_id}/content",
    [Scope.ROMS_READ],
)
async def download_component_manifest_member(
    request: Request, id: int, component_id: int, member_id: int
):
    rom, component = _dlc_component(request, id, component_id)
    member = next(
        (item for item in component.manifest_members if item.id == member_id), None
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
```

**Apply:** Use `@protected_route(..., [Scope.ROMS_READ])`, load the requested ROM, call `assert_rom_visible`, and mask missing/non-owned selected entities as 404. Reuse the exact existing component/member relationship, but do not copy this route's `StreamingResponse`, `preflight_mapped_download`, or `_mapped_chunks`: those are Phase 15 transfer behavior. The Phase 14 endpoint creates and returns JSON only. A manifest GET must enforce its recorded `user_id` and convert status to the distinct clear failure response required by DLMT-03.

### `backend/main.py` (route registration, request-response)

**Analog:** `backend/main.py:33-60, 171-199`.

```python
from endpoints.client_tokens import router as client_tokens_router
from endpoints.roms import router as rom_router

app.include_router(client_tokens_router, prefix="/api")
app.include_router(rom_router, prefix="/api")
```

**Apply:** Add the standalone download-manifest router import and `app.include_router(..., prefix="/api")`; do not put its route under the legacy content-streaming router.

### `backend/alembic/versions/0118_add_download_manifests.py` (migration, CRUD)

**Analog:** `backend/alembic/versions/20260831_add_pc_rom_components.py:11-83`.

```python
revision = "0115_pc_rom_components"
down_revision = "0114_legacy_source_identities"

def upgrade() -> None:
    op.create_table(
        "rom_component_manifest_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.String(length=700), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["component_id"], ["rom_components.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

def downgrade() -> None:
    op.drop_table("rom_component_manifest_members")
```

**Apply:** Follow the current Alembic revision chain, timestamp helper, explicit enum creation/drop, named uniqueness constraints, `BigInteger`, and CASCADE FKs. Create download-manifest tables only in RomM's database. No migration may touch, scan, add sidecars to, or otherwise write an external source root. Hand-review MariaDB/MySQL/PostgreSQL compatibility and exercise both upgrade and downgrade.

### `backend/tests/models/test_download_manifest.py` (test, CRUD)

**Analog:** `backend/tests/models/test_rom.py:14-64` and `backend/tests/handler/filesystem/test_roms_handler.py:1710-1833`.

```python
class TestPcComponentManifests:
    @pytest.mark.asyncio
    async def test_explicit_component_folders_build_exact_read_only_manifests(
        self, tmp_path: Path
    ):
        # ... create component files, then scan
        member = component.manifest_members[0]
        assert member.size_bytes == len(expected_bytes)
        assert member.sha256 == hashlib.sha256(expected_bytes).hexdigest()
```

**Apply:** Model tests assert cascade/unique constraints, ownership, status enum, snapshot separate from SHA-256, and 64-bit-capable sizes. Build source fixtures through the existing component scanner, capture a before/after source tree digest, and prove manifest preparation only reads it. Cover ambiguous/missing/unsafe/unready evidence, duplicate selection, expired versus source-changed distinction, and source mutation after capture.

### `backend/tests/endpoints/test_download_manifests.py` (test, request-response)

**Analog:** `backend/tests/endpoints/roms/test_pc_component_resources.py:8-107`.

```python
def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}

response = client.get(
    f"/api/roms/{rom.id}/pc-components/{component.id}/...",
    headers=_headers(access_token),
)
assert response.status_code == status.HTTP_200_OK
```

**Apply:** Use real test-client auth and persisted `RomComponent`/`RomComponentManifestMember` fixtures. Assert whole-game and selected-component output, authentication/scope and hidden-ROM masking, owner-only manifest reads, exact destination/size/SHA-256/snapshot/download fields, and explicit expiry/revocation/source-change failures. Assert JSON never contains `container_path`, `fs_path`, `fs_name`, the temporary fixture root, or a NAS path. Assert no `StreamingResponse`/ZIP behavior is invoked in Phase 14.

## Shared Patterns

### Authorization and visibility

**Sources:** `backend/endpoints/roms/pc_component_resources.py:31-43`, `backend/handler/auth/dependencies.py:91-107`.
**Apply to:** manifest creation and retrieval routes.

```python
rom = db_rom_handler.get_rom(rom_id)
if not rom:
    raise RomNotFoundInDatabaseException(rom_id)
assert_rom_visible(request, rom)

if request.user.is_authenticated and not get_permissions(request).can_see_rom(
    rom.id, rom.platform_id
):
    raise RomNotFoundInDatabaseException(rom.id)
```

Use the `roms.read` coarse route scope plus `assert_rom_visible`. Add persisted manifest `user_id` filtering to ensure the future per-member URL is not a durable grant.

### Read-only hash and source resolution

**Sources:** `backend/handler/filesystem/roms_handler.py:262-317`, `backend/handler/filesystem/storage_resolver.py:270-345`.
**Apply to:** snapshot capture/source evidence validation.

```python
relative_path = PurePosixPath(member.relative_path)
if relative_path.is_absolute() or ".." in relative_path.parts:
    raise ValueError("PC component manifest path is invalid")

with self.open_rom_hash(file_path) as source:
    sha256 = source.hash("sha256")

if storage_root.mode != EXTERNAL_READ_ONLY_MODE:
    raise UnsafeWritableRootError(storage_root.id)
```

Resolve source identity only from persisted trusted components/members and read-capability APIs. Never accept a client source path and never include a resolved source path in a contract. Do not use the legacy direct content route as a manifest-construction dependency.

### Error semantics

**Sources:** `backend/endpoints/roms/pc_component_resources.py:39-43`, `backend/handler/auth/dependencies.py:91-107`.
**Apply to:** selection, ownership, and stale-status paths.

```python
component = db_rom_handler.get_pc_component_by_id(rom_id, component_id)
if component is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
```

Retain 404 masking for invisible/missing resources. Use distinct typed/public status failures for `EXPIRED`, `REVOKED`, and `SOURCE_CHANGED`; never collapse expiry to source change or allow a partial member set.

### Testing and verification commands

```bash
cd backend
uv run pytest tests/models/test_download_manifest.py tests/endpoints/test_download_manifests.py -vv
uv run pytest tests/handler/filesystem/test_roms_handler.py -k PcComponentManifests -vv
uv run alembic upgrade head
uv run alembic downgrade -1
trunk fmt && trunk check
```

The migration commands require the project's configured test/development database. Do not point them at a real NAS mount.

## No Analog Found

| File/Concern                                                                                                         | Role            | Data Flow        | Reason                                                                                                                                                                                                                        |
| -------------------------------------------------------------------------------------------------------------------- | --------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Strong per-member snapshot validator generation and persisted `VALID`/`EXPIRED`/`REVOKED`/`SOURCE_CHANGED` lifecycle | model/service   | transform        | Existing PC manifests capture only relative path, size, and SHA-256. There is no download-manifest lifecycle yet. Implement this from the approved design while retaining the persistence and read-capability patterns above. |
| Public opaque `file_id` plus future relative delivery URL                                                            | response schema | request-response | Existing PC endpoint identifies content through ROM/component/member path parameters and streams immediately. Phase 14 needs a new path-free client contract, while Phase 15 owns actual delivery.                            |

## Metadata

**Analog search scope:** `backend/models`, `backend/endpoints`, `backend/endpoints/responses`, `backend/handler/database`, `backend/handler/filesystem`, `backend/alembic/versions`, `backend/tests`
**Files scanned:** 24
**Pattern extraction date:** 2026-09-15
