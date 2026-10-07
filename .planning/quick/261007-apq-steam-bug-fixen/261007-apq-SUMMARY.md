---
phase: quick
plan: 261007-apq
subsystem: frontend
tags: [steam, setup-wizard, heartbeat, i18n, vitest]

requires:
  - phase: 18-steam-metadata-integration
    provides: Steam heartbeat flag and metadata provider contract
provides:
  - Steam setup-wizard catalog entry with flag-only heartbeat semantics
  - Localized Steam setup copy across all setup locales
  - Focused regression coverage for Steam rendering, probing, disabled state, and statuses
affects: [setup-wizard, metadata-settings, frontend-locales]

tech-stack:
  added: []
  patterns: [existing metadata heartbeat probe and flag-only status vocabulary]

key-files:
  created: [frontend/src/v2/components/Auth/SetupStepMetadata.test.ts]
  modified:
    [
      frontend/src/v2/components/Auth/SetupStepMetadata.vue,
      frontend/src/locales/*/setup.json,
    ]

key-decisions:
  - "Steam remains a flag-only provider: STEAM_API_ENABLED controls availability and no setup-local toggle or API key path was added."
  - "Steam is rendered beside SteamGridDB but remains a separate heartbeat provider with key steam."

patterns-established:
  - "Flag-only metadata providers use disabled, available, checking, and unreachable status vocabulary."

requirements-completed: []

duration: 10min
completed: 2026-10-07
status: complete
---

# Quick Task 261007-apq: Steam setup wizard regression fix

**Steam is now visible in setup with global flag activation, heartbeat health probing, and parity-checked localized guidance.**

## Performance

- **Duration:** Approximately 10 minutes
- **Started:** 2026-10-07T07:44:00Z
- **Completed:** 2026-10-07T07:54:00Z
- **Tasks:** 3
- **Files modified:** 20

## Accomplishments

- Added Steam to `SetupStepMetadata` with `/assets/scrappers/steam.svg`, provider key `steam`, `requiresKey: false`, and `STEAM_API_ENABLED` gating.
- Preserved the existing heartbeat probe and flag-only status vocabulary, including no-probe behavior while disabled.
- Added English, German, and translated setup copy to all 18 setup locales with equal sorted key sets.
- Added six focused setup regression tests; the existing Steam-versus-SteamGridDB heartbeat parity test remains green.

## Task Commits

1. **Focused regression coverage** - `c7bc3507d` (test)
2. **Steam setup provider entry** - `b18270d3c` (feat)
3. **Localized Steam setup guidance** - `ec8bbe694` (feat)

Planning artifacts were intentionally not staged or committed, per task instruction.

## Files Created/Modified

- `frontend/src/v2/components/Auth/SetupStepMetadata.vue` - Steam catalog entry and global flag gating.
- `frontend/src/v2/components/Auth/SetupStepMetadata.test.ts` - Steam rendering, probing, disabled, status, and authoritative-copy tests.
- `frontend/src/locales/*/setup.json` - Two sorted Steam keys in all 18 setup locales.

## Decisions Made

- Reused the existing metadata heartbeat store and status mapping, with no new provider, toggle, config store, or API-key architecture.
- Kept `backend/endpoints/sockets/scan.py` and all unrelated dirty files untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected temporary remote locale editor escaping**

- **Found during:** Task 3
- **Issue:** The first temporary Python editor emitted invalid JSON quoting for translated strings.
- **Fix:** Restored only the 18 setup locale files and reran the editor with `json.dumps(..., ensure_ascii=False)`.
- **Verification:** All setup JSON files parse; setup parity and sorting pass.
- **Committed in:** `ec8bbe694`

**Total deviations:** 1 auto-fixed blocking editor issue.

## Verification

- Focused Vitest: **7/7 passed** across `SetupStepMetadata.test.ts` and `heartbeat.test.ts`.
- Frontend typecheck: **passed** (`vue-tsc --noEmit`).
- Setup locale parity and sorted-key check: **passed**, 18 files and 98 keys.
- Task-scoped `git diff --check`: **passed**.

## Blockers / Pre-existing Issues

- Full `check_i18n_locales.py` remains red because existing non-setup locale files lack `refreshing-media` and `media-only*` keys. No such issue exists in the 18 setup files changed here.
- Full `check_i18n_sorted.py` remains red only for existing `de_DE/rom.json`, `de_DE/scan.json`, `en_US/rom.json`, and `en_US/scan.json`; setup files pass the same sorting logic.
- Repository-wide `git diff --check` remains red on pre-existing blank-line-at-EOF changes in unrelated generated files.
- `backend/endpoints/sockets/scan.py` was already dirty before this task and is not part of any task commit.

## Known Stubs

None.

## Self-Check: PASSED

- Summary file exists at `.planning/quick/261007-apq-steam-bug-fixen/261007-apq-SUMMARY.md`.
- Commits `c7bc3507d`, `b18270d3c`, and `ec8bbe694` exist.
- Commit range contains only frontend test/component/locale files.

---

_Quick task: 261007-apq_
_Completed: 2026-10-07_
