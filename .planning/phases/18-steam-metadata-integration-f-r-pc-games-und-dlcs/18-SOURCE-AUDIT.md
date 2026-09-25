# Phase 18 Source Audit

| Source       | Item                                                                                                                 | Disposition | Plan                |
| ------------ | -------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------- |
| GOAL         | Separate official Steam Storefront metadata for PC games and DLCs, without replacing IGDB or SteamGridDB             | COVERED     | 18-01 through 18-05 |
| REQ          | STEAM-01 provider identity and configuration                                                                         | COVERED     | 18-01, 18-03        |
| REQ          | STEAM-02 persistent, localized main-game enrichment                                                                  | COVERED     | 18-01, 18-02, 18-04 |
| REQ          | STEAM-03 IGDB-first safe DLC enrichment                                                                              | COVERED     | 18-05               |
| REQ          | STEAM-04 UI/API presentation and priority integration                                                                | COVERED     | 18-02, 18-03        |
| REQ          | STEAM-05 non-regression, failure isolation, and verification                                                         | COVERED     | 18-01 through 18-05 |
| RESEARCH     | Upstream-close no-key transport, typed details, limiter, 429 and malformed-payload handling                          | COVERED     | 18-01               |
| RESEARCH     | Current malformed migration graph has two `0119` revisions, validated in container context on MariaDB and PostgreSQL | COVERED     | 18-02, VALIDATION   |
| RESEARCH     | Stored-ID refresh and same-App-ID locale fallback                                                                    | COVERED     | 18-01, 18-04        |
| RESEARCH     | One normalized manual/automatic field-merge policy and artwork handoff, using explicit manual-field provenance       | COVERED     | 18-04               |
| RESEARCH     | `fullgame.appid` numeric/numeric-string extraction, IGDB identity before typed, parent-aware DLC validation          | COVERED     | 18-05               |
| RESEARCH     | Generated OpenAPI TypeScript artifacts are a backend-owned contract                                                  | COVERED     | 18-02               |
| CONTEXT D-01 | Steam is independent; `sgdb` remains SteamGridDB artwork-only                                                        | COVERED     | 18-01, 18-03        |
| CONTEXT D-02 | `de/CH` then `en/US`, same App ID only; no automatic search outside win/linux/mac                                    | COVERED     | 18-01, 18-04        |
| CONTEXT D-03 | nullable IDs/JSON data, no component App-ID global uniqueness                                                        | COVERED     | 18-02               |
| CONTEXT D-04 | manual fields and selected artwork prevail, while IGDB relationships remain authoritative                            | COVERED     | 18-04               |
| CONTEXT D-05 | only unambiguous IGDB-resolved DLCs can be Steam-enriched, with type/parent/confidence gates                         | COVERED     | 18-05               |
| CONTEXT D-06 | logging and failure isolation without payloads/secrets                                                               | COVERED     | 18-01, 18-04, 18-05 |

The separate `18-VALIDATION.md` is the executable final evidence matrix. It
contains the mandatory container-context migration commands and v2 manual UAT
gate, rather than treating either as an environment blocker.

## Gap-Closure Coverage, 2026-09-25

