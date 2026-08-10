# Phase 3 Source Coverage Audit

| Source   | ID            | Feature or constraint                                                                                                | Plan                              | Status  |
| -------- | ------------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ------- |
| GOAL     | Phase 3       | Authorized administrators safely inspect roots and manage one audited, non-overlapping relative mapping per platform | 03-01 through 03-06               | COVERED |
| REQ      | MAP-01        | Assign a platform to a contained existing relative directory                                                         | 03-03, 03-05                      | COVERED |
| REQ      | MAP-02        | At most one active mapping per platform with inactive history                                                        | 03-01, 03-03, 03-05               | COVERED |
| REQ      | MAP-03        | Mapping operations never mutate source storage                                                                       | 03-02, 03-03, 03-05, 03-06        | COVERED |
| REQ      | MAP-04        | Distinct sibling directories under one root are allowed                                                              | 03-03, 03-05                      | COVERED |
| REQ      | MAP-05        | Equal and ancestor/descendant overlaps are rejected                                                                  | 03-03, 03-05                      | COVERED |
| REQ      | MAP-06        | Missing mapping is explicit with no fallback                                                                         | 03-03, 03-05, 03-06               | COVERED |
| REQ      | API-01        | Admin root listing with live safe status                                                                             | 03-02, 03-04                      | COVERED |
| REQ      | API-02        | Contained bounded relative directory browsing                                                                        | 03-02, 03-04                      | COVERED |
| REQ      | API-03        | Typed read/create/change/test/preview/remove endpoints                                                               | 03-05, 03-06                      | COVERED |
| REQ      | API-04        | Anonymous enumeration and non-admin mutation are denied                                                              | 03-04, 03-05, 03-06               | COVERED |
| REQ      | AUD-01        | Atomic actor/time/platform/action/old/new audit                                                                      | 03-01, 03-03, 03-05               | COVERED |
| REQ      | AUD-02        | Audit and responses reveal no host or unrelated paths                                                                | 03-01, 03-03, 03-04, 03-05, 03-06 | COVERED |
| REQ      | TEST-02       | Full API, auth, traversal, lifecycle, test, and preview matrix                                                       | 03-02 through 03-06               | COVERED |
| CONTEXT  | D-01          | Live non-persisting root health on retrieval                                                                         | 03-02, 03-04                      | COVERED |
| CONTEXT  | D-02          | Stable bounded cursor directory pages                                                                                | 03-02, 03-04                      | COVERED |
| CONTEXT  | D-03          | Minimal directory entry allowlist                                                                                    | 03-02, 03-04                      | COVERED |
| CONTEXT  | D-04          | Stable bounded path-safe root/browser errors                                                                         | 03-01, 03-02, 03-04               | COVERED |
| CONTEXT  | D-05          | Test and persistence are separate                                                                                    | 03-03, 03-05                      | COVERED |
| CONTEXT  | D-06          | Mapping changes preserve catalog and require later explicit rescan                                                   | 03-03, 03-05                      | COVERED |
| CONTEXT  | D-07          | Removal changes mapping only and audits it                                                                           | 03-03, 03-05                      | COVERED |
| CONTEXT  | D-08          | Missing mapping is typed with no legacy/empty fallback                                                               | 03-03, 03-05, 03-06               | COVERED |
| CONTEXT  | D-09          | Explicit optimistic version precondition                                                                             | 03-01, 03-03, 03-05               | COVERED |
| CONTEXT  | D-10          | Overlap errors reveal identifiers, not paths                                                                         | 03-01, 03-03, 03-05               | COVERED |
| CONTEXT  | D-11          | Active mappings alone reserve identities/paths                                                                       | 03-01, 03-03, 03-05               | COVERED |
| CONTEXT  | D-12          | Stable 409 with current version and no server merge/retry                                                            | 03-01, 03-03, 03-05               | COVERED |
| CONTEXT  | D-13          | Audit mutations only, not reads/tests/previews                                                                       | 03-03, 03-05, 03-06               | COVERED |
| CONTEXT  | D-14          | Audit old/new field allowlist                                                                                        | 03-01, 03-03, 03-05               | COVERED |
| CONTEXT  | D-15          | Immutable actor ID and bounded display snapshot                                                                      | 03-01, 03-03, 03-05               | COVERED |
| CONTEXT  | D-16          | Admin-only newest-first filtered cursor audit history                                                                | 03-03, 03-05                      | COVERED |
| RESEARCH | Schema        | Migration 0109, active/version backfill, portable indexes, reversible three-dialect cycle                            | 03-01, 03-06                      | COVERED |
| RESEARCH | Concurrency   | Deterministic locks, final active-only validation, real MariaDB/PostgreSQL concurrency evidence                      | 03-03, 03-06                      | COVERED |
| RESEARCH | Cursor safety | Query-bound filesystem and audit cursors with strict bounded decoding                                                | 03-02, 03-03, 03-04, 03-05        | COVERED |
| RESEARCH | OpenAPI       | Explicit Pydantic allowlists, generated types, frontend typecheck                                                    | 03-04 through 03-06               | COVERED |
| RESEARCH | Preview       | Bounded non-mutating summary without scanner/catalog cutover                                                         | 03-06                             | COVERED |
| RESEARCH | Scope         | Backend/admin contracts only, no UI, scanner cutover, Team4s edits, or production NAS actions                        | All plans                         | COVERED |

No deferred item is planned. No source item is missing.
