---
status: complete
quick_task: 261002-lj2
subsystem: pc-automation
tags: [pc-automation, steam, localization, scan, uat]
requires:
  - phase: 22
    provides: PC automation and isolated UAT infrastructure
provides:
  - Final durable scan versions for PC automation evidence
  - Persisted German Steam display summaries for scan-only patches
  - Scanner-compatible Cyberpunk parent and DLC fixture contract
affects: [phase-22-uat, pc-automation, steam-metadata]
key-files:
  created: []
  modified:
    - backend/handler/scan_handler.py
    - backend/tests/handler/test_scan_handler.py
    - backend/tests/integration/test_scan_source_immutability.py
    - .planning/phases/22-bulk-automatisierung-f-r-pc-spiel-und-dlc-zuordnung/22-UAT.md
key-decisions:
  - "Queue evidence is produced only after the scan reloads its durable target."
  - "Any non-empty normalized Steam patch reaches the existing durable persistence path."
  - "Phantom Liberty is a child below the Cyberpunk parent DLC directory, not a flat sibling ROM."
metrics:
  tests_passed: 20
  completed: 2026-10-02
---

# Quick Task 261002-lj2: Correct Phase 22 scan lifecycle, Steam locale persistence, and DLC UAT layout

The Phase 22 scan now creates automation evidence from the final persisted
catalog version, persists eligible localized Steam display updates, and has a
synthetic scanner-compatible parent-plus-DLC UAT fixture layout.

## Accomplishments

- Reloaded the durable parent after scan-side Steam, media, and component-link
  writes before parent or component automation runs. This prevents a new queue
  row from becoming stale through its own scan while retaining normal later
  stale-version protection.
- Reproduced the German-summary defect for Steam app IDs `1091500` and
  `2138330` against a disposable MariaDB catalog. The scan now persists a
  non-empty normalized Steam display patch even when it has no structured
  metadata or media changes. The durable records contain the German summary,
  `language=german`, and no summary fallback marker.
- Added immutable source coverage for `Cyberpunk 2077/dlc/Phantom Liberty` and
  updated the isolated UAT procedure to require 20 text-only fixtures in that
  scanner-recognized layout and a catalog component assertion before browser
  review.

## Verification

- Disposable MariaDB TDD run: the two localized-summary cases failed before
  the display-patch persistence change and passed afterwards.
- Disposable MariaDB focused follow-up: 36 scan-handler tests passed (with one
  known unrelated structured-metadata test excluded) and 16 Steam-merge plus
  PC-automation database tests passed.
- Focused lifecycle and media timestamp test run: 2 passed.
- Source immutability suite: 4 passed.
- A direct host pytest rerun is unavailable by design because its configured
  MariaDB endpoint is `127.0.0.1:3306` and no host database is running. The
  disposable database used above was removed after verification.

## Task Commits

1. `0170f8289` `fix(22): finalize PC automation scan evidence`
2. `8f144300b` `fix(22): persist localized Steam scan summaries`

## Known Limitations

- The full combined affected-suite run retains existing unrelated failures in a
  structured-metadata expectation, Steam fallback-language coverage, and some
  filesystem fixture/download tests. They were not changed by this quick task.
- Browser UAT remains the next checkpoint. It must use a newly named
  disposable Compose project and read-only synthetic fixture directory.

## Next Step

Prepare a fresh isolated browser UAT stack, verify the Cyberpunk parent exposes
the Phantom Liberty DLC component in the disposable catalog, then hand the
browser test back to the user.
