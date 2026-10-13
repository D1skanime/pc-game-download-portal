---
quick_task: 261013-mmt
description: Canonicalize Windows/PC storage and scan paths to win with safe pc compatibility
status: executed
---

# Plan

## Objective

Make `win` the canonical filesystem, storage-mapping, and scan slug for Windows/PC while keeping existing `pc` libraries and persisted mappings usable without moving, renaming, or mutating external archive files.

## Exact files

- `backend/handler/filesystem/platforms_handler.py`
- `backend/handler/filesystem/roms_handler.py`
- `backend/handler/scan_handler.py`
- `backend/endpoints/sockets/scan.py`
- `backend/endpoints/storage.py`
- `backend/tests/handler/filesystem/test_platforms_handler.py`
- `backend/tests/handler/filesystem/test_roms_handler.py`
- `backend/tests/handler/test_scan_handler.py`
- `backend/tests/endpoints/sockets/test_scan.py`
- `backend/tests/endpoints/storage/test_legacy_bootstrap_paths.py`

## Tasks

1. Add one shared, narrowly scoped PC slug canonicalization contract in the existing backend path/scan flow. Normalize `pc` to `win` for new filesystem path construction, platform resolution, scan dispatch, selected-platform inputs, and Windows-specific admission checks. Keep non-PC platform bindings unchanged. Ensure all callers use the same canonicalization point so path generation and scan identity cannot diverge.

2. Update storage bootstrap and legacy resolution to use the canonical `win` target while preserving safe legacy compatibility. Canonical `win` storage paths and mappings must take precedence. An existing `pc` directory or persisted `pc` mapping may be reused only as a read/scan fallback when the canonical target is absent; do not rename, copy, delete, or write into the external archive as part of compatibility. Do not scan both aliases, and do not silently create a second mapping for the same PC library. Preserve the existing `win` database platform identity and make bootstrap idempotent across canonical and legacy layouts.

3. Add regression coverage for both path shapes and migration behavior. Cover Structure A and Structure B path builders, `pc` input canonicalizing to `win`, canonical-first precedence when both folders exist, legacy-only `pc` fallback, selected scan requests using `pc`, Windows quick/update scan admission after normalization, and storage bootstrap reuse without external filesystem mutation. Include assertions for the exact filesystem paths, selected scan slugs, mapping/root reuse, and no duplicate scan dispatch.

4. Verify the focused backend suites and repository checks, then record the implementation result in the quick-task summary. Run the path, scan, and storage tests first, followed by `git diff --check` and the applicable Trunk checks. If the fixture database is unavailable, report that limitation explicitly and retain the commands and static checks as evidence; do not claim the database-backed tests passed.

## Migration and compatibility behavior

- Canonical identity: Windows/PC is `win` for filesystem paths, `Platform.fs_slug`, storage mappings, scan selection, and Windows-specific scan logic.
- Legacy input: `pc` remains an accepted alias at controlled filesystem/scan/storage boundaries and resolves to the same `win` identity.
- Canonical-first resolution: use `win` when both `win` and `pc` layouts exist. Use an existing `pc` layout only when `win` is absent, with one resolved scan target.
- Non-destructive migration: do not rename or move `pc` directories, rewrite archive contents, delete legacy mappings, or scan both aliases. New paths and mappings use `win`; legacy state is reused safely until explicitly migrated by a separate operation.
- Idempotence: repeated bootstrap calls return the same effective root/mapping and do not create duplicate PC platform rows or mappings.

## Regression commands

```text
cd backend && uv run pytest \
  tests/handler/filesystem/test_platforms_handler.py \
  tests/handler/filesystem/test_roms_handler.py \
  tests/handler/test_scan_handler.py \
  tests/endpoints/sockets/test_scan.py \
  tests/endpoints/storage/test_legacy_bootstrap_paths.py -q
git diff --check
trunk fmt --check
trunk check
```

## Verification

- `git grep` shows no active PC storage/scan path builder that bypasses the canonicalization contract.
- Focused tests prove `win` is emitted and selected canonically, while `pc` fallback remains bounded, canonical-first, idempotent, and non-destructive.
- Full relevant backend verification is green, or any unavailable service/fixture is documented with the exact failed command and no false pass claim.
- No production implementation is part of this planning task; this file is the only intended artifact.
