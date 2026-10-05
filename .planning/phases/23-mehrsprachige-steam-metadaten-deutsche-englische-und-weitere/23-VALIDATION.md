---
phase: 23
slug: mehrsprachige-steam-metadaten-deutsche-englische-und-weitere
status: accepted-with-infrastructure-limitation
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-04
---

# Phase 23 Validation Strategy

> Per-phase validation contract for bounded Steam text acquisition, additive
> parent and DLC persistence, typed detail responses, and client-side locale
> resolution.

## Test Infrastructure

| Property               | Value                                                                                                                                                                                                                                                                                                                                                                                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Framework**          | pytest with pytest-asyncio and Vitest                                                                                                                                                                                                                                                                                                                                                                        |
| **Config file**        | `backend/pytest.ini`, `frontend/vitest.config.ts`                                                                                                                                                                                                                                                                                                                                                            |
| **Quick run command**  | `cd backend && uv run pytest tests/handler/metadata/test_steam_handler.py tests/handler/metadata/test_steam_merge.py tests/handler/metadata/test_pc_automation.py tests/handler/database/test_roms_handler.py tests/endpoints/roms/test_pc_metadata.py tests/endpoints/sockets/test_scan.py tests/endpoints/roms/test_rom.py -q && cd ../frontend && npm run test -- steamTextVariants && npm run typecheck` |
| **Full suite command** | `trunk fmt && trunk check && cd frontend && npm run typecheck && npm run test`                                                                                                                                                                                                                                                                                                                               |
| **Estimated runtime**  | Under 120 seconds for focused automated checks where isolated backend and frontend infrastructure is available                                                                                                                                                                                                                                                                                               |

## Sampling Rate

- **After every task commit:** Run the mapped focused pytest or Vitest command.
- **After every plan wave:** Run the cumulative focused backend suite; after Wave 3, also run generated-client typecheck and the resolver suite.
- **Before phase verification:** Run scoped Trunk formatting/checks, focused backend tests, generated-client typecheck, resolver tests, and the isolated browser UAT.
- **Max feedback latency:** 120 seconds for automated feedback where infrastructure is available.

## Per-Task Verification Map

