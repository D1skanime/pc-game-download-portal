---
name: rom-updated-at-fractional-seconds
status: in-progress
---

# Fix ROM timestamp precision for scan media reconciliation

- Change the shared timestamp model and add Alembic revision 0134 so roms.updated_at uses TIMESTAMP(6).
- Recreate only the Dev database romm after the migration is present.
- Verify migrations, service health, fresh schema precision, and the normal scan/media path.
