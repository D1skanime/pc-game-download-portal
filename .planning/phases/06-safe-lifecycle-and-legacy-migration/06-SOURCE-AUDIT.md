# Phase 6 Source Audit

This table is the complete current Phase 6 coverage set bound to Plan 47 acceptance run `0525ee9a9a51ae4fad34e5791398cd40` and digest `f4b45a758dd5950caaee1f479220cb617aab1a053d7e5fa052ec0c72a47d94ff`.

| Source       | ID      | Required item                                                                    | Plan evidence     | Status  |
| ------------ | ------- | -------------------------------------------------------------------------------- | ----------------- | ------- |
| GOAL         | GOAL-06 | Remove catalog state and bridge layouts without restructuring or deleting source | 33-47             | COVERED |
| REQ          | CAT-01  | Explicit catalog-only and manual-ownership language                              | 38-41,45,47       | COVERED |
| REQ          | CAT-02  | Owned-only integrity with source preservation                                    | 33-34,38-45,47    | COVERED |
| REQ          | CAT-03  | Mapping removal retains catalog and source                                       | 47                | COVERED |
| REQ          | CAT-04  | External mutations blocked and inventory exhaustive                              | 34,36,47          | COVERED |
| REQ          | MIG-01  | Exact legacy layouts represented without source change                           | 37,44,47          | COVERED |
| REQ          | MIG-02  | Portable practical reversibility                                                 | 35,42,44,46-47    | COVERED |
| REQ          | MIG-03  | Unsafe or ambiguous layouts require manual mapping                               | 37,44,47          | COVERED |
| REQ          | MIG-04  | Persistence across restart and deployment lifecycle                              | 35,42,44,46-47    | COVERED |
| REQ          | MIG-05  | Explicit bounded compatibility with no fallback                                  | 37,42,44,46-47    | COVERED |
| VERIFICATION | MH-01   | Game removal preserves source                                                    | 47                | COVERED |
| VERIFICATION | MH-02   | Mapping and catalog removal preserve source and deny mutation                    | 36,47             | COVERED |
| VERIFICATION | MH-03   | Supported layouts map without restructuring                                      | 37,44,47          | COVERED |
| VERIFICATION | MH-04   | Ambiguous layouts remain manual and time-bounded                                 | 37,44,47          | COVERED |
| VERIFICATION | MH-05   | Portable rollback and nonproductive HEAD behavior                                | 35,46-47          | COVERED |
| VERIFICATION | MH-06   | Detached user value reconnects                                                   | 47                | COVERED |
| VERIFICATION | MH-07   | Catalog removal accepts IDs only                                                 | 47                | COVERED |
| VERIFICATION | MH-08   | Cleanup targets owned assets only                                                | 33-34,43,47       | COVERED |
| VERIFICATION | MH-09   | Mapping consequences remain bounded                                              | 47                | COVERED |
| VERIFICATION | MH-10   | Mapping removal is atomic                                                        | 47                | COVERED |
| VERIFICATION | MH-11   | Later scan reconnection is retry-safe                                            | 47                | COVERED |
| VERIFICATION | MH-12   | Detection is explicitly authorized                                               | 37,47             | COVERED |
| VERIFICATION | MH-13   | Two grammars stay within budgets                                                 | 37,47             | COVERED |
| VERIFICATION | MH-14   | Impact preview is truthful and source-bound                                      | 37,42,44,47       | COVERED |
| VERIFICATION | MH-15   | Confirmation binds source and catalog                                            | 44,47             | COVERED |
| VERIFICATION | MH-16   | Mapping conflicts block migration                                                | 44,47             | COVERED |
| VERIFICATION | MH-17   | Migration change set is atomic                                                   | 44,46-47          | COVERED |
| VERIFICATION | MH-18   | Injected failure leaves no partial database state                                | 44,47             | COVERED |
| VERIFICATION | MH-19   | Absent or ambiguous catalog entries stay unreachable                             | 37,42,44,46-47    | COVERED |
| VERIFICATION | MH-20   | Only productive consumers mark first use                                         | 35,47             | COVERED |
| VERIFICATION | MH-21   | First-use CAS revalidates revision                                               | 35,47             | COVERED |
| VERIFICATION | MH-22   | Concurrent productive first use is singular                                      | 47                | COVERED |
| VERIFICATION | MH-23   | Rollback binds migration, platform, and version                                  | 35,46-47          | COVERED |
| VERIFICATION | MH-24   | Rollback restores exact unchanged entities                                       | 44,46-47          | COVERED |
| VERIFICATION | MH-25   | Used, stale, and replayed rollback fails safely                                  | 35,44,47          | COVERED |
| VERIFICATION | MH-26   | Source manifests remain unchanged                                                | 33-47             | COVERED |
| VERIFICATION | MH-27   | Server and UI inventory are exhaustive                                           | 36,47             | COVERED |
| VERIFICATION | MH-28   | OpenAPI and generated contracts are coherent                                     | 43,47             | COVERED |
| VERIFICATION | MH-29   | Primary manual replacement is failure-atomic                                     | 33,38-41,43,45,47 | COVERED |
| VERIFICATION | MH-30   | Screenshot visibility precedes effects                                           | 34,47             | COVERED |
| VERIFICATION | MH-31   | OwnedCreate is complete and durable or has no final                              | 33,47             | COVERED |
| REVIEW       | CR-01   | Migration selection is source-observed                                           | 37,42,44,46-47    | COVERED |
| REVIEW       | CR-02   | Manual replacement handles backend and frontend races                            | 33,38-41,43,45,47 | COVERED |
| REVIEW       | CR-03   | Screenshot visibility is enforced                                                | 34,47             | COVERED |
| REVIEW       | CR-04   | OwnedCreate is crash-durable                                                     | 33,47             | COVERED |
| REVIEW       | WR-01   | HEAD does not consume rollback eligibility                                       | 35,47             | COVERED |
| REVIEW       | WR-02   | Inventory covers transport mutation forms                                        | 36,47             | COVERED |
| REVIEW       | WR-03   | Content-Disposition is safe                                                      | 35,47             | COVERED |
| RESEARCH     | R-01    | Observation is bounded with truthful lower bounds                                | 37,44,47          | COVERED |
| RESEARCH     | R-02    | Locks and optimistic versions are portable and ordered                           | 43-44,46-47       | COVERED |
| RESEARCH     | R-03    | Owned cleanup is explicit and retry-safe                                         | 33,43,47          | COVERED |
| RESEARCH     | R-04    | Reconnection uses exact logical identity                                         | 37,42,44,47       | COVERED |
| RESEARCH     | R-05    | Productive first-use CAS precedes source open                                    | 35,47             | COVERED |
| RESEARCH     | R-06    | MariaDB, MySQL, and PostgreSQL lifecycle authority                               | 42,46-47          | COVERED |
| RESEARCH     | R-07    | Compatibility is status-only with no legacy fallback                             | 37,42,44,47       | COVERED |
| RESEARCH     | R-08    | Generated contracts follow backend API changes                                   | 43,47             | COVERED |
| RESEARCH     | R-09    | Manifests are complete and mutation inventory is closed                          | 34-36,47          | COVERED |
| UI-SPEC      | UI-01   | One file uses one POST with no queue                                             | 40,45,47          | COVERED |
| UI-SPEC      | UI-02   | Viewer and path stay stable until success                                        | 41,43,45,47       | COVERED |
| UI-SPEC      | UI-03   | Pending state disables every mutation entry                                      | 41,45,47          | COVERED |
| UI-SPEC      | UI-04   | Refresh precedes success with truthful terminal states                           | 38-40,45,47       | COVERED |
| UI-SPEC      | UI-05   | Permissions, aria, focus, and universal input work                               | 41,45,47          | COVERED |
| UI-SPEC      | UI-06   | Existing responsive layouts, themes, and tokens only                             | 45,47             | COVERED |
| UI-SPEC      | UI-07   | Inventory remains build-time only                                                | 36,47             | COVERED |
| UI-SPEC      | UI-08   | No UI is added for backend-only or Phase 7 work                                  | 33-37,42-44,46-47 | COVERED |
| CONTEXT      | D-01    | Mapping removal retains visible catalog and user value                           | 47                | COVERED |
| CONTEXT      | D-02    | Old work aborts at safe boundaries                                               | 35,47             | COVERED |
| CONTEXT      | D-03    | Later reconnection is unambiguous                                                | 37,42,44,47       | COVERED |
| CONTEXT      | D-04    | Mapping-removal confirmation is clear                                            | 47                | COVERED |
| CONTEXT      | D-05    | Only owned config and audit change; source stays immutable                       | 33-35,43-44,47    | COVERED |
| CONTEXT      | D-06    | Detection is administrator-started                                               | 37,44,47          | COVERED |
| CONTEXT      | D-07    | Only exact canonical paths qualify                                               | 37,44,47          | COVERED |
| CONTEXT      | D-08    | Aliases are ignored                                                              | 37,44,47          | COVERED |
| CONTEXT      | D-09    | Summaries are bounded and redacted                                               | 37,42,44,47       | COVERED |
| CONTEXT      | D-10    | Unusable candidates remain visible and unselectable                              | 37,42,47          | COVERED |
| CONTEXT      | D-11    | Migration changes owned database and config only                                 | 37,42,44,46-47    | COVERED |
| CONTEXT      | D-12    | Per-platform impact preview is truthful and typed                                | 44,47             | COVERED |
| CONTEXT      | D-13    | Per-platform confirmation is independent                                         | 44,47             | COVERED |
| CONTEXT      | D-14    | Mapping, reconnection, audit, and rollback are atomic                            | 44,46-47          | COVERED |
| CONTEXT      | D-15    | Rollback closes only after productive first use                                  | 35,47             | COVERED |
| CONTEXT      | D-16    | Rollback restores owned state only                                               | 35,44,46-47       | COVERED |
| CONTEXT      | D-17    | Active mapping blocks migration                                                  | 44,47             | COVERED |
| CONTEXT      | D-18    | Equal, ancestor, and descendant overlap blocks                                   | 44,47             | COVERED |
| CONTEXT      | D-19    | Absent or ambiguous entries remain unreachable                                   | 37,42,44,46-47    | COVERED |
| CONTEXT      | D-20    | Failure rolls back and retry remains safe                                        | 33,43-44,46-47    | COVERED |
| CONTEXT      | D-21    | Manual mapping never guesses or falls back                                       | 37,42,44,47       | COVERED |
| CONTEXT      | D-22    | Catalog removal retains user value and source                                    | 33-34,43,47       | COVERED |
| CONTEXT      | D-23    | Only two literal historical grammars qualify                                     | 37,44,47          | COVERED |

## Boundary

Phase 7 administration UI, deployment, production NAS activation, and source mutation are excluded by the locked phase boundary. Frozen v1 manual consumers and shared plural/emitter contracts remain assigned to Phase 8. Atime remains assigned to Phase 9. These exclusions are outside the current table and do not reduce Phase 6 coverage.
