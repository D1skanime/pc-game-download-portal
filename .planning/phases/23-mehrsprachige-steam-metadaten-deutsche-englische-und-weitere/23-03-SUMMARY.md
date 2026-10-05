---
phase: 23-mehrsprachige-steam-metadaten-deutsche-englische-und-weitere
plan: 03
subsystem: api-and-frontend
tags: [steam, metadata, localization, openapi, vue, vitest, uat]
requires:
  - phase: 23-mehrsprachige-steam-metadaten-deutsche-englische-und-weitere
    provides: Additively persisted parent and DLC Steam text variants
provides:
  - Typed detail-only Steam text variant contract for parent and DLC metadata
  - Client-side selected-locale, English, then legacy summary resolution
  - User-accepted isolated multilingual browser UAT
affects: [PC detail views, Steam metadata, generated frontend models]
tech-stack:
  added: []
  patterns:
    - Pure locale resolver with no provider or scan side effects
    - Steam variants are used only when Steam remains the display authority
key-files:
  created:
    - frontend/src/v2/utils/steamTextVariants.ts
    - frontend/src/v2/utils/steamTextVariants.test.ts
  modified:
    - backend/endpoints/responses/rom.py
    - backend/tests/endpoints/roms/test_rom.py
    - frontend/src/v2/views/GameDetails.vue
    - frontend/src/v2/components/GameDetails/PcDlcDetail.vue
key-decisions:
  - "Manual text keeps precedence over localized Steam text."
  - "Non-Steam selected metadata keeps precedence over localized Steam text."
  - "Switching locale resolves already-returned metadata locally and never starts a Steam request or scan."
requirements-completed: [STEAM-04, STEAM-05]
completed: 2026-10-05
---

# Phase 23 Plan 03: Localized Steam Detail Presentation Summary

**Detailed parent and DLC views now choose persisted Steam text by UI locale, fall back to English and legacy text, and keep manual or non-Steam metadata authoritative.**

## Accomplishments

- Added narrow typed Steam metadata and text-variant response schemas only to existing detailed parent and DLC responses, then regenerated the dependent frontend models.
- Added a pure, tested locale resolver that normalizes the UI base locale and selects selected-language text, English, then legacy summary.
- Wired the resolver into parent and DLC detail surfaces without adding browser-to-Steam traffic or scan work on locale changes.
- Completed a fresh isolated, read-only synthetic-fixture UAT stack. The user accepted the live UAT on 2026-10-05.
- Follow-up quick work retained localized DLC text after a generic IGDB metadata selection, covering the real UAT path where Steam provenance remains available but is no longer the selected metadata source.

## Task Commits

1. **Task 1: Detailed response regression coverage** - `fccee18bc` (test)
2. **Task 1: Typed Steam detail response contract** - `0c0fb9dbd` (feat)
3. **Task 2: Localized resolver regression coverage** - `d31526ac2` (test)
4. **Task 2: Localized parent and DLC detail presentation** - `c2fa25b39` (feat)
5. **UAT evidence and isolated-stack preparation** - `05521f5ea`, `703cb658a` (docs)
6. **Post-UAT DLC authority regression and fix** - `94b880e66`, `57e4376e1`, `81d981b56`

## Verification

- PASS: `npm run test -- steamTextVariants`.
- PASS: `npm run typecheck`.
- PASS: Detail API contract, generated models, parent resolver, and DLC resolver were exercised by focused regression tests.
- PASS: Isolated disposable stack used a new empty database, read-only synthetic fixture mount, disabled scheduled rescans, retained a 15-minute cron configuration, and disabled the 10-second automation path.
- PASS: The user performed live UAT for parent and DLC localized text and accepted it on 2026-10-05.
- BLOCKED: The host database-backed pytest suite cannot start because its MariaDB endpoint at `127.0.0.1:3306` is unavailable. This is an environment limitation; it is not presented as a passing host-suite result.

## Deviations and Follow-up Work

- The live UAT showed that an IGDB-selected DLC could still retain valid persisted Steam variants. The resolver authority rule was broadened from Steam-only selection to all non-manual selected sources, with a focused regression test.
- Related UAT follow-ups added root-level PC download components, allowed nested existing-PC quick scan synchronization, and rendered local DLC and expansion cards on game overviews.

## Known Follow-up

Steam HTML entities such as `&quot;` in a localized description remain a separate normalization issue. It was observed during UAT but is not silently claimed as fixed by this phase.

## Self-Check: PASSED

- Confirmed all Plan 03 implementation, generated-client, and test files are present in Git history.
- Confirmed the user accepted the disposable live UAT.
