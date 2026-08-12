# Phase 6 Source Audit

All GOAL, REQ, RESEARCH, and CONTEXT inputs are covered. Deferred ideas: none. Phase 7 UI, deployment, source mutations, v1 changes, and production NAS activation are excluded by phase boundary, not gaps.

| SOURCE   | ID     | Feature or constraint                                                                   | Plan        | Status  | Notes                                           |
| -------- | ------ | --------------------------------------------------------------------------------------- | ----------- | ------- | ----------------------------------------------- |
| GOAL     | -      | Operators remove catalog state and bridge layouts without restructuring/deleting source | 01-09       | COVERED | Explicit task action and automated verification |
| REQ      | CAT-01 | Explicit catalog-only contract                                                          | 02          | COVERED | Explicit task action and automated verification |
| REQ      | CAT-02 | Owned-only removal with source preservation                                             | 02          | COVERED | Explicit task action and automated verification |
| REQ      | CAT-03 | Mapping removal retains catalog                                                         | 03          | COVERED | Explicit task action and automated verification |
| REQ      | CAT-04 | External mutations absent and blocked                                                   | 02,03,09    | COVERED | Explicit task action and automated verification |
| REQ      | MIG-01 | Represent exact legacy layouts without content mutation                                 | 04-06       | COVERED | Explicit task action and automated verification |
| REQ      | MIG-02 | Portable reversible database migration                                                  | 01,08,09    | COVERED | Explicit task action and automated verification |
| REQ      | MIG-03 | Unsafe layouts require manual mapping                                                   | 04-06       | COVERED | Explicit task action and automated verification |
| REQ      | MIG-04 | Mappings survive restart/deployment lifecycle                                           | 01,06-09    | COVERED | Explicit task action and automated verification |
| REQ      | MIG-05 | Expiring observable status with zero fallback                                           | 04,05,08,09 | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-01   | mapping removal retains visible unreachable catalog and user value                      | 03          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-02   | old work aborts at safe boundaries                                                      | 03          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-03   | unambiguous later reconnection                                                          | 03          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-04   | normal confirmation facts, no typed name                                                | 02,03       | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-05   | configuration/audit only and source immutable                                           | 03          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-06   | administrator-started detection only                                                    | 04          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-07   | exact canonical paths only                                                              | 04          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-08   | aliases ignored                                                                         | 04          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-09   | bounded redacted summaries                                                              | 04          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-10   | unusable candidates visible/unselectable                                                | 04          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-11   | migration changes owned DB/config only                                                  | 06          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-12   | typed per-platform impact preview                                                       | 05          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-13   | independent per-platform confirmation                                                   | 06          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-14   | atomic mapping/reconnection/audit/rollback metadata                                     | 01,06       | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-15   | rollback only before durable first use                                                  | 01,08       | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-16   | rollback restores owned state only                                                      | 01,08       | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-17   | active mapping blocks migration                                                         | 05,06       | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-18   | all equal/ancestor/descendant overlaps block                                            | 05,06       | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-19   | only unambiguous matches reconnect                                                      | 03,06       | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-20   | failure fully rolls back and retry is safe                                              | 06          | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-21   | manual mapping outcome and no fallback                                                  | 04,05,08,09 | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-22   | catalog removal retains saves/states/history and identity                               | 01,02       | COVERED | Explicit task action and automated verification |
| CONTEXT  | D-23   | only two literal historical grammars                                                    | 04          | COVERED | Explicit task action and automated verification |
| RESEARCH | R-01   | 10,000-entry and 5-second budgets with lower-bound results                              | 04,05       | COVERED | Explicit task action and automated verification |
| RESEARCH | R-02   | ordered cross-dialect row locks and optimistic versions                                 | 01,03,06,07 | COVERED | Explicit task action and automated verification |
| RESEARCH | R-03   | durable cleanup intent for non-ACID owned asset deletion                                | 01,02       | COVERED | Explicit task action and automated verification |
| RESEARCH | R-04   | exact logical identity then unique complete-hash reconnection                           | 02,03,06    | COVERED | Explicit task action and automated verification |
| RESEARCH | R-05   | first-use CAS before source open and rollback race                                      | 01,07       | COVERED | Explicit task action and automated verification |
| RESEARCH | R-06   | three-dialect Alembic and concurrency verification                                      | 01,08,09    | COVERED | Explicit task action and automated verification |
| RESEARCH | R-07   | compatibility status only, no legacy source fallback                                    | 04,05,08,09 | COVERED | Explicit task action and automated verification |
| RESEARCH | R-08   | generated types only after backend contract changes                                     | 09          | COVERED | Explicit task action and automated verification |
| RESEARCH | R-09   | immutable source manifests and closed mutation inventory                                | 02-09       | COVERED | Explicit task action and automated verification |

## Coverage verdict

No source item is missing. Plans 01 through 09 collectively cover CAT-01 through CAT-04, MIG-01 through MIG-05, and D-01 through D-23 without scope reduction.

## Checker Revision 1 Traceability

- D-04 typed mapping-removal consequences and confirmation: Plan 03.
- D-15 typed rollback eligibility, status, and rollback API: Plan 08; generated contract closure: Plan 09.
- Real three-dialect executable gates: Plans 01, 08, and 09.
- Controlled OpenAPI generation and frontend typecheck: Plan 09.
- Final regression task starts green: Plan 09.

## Checker Revision 2 Traceability

- Plan 04 depends on Plans 01 and 03, serializing its shared storage endpoint/schema files.
- Former Plan 07 is split into Plan 07 productive first-use CAS and Plan 08 rollback API/persistence; final closure is Plan 09.
- Every plan now names concrete truths, real wiring, and mapped analog source files from 06-PATTERNS.md.

## Checker Revision 3 Traceability

- Plan 07 contains only productive first-use CAS consumer wiring.
- Plan 08 exclusively owns typed rollback, restart persistence, and dialect verification.
- Plan 09 uses RED harness tests before GREEN harness implementation and final closure.
- Phase status is planned with 0 of 9 plans complete.
