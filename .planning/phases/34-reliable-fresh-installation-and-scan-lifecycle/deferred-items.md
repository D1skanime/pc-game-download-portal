# Phase 34 Deferred Items

## 34-02 baseline migration blockers (2026-10-18)

The guarded three-dialect schema command fails before any Phase 34 migration exists.
These failures predate 34-02 and were not modified.

- MySQL 8.4: backend/alembic/versions/0001_initial_models.py:104 emits CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username), rejected with SQL error 1064.
  Evidence: /tmp/pgdp34-3c3748d9193041349ae6a421f1dc4b3b-67w7shzt/evidence/14.log.
- PostgreSQL 15: backend/alembic/versions/0134_rom_updated_at_fractional_seconds.py:16 emits ALTER TABLE roms MODIFY COLUMN updated_at TIMESTAMP(6) ... ON UPDATE CURRENT_TIMESTAMP(6), rejected with psycopg.errors.SyntaxError.
  Evidence: /tmp/pgdp34-baefc87ae94542498d4ff15ba2ee61fe-trb02u2b/evidence/14.log.

Repair requires explicit scope for historical migration portability, followed by the full isolated matrix.
Do not stamp past failures, substitute SQLite, skip dialects, or report the operation contract complete.
