# Phase 1: Immutable Storage Foundation - Research

**Researched:** 2026-08-04
**Domain:** Portable persistence and non-mutating filesystem path resolution
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### External library ownership

- D-01: The real games collection is an archive owned outside RomM. RomM adapts to its existing directory structure and never requires users to copy, move, rename, or reorganize it.
- D-02: Deployment mounts one shared NAS games root at a configured container path, for example `/volume1/Mediathek/Games:/romm/library:ro`.
- D-03: Every external library root uses the immutable mode `external_read_only`. Phase 1 provides no writable mode and no UI or configuration toggle that can enable writes.
- D-04: RomM-owned database state, resources, assets, configuration, cache, hashes, scan state, temporary files, and audit data remain outside the external root.
- D-05: The storage foundation must not create a root or any directory during initialization or health inspection. A missing or unreadable deployment mount fails closed with a controlled status.

#### Storage-root model

- D-06: Add a persistent storage-root entity with at least ID, display name, container path, mode, active state, creation timestamp, and update timestamp.
- D-07: The container path is deployment-owned. Normal administration must not accept arbitrary absolute host or system paths.
- D-08: The schema must allow multiple storage roots in future, although the first deployment uses one NAS root.
- D-09: Root status reports reachable, readable, non-writable, last checked time, and a safe error without mutating the root.
- D-10: A root registered as `external_read_only` is expected to be non-writable. A writable observation is a warning or failed safety state, never permission to write.

#### Platform-storage mapping model

- D-11: Each platform maps to an existing relative subdirectory of a storage root through a dedicated persistent entity.
- D-12: Store `storage_root_id` plus normalized `relative_path`; never store a NAS host path or a composed absolute container path in the mapping.
- D-13: Phase 1 permits at most one active mapping per platform.
- D-14: Multiple platforms may map to distinct directories below the same root.
- D-15: Ancestor, descendant, duplicate, and otherwise unsafe overlaps are rejected by default.
- D-16: Saving or validating a mapping must not create, move, rename, copy, or otherwise change filesystem content.
- D-17: Mapping targets must exist, be readable directories, and belong to an active root.

#### Central safe resolution

- D-18: All external-library path resolution uses one central, non-mutating resolver rather than the current directory-creating `FSHandler` constructor behavior.
- D-19: Resolver input is a logical relative path only. Reject absolute POSIX paths, Windows drive paths, UNC paths, parent traversal, invalid empty segments, NUL/control input, and separator-confusable escape forms.
- D-20: Resolve root and target canonically and verify containment after symlink resolution. Lexical `startsWith` or string-prefix checks are not sufficient.
- D-21: Platform mappings resolve to directories only.
- D-22: Milestone 1 rejects symlinks by default. Supporting a verified in-root symlink later requires an explicit decision and dedicated race-safe tests.
- D-23: Path behavior must support spaces, dots, hyphens, umlauts, Unicode, long directory names, and nested subdirectories.
- D-24: Controlled domain errors distinguish invalid input, missing root, inactive root, missing target, non-directory target, unreadable target, unsafe symlink, escape attempt, and unsafe writable-root observation without leaking unrelated filesystem paths.

#### Database and compatibility

- D-25: Use the existing SQLAlchemy 2 and Alembic conventions and preserve MariaDB, MySQL, and PostgreSQL portability.
- D-26: The migration adds the new schema only. It does not create, rename, move, copy, or delete library files or directories.
- D-27: Do not perform speculative legacy backfill in Phase 1. The legacy migration and fallback strategy is implemented in Phase 6 after read paths have a safe mapping contract.
- D-28: Use integer identities and relationship/index conventions consistent with the existing RomM models unless concrete repository constraints require another existing convention.

#### Security and evidence

- D-29: Docker `:ro` is defense in depth, not the application policy. Phase 1 models immutability and proves non-mutating resolution even against a writable test fixture.
- D-30: Unit coverage includes valid root, normal and nested directories, spaces, umlauts, Unicode, empty path behavior, traversal, repeated traversal, absolute POSIX, drive, UNC, missing root, missing target, file target, inactive root, read-only status, writable-root warning, and symlink escape.
- D-31: Tests compare filesystem state before and after root registration, health inspection, and mapping validation to prove that Phase 1 creates no source files or directories.
- D-32: Access-time changes depend on NAS and mount policy. Documentation later recommends `noatime` or a NAS-specific equivalent when metadata-level immutability is required.

#### Frontend and later work

- D-33: The fork is v2-only, but Phase 1 contains no frontend feature work and does not remove v1. The bounded v1 removal remains Phase 8.
- D-34: Team4s is a read-only design-principles reference only. It is never modified, copied as React code, restarted, or made a build/runtime dependency.
- D-35: PC components, manifests, resumable downloads, Windows client work, upload, source organization, ZIP redesign, and install planning are outside Phase 1.

