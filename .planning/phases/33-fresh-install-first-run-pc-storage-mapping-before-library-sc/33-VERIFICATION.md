---
phase: 33-fresh-install-first-run-pc-storage-mapping-before-library-sc
verified: "2026-10-20T10:22:06.526349+02:00"
status: passed
scope: tested Phase 33 setup, readiness and collection correction
reverification: true
limitations:
  - Physical gamepad was unavailable and remains untested.
  - Independent deep code review remains pending.
---

# Phase 33 verification refresh

The 2026-10-15 report is preserved (trailing whitespace normalized) in 33-VERIFICATION-2026-10-15.md.
Its unreachable test database, unavailable Chromium and early implementation
gaps are superseded by actual executable evidence and the user's live UAT
acceptance on 2026-10-20. This is a scoped verification refresh, not an
independent deep source-code review or a blanket Phase 34 acceptance.

## Reverification performed

- Re-ran 33-evidence-validate.py against the final actual browser receipt with
  --assert-cleanup: PASS.
- Recomputed all 81 file hashes listed in 33-ACCEPTANCE-RECEIPTS.json.
- Compared 2511 tracked backend/frontend source files against the accepted
  final browser snapshot: no differences.
- Confirmed user acceptance recorded in 33-UAT.md and 33-06-SUMMARY.md.

## Goal evidence

| Observable behavior | Result | Evidence |
| --- | --- | --- |
| Direct Games folders discovered; pc maps to Windows; unknown folders assigned inline | PASS | Final browser discovery and inline_assignment |
| Server readiness precedes Home/Scan and survives reload | PASS | ready, reload, get_only and mapped_reads |
| Selected child indexes as one game with both archive parts | PASS | explicit_child_scope and detailed ROM response |
| Parent retirement is atomic; retained state does not migrate to child | PASS | parent_retired, retained audit and SQL reconnect regressions |
| Only exclusively owned media removed; shared/source data preserved | PASS | safe_owned_cleanup and source manifests |
| Full and scheduled scans discover new direct children without parent recreation | PASS | normal_discovers_children and scheduled_discovers_children |
| Worker progress uses actual inventory | PASS | Exact actual worker counts 3/1/4/6 |
| Themes, 320px/desktop, mouse, keyboard and touch | PASS | Named browser checks and 48px measured controls |
| Human acceptance of exercised live scope | PASS | User: "gut uat so weit bestanden" |

## Supporting checks and limits

All 22 final browser checks passed. Frontend typecheck, 1,102 tests, build and
maintainability passed. MariaDB/PostgreSQL collection, authorization, lock/count
and retained-state suites passed as detailed in 33-10-SUMMARY.md. Fresh final
schema cycles passed on MariaDB, MySQL and PostgreSQL with exact source parity.
Scoped lint and commit hooks passed. Historical unrelated legacy backend
failures remain recorded; the whole backend test suite is not claimed green.

Physical gamepad remains untested. Independent deep review is still pending.
The user explicitly requested push and merge to main after accepting live UAT.
Phase 34 Portainer acceptance and frozen 34-16 remain open. No source Games,
media reset or deployment change is part of this shipping step.
