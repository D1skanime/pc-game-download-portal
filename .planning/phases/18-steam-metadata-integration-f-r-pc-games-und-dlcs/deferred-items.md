# Deferred Items

## PostgreSQL baseline migration enum collision

- **Found during:** Plan 18-02, Task 3
- **Scope:** Pre-existing migration `backend/alembic/versions/20260831_add_pc_rom_components.py`
- **Issue:** A fresh PostgreSQL 16 database fails while upgrading this baseline
  revision because `romcomponentkind` already exists. The verifier reached
  `0126_add_steam_metadata` as the sole graph head, then preserved Alembic's
  first failure and removed the disposable database container.
- **Disposition:** Out of scope for the Steam persistence migration. Repair the
  baseline PostgreSQL enum creation in a dedicated migration-compatibility plan.

## Heartbeat default misses registered Steam provider flag

- **Found during:** Plan 18-06, Task 2
- **Scope:** `frontend/src/stores/heartbeat.ts`
- **Issue:** Regenerated `MetadataSourcesDict` requires `STEAM_API_ENABLED`, but
  the pre-existing `defaultHeartbeat.METADATA_SOURCES` object does not supply it.
  This makes the full frontend typecheck fail independently of ROM/component
  contract generation.
- **Disposition:** Out of scope for this plan's ROM/component API-only boundary.
  Add the default in the plan that owns Steam heartbeat provider integration.