### the agent's Discretion

- Exact model and module filenames within the established backend conventions.
- Whether root health is persisted directly on the root row or through a separate status record, provided the stored result remains safe, bounded, and testable.
- Exact enum persistence strategy, provided it remains portable across supported databases and returns a stable API string later.
- Exact domain exception hierarchy and repository method names.
- Transaction and eager-loading details consistent with existing database handlers.
- Whether the empty relative path represents the root itself for internal resolution. Platform mappings must still resolve to an explicitly valid directory according to the final model contract.

### Deferred Ideas (OUT OF SCOPE)

- Central operation policy and mutation-path enforcement: Phase 2.
- Storage-root and mapping administration APIs, browsing, and audit: Phase 3.
- Team4s-informed RomM v2 design contract: Phase 4.
- Preview, scanner, watcher, hashing, streaming, and download cutover: Phase 5.
- Catalog-only removal and legacy migration: Phase 6.
- V2 administration UI: Phase 7.
- Complete v1 removal: Phase 8.
- Production-like nginx, worker, real NAS, atime, and full immutability evidence: Phase 9.
- PC components, manifests, resumable downloads, Windows client work, uploads, source reorganization, ZIP redesign, and install planning: later milestones.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ROOT-01 | Register one deployment-mounted NAS root as active. | Add `StorageRoot`; registration persists configuration only and health-inspects without creation. |
| ROOT-02 | External roots only use `external_read_only`. | Persist a stable string with a model default and DB constraint; expose no writable enum value. |
| ROOT-03 | Report reachability, readability, non-writability, and check time without creation. | Pure `stat`/directory-open/access inspection plus bounded persisted health fields. |
| ROOT-04 | Keep deployment container root separate from relative mappings. | Separate root and mapping tables joined by FK. |
| PATH-01 | Accept normalized relative paths and reject cross-dialect escape forms. | A pure lexical normalization stage precedes filesystem calls. |
| PATH-02 | Canonicalize and prove post-symlink containment. | `resolve(strict=True)` plus `relative_to`, then component `lstat` rejection. |
| PATH-03 | Accept only readable existing directories under active roots. | Typed resolver preconditions and domain errors. |
| PATH-04 | Support normal Unicode/nested names without string-prefix checks. | Preserve segment text and use path-aware containment. |
| PATH-05 | Reject symlinks by default. | Reject root and every candidate component identified by `lstat`. |
| TEST-01 | Cover adversarial path classes. | Dedicated real-filesystem resolver and health test matrix, including no-mutation snapshots. |
</phase_requirements>

## Summary

Implement this phase as an additive backend storage package, not as an extension of the current mutation-rich filesystem handler. The current `FSHandler.__init__` resolves its path and immediately calls `mkdir(parents=True, exist_ok=True)`, while `validate_path()` intentionally falls back to lexical containment when it sees a symlink. Both conflict directly with the locked external-root contract. [VERIFIED: `backend/handler/filesystem/base_handler.py`]

Use two new ORM entities: `StorageRoot` and `PlatformStorageMapping`. Keep health fields on `StorageRoot` for the smallest atomic model. Store the root's configured container path only on `StorageRoot`; store a normalized POSIX relative string only on `PlatformStorageMapping`. Enforce one mapping per platform and exact `(storage_root_id, relative_path)` uniqueness in the database; enforce ancestor/descendant overlap in application logic in the same transaction because portable relational constraints cannot express path ancestry cleanly. [VERIFIED: `.planning/phases/01-immutable-storage-foundation/01-CONTEXT.md`] [CITED: https://docs.sqlalchemy.org/en/20/core/constraints.html]

