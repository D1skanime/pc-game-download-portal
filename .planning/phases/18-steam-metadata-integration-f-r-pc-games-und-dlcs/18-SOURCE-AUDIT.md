# Phase 18 Source Audit

| Source       | Item                                                                                                     | Disposition | Plan                |
| ------------ | -------------------------------------------------------------------------------------------------------- | ----------- | ------------------- |
| GOAL         | Separate official Steam Storefront metadata for PC games and DLCs, without replacing IGDB or SteamGridDB | COVERED     | 18-01 through 18-05 |
| REQ          | STEAM-01 provider identity and configuration                                                             | COVERED     | 18-01, 18-03        |
| REQ          | STEAM-02 persistent, localized main-game enrichment                                                      | COVERED     | 18-01, 18-02, 18-04 |
| REQ          | STEAM-03 IGDB-first safe DLC enrichment                                                                  | COVERED     | 18-05               |
| REQ          | STEAM-04 UI/API presentation and priority integration                                                    | COVERED     | 18-02, 18-03        |
| REQ          | STEAM-05 non-regression, failure isolation, and verification                                             | COVERED     | 18-01 through 18-05 |
| RESEARCH     | Upstream-close no-key transport, typed details, limiter, 429 and malformed-payload handling              | COVERED     | 18-01               |
| RESEARCH     | Current malformed migration graph has two `0119` revisions                                               | COVERED     | 18-02               |
| RESEARCH     | Stored-ID refresh and same-App-ID locale fallback                                                        | COVERED     | 18-01, 18-04        |
| RESEARCH     | One normalized manual/automatic field-merge policy and artwork handoff                                   | COVERED     | 18-04               |
| RESEARCH     | IGDB identity before typed, parent-aware DLC validation                                                  | COVERED     | 18-05               |
| CONTEXT D-01 | Steam is independent; `sgdb` remains SteamGridDB artwork-only                                            | COVERED     | 18-01, 18-03        |
| CONTEXT D-02 | `de/CH` then `en/US`, same App ID only; no automatic search outside win/linux/mac                        | COVERED     | 18-01, 18-04        |
| CONTEXT D-03 | nullable IDs/JSON data, no component App-ID global uniqueness                                            | COVERED     | 18-02               |
| CONTEXT D-04 | manual fields and selected artwork prevail, while IGDB relationships remain authoritative                | COVERED     | 18-04               |
| CONTEXT D-05 | only unambiguous IGDB-resolved DLCs can be Steam-enriched, with type/parent/confidence gates             | COVERED     | 18-05               |
| CONTEXT D-06 | logging and failure isolation without payloads/secrets                                                   | COVERED     | 18-01, 18-04, 18-05 |

Deferred work such as translation, login, library synchronization, downloads, installation, achievements, cloud features, and a generic matching framework is intentionally absent from every plan.
