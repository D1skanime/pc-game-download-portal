---
phase: 02
slug: read-only-policy-boundary
status: planned
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-09
---

# Phase 02 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property               | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Framework**          | pytest 9.0.3, pytest-asyncio 1.3.0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **Config file**        | `backend/pytest.ini`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **Quick run command**  | `cd backend && uv run pytest tests/handler/filesystem/test_storage_policy.py tests/handler/filesystem/test_storage_access.py tests/handler/filesystem/test_owned_storage.py -x`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **Full suite command** | cd backend &amp;&amp; uv run pytest tests/handler/filesystem/test_storage_policy.py tests/handler/filesystem/test_storage_access.py tests/handler/filesystem/test_owned_storage.py tests/handler/filesystem/test_external_read_consumers.py tests/handler/filesystem/test_firmware_handler.py tests/handler/filesystem/test_platforms_handler.py tests/endpoints/test_heartbeat.py tests/config/test_config_loader.py tests/endpoints/sockets/test_scan.py tests/handler/filesystem/test_roms_handler.py tests/endpoints/test_streaming.py tests/endpoints/roms/test_files.py tests/endpoints/roms/test_rom.py tests/endpoints/test_storage_policy_denials.py tests/endpoints/roms/test_upload.py tests/endpoints/roms/test_manual.py tests/endpoints/roms/test_screenshot.py tests/endpoints/roms/test_soundtrack.py tests/endpoints/test_platform.py tests/tasks/test_storage_policy.py tests/handler/filesystem/test_storage_inventory.py tests/utils/test_archives.py tests/utils/test_zip_cache.py tests/utils/test_gamelist_exporter.py tests/utils/test_pegasus_exporter.py tests/utils/test_audio_tags.py tests/handler/filesystem/test_sync_handler.py tests/test_sync_watcher.py tests/tasks/test_cleanup_orphaned_resources.py tests/tasks/test_cleanup_upload_tmp.py tests/tasks/test_cleanup_zip_cache.py tests/tasks/test_sync_push_pull.py -x |
| **Container command**  | `python3 backend/tools/verify_read_only_policy.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **Estimated runtime**  | To be measured during Wave 0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

## Sampling Rate

- **After every task commit:** Run the narrowest affected test file with `-x`.
- **After every plan wave:** Run the full Phase 2 suite.
- **Before `$gsd-verify-work`:** Run the full suite, the writable/`:ro` container verifier, scoped Trunk checks, and review the mutation inventory.
- **Max feedback latency:** 120 seconds for task-level tests; container evidence runs at wave and phase gates.

## Per-Task Verification Map

| Tasks        | Plan  | Wave | Scope         |
| ------------ | ----- | ---- | ------------- |
| 02-01-01..02 | 02-01 | 1    | policy        |
| 02-02-01..02 | 02-02 | 2    | access        |
| 02-03-01..02 | 02-03 | 3    | owned storage |
| 02-04-01..02 | 02-04 | 4    | all reads     |
| 02-05-01..02 | 02-05 | 5    | endpoints     |
| 02-06-01..02 | 02-06 | 5    | transforms    |
| 02-07-01..02 | 02-07 | 5    | sync tasks    |
| 02-08-01..02 | 02-08 | 6    | inventory     |
| 02-09-01..02 | 02-09 | 7    | final gate    |

_Final plan task IDs replace the provisional Wave 0 IDs during planning._

## Wave 0 Requirements

- [ ] `backend/tests/handler/filesystem/test_storage_policy.py` - exact allow/deny/unknown matrix, composition-only descriptor construction, caller-text non-forgeability, and pre-access tripwires.
- [ ] `backend/tests/handler/filesystem/test_storage_access.py` - capability surface, post-close behavior, unchanged manifests, and coordinated path-swap races.
- [ ] `backend/tests/handler/filesystem/test_owned_storage.py` - trusted LIBRARY_BASE_PATH provider, singleton pre-construction overlap validation, and equal/bidirectional ancestry fail-closed evidence.
- [ ] `backend/tests/endpoints/test_storage_policy_denials.py` - bounded HTTP 403 contract without path disclosure.
- [ ] `backend/tests/tasks/test_storage_policy.py` - visible job/internal denial with no fallback or partial-success event.
- [ ] `backend/tests/handler/filesystem/test_storage_inventory.py` - closed inventory of filesystem mutation seams.
- [ ] `backend/tools/verify_read_only_policy.py` - identical writable and `:ro` fixture matrix with deterministic cleanup.
- [ ] Docker fixture or compose profile that mounts the external test library `:ro` while RomM-owned output remains writable and separate.
- [ ] Recursive before/after manifest helper excluding atime and covering names, kinds, sizes, modes, timestamps, links, and content hashes where applicable.
- [ ] Tripwires for `stat`, `scandir`, read/write `open`, `Path` access, temporary files, `mkdir`, unlink, rename, replace, copy, move, extraction, patching, sidecars, and cover writes.

## Manual-Only Verifications

All Phase 2 behaviors are automatable. Real NAS activation, protocol-specific atime behavior, and production operations remain Phase 9 scope.

## Validation Sign-Off

- [x] All tasks have automated verification or explicit Wave 0 dependencies.
- [x] Sampling continuity has no three consecutive tasks without automated verification.
- [x] Wave 0 covers every missing test and fixture reference.
- [x] No watch-mode flags are used.
- [x] Task-level feedback latency remains below 120 seconds.
- [x] Writable and `:ro` fixtures produce the same typed denial outcomes.
- [x] Final plan task IDs replace provisional validation rows.
- [x] `nyquist_compliant: false` is set after the plan-task map is final and complete.

**Approval:** approved, every Phase 2 requirement, D-01 through D-16, validation artifact, and HIGH threat is mapped to final plan task IDs
