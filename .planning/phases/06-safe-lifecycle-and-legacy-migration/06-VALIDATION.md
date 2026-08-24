---
phase: 06-safe-lifecycle-and-legacy-migration
status: passed
nyquist_validation: enabled
requirements:
  [CAT-01, CAT-02, CAT-03, CAT-04, MIG-01, MIG-02, MIG-03, MIG-04, MIG-05]
created: 2026-08-12
validated: 2026-08-24
acceptance_record: 06-47-ACCEPTANCE.json
---

# Phase 6: Safe Lifecycle and Legacy Migration - Validation

## Final Verdict

Plan 06-47 passed the checked-in complete acceptance gate in the canonical Linux checkout. The run used isolated nonce-owned databases, principals, basetemps, containers, and Node volume resources. It did not deploy, restart `romm-dev`, publish a port, or mutate external source content.

Run ID: `0525ee9a9a51ae4fad34e5791398cd40`

Run Digest: `f4b45a758dd5950caaee1f479220cb617aab1a053d7e5fa052ec0c72a47d94ff`

Prior modules: 29

Prior outcomes: 843

The canonical JSON digest recomputes successfully from the structured acceptance record. All required source IDs are bound through the companion source audit.

## Environment and Integrity

| Check                | Fresh result                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------------- |
| Host and checkout    | Linux; `/home/d1sk/romm`; branch `codex/pc-module-analysis`                                    |
| Origin and project   | `https://github.com/rommapp/romm.git`; `RomM PC Library`                                       |
| Required ancestor    | `3e0b278cf3e71fe84f1e7b20b354f94728fc9531` present                                             |
| Source service       | `romm-dev` remained `exited`                                                                   |
| Normal database      | `SELECT 1` returned 1 before and after the complete run                                        |
| Untracked baseline   | 28 entries; SHA-256 `4d4264efbb75049e71230f2417667c867656f6dd5054640e7aa6b8af391c81e1`         |
| Source manifest      | 2,746 entries; before/after `1181a7adf53c5c9b004d6f818c38ec8ceb9c1d0ac813f7f47a37b007be452483` |
| Generated manifest   | 257 files; before/after `dc4ecf6f1cc2b71cac62c9490ae30fa2f82ff7c669ecf68eda4dcea26ac2fb5d`     |
| Repository diff gate | `git diff --check` exit 0                                                                      |
| Cleanup              | 0 containers, databases, principals, basetemps, and volumes owned by Plan 47                   |

## Fresh Backend Results

Every module ran without `-k`, with `-p no:env`, `-p no:cacheprovider`, `ROMM_BASE_PATH=romm_test`, and its own exact database, principal, password, basetemp, and disposable runner.

### Prior contract

| Module                                                   | Passed | Skipped | Exit |
| -------------------------------------------------------- | -----: | ------: | ---: |
| tests/alembic/test_mapping_preview_migration.py          |      1 |       0 |    0 |
| tests/endpoints/roms/test_files.py                       |     16 |       7 |    0 |
| tests/endpoints/roms/test_rom.py                         |     76 |       0 |    0 |
| tests/endpoints/storage/test_mapping_preview.py          |      2 |       0 |    0 |
| tests/endpoints/test_storage.py                          |     62 |       0 |    0 |
| tests/endpoints/test_storage_policy_denials.py           |     55 |       0 |    0 |
| tests/handler/database/test_storage_handler.py           |     28 |       0 |    0 |
| tests/handler/filesystem/test_external_read_consumers.py |      9 |       0 |    0 |
| tests/handler/filesystem/test_owned_storage.py           |      6 |       0 |    0 |
| tests/handler/filesystem/test_storage_access.py          |     61 |       0 |    0 |
| tests/handler/filesystem/test_storage_inventory.py       |     12 |       0 |    0 |
| tests/handler/filesystem/test_storage_policy.py          |    263 |       0 |    0 |
| tests/handler/filesystem/test_storage_resolver.py        |     57 |       0 |    0 |
| tests/handler/filesystem/test_sync_handler.py            |     20 |       0 |    0 |
| tests/handler/storage/test_preview.py                    |      3 |       0 |    0 |
| tests/handler/test_scan_command.py                       |      4 |       0 |    0 |
| tests/integration/test_mapped_scan.py                    |      3 |       0 |    0 |
| tests/integration/test_scan_source_immutability.py       |      2 |       0 |    0 |
| tests/models/test_storage.py                             |     12 |       0 |    0 |
| tests/tasks/test_mapping_revision_jobs.py                |      2 |       0 |    0 |
| tests/tasks/test_storage_policy.py                       |      4 |       0 |    0 |
| tests/test_sync_watcher.py                               |     11 |       0 |    0 |
| tests/test_watcher.py                                    |      2 |       0 |    0 |
| tests/tools/test_verify_storage_migrations.py            |     23 |       0 |    0 |
| tests/utils/test_archives.py                             |     24 |       0 |    0 |
| tests/utils/test_audio_tags.py                           |     28 |       0 |    0 |
| tests/utils/test_gamelist_exporter.py                    |     20 |       0 |    0 |
| tests/utils/test_pegasus_exporter.py                     |     26 |       0 |    0 |
| tests/utils/test_zip_cache.py                            |      4 |       0 |    0 |
| Total                                                    |    836 |       7 |    0 |

