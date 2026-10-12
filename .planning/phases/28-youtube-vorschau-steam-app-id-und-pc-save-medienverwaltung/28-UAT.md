# Phase 28 UAT

Date: 2026-10-12
Environment: canonical Linux checkout /home/d1sk/pc-game-download-portal
Branch: codex/phase-28-youtube-steam-saves

## Result

Status: PARTIAL, completion gates pending.

The backend Save/State implementation and migration tests pass. Phase-specific frontend tests, typecheck, and production build pass inside the running romm-dev container. The RomM Dev stack is reachable on port 3100 and browser UAT verified the YouTube preview, Steam App ID field, and Save Data/State UI. Trunk is not installed in the container, and mutating upload/download byte-hash round trips plus responsive browser checks remain pending.

## Automated evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Save/State filesystem, endpoint, and migration tests | PASS | backend/.venv/bin/pytest -q tests/handler/filesystem/test_assets_handler.py tests/endpoints/test_saves.py tests/endpoints/test_states.py tests/tasks/test_pc_save_migration.py -> 147 passed |
| Task registry plus migration/endpoints regression | PASS | backend/.venv/bin/pytest -q tests/handler/filesystem/test_assets_handler.py tests/endpoints/test_tasks.py tests/endpoints/test_saves.py tests/endpoints/test_states.py tests/tasks/test_pc_save_migration.py -> 164 passed |
| Python syntax for changed backend files | PASS | Worker verified all 9 backend files |
| git diff --check | PASS | Clean on the phase branch |
| Frontend focused tests | PASS | docker exec romm-dev npm run test -- --run ... -> 11 passed |
| Frontend typecheck | PASS | docker exec romm-dev npm run typecheck -> exit 0 |
| Production frontend build | PASS | docker exec romm-dev npm run build -> built in 4.86s, warnings only |
| Locale parity | BASELINE FAIL | Existing missing keys in scan.json, setup.json, and rom.json for 17 locales, unrelated to the new keys |
| Locale sorted gate | BASELINE FAIL | Existing unsorted locale files, including rom.json in most locales |
| Trunk fmt/check | BLOCKED | trunk is not installed |
| Dev-stack reachability | PASS | curl -I http://127.0.0.1:3100/ -> HTTP/1.1 200 OK; romm-dev container and Vite process active |

## Save/State matrix

The automated endpoint and migration suite covers the expected server behavior. Browser checks passed for the rendered YouTube preview, Steam App ID field, and Save Data/State surfaces. Byte-hash upload/download cells remain pending.

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

Remaining UAT and environment gates:

1. Save Data: perform raw and ZIP uploads, verify original filenames and sizes, then verify list refresh after upload/delete.
2. Desktop and narrow viewport checks for Save Data and Overview.
3. Upload/download SHA-256 equality for one raw save and one ZIP save.
4. Canonical resource folder and legacy fallback inspection.
5. Run trunk fmt && trunk check after Trunk is installed in the relevant Linux environment.

No roadmap completion marker was changed because Trunk and the mutating upload/download UAT cells remain open.
