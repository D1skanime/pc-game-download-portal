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