### Deduplicated Phase 6 contract

| Module                                           | Passed | Skipped | Exit |
| ------------------------------------------------ | -----: | ------: | ---: |
| tests/endpoints/roms/test_catalog_removal.py     |     12 |       0 |    0 |
| tests/endpoints/roms/test_manual.py              |      3 |       0 |    0 |
| tests/endpoints/sockets/test_scan.py             |     76 |       0 |    0 |
| tests/endpoints/test_saves.py                    |     98 |       0 |    0 |
| tests/endpoints/test_screenshots.py              |     18 |       0 |    0 |
| tests/endpoints/test_states.py                   |     15 |       0 |    0 |
| tests/handler/database/test_storage_lifecycle.py |     31 |       0 |    0 |
| tests/handler/storage/test_legacy_migration.py   |     43 |       0 |    0 |
| tests/handler/storage/test_read_context.py       |     17 |       0 |    0 |
| tests/integration/test_legacy_migration.py       |     37 |       0 |    0 |
| tests/models/test_safe_lifecycle.py              |     12 |       0 |    0 |
| tests/tasks/test_detect_legacy_storage.py        |      3 |       0 |    0 |
| tests/tools/test_verify_phase6_contracts.py      |     31 |       0 |    0 |
| tests/utils/test_rom_patcher.py                  |      7 |       0 |    0 |
| Total                                            |    403 |       0 |    0 |

## Cross-Stack Results

| Stage                               | Structured result                              |
| ----------------------------------- | ---------------------------------------------- |
| MariaDB migration authority         | Complete, exit 0                               |
| MySQL migration authority           | Complete, exit 0                               |
| PostgreSQL migration authority      | Complete, exit 0                               |
| Controlled OpenAPI contract         | Exit 0                                         |
| Generated frontend contract         | 257 files, exact before/after digest match     |
| Focused frontend tests              | Exit 0                                         |
| Full frontend tests                 | Exit 0                                         |
| Frontend typecheck                  | Exit 0                                         |
| Trapped production build            | Exit 0                                         |
| Locale parity and sorting           | Exit 0                                         |
| Repository-topology static checks   | Exit 0                                         |
| Complete backend/frontend manifests | 2,746 entries, exact before/after digest match |

The generated verifier initially exposed three generator-owned terminal blank-line differences. Commit `22b983dcb` synchronized that exact output without changing schema semantics. The final bound run then produced identical generated manifests.

## UI Evidence

Plan 47 did not restart the intentionally stopped application service and did not claim a fresh interactive UI run. The approved Plan 45 matrix remains valid because its relevant implementation and test files did not drift after commit `364bb2764`. The bound acceptance record therefore marks `fresh_run=false` and `status=previously_validated_no_drift` for both themes, 320px through 4K, mouse/touch/keyboard/gamepad, focus, announcements, slow/failure/retry/conflict/refresh, and stable viewer behavior.

## Evidence Corrections and Infrastructure Note

The exact fresh prior-module result is 836 passed plus 7 skipped, or 843 outcomes. An earlier narrative claimed 931 passed plus 8 skipped, or 939 outcomes. No stored raw historical output exists to reconcile the 96-outcome difference. The user approved binding Plan 47 to the reproducible 843 result. This corrects an unsupported historical count and does not, by itself, establish a functional regression.

A separate Wave 4 diagnostic that attempted 61 tests exited 137 during global database/Alembic setup. Per the user decision, that event is recorded as an infrastructure-only warning. It was not rerun or represented as fresh Plan 47 evidence. Plan 47 instead uses the successful isolated module and dialect results listed above.

## Canonical Command

```text
python3 backend/tools/verify_phase6_acceptance.py --checkout /home/d1sk/romm --base-commit 3e0b278cf3e71fe84f1e7b20b354f94728fc9531 --branch codex/pc-module-analysis --origin https://github.com/rommapp/romm.git --project "RomM PC Library" --source-container romm-dev --db-container romm-db-dev --expected-source-image romm-romm-dev --network romm_default --node-image node:24-bookworm --contract-port 39006 --baseline-untracked-count 28 --prior-outcomes-min 843 --evidence-json .planning/phases/06-safe-lifecycle-and-legacy-migration/06-47-ACCEPTANCE.json --run-complete
```

Exit 0. The acceptance JSON was written atomically only after every structured stage and cleanup assertion passed.