Build resolution as explicit stages: lexical validation, strict canonical root resolution, component-by-component symlink rejection, strict target resolution, path-aware containment, directory/readability checks, and a bounded result/error. `Path.resolve(strict=True)` and `Path.relative_to()` establish point-in-time canonical containment but do not make a later path-based open race-free. Phase 1 should document this limit and keep the resolver non-mutating; descriptor-relative `openat`/`dir_fd` plus `O_NOFOLLOW` belongs in the later read/open boundary, because this phase resolves directories and does not yet consume source files. [CITED: https://docs.python.org/3.13/library/pathlib.html#pathlib.Path.resolve] [CITED: https://docs.python.org/3.13/library/os.html#files-and-directories]

**Primary recommendation:** Add portable root/mapping schema and a standalone pure/non-mutating resolver with typed errors, then gate the phase on real-filesystem adversarial tests and upgrade/downgrade migration checks. [VERIFIED: repository and phase context]

## Project Constraints (from AGENTS.md)

- Read and follow `CLAUDE.md`. [VERIFIED: `AGENTS.md`]
- Backend work follows the endpoint to handler to database/filesystem layering and uses `@begin_session` for database handlers. [VERIFIED: `.claude/skills/backend-development/SKILL.md`]
- SQLAlchemy/Alembic migrations must work on MariaDB, MySQL, and PostgreSQL and must be hand-reviewed. [VERIFIED: `.claude/skills/backend-development/SKILL.md`]
- New logic travels with tests; run backend tests through `uv run pytest`. [VERIFIED: `CLAUDE.md`]
- Run formatting/linting through Trunk, never bypass hooks, never commit secrets, and write English without em dashes. [VERIFIED: `CLAUDE.md`]
- Phase 1 has no endpoint or response-schema change, so frontend type generation is not part of this phase. [VERIFIED: phase boundary]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Root and mapping identity | Database / Storage | API / Backend | SQL owns durable identity; backend owns invariants. |
| Root registration and health | API / Backend | Database / Storage | Handler performs non-mutating inspection and persists bounded state. |
| Relative-path normalization | API / Backend | - | Pure server-side validation must precede filesystem access. |
| Canonical containment and symlink rejection | API / Backend | Database / Storage | Resolver combines trusted root identity with untrusted logical path. |
| Uniqueness and overlap | Database / Storage | API / Backend | DB handles exact conflicts; handler handles path ancestry. |
| Adversarial evidence | API / Backend | Database / Storage | Tests exercise real filesystem objects and portable schema. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.13` | `pathlib`, `os`, `stat`, typed errors | Already required; no new filesystem dependency is needed. [VERIFIED: `pyproject.toml`] |
| SQLAlchemy | `~=2.0` project constraint | ORM entities, FKs, constraints, transactions | Existing persistence layer and supported dialect abstraction. [VERIFIED: `pyproject.toml`] |
| Alembic | `~=1.16` project constraint | Additive schema migration | Existing migration system uses online/offline batch rendering. [VERIFIED: `pyproject.toml`, `backend/alembic/env.py`] |
| pytest | `~=9.0` project constraint | Unit and migration verification | Existing async-enabled backend test framework. [VERIFIED: `pyproject.toml`, `backend/pytest.ini`] |
| Hypothesis | `~=6.0` project constraint | Optional segment/property coverage | Already installed and suited to lexical normalization invariants. [VERIFIED: `pyproject.toml`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `pathlib` | Python 3.13 | Strict canonicalization and path-aware containment | Every resolution after lexical validation. [CITED: https://docs.python.org/3.13/library/pathlib.html] |
| stdlib `os`/`stat` | Python 3.13 | `lstat`, permission observation, optional descriptor-relative prototype | Symlink checks and health observation. [CITED: https://docs.python.org/3.13/library/os.html#files-and-directories] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Standalone storage resolver | Subclass `FSHandler` | Rejected because inherited initialization and public methods carry mutation capability. [VERIFIED: `backend/handler/filesystem/base_handler.py`] |
| String mode with DB check | Native DB enum | Native enum migration/drop behavior differs across PostgreSQL and MySQL; a bounded string is simpler for the single locked value. [VERIFIED: `backend/alembic/versions/0062_rom_file_category_enum.py`] |
| Path-aware containment | `str.startswith` | Prefixes confuse siblings such as `/library` and `/library-old`; `relative_to` expresses component containment. [CITED: https://docs.python.org/3.13/library/pathlib.html#pathlib.PurePath.relative_to] |

**Installation:** No new package installation. [VERIFIED: repository stack]

## Architecture Patterns

### System Architecture Diagram

```text
deployment container path + logical relative path
             |
             v
       database identity lookup
       root active? mode fixed?
             |
             v
       lexical normalizer
  reject absolute/drive/UNC/control/empty/.. 
             |
             v
 strict root resolve -> component lstat -> reject any symlink
             |
             v
 strict target resolve -> target.relative_to(root)
             |
      +------+------+
      |             |
 directory/readable  controlled domain error
      |
      v
 ResolvedStoragePath (root id, normalized relative path, canonical Path)
```

### Recommended Project Structure

```text
backend/
├── models/storage.py                         # StorageRoot and PlatformStorageMapping
├── handler/database/storage_handler.py       # persistence and overlap transaction
├── handler/filesystem/storage_resolver.py    # no constructor side effects, no write methods
├── exceptions/storage_exceptions.py          # bounded domain taxonomy
├── alembic/versions/0063_*.py                 # additive tables only
└── tests/
    ├── models/test_storage.py
    ├── handler/database/test_storage_handler.py
    └── handler/filesystem/test_storage_resolver.py
```

Alembic must import the new models in `backend/alembic/env.py`; otherwise `BaseModel.metadata` autogeneration will not see their tables. [VERIFIED: `backend/alembic/env.py`]

### Pattern 1: Separate lexical normalization from filesystem resolution

**What:** Normalize a string into one canonical POSIX-style relative representation before joining it to a root. Reject NUL and C0/DEL controls, `PurePosixPath.is_absolute()`, leading `/`, any backslash, Windows drive/device/UNC syntax using `PureWindowsPath`, empty internal segments, and `..`; remove `.` segments; preserve case and Unicode text. [CITED: https://docs.python.org/3.13/library/pathlib.html]

**When to use:** On every stored mapping and every later logical child path. Store only the normalizer output. [VERIFIED: phase decisions D-12, D-19]

```python
# Source: Python 3.13 pathlib documentation
def normalize_relative_path(raw: str, *, allow_root: bool = False) -> str:
    # Exact implementation should explicitly inspect raw separators before
    # constructing PurePosixPath, because PurePosixPath collapses some syntax.
    ...
```

Do not URL-decode in this layer. HTTP decoding belongs at the endpoint boundary in Phase 3; `%2e%2e` is a legal literal filesystem name unless the transport has decoded it. [ASSUMED]

### Pattern 2: Canonical containment plus strict no-symlink walk

**What:** Resolve the configured root with `strict=True`; reject if the root itself is a symlink; walk each candidate component with `lstat()` and reject links; then resolve the target strictly and require `target.relative_to(root)`. Check existence through strict resolution, then directory type and readability. [CITED: https://docs.python.org/3.13/library/pathlib.html#pathlib.Path.resolve]

**When to use:** Root registration/health and mapping validation. Do not reuse `FSHandler`, call `mkdir`, touch a probe, acquire a file lock, or invoke `os.walk`. [VERIFIED: phase decisions D-05, D-16, D-18]

### Pattern 3: Health is observation, not a write probe

**What:** Persist `reachable`, `readable`, `non_writable`, `last_checked_at`, and a bounded error code/message. Determine reachability/type with strict resolution/stat, readability by opening the directory for enumeration or using an equivalent operation the process actually needs, and writability as an observation such as `os.access(path, os.W_OK, effective_ids=True)` where supported. Never prove writability by creating a file. [CITED: https://docs.python.org/3.13/library/os.html#os.access]

**When to use:** Registration and explicit health refresh. A writable observation maps to an unsafe status/error, not a writable capability. Permission bits alone are insufficient because ACLs, effective identity, root, and mount flags affect access. [CITED: https://docs.python.org/3.13/library/os.html#os.access]

### Pattern 4: Portable schema with layered invariants

**What:** Use integer autoincrement IDs and `BaseModel` timestamps. Recommended root fields are bounded `String` name/container_path/mode/error_code/error_message, non-null booleans, and nullable timezone-aware last-check timestamp. Mapping fields are integer FKs, bounded `String` relative path, and active state. Add named FK/unique/index constraints. [VERIFIED: `backend/models/base.py`, `backend/models/platform.py`] [CITED: https://docs.sqlalchemy.org/en/20/core/constraints.html]

**When to use:** Create root first, then mapping. Use `ondelete="RESTRICT"` (or omit cascades and require explicit deletion) so deleting a root cannot silently delete mappings. Keep `Platform.fs_slug` unchanged. [VERIFIED: phase boundary and existing model]

Recommended constraints:

- `storage_roots.mode` constrained to `external_read_only`. [VERIFIED: D-03]
- unique root identity for `container_path` to prevent duplicate registration. [ASSUMED]
- unique `platform_storage_mappings.platform_id` because Phase 1 permits at most one active mapping and no lifecycle API exists yet. [VERIFIED: D-13]
- unique `(storage_root_id, relative_path)` for exact duplicate targets. [VERIFIED: D-15]
- index `storage_root_id` for relationship/overlap lookup. [CITED: https://docs.sqlalchemy.org/en/20/core/constraints.html]

Ancestor/descendant overlap must normalize both paths first and compare path parts, never raw prefixes. Serialize conflict validation and insert in one DB transaction; exact uniqueness remains the final concurrency guard. Full concurrent prevention for non-equal ancestry is not portable without stronger locking, so the handler should lock relevant mapping rows/root where supported and document this residual edge. [ASSUMED]

### Anti-Patterns to Avoid

- **Constructing `FSHandler` for a root:** it creates missing directories. [VERIFIED: `backend/handler/filesystem/base_handler.py`]
- **Calling `Path.resolve()` before classifying input:** on the host OS, Windows-looking input can be treated as ordinary POSIX text. Parse both POSIX and Windows dialects first. [CITED: https://docs.python.org/3.13/library/pathlib.html]
- **Treating `os.access` as authorization:** it is an observation and can race; actual later opens must still handle failure. [CITED: https://docs.python.org/3.13/library/os.html#os.access]
- **Storing computed absolute mapping paths:** breaks deployment portability and violates ROOT-04. [VERIFIED: ROOT-04]
- **Using a native enum without dialect review:** the current migration head demonstrates special PostgreSQL enum handling and even has no downgrade, which should not be copied. [VERIFIED: `backend/alembic/versions/0062_rom_file_category_enum.py`]
- **Backfilling `fs_slug`:** legacy inference is Phase 6 and can be ambiguous. [VERIFIED: D-27]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Canonical path semantics | String splitting/prefix containment | `PurePosixPath`, `PureWindowsPath`, `Path.resolve`, `Path.relative_to` | Handles path components and cross-dialect classification. [CITED: Python pathlib docs] |
| Referential integrity | Application-only root/platform checks | SQL FK and unique constraints | Protects concurrent and non-handler writes. [CITED: SQLAlchemy constraints docs] |
| Transactions | Ad hoc sessions/commits | Existing `@begin_session` handler pattern | Matches repository lifecycle. [VERIFIED: backend skill and DB handlers] |
| Test data generation | Custom random path generator | Hypothesis strategies where useful | Already in the project development stack. [VERIFIED: `pyproject.toml`] |

**Key insight:** The custom code should only express RomM's domain contract. Filesystem primitives, relational constraints, and transaction management already exist and should remain the security substrate. [VERIFIED: standard library and project stack]

## Common Pitfalls

### Pitfall 1: Normalization erases evidence before validation

**What goes wrong:** `a//b`, `a/./b`, a backslash path, or Windows drive syntax is silently normalized into an accepted path. [ASSUMED]

**Why it happens:** Path constructors normalize some segments according to their own path flavor. [CITED: https://docs.python.org/3.13/library/pathlib.html]

**How to avoid:** Validate raw characters/separators and both path dialects first, then construct the canonical representation.

**Warning signs:** Tests assert only final paths, not rejected raw inputs.

### Pitfall 2: Root symlink is overlooked

**What goes wrong:** Candidate components contain no links, but the registered root itself redirects elsewhere. [ASSUMED]

**How to avoid:** `lstat` the configured root before canonical resolution and reject if it is a symlink; also reject every candidate component.

**Warning signs:** Tests cover leaf escape only.

### Pitfall 3: Health checking mutates the archive

**What goes wrong:** A write probe, `mkdir`, lock, cache, or temp file changes the source. [VERIFIED: D-05]

**How to avoid:** Restrict health implementation to metadata/directory-read operations and test a recursive before/after manifest including names, types, sizes, modes, mtimes, and link targets. Exclude atime from Phase 1 evidence per D-32. [VERIFIED: D-31, D-32]

**Warning signs:** Health uses `tempfile`, `.touch()`, `open(..., "w")`, or any current `FSHandler` instance.

### Pitfall 4: Writable means healthy

**What goes wrong:** A writable fixture is marked safe because reads succeed. [VERIFIED: D-10]

**How to avoid:** Model reachability/readability and immutability safety separately. `external_read_only` plus observed writable must yield a warning/failed safety state.

**Warning signs:** One `healthy: bool` hides the reason.

### Pitfall 5: TOCTOU is overstated or ignored

**What goes wrong:** The plan claims `resolve` makes later reads race-free, or expands Phase 1 into a complete file-serving redesign. [VERIFIED: phase boundary]

**How to avoid:** State precisely that this resolver validates a directory at one instant. A hostile writer can replace a component after validation. Later consumers should open relative to a trusted root descriptor and use no-follow semantics, then validate the opened object. Python exposes `dir_fd` support and `O_NOFOLLOW` on supported Unix systems, but NAS behavior and long-read identity require Phase 9 evidence. [CITED: https://docs.python.org/3.13/library/os.html#files-and-directories]

**Warning signs:** Resolver returns a `Path` described as permanently safe.

### Pitfall 6: Migration passes one dialect only

**What goes wrong:** enum/check/default/index DDL differs, or downgrade cannot remove dependent tables. [VERIFIED: repository migration conventions]

**How to avoid:** Create mapping after roots; downgrade mapping before roots; use named constraints; run upgrade, downgrade, and re-upgrade on MariaDB and PostgreSQL CI targets, and compile/execute against MySQL where supported. [CITED: https://alembic.sqlalchemy.org/en/latest/ops.html]

**Warning signs:** Autogenerated migration is accepted without hand review.

## Code Examples

### Resolver result and error taxonomy

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class ResolvedStoragePath:
    storage_root_id: int
    relative_path: str
    path: Path

class StorageResolutionError(Exception): ...
class InvalidRelativePathError(StorageResolutionError): ...
class MissingStorageRootError(StorageResolutionError): ...
class InactiveStorageRootError(StorageResolutionError): ...
class MissingStorageTargetError(StorageResolutionError): ...
class NonDirectoryStorageTargetError(StorageResolutionError): ...
class UnreadableStorageTargetError(StorageResolutionError): ...
class UnsafeSymlinkError(StorageResolutionError): ...
class StorageEscapeError(StorageResolutionError): ...
class UnsafeWritableRootError(StorageResolutionError): ...
```

This taxonomy is intentionally domain-specific and should carry safe identifiers/relative values, not arbitrary `OSError` paths. [VERIFIED: D-24]

### Canonical containment core

```python
# Source: https://docs.python.org/3.13/library/pathlib.html
root = configured_root.resolve(strict=True)
target = (root / normalized_relative).resolve(strict=True)
try:
    target.relative_to(root)
except ValueError as exc:
    raise StorageEscapeError(normalized_relative) from exc
```

This snippet is necessary but not sufficient: perform raw-input validation and the `lstat` no-symlink walk before accepting the result. [VERIFIED: D-19, D-22]

### Declarative uniqueness

```python
# Source: https://docs.sqlalchemy.org/en/20/core/constraints.html
__table_args__ = (
    UniqueConstraint("platform_id", name="uq_platform_storage_mapping_platform"),
    UniqueConstraint(
        "storage_root_id",
        "relative_path",
        name="uq_platform_storage_mapping_root_path",
    ),
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `FSHandler` creates base path in constructor | Separate non-mutating resolver | Phase 1 | Missing mount fails closed instead of being bootstrapped. [VERIFIED: phase scope] |
| `fs_slug` plus Structure A/B inference | Explicit root plus relative mapping | Phase 1 schema; consumer cutover Phase 5 | Existing archive organization becomes authoritative. [VERIFIED: roadmap] |
| Lexical allowance for configured symlinks | Reject every symlink for external roots | Phase 1 | Removes escape ambiguity; later exception requires a new decision. [VERIFIED: D-22] |
| Fixed `LIBRARY_BASE_PATH` as identity | Persistent deployment-owned root identity | Phase 1 | Supports future multiple roots without storing host paths in mappings. [VERIFIED: D-08] |

**Deprecated/outdated:**

- `FSHandler.validate_path()` is not valid for the new external-storage security contract, but remains untouched for current legacy consumers until their later cutover. [VERIFIED: phase boundary]
- `FSPlatformsHandler.get_platforms()` may bootstrap the ROM directory and must not be called by Phase 1 root/mapping validation. [VERIFIED: `backend/handler/filesystem/platforms_handler.py`]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | URL decoding is excluded from the resolver layer. | Pattern 1 | Phase 3 transport tests may require a shared decoding boundary. |
| A2 | `container_path` should be unique. | Pattern 4 | Duplicate root records might be a supported future aliasing use case. |
| A3 | Locking every active StorageRoot row in deterministic ID order serializes mapping overlap checks while Phase 1 root registration remains deployment-initialization-only. | Pattern 4 | Concurrent active-root registration would need the same lock contract in a later administration phase. |
| A4 | Raw normalization edge examples behave as described across accepted inputs. | Pitfall 1 | Test matrix must settle exact accepted dot/empty semantics. |
| A5 | Root symlinks should be rejected as part of D-22. | Pitfall 2 | Deployment may rely on a symlinked mount point, requiring explicit user decision. |

## Open Questions (RESOLVED)

1. **RESOLVED: Does internal empty relative path represent the root?**
   - What we know: Context leaves this to agent discretion; mappings must point to an explicitly valid directory. [VERIFIED: CONTEXT.md]
   - What's unclear: Whether a platform may map to the root itself.
   - Resolution: Empty represents the root only for the explicit internal root-health and root-resolution contract. Platform mappings always persist a non-empty normalized relative path, so no platform maps to the root itself. [RESOLVED: agent discretion, D-11, D-17, D-19]

2. **RESOLVED: Can the configured root itself be a symlink?**
   - What we know: all symlinks are rejected by default and canonical root containment is required. [VERIFIED: D-20, D-22]
   - What's unclear: Whether deployment tooling presents `/romm/library` as a symlink rather than a mount point.
   - Resolution: Reject a configured root when its filesystem entry is a symlink, and reject every symlink target component in milestone 1. Deployment must provide a direct mount path. [RESOLVED: D-20, D-22]

3. **RESOLVED: How should non-writable observation be represented?**
   - What we know: health must report it, and writable observation is unsafe. [VERIFIED: D-09, D-10]
   - What's unclear: exact status enum versus independent booleans.
   - Resolution: Persist nullable bounded `reachable`, `readable`, and `non_writable` observations plus nullable `last_checked_at`, `last_error_code`, and `last_error_message` directly on `StorageRoot`. Health uses metadata and access observation only, never a write probe. [RESOLVED: agent discretion, D-09, D-10]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python project runtime | Resolver/tests | Project declares yes | `>=3.13` | Use project `uv` environment, not host Python 3.10. [VERIFIED: `pyproject.toml`; environment probe] |
| uv | Tests/migrations | Available through project workflow | repository-managed | None needed. [VERIFIED: `CLAUDE.md`] |
| MariaDB | Migration CI | Repository CI/config | supported target | CI service. [VERIFIED: backend skill] |
| PostgreSQL | Migration CI | Repository CI/config | supported target | CI service. [VERIFIED: backend skill] |
| MySQL | Portability target | Docker image available through repository Docker workflows | `mysql:8.4` | Repository verifier starts an ephemeral MySQL container and CI executes the same migration cycle. [RESOLVED: `CLAUDE.md`, Docker/CI pattern] |

**Missing dependencies with no fallback:** None identified for planning. [VERIFIED: repository stack]

**Missing dependencies with fallback:** The SSH host's system Python is 3.10.12; all commands must use `uv run` to obtain the project's Python 3.13 environment. [VERIFIED: environment probe]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest `~=9.0`, pytest-asyncio `~=1.1`, Hypothesis `~=6.0` [VERIFIED: `pyproject.toml`] |
| Config file | `backend/pytest.ini` [VERIFIED: repository] |
| Quick run command | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py tests/models/test_storage.py -x` |
| Full phase command | `cd backend && uv run pytest tests/handler/filesystem/test_storage_resolver.py tests/handler/database/test_storage_handler.py tests/models/test_storage.py -x` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ROOT-01 | Existing root registers active without creation | integration/unit | `uv run pytest tests/handler/database/test_storage_handler.py -k register -x` | No, Wave 0 |
| ROOT-02 | Only immutable mode persists | model/migration | `uv run pytest tests/models/test_storage.py -k mode -x` | No, Wave 0 |
| ROOT-03 | Health is bounded and non-mutating | real-filesystem unit | `uv run pytest tests/handler/filesystem/test_storage_resolver.py -k health -x` | No, Wave 0 |
| ROOT-04 | Mapping stores FK plus relative text only | model/migration | `uv run pytest tests/models/test_storage.py -k mapping -x` | No, Wave 0 |
| PATH-01 | Reject invalid lexical forms | parameterized/property unit | `uv run pytest tests/handler/filesystem/test_storage_resolver.py -k normalize -x` | No, Wave 0 |
| PATH-02 | Canonical containment | real-filesystem unit | `uv run pytest tests/handler/filesystem/test_storage_resolver.py -k containment -x` | No, Wave 0 |
| PATH-03 | Active/existing/readable/directory checks | real-filesystem unit | `uv run pytest tests/handler/filesystem/test_storage_resolver.py -k target -x` | No, Wave 0 |
| PATH-04 | Unicode, spaces, long and nested names | parameterized unit | `uv run pytest tests/handler/filesystem/test_storage_resolver.py -k valid_names -x` | No, Wave 0 |
| PATH-05 | Root/intermediate/leaf links rejected | real-filesystem unit | `uv run pytest tests/handler/filesystem/test_storage_resolver.py -k symlink -x` | No, Wave 0 |
| TEST-01 | Complete adversarial matrix | suite gate | `uv run pytest tests/handler/filesystem/test_storage_resolver.py -x` | No, Wave 0 |

### Required test matrix

- Valid root, root mapping policy, normal/nested, spaces, dots, hyphens, umlauts, composed/decomposed Unicode, long component near filesystem limit. [VERIFIED: D-23, D-30]
- Empty overall input under both internal and mapping contracts; `//`, leading/trailing separator, repeated separator, `.` and empty internal segments. [VERIFIED: D-19, D-30]
- `..`, repeated/mixed traversal, absolute POSIX, `C:\\...`, `C:/...`, UNC, device paths, backslashes, NUL, C0 and DEL controls. [VERIFIED: D-19, D-30]
- Missing/inactive root, missing target, regular file target, unreadable root/target, writable-root unsafe state. [VERIFIED: D-24, D-30]
- Root, first, middle, and leaf symlinks; absolute/relative link targets; in-root and escaping links; broken links and loops. [VERIFIED: D-22, TEST-01]
- Sibling-prefix containment such as root `/library` and target `/library-old`. [VERIFIED: D-20]
- Exact duplicate and ancestor/descendant overlap after normalization, including `a` versus `a/b`; unrelated common textual prefixes remain allowed. [VERIFIED: D-15]
- Before/after recursive manifests around registration, health, resolver, and mapping save. Monkeypatch `Path.mkdir`, `open` write modes, `tempfile`, and mutation helpers to fail if invoked, while retaining real `stat/lstat/resolve` behavior. [VERIFIED: D-31]

Unreadability tests should run under a non-root identity or mock only the permission observation boundary because chmod-based denial is unreliable when tests run as root. [ASSUMED]

### Sampling Rate

- **Per task commit:** relevant single test file with `-x`.
- **Per wave merge:** full phase command above.
- **Phase gate:** full backend phase suite, Alembic upgrade/downgrade/re-upgrade on supported CI databases, then `trunk fmt && trunk check`. [VERIFIED: backend skill]

### Wave 0 Gaps

- [ ] `backend/tests/handler/filesystem/test_storage_resolver.py`
- [ ] `backend/tests/handler/database/test_storage_handler.py`
- [ ] `backend/tests/models/test_storage.py`
- [ ] `backend/tools/verify_storage_migrations.py` starts isolated MariaDB 10.11, MySQL 8.4, and PostgreSQL 15 containers and runs upgrade, downgrade to 0107, and re-upgrade independently; `.github/workflows/migrations.yml` is the authoritative CI gate for the same matrix.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No API in Phase 1. [VERIFIED: phase boundary] |
| V3 Session Management | No | No API in Phase 1. [VERIFIED: phase boundary] |
| V4 Access Control | Yes | Trusted storage-root identity plus active/mode checks before resolution. [VERIFIED: D-17, D-18] |
| V5 Input Validation | Yes | Pure normalization, typed errors, canonical containment, real-filesystem tests. [VERIFIED: PATH-01 through PATH-05] |
| V6 Cryptography | No | No cryptographic operation in Phase 1. [VERIFIED: phase boundary] |

### Known Threat Patterns for Python/SQLAlchemy storage

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal/cross-dialect absolute input | Tampering / Information Disclosure | Raw lexical rejection plus canonical path containment. [CITED: Python pathlib docs] |
| Symlink escape | Tampering / Information Disclosure | Reject links at root and every component using `lstat`, then strict resolve. [CITED: Python os/pathlib docs] |
| TOCTOU component replacement | Tampering | Declare point-in-time resolver limit; later opens use descriptor-relative no-follow semantics. [CITED: Python os docs] |
| Error path disclosure | Information Disclosure | Translate `OSError` into bounded codes/messages without unrelated absolute paths. [VERIFIED: D-24] |
| Concurrent duplicate or cross-root overlapping mapping | Tampering | In one transaction, lock all active StorageRoot rows by ascending ID with `SELECT FOR UPDATE`, compare and recheck canonical targets, then insert; uniqueness remains an exact-collision backstop. [CITED: SQLAlchemy ORM query guide; SQLAlchemy constraints docs] |
| Health write probe | Tampering | Metadata/read-only operations and before/after manifest. [VERIFIED: D-05, D-31] |

## What Might Have Been Missed

- Network filesystems may report permissions differently from local fixtures, and directory reads can affect atime depending on mount policy. Production NAS behavior is explicitly Phase 9. [VERIFIED: D-32, roadmap]
- Unicode normalization and case sensitivity differ by filesystem. Phase 1 should preserve exact text, not case-fold or Unicode-normalize names, and overlap should compare the stored canonical text plus actual resolved path. Cross-filesystem collision policy remains an operational concern. [ASSUMED]
- A path can exceed platform-wide limits even when each segment is valid. Convert resulting `OSError` to a controlled invalid/unreachable error and test a safely bounded long segment rather than assuming universal maximums. [ASSUMED]
- Database health timestamps may use application defaults while migration-created rows need server defaults. Since Phase 1 performs no backfill, nullable health fields avoid dialect-specific bootstrap timestamps. [ASSUMED]

## Sources

### Primary (HIGH confidence)

- `backend/handler/filesystem/base_handler.py` and `platforms_handler.py` - current mutation and symlink seams.
- `backend/models/base.py`, `platform.py`, `backend/handler/database/platforms_handler.py` - ORM and handler conventions.
- `backend/alembic/env.py`, `backend/alembic/versions/0062_rom_file_category_enum.py` - import, batch, and dialect patterns.
- `backend/pytest.ini`, `pyproject.toml`, existing filesystem tests - validation stack and test layout.
- https://docs.python.org/3.13/library/pathlib.html - path flavors, strict resolution, symlink and containment APIs.
- https://docs.python.org/3.13/library/os.html - access caveats, `lstat`, descriptor-relative APIs, no-follow primitives.
- https://docs.sqlalchemy.org/en/20/core/constraints.html - FK, unique, check, and index declarations.
- https://alembic.sqlalchemy.org/en/latest/ops.html - portable table/constraint migration operations.

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md`, `STACK.md`, `PITFALLS.md`, and `SUMMARY.md` - milestone analysis cross-checked against source.

### Tertiary (LOW confidence)

- None. Unverified judgments are explicitly recorded in the Assumptions Log.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - verified from current project manifest and official documentation.
- Architecture: HIGH - locked decisions align with exact current repository seams.
- Pitfalls: HIGH - primary risks are observable in source and official filesystem semantics; NAS-specific behavior is deferred.

**Research date:** 2026-08-04
**Valid until:** 2026-09-03
