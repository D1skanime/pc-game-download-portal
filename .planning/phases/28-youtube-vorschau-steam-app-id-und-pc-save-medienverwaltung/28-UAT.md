# Phase 28 UAT

Date: 2026-10-12
Environment: canonical Linux checkout /home/d1sk/pc-game-download-portal
Branch: codex/phase-28-youtube-steam-saves

## Result

Status: BLOCKED before completion.

The backend Save/State implementation and migration tests pass. Frontend test/build/typecheck and Trunk gates could not run because the canonical Linux host has no node, npm, or trunk. No RomM Docker services are running in the checkout, so live browser UAT and byte-hash upload round trips could not be performed. The unrelated service answering port 3000 identifies itself as Next.js and was not used as RomM evidence.

## Automated evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Save/State filesystem, endpoint, and migration tests | PASS | backend/.venv/bin/pytest -q tests/handler/filesystem/test_assets_handler.py tests/endpoints/test_saves.py tests/endpoints/test_states.py tests/tasks/test_pc_save_migration.py -> 147 passed |
| Task registry plus migration/endpoints regression | PASS | backend/.venv/bin/pytest -q tests/endpoints/test_tasks.py tests/tasks/test_pc_save_migration.py tests/endpoints/test_saves.py tests/endpoints/test_states.py -> 137 passed |
| Python syntax for changed backend files | PASS | Worker verified all 9 backend files |
| git diff --check | PASS | Clean on the phase branch |
| Frontend focused tests and typecheck | BLOCKED | npm and node are not installed on the canonical Linux host |
| Production frontend build | BLOCKED | npm and node are not installed |
| Locale parity | BASELINE FAIL | Existing missing keys in scan.json, setup.json, and rom.json for 17 locales, unrelated to the new keys |
| Locale sorted gate | BASELINE FAIL | Existing unsorted locale files, including rom.json in most locales |
| Trunk fmt/check | BLOCKED | trunk is not installed |
| Docker health | NOT AVAILABLE | docker compose ps found the compose file but no running services |

## Save/State matrix

The automated endpoint and migration suite covers the expected server behavior. Live browser and byte-hash cells remain pending because no RomM Dev service is running.

| Asset | Path | Owner authorization | Public visibility | Device sync | Optimistic conflict | Emulator separation | Missing-file handling | Download | Delete |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Save | canonical ROM resource | PASS, endpoint tests | PASS, existing semantics retained | PASS, endpoint tests | PASS, endpoint tests | PASS, canonical path tests | PASS, endpoint tests | PASS, canonical fallback tests | PASS, endpoint tests |
| Save | legacy asset path | PASS, endpoint tests | PASS, existing semantics retained | PASS, endpoint tests | PASS, endpoint tests | PASS, legacy path tests | PASS, missing-file tests | PASS, legacy fallback tests | PASS, legacy delete tests |
| State | canonical ROM resource | PASS, endpoint tests | PASS, existing semantics retained | PASS, existing semantics retained | PASS, endpoint tests | PASS, canonical path tests | PASS, endpoint tests | PASS, canonical fallback tests | PASS, endpoint tests |
| State | legacy asset path | PASS, existing semantics retained | PASS, existing semantics retained | PASS, existing semantics retained | PASS, endpoint tests | PASS, legacy path tests | PASS, missing-file tests | PASS, legacy fallback tests | PASS, legacy delete tests |

## Migration evidence

- Raw bytes remain unchanged in the migration tests.
- ZIP bytes remain opaque and round-trip unchanged in the migration tests.
- Canonical destinations are ROM-owned and separated into pc-saves and pc-states, with emulator-specific subdirectories.
- Temporary migration files are removed after interrupted copies.
- Legacy source bytes remain readable after database update failure and can be retried.
- The migration is exposed through the existing manual task registry as pc_save_migration.
- A live migration run and retry against a running Dev instance are pending.

## Browser UAT pending

The following must be run after the Linux host has the frontend runtime and a running RomM Dev stack:

1. Overview: valid YouTube ID renders the privacy-mode iframe, external fallback link, and invalid-ID message.
2. Edit ROM: Steam App ID is visible, numeric, persisted, and clearable through the existing contract.
3. Save Data: raw and ZIP uploads remain opaque, original filenames and sizes are visible, and the list refreshes after upload/delete.
4. Desktop and narrow viewport checks for Save Data and Overview.
5. Upload/download SHA-256 equality for one raw save and one ZIP save.
6. Canonical resource folder and legacy fallback inspection.
7. Full npm gates and trunk fmt && trunk check.

No roadmap completion marker was changed because these required completion gates remain open.
