# Phase 33 Validation Architecture

## Scope and authority

Phase 33 proves that a fresh installation enters the existing PC/Windows mapping workflow before the empty-library screen. The canonical persisted representation is:

- Storage root: configured deployment root Games
- Mapping relative_path: pc
- Effective source target: Games/pc
- Platform identity: canonical Windows platform returned by the server, even when filesystem discovery reports pc

Only authenticated setup completion may call the mutating POST /storage/legacy/bootstrap. Home and Scan readiness are read-only and use the existing GET mapping/root contracts. The backend scan command builder remains authoritative and fail-closed.

## Automated command matrix

| Gate | Command | Owner |
|---|---|---|
| Naming and deployment render | bash scripts/verify-pgdp-naming.sh and docker compose --env-file examples/portainer.env.example -f examples/portainer-stack.yml config | Plan 04 |
| Storage bootstrap and exact pair | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/backend && uv run pytest tests/endpoints/storage/test_legacy_bootstrap_paths.py tests/endpoints/test_storage.py -q' | Plan 01 |
| Readiness helper | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/frontend && npm run test -- src/services/api/storage.test.ts' | Plan 01 |
| Setup handoff | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/frontend && npm run test -- src/v2/views/Auth/Setup.test.ts' | Plan 02 |
| Empty Home and Scan gates | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/frontend && npm run test -- src/v2/views/Home.test.ts src/v2/views/Scan.test.ts' | Plan 03 |
| Frontend integration | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/frontend && npm run typecheck && npm run test' | Plan 04 |
| Backend integration | docker compose run --rm --no-deps --entrypoint bash romm-dev -lc 'cd /app/backend && uv run pytest tests --collect-only -q && uv run pytest tests/endpoints/storage/test_legacy_bootstrap_paths.py tests/endpoints/test_storage.py tests/endpoints/sockets/test_scan.py tests/integration/test_mapped_scan.py -q' | Plan 04 |
| Repository hygiene | git diff --check and scoped git status --short from the canonical checkout | Plan 04 |

All project tooling runs in romm-dev; host Node/npm/uv are not accepted as substitutes.

## Sampling cadence

- Per Task: run the focused command for the changed contract before moving to the next task.
- Per Wave 1: run Plan 01 backend and frontend focused gates plus git diff --check.
- Per Wave 2: run Plan 02 setup tests, Plan 03 Home/Scan tests, and frontend typecheck.
- Phase gate: run deployment render/naming, full frontend suite, backend collection/focused integration, and disposable browser UAT before verification.
- Browser sampling: exercise the golden path in v2-dark and v2-light, at desktop and narrow viewport, with mouse, touch, keyboard, and gamepad. Repeat the no-mapping, unhealthy-root, and reload cases at least once each.

## Wave 0 gaps and closure

These gaps came from the research inventory and are now assigned to executable plans:

| Gap | Closure | Evidence |
|---|---|---|
| Setup view/router test | Plan 02 Task 1 | Setup.test.ts, setup completion route assertion |
| Home empty-state mapping-vs-scan test | Plan 03 Task 1 | Home.test.ts, CTA absence/presence |
| Fresh backend fixture for exact Games/pc + Windows identity + persistence | Plan 01 Task 1 | bootstrap endpoint tests and exact root/path assertions |
| Disposable first-run command/browser matrix | Plan 04 Tasks 1-2 | this file plus 33-UAT.md |
| Readiness mutates storage during Home/Scan | Plan 01 Task 2 and Plan 03 Task 1 | GET-only API mocks and zero POST assertions |
| Input-modality coverage | Plan 04 Task 2 | browser evidence for mouse/touch/keyboard/gamepad |

No Wave 0 gap remains unassigned. Any unavailable infrastructure is recorded as blocked evidence, never silently converted to pass.

## Evidence rules

Use disposable state only. Record exact Compose project ID, container image, synthetic credentials policy, fixture manifest before/after, browser URL, viewport/theme/input modality, screenshots or traces, test output, and cleanup result. Do not inspect or alter live NAS mounts, Team4s, existing volumes, or production credentials.