| Task ID  | Plan | Wave | Requirements       | Threat Ref                | Secure Behavior                                                                                                                                               | Test Type                             | Automated Command                                                                                                                                                                                                                                                                                                                                                               | File Exists                                                                          | Status  |
| -------- | ---- | ---- | ------------------ | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------- |
| 23-01-01 | 01   | 1    | STEAM-02, STEAM-05 | T-23-01, T-23-02, T-23-03 | Defines a bounded, canonical same-App-ID language request set and failure isolation before implementation.                                                    | async handler TDD                     | `cd backend && uv run pytest tests/handler/metadata/test_steam_handler.py -q`                                                                                                                                                                                                                                                                                                   | Yes                                                                                  | pending |
| 23-01-02 | 01   | 1    | STEAM-02, STEAM-05 | T-23-01, T-23-02, T-23-03 | Acquires only validated non-empty Steam variants, retains German-first legacy scalars, and makes malformed or unavailable locales non-fatal.                  | async handler                         | `cd backend && uv run pytest tests/handler/metadata/test_steam_handler.py -q`                                                                                                                                                                                                                                                                                                   | Yes                                                                                  | pending |
| 23-02-01 | 02   | 2    | STEAM-02, STEAM-05 | T-23-04, T-23-05, T-23-06 | Defines additive per-language merge, manual and non-Steam authority, authoritative component-column persistence, and scan/selection propagation.              | merge and endpoint TDD                | `cd backend && uv run pytest tests/handler/metadata/test_steam_merge.py tests/handler/metadata/test_pc_automation.py tests/handler/database/test_roms_handler.py tests/endpoints/roms/test_pc_metadata.py tests/endpoints/sockets/test_scan.py -q`                                                                                                                              | Yes                                                                                  | pending |
| 23-02-02 | 02   | 2    | STEAM-02, STEAM-05 | T-23-04, T-23-05, T-23-06 | Persists only valid Steam-owned variants additively for parent and DLC metadata without migrations, shadow metadata, or protected-field loss.                 | merge, handler, and route             | `cd backend && uv run pytest tests/handler/metadata/test_steam_merge.py tests/handler/metadata/test_pc_automation.py tests/handler/database/test_roms_handler.py tests/endpoints/roms/test_pc_metadata.py tests/endpoints/sockets/test_scan.py -q`                                                                                                                              | Yes                                                                                  | pending |
| 23-03-01 | 03   | 3    | STEAM-04, STEAM-05 | T-23-07                   | Publishes a narrow typed text-variant contract only on detailed parent and DLC responses, preserving existing authorization and list payload shape.           | schema/endpoint and OpenAPI           | `cd backend && uv run pytest tests/endpoints/roms/test_rom.py -q && cd ../frontend && npm run generate && npm run typecheck`                                                                                                                                                                                                                                                    | Partial, generated model and endpoint assertions are created or updated in this task | pending |
| 23-03-02 | 03   | 3    | STEAM-04, STEAM-05 | T-23-08, T-23-09, T-23-10 | Resolves UI base language, then English, then legacy summary locally, while retaining manual and non-Steam authority and recording isolated fixture evidence. | Vitest TDD, typecheck, and UAT record | `cd frontend && npm run test -- steamTextVariants && npm run typecheck && cd .. && trunk check --no-fix -- backend/endpoints/responses/rom.py backend/tests/endpoints/roms/test_rom.py frontend/src/v2/utils/steamTextVariants.ts frontend/src/v2/utils/steamTextVariants.test.ts frontend/src/v2/views/GameDetails.vue frontend/src/v2/components/GameDetails/PcDlcDetail.vue` | No, `steamTextVariants.test.ts` is created in this task                              | pending |
| 23-03-03 | 03   | 3    | STEAM-04, STEAM-05 | T-23-08, T-23-09, T-23-10 | Confirms parent and DLC German, English, and missing-language fallback behavior in a disposable read-only synthetic fixture without source changes.           | integration plus human verification   | `cd backend && uv run pytest tests/handler/metadata/test_steam_handler.py tests/handler/metadata/test_steam_merge.py tests/endpoints/roms/test_rom.py -q && cd ../frontend && npm run test -- steamTextVariants && npm run typecheck`                                                                                                                                           | Partial, `23-UAT.md` is created or updated in Task 23-03-02                          | pending |

_Status: pending, green, red, or flaky._

## Wave 0 Requirements

- [ ] `frontend/src/v2/utils/steamTextVariants.test.ts` must be created in Task 23-03-02 before the resolver implementation is accepted.
- [ ] Endpoint assertions in `backend/tests/endpoints/roms/test_rom.py` must cover detailed parent and DLC variant serialization before response-schema implementation is accepted.
- [ ] No additional test framework, package, migration, or external service setup is required.

## Manual-Only Verifications

| Behavior                           | Requirements       | Why Manual                                                                            | Test Instructions                                                                                                                                                                                                                                                    |
| ---------------------------------- | ------------------ | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parent and DLC locale presentation | STEAM-04, STEAM-05 | A browser must observe reactive UI language changes and the rendered detail surfaces. | In the disposable UAT stack, verify German, English, and a supported UI locale without a stored variant for both a PC parent and DLC. Confirm no rescan or provider request is needed after changing the locale.                                                     |
| Immutable fixture source           | STEAM-02, STEAM-05 | Read-only mount and pre/post manifest identity need environment-level observation.    | Use only the synthetic text-only fixture specified in `23-UAT.md`; confirm its mount is read-only, compare recorded names, hashes, sizes, and structure before and after, and record no NAS, Team4s, real-library, production-data, credential, or real-path access. |

## Validation Sign-Off

- [x] Every Plan 01, 02, and 03 task has an automated command or a declared Wave 0 dependency.
- [x] Sampling continuity has no three consecutive tasks without automated verification.
- [x] Wave 0 covers the resolver test and detailed response assertions.
- [x] No watch-mode flags are used in CI verification.
- [x] Focused frontend feedback completed within the target latency.
- [x] User-accepted browser evidence covers parent and DLC localized presentation in the isolated read-only fixture.
- [ ] `nyquist_compliant: true` remains deferred because the database-backed host pytest suite cannot bootstrap without MariaDB at `127.0.0.1:3306`.

**Approval:** accepted by user UAT on 2026-10-05, with the explicit host-MariaDB limitation recorded above.