| Source       | Actionable closure item                                                                                 | Disposition | Plan         |
| ------------ | ------------------------------------------------------------------------------------------------------- | ----------- | ------------ |
| GOAL         | A failed IGDB DLC hydration cannot authorize Steam matching or persistence                              | COVERED     | 18-10        |
| GOAL         | Phase completion has reproducible canonical-container backend and MariaDB/PostgreSQL migration evidence | COVERED     | 18-11        |
| GOAL         | The declared generated detailed-ROM contract is an existing generator-owned artifact                    | COVERED     | 18-12        |
| REQ          | STEAM-02 persistence and dialect evidence                                                               | COVERED     | 18-11, 18-12 |
| REQ          | STEAM-03 hydrated IGDB identity before Steam DLC lookup                                                 | COVERED     | 18-10        |
| REQ          | STEAM-04 generated API contract linkage                                                                 | COVERED     | 18-12        |
| REQ          | STEAM-05 non-fatal failure isolation and focused backend evidence                                       | COVERED     | 18-10, 18-11 |
| RESEARCH     | Portable migration verification and PostgreSQL enum lifecycle                                           | COVERED     | 18-11        |
| RESEARCH     | Backend-owned generated OpenAPI contract                                                                | COVERED     | 18-12        |
| CONTEXT D-03 | Nullable provenance remains portable and has no component App-ID uniqueness                             | COVERED     | 18-11        |
| CONTEXT D-05 | Only hydrated unambiguous IGDB DLC identity can trigger Steam enrichment                                | COVERED     | 18-10        |
| CONTEXT D-06 | Failures are isolated without payload/secret disclosure and closure evidence has final statuses         | COVERED     | 18-10, 18-11 |

## Final Closure Coverage, 2026-09-25

| Source   | ID       | Actionable closure item                                                                                                | Plan                | Status  | Notes                                                                                         |
| -------- | -------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------- | ------- | --------------------------------------------------------------------------------------------- |
| GOAL     | —        | Valid manual parent Steam selection and existing-component provenance work under their guarded persistence boundaries. | 18-13               | COVERED | Resolves the two actual 18-11 focused-suite failures only after test-led cause investigation. |
| GOAL     | —        | Phase closure has complete real command evidence.                                                                      | 18-15               | COVERED | Requires exact 186-pass MariaDB runner output and successful PostgreSQL full cycle.           |
| REQ      | STEAM-01 | Independent provider evidence remains retained in final validation.                                                    | 18-15               | COVERED | Existing provider/UAT evidence is preserved and distinguished from new runs.                  |
| REQ      | STEAM-02 | Guarded parent persistence and portable Steam migration proof.                                                         | 18-13, 18-14, 18-15 | COVERED | Covers current-version write, historical view compatibility, and dialect evidence.            |
| REQ      | STEAM-03 | Existing safe DLC outcome remains verified in final evidence.                                                          | 18-15               | COVERED | No deferred DLC, ownership, or matching work is introduced.                                   |
| REQ      | STEAM-04 | Existing API/generated contract evidence remains traceable.                                                            | 18-15               | COVERED | Plan 18-12 remains the contract-link correction.                                              |
| REQ      | STEAM-05 | Product regressions, failure isolation, and full evidence pass.                                                        | 18-13, 18-14, 18-15 | COVERED | No assertion is relaxed, skipped, or converted to a mock-only test.                           |
| RESEARCH | —        | PostgreSQL compatibility with historical `roms_metadata.player_count` view type.                                       | 18-14               | COVERED | Diagnose first, then follow the established 0098 type-stability convention only if confirmed. |
| RESEARCH | —        | Canonical-network MariaDB and disposable PostgreSQL verification.                                                      | 18-15               | COVERED | Reuses existing isolated runners without host database access.                                |
| CONTEXT  | D-03     | Nullable observational Steam component provenance has no global App-ID uniqueness and is portable.                     | 18-13, 18-14        | COVERED | Retains existing-component-only persistence and cross-dialect migration proof.                |
| CONTEXT  | D-04     | Manual fields and IGDB structured relationships remain authoritative.                                                  | 18-13               | COVERED | Endpoint and component tests retain manual/IGDB protections.                                  |
| CONTEXT  | D-05     | Safe DLC constraints remain intact during closure.                                                                     | 18-15               | COVERED | Final suite includes the previously repaired hydration gate coverage.                         |
| CONTEXT  | D-06     | Failures remain bounded, secret-free, and truthfully evidenced.                                                        | 18-13, 18-14, 18-15 | COVERED | Root cause is established before code changes and runners preserve first failure.             |

Deferred work such as translation, login, library synchronization, downloads, installation, achievements, cloud features, and a generic matching framework is intentionally absent from every plan.
