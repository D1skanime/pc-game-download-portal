---
phase: 23-mehrsprachige-steam-metadaten-deutsche-englische-und-weitere
plan: 01
subsystem: metadata
tags: [steam, metadata, localization, pytest]
requires:
  - phase: 18-steam-metadata-integration-fur-pc-games-und-dlcs
    provides: Same-app Steam enrichment and German-first scalar fallback behavior
provides:
  - Bounded, canonical Steam text-language configuration
  - Validated provenance-bearing localized Steam text variants
affects: [steam_metadata, PC metadata enrichment, Phase 23 plans 02 and 03]
tech-stack:
  added: []
  patterns:
    [
      Allowlisted provider-language mapping,
      same-app localized response validation,
    ]
key-files:
  created: []
  modified:
    - backend/config/__init__.py
    - backend/handler/metadata/steam_handler.py
    - backend/tests/handler/metadata/test_steam_handler.py
    - env.template
key-decisions:
  - "Steam request identifiers map through an explicit allowlist to UI base tags."
  - "All configured locales are validated against the requested positive app ID before creating a text variant."
patterns-established:
  - "Localized Steam responses remain additive provenance data while legacy German-first scalar fields stay compatible."
requirements-completed: [STEAM-02, STEAM-05]
duration: 19min
completed: 2026-10-04
---

# Phase 23 Plan 01: Bounded Steam Text Variant Acquisition Summary

**Configured German, English, and supported additional Steam text variants are retained per validated app ID while legacy German-first display fields remain intact.**

## Performance

- **Duration:** 19 min
- **Tasks:** 2 completed
- **Files modified:** 4

## Accomplishments

- Added a canonical, deduplicated, allowlisted `STEAM_API_TEXT_LANGUAGES` configuration with German and English by default.
- Fetches every bounded configured language only for the already requested Steam app ID and drops malformed, mismatched, empty, or unavailable responses independently.
- Persists trimmed `name` and `summary` variants with Steam-language provenance under `steam_metadata.text_variants` without changing scalar display fallback behavior.

## Task Commits

1. **Task 1: Specify bounded same-app Steam text-variant behavior** - `fbff0dd1c` (test)
2. **Task 2: Implement configured same-app Steam text variants** - `c246fce95` (feat)

## Files Created/Modified

- `backend/config/__init__.py` - Defines the supported Steam-to-UI language map and parses bounded configured request languages.
- `env.template` - Documents the default German and English text-variant configuration.
- `backend/handler/metadata/steam_handler.py` - Validates same-app locale responses and emits provenance-bearing text variants.
- `backend/tests/handler/metadata/test_steam_handler.py` - Covers default, configured, duplicate, malformed, and display-compatibility cases.

## Decisions Made

- Used an explicit Steam request-language to UI-base-tag map instead of deriving tags from display names or browser locale data.
- Kept English as the existing fallback source for scalar fields while collecting all configured validated variants additively.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Resolved scoped handler type-check errors**

- **Found during:** Task 2
- **Issue:** The scoped Trunk check reported incompatible inferred list assignment and dynamic `TypedDict` keys in the metadata builder.
- **Fix:** Used separately typed DLC, developer, and publisher assignments.
- **Files modified:** `backend/handler/metadata/steam_handler.py`
- **Verification:** Scoped `trunk check --no-fix` passed.
- **Committed in:** `c246fce95`

**Total deviations:** 1 auto-fixed (1 blocking)

## Issues Encountered

- The plan-mandated `cd backend && uv run pytest tests/handler/metadata/test_steam_handler.py -q` is blocked before collection by the pre-existing unavailable MariaDB endpoint at `127.0.0.1:3306`.
- `cd backend && uv run pytest --noconftest tests/handler/metadata/test_steam_handler.py -q` passed all 19 handler tests. It omits only the database bootstrap fixture and does not access external services.

## Verification

- PASS: `cd backend && uv run pytest --noconftest tests/handler/metadata/test_steam_handler.py -q` (19 passed, one pre-existing pytest-cache permission warning)
- PASS: `trunk fmt -- backend/config/__init__.py env.template backend/handler/metadata/steam_handler.py backend/tests/handler/metadata/test_steam_handler.py`
- PASS: `trunk check --no-fix -- backend/config/__init__.py env.template backend/handler/metadata/steam_handler.py backend/tests/handler/metadata/test_steam_handler.py`
- BLOCKED: `cd backend && uv run pytest tests/handler/metadata/test_steam_handler.py -q` (MariaDB unavailable at `127.0.0.1:3306`)

## Known Stubs

None.

## Next Phase Readiness

Phase 23 plans 02 and 03 can merge, expose, and select the collected `steam_metadata.text_variants` data. The normal backend test command remains blocked until the local test MariaDB endpoint is restored.

## Self-Check: PASSED

- Confirmed all four changed implementation and test files exist.
- Confirmed commits `fbff0dd1c` and `c246fce95` exist in Git history.
