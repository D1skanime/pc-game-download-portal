# Phase 33 Plan 06: Focused TDD Deviation Note

## Deviation

Fresh UAT exposed that `GET /api/setup/folders` returned HTTP 409 on an empty
database even when the configured library bind was present. The regression test
now proves that `SetupFolderHandler.root()` registers the configured library
root through `db_storage_handler.register_root` when no active matching root
exists. The minimal fallback preserves the existing external read-only health
and policy checks and does not add a second mapping step.

## Verification

- RED: `test_root_registers_configured_library_when_database_is_empty` failed
  before the production change.
- GREEN: focused handler and endpoint tests passed, 10 passed.
- Live temporary UAT: `GET /api/setup/folders` returned HTTP 200 and discovered
  `My Games` and `pc`; the database contains one healthy external read-only
  root at `/app/romm/library`.
- In-memory Python compilation passed for both changed files.

Full Phase 33 browser UAT remains pending and is not marked complete here.
