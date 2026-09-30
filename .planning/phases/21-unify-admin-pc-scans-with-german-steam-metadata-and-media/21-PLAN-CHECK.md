# Phase 21 Plan Check

**Checked:** 2026-09-30
**Recheck:** Revision 1
**Plans checked:** 21-01 through 21-04
**Final verdict:** PASS with one MEDIUM advisory

## Recheck result

The revised plan set now achieves the Phase 21 goal backward from the locked
context: eligible administrator scans share the targeted German-first,
same-App-ID Steam patch, refresh new/update/complete PC records, reconcile
Steam candidates through owned storage, preserve operator-owned state, and
leave excluded scan paths and the source library untouched.

The dependency graph remains valid and acyclic: 21-01 and 21-02 are Wave 1,
21-03 depends on 21-02, and 21-04 depends on 21-01 and 21-03. All task
structures remain complete. No task adds deferred Steam login/synchronization,
changes DLC rules, accesses NAS or Team4s, starts Docker Compose, or writes to
the external source library.

## Earlier blockers and highs, rechecked

| Earlier finding                                       | Result           | Evidence                                                                                                                                                                                                                                                                     |
| ----------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Alembic filename/revision collision                   | Resolved         | 21-02 now plans `0132_steam_scan_owned_media_state.py` with revision `0132_steam_scan_owned_media_state` and `down_revision = "0131_owned_background_audio"`. The checked-in head is `0131_owned_background_audio`; neither existing 0130 nor 0131 migration is overwritten. |
| Missing Nyquist artifact                              | Resolved         | `21-VALIDATION.md` exists, maps D-01 through D-10 to commands, includes migration evidence and the source-immutability suite, and records blocked infrastructure as evidence rather than a pass.                                                                             |
| Missing executable D-11 UAT                           | Resolved         | 21-04 has a blocking human-verify task that records the isolated Witcher scenario in `21-UAT.md`, including PASS, FAIL, or BLOCKED.                                                                                                                                          |
| Owned-storage retry idempotence                       | Resolved in plan | 21-02 and 21-03 now require active-path reuse before download, post-commit cleanup only for returned unreferenced paths, no cleanup of reused paths, and duplicate-scan/no-orphan tests.                                                                                     |
| Missing roadmap source of truth                       | Resolved         | Phase 21 now has its explicit goal, reused STEAM-02/STEAM-05 scope, four plans, and waves in `ROADMAP.md`.                                                                                                                                                                   |
| Source-immutability and ambiguity/rate-limit coverage | Resolved         | 21-04 includes the source-immutability suite and explicit ambiguity/rate-limit no-op assertions; the validation matrix and final focused suite include the integration test.                                                                                                 |

## Remaining findings

### MEDIUM: Per-task verification commands omit a test file they claim to add

21-04 Tasks 1 and 2 list
`backend/tests/integration/test_scan_source_immutability.py` in `<files>` and
their actions, but their individual `<verify>` commands do not run it. The
final phase suite and Task 3 do run it, so the phase has coverage and this does
not block execution.

**Recommended repair:** Add
`tests/integration/test_scan_source_immutability.py -x` to Task 1 or Task 2's
automated verify command, so the TDD feedback loop checks the source-boundary
test at the same task that changes it.

## Passed dimensions

- Context compliance: D-01 through D-12 are represented, with the Witcher
  UAT as an explicit blocked-or-recorded checkpoint.
- Requirement coverage: STEAM-02 and STEAM-05 appear in all relevant plan
  front matter and are now explicitly reused by the Phase 21 roadmap entry.
- Architectural tiering: metadata resolution stays pure in handlers,
  persistence remains in `DBRomsHandler`, byte storage stays in owned-resource
  helpers, and existing Media API/UI transport is reused.
- Cross-plan data contract: empty or failed Steam patches never become empty
  inventories; a complete successful inventory is the only tombstone input.
- Scope: 2 tasks in 21-01 through 21-03, plus the necessary final blocking UAT
  checkpoint in 21-04. No plan exceeds the context budget.
- Validation derivation: truths, artifacts, key links, focused suite,
  migration checks, and manual UAT evidence trace back to the phase goal.

Plans are ready for Phase 21 execution. The MEDIUM advisory can be folded into
the plan opportunistically without reopening the revision gate.
