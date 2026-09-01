---
phase: 11
slug: local-pc-media-and-dlc-navigation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-01
---

# Phase 11 - Validation Strategy

## Test Infrastructure

| Property           | Value                                                                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Backend            | pytest through `uv run pytest`                                                                                                                   |
| Frontend           | Vitest through `npm run test`                                                                                                                    |
| API contract       | Generated OpenAPI types through `npm run generate`                                                                                               |
| Quick backend run  | `cd backend && uv run pytest tests/endpoints/roms/test_pc_metadata.py tests/handler/filesystem/test_roms_handler.py -q`                          |
| Quick frontend run | `cd frontend && npm run test -- --run src/v2/components/GameDetails/PcComponents.test.ts src/v2/components/GameDetails/PcMetadataReview.test.ts` |
| Full phase run     | Focused backend tests, generated types, frontend typecheck/Vitest, isolated Playwright flow, and Trunk                                           |

## Sampling Rate

- After each backend task commit, run the relevant focused pytest files.
- After each frontend task commit, run the affected Vitest files and typecheck.
- After every wave, run the complete focused backend/frontend commands.
- Before phase verification, run the source-tree sentinel before and after the
  isolated browser flow.
- Maximum feedback latency: 90 seconds for focused tests.

## Per-Task Verification Map

| Task ID  | Plan | Wave | Requirement                          | Threat Ref         | Secure Behavior                                                    | Test Type       | Automated Command                                                                                                                     | Status  |
| -------- | ---- | ---- | ------------------------------------ | ------------------ | ------------------------------------------------------------------ | --------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 11-01-01 | 01   | 1    | PCLM-01, PCLM-02                     | T-11-01            | Selection records bind role to path and SHA-256, not host paths    | model/migration | `uv run pytest tests/models/test_rom.py -q`                                                                                           | pending |
| 11-01-02 | 01   | 1    | PCLM-01, PCSAFE-01                   | T-11-02            | Only verified direct image bytes are copied into owned storage     | filesystem/API  | `uv run pytest tests/handler/filesystem/test_pc_media_handler.py tests/endpoints/roms/test_pc_metadata.py -q`                         | pending |
| 11-01-03 | 01   | 1    | PCLM-02, PCSAFE-01                   | T-11-03            | Rescan preserves exact evidence and cleans only owned stale assets | scanner         | `uv run pytest tests/handler/test_scan_handler.py tests/handler/filesystem/test_roms_handler.py -q`                                   | pending |
| 11-02-01 | 02   | 2    | PCDLC-01                             | T-11-04            | DLC candidate/apply scope cannot change base metadata              | API             | `uv run pytest tests/endpoints/roms/test_pc_metadata.py tests/handler/metadata/test_pc_match_handler.py -q`                           | pending |
| 11-02-02 | 02   | 2    | PCLM-01, PCLM-02                     | T-11-02            | UI requires an explicit role and retains error state               | Vitest          | `npm run test -- --run src/v2/components/GameDetails/PcLocalMediaReview.test.ts`                                                      | pending |
| 11-02-03 | 02   | 2    | PCDLC-02                             | T-11-05            | DLC card uses an internal URL and never opens IGDB                 | Vitest          | `npm run test -- --run src/v2/components/GameDetails/FilesTab/FilesTab.test.ts src/v2/components/GameDetails/RelatedGameCard.test.ts` | pending |
| 11-03-01 | 03   | 3    | PCLM-01, PCLM-02, PCDLC-01, PCDLC-02 | T-11-01 to T-11-05 | Fixture proves full operator flow and source immutability          | Playwright      | `npm run test:e2e -- pc-local-media-and-dlc-navigation.spec.ts`                                                                       | pending |
| 11-03-02 | 03   | 3    | PCSAFE-01, PCTEST-01                 | T-11-02, T-11-03   | Invalid/archived inputs cannot become artwork                      | regression      | focused pytest and Vitest suites                                                                                                      | pending |
| 11-03-03 | 03   | 3    | All                                  | T-11-01 to T-11-05 | Contract, types, format, lint, and targeted browser evidence agree | quality gate    | `trunk fmt && trunk check`                                                                                                            | pending |

## Wave 0 Requirements

Existing pytest, Vitest, OpenAPI generation, and Playwright infrastructure cover
the phase. New focused test files are introduced by their owning TDD tasks.

## Manual-Only Verification

| Behavior                                                                         | Requirement       | Why Manual                                         | Test Instructions                                                                                                                                                         |
| -------------------------------------------------------------------------------- | ----------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Visual crop, focus return, keyboard/gamepad behavior, and readable narrow layout | PCLM-01, PCDLC-02 | Browser interaction and responsive visual judgment | In the isolated stack select each role, open/close dialogs with keyboard, activate the local DLC card, and inspect desktop plus narrow viewport.                          |
| Exact source-image persistence after a real rescan                               | PCLM-02           | Requires a controlled external fixture change      | Snapshot source tree, select a fixture image, rescan unchanged, then change/remove only the disposable fixture image and rescan. Confirm only its owned selection clears. |

## Validation Sign-Off

- [x] All tasks have an automated verification command.
- [x] Sampling continuity has no three-task unverified gap.
- [x] Existing infrastructure covers Wave 0.
- [x] No watch-mode commands are used.
- [x] Focused feedback latency is bounded.

**Approval:** approved 2026-09-01
