# Deferred items from Phase 26 Plan 26-01

These pre-existing failures were observed while running broader media tests and are outside the files or behavior changed by this plan:

- tests/handler/database/test_rom_media.py::test_model_keeps_candidate_and_placements_independent - placement fixture leaves rom_id null.
- tests/handler/database/test_rom_media.py::test_d07_steam_inventory_is_idempotent_and_keeps_shared_path - database datetime comparison differs only by timezone awareness.
- tests/handler/database/test_rom_media.py::test_complete_reorder_rejects_incomplete_membership - existing reorder fixture returns no applied result.
- tests/handler/database/test_rom_media.py::test_owned_media_role_is_immutable_after_persistence - existing role immutability assertion does not raise.
- tests/handler/database/test_rom_media.py::test_owned_media_schema_serializes_role_and_safe_display_label - existing lazy placement relationship is unavailable during direct schema validation.
- tests/endpoints/roms/test_media.py::test_replace_local_background_audio_requires_same_rom_soundtrack - existing detailed-ROM response has a null file timestamp.

The plan-scoped suppression, restore, deletion cleanup, and manual-description tests pass in focused runs.
