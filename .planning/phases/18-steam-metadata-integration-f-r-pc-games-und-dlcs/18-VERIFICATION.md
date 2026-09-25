---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
verified: 2026-09-25T15:33:09Z
status: passed
score: 25/25 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 24/25
  gaps_closed:
    - "Phase closure has complete command-backed backend, dialect, generated-contract, frontend, lint, and approved v2 UAT evidence."
  gaps_remaining: []
  regressions: []
---

# Phase 18: Steam Metadata Integration fuer PC Games und DLCs Verification Report

**Phase Goal:** Add the official Steam Storefront provider to eligible PC games and safely identified DLC components, with German-first text while preserving IGDB relationships, manual data, and SteamGridDB's artwork-only role.
**Verified:** 2026-09-25T15:33:09Z
**Status:** passed
**Re-verification:** Yes, after gap closure

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                   | Status   | Evidence                                                                                                                           |
| --- | ----------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 1   | No-key Steam provider can be enabled independently.                                                                     | VERIFIED | Separate config, watcher, priority validation, and heartbeat paths use `steam`.                                                    |
| 2   | German-first reads use only the resolved App ID for English fallback.                                                   | VERIFIED | `steam_handler.py` retrieves localized details with the same `steam_id`; isolated suite passes.                                    |
| 3   | Storefront faults are non-fatal.                                                                                        | VERIFIED | `SteamService` returns typed empty results for timeout, malformed, regional, and retry-exhausted responses.                        |
| 4   | Automatic name search is platform-gated, while stored IDs refresh on excluded PC platforms.                             | VERIFIED | Scan logic limits searching to supported PC slugs while retaining explicit-ID resolution.                                          |
| 5   | ROMs and components retain nullable Steam identity and provenance.                                                      | VERIFIED | Models, revision `0126`, schemas, and generated contracts expose nullable Steam fields.                                            |
| 6   | Migration graph is one-headed and Steam persistence is reversible.                                                      | VERIFIED | Current MariaDB head, upgrade, downgrade, re-upgrade, and disposable PostgreSQL cycle all passed.                                  |
| 7   | Steam and SteamGridDB remain separate in priority and heartbeat paths.                                                  | VERIFIED | Separate slugs, handlers, health dispatches, and v2 records remain wired.                                                          |
| 8   | V2 settings and provider links show Steam separately.                                                                   | VERIFIED | `providers.ts` links `steam_id` to Storefront; settings has distinct Steam and SteamGridDB entries; approved UAT retained.         |
| 9   | Registry omissions have focused regression coverage.                                                                    | VERIFIED | Current isolated Compose evidence is `189 passed, 7 warnings`, including registry and heartbeat coverage.                          |
| 10  | Eligible PC main games get field-safe Steam metadata while IGDB relations remain intact.                                | VERIFIED | Candidate selection and scan both use guarded `normalize_steam` updates.                                                           |
| 11  | Automatic and manual selection share the non-empty, manual-safe merge policy.                                           | VERIFIED | Both paths call `normalize_steam`; suite covers field and manual protections.                                                      |
| 12  | Steam artwork is candidate-only and cannot replace selected artwork silently.                                           | VERIFIED | Steam normalizer does not write selected media; persistence remains explicit.                                                      |
| 13  | IGDB remains the required authority for automatic DLC discovery.                                                        | VERIFIED | Socket scan obtains a related IGDB candidate before Steam validation.                                                              |
| 14  | Only a hydrated, unique IGDB DLC identity can permit Steam DLC enrichment.                                              | VERIFIED | Hydration errors, invalid details, ID mismatch, or empty title return `None`; scan returns before Steam.                           |
| 15  | Unsafe DLC type, ambiguity, malformed parent, and parent mismatch preserve state.                                       | VERIFIED | Validated matching rejects each before persistence; suite passes.                                                                  |
| 16  | Safe DLC receives same-App-ID locale fallback.                                                                          | VERIFIED | Validated DLC uses the Steam handler exact-ID localized-detail path.                                                               |
| 17  | Existing API surfaces expose Steam ID and provenance.                                                                   | VERIFIED | Backend response schemas and both generated models include `steam_id` and `steam_metadata`.                                        |
| 18  | Generated contracts connect to the declared OpenAPI artifact.                                                           | VERIFIED | The plan and validation matrix name existing `DetailedRomSchema.ts`, which contains both fields.                                   |
| 19  | Stored IDs refresh by ID and reject mismatched responses.                                                               | VERIFIED | Stored-ID path resolves first and checks response identity.                                                                        |
| 20  | Classic ROMs never enter Steam lookup.                                                                                  | VERIFIED | Steam scan resolution is restricted to explicit PC platforms.                                                                      |
| 21  | Steam failure leaves other provider output usable.                                                                      | VERIFIED | Steam errors yield `{}` and provider collection isolates failures.                                                                 |
| 22  | Upstream versus fork-only behavior is documented.                                                                       | VERIFIED | The maintained Steam integration design specification records the boundary.                                                        |
| 23  | Closure has complete command-backed backend, dialect, generated-contract, frontend, lint, and approved v2 UAT evidence. | VERIFIED | Current MariaDB suite, both dialect cycles, static contracts, frontend checks, scoped Trunk, and approved UAT have evidence below. |
| 24  | Existing components retain Steam provenance without duplication.                                                        | VERIFIED | Existing-component persistence is provider-scoped; shared nullable App IDs are covered.                                            |
| 25  | Steam component persistence cannot erase IGDB structured data or become display authority.                              | VERIFIED | Allowlisted Steam persistence preserves IGDB fields and manual state.                                                              |

**Score:** 25/25 truths verified

### Required Artifacts

| Artifact                                                 | Expected                                          | Status   | Details                                                                                       |
| -------------------------------------------------------- | ------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------- |
| `backend/adapters/services/steam.py`                     | Bounded Storefront transport                      | VERIFIED | Real HTTP response normalization, bounded retry, and typed degradation.                       |
| `backend/handler/metadata/steam_handler.py`              | Localized exact-ID normalization                  | VERIFIED | Consumes service results and same-ID fallback.                                                |
| `backend/handler/metadata/steam_merge.py`                | Manual-safe common merge                          | VERIFIED | Non-empty field updates, field provenance, no selected-media writes.                          |
| `backend/handler/metadata/pc_match_handler.py`           | Fail-closed DLC identity and validation           | VERIFIED | Hydration and Steam product/parent checks short-circuit unsafe paths.                         |
| `backend/endpoints/sockets/scan.py`                      | Hydration gate and existing-component application | VERIFIED | `candidate is None` returns before Steam; only existing component receives updates.           |
| `backend/alembic/versions/0126_add_steam_metadata.py`    | Portable reversible persistence                   | VERIFIED | Model columns match; MariaDB and PostgreSQL cycles pass.                                      |
| `backend/tools/verify_phase18_backend_tests.sh`          | Isolated MariaDB evidence runner                  | VERIFIED | Uses guarded generated schema, Compose DB host, EXIT cleanup, and now passes scoped Trunk.    |
| `backend/tools/verify_phase18_postgres_migration.sh`     | Disposable PostgreSQL migration verifier          | VERIFIED | Fresh container reached head, downgraded, re-upgraded, and cleaned up.                        |
| `frontend/src/__generated__/models/DetailedRomSchema.ts` | Detailed-ROM generated contract                   | VERIFIED | Present, substantive, and includes both Steam fields.                                         |
| `frontend/src/v2/views/Settings/MetadataSources.vue`     | Separate provider presentation                    | VERIFIED | Steam no-key tile and SteamGridDB artwork-provider tile consume heartbeat data independently. |

### Key Link Verification

| From                                         | To                 | Via                                  | Status | Details                                                                |
| -------------------------------------------- | ------------------ | ------------------------------------ | ------ | ---------------------------------------------------------------------- |
| Steam handler                                | Steam service      | Search and exact-ID detail calls     | WIRED  | Declared patterns verified and suite exercises results.                |
| Socket DLC scan                              | PC matcher         | Hydrated IGDB candidate before Steam | WIRED  | Early return at `scan.py:120`; Steam call begins only after hydration. |
| PC matcher                                   | Steam handler      | Validated DLC lookup                 | WIRED  | Lookup follows identity hydration and accepts one validated result.    |
| Manual candidate endpoint and automatic scan | Steam merge        | `normalize_steam`                    | WIRED  | Both route paths invoke the shared normalizer before persistence.      |
| Response schemas                             | Generated models   | OpenAPI generation contract          | WIRED  | Detailed and component schemas contain backend Steam fields.           |
| MariaDB runner                               | `romm-db-dev`      | Compose `DB_HOST`                    | WIRED  | Current runner completed against generated Compose-network schema.     |
| PostgreSQL runner                            | revision `0126`    | Fresh migration cycle                | WIRED  | Current direct invocation completed through head.                      |
| v2 settings                                  | heartbeat response | `STEAM_API_ENABLED`                  | WIRED  | Dedicated UI tile consumes Steam flag independently of SteamGridDB.    |

### Data-Flow Trace (Level 4)

| Artifact       | Data Variable            | Source                                                     | Produces Real Data                               | Status  |
| -------------- | ------------------------ | ---------------------------------------------------------- | ------------------------------------------------ | ------- |
| Steam handler  | normalized Steam result  | Storefront localized detail response                       | Yes, bounded remote result with same-ID fallback | FLOWING |
| PC scan        | normalized Steam updates | Stored App ID or eligible Storefront search                | Yes, applied only through guarded merge          | FLOWING |
| DLC scan       | `steam_candidate`        | Hydrated IGDB candidate, then validated Storefront details | Yes, hydration failure disconnects Steam lookup  | FLOWING |
| v2 provider UI | App ID and enabled state | Generated response and heartbeat                           | Yes, displayed as independent Steam data         | FLOWING |

### Behavioral Spot-Checks

| Behavior                        | Command                                                                  | Result                                                             | Status |
| ------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------ | ------ |
| Isolated Phase 18 backend suite | `bash backend/tools/verify_phase18_backend_tests.sh`                     | `189 passed, 7 warnings in 28.82s`                                 | PASS   |
| MariaDB migration cycle         | documented Compose `heads && upgrade && downgrade -1 && upgrade` command | Head `0126_add_steam_metadata`; exit 0                             | PASS   |
| PostgreSQL migration cycle      | `bash backend/tools/verify_phase18_postgres_migration.sh`                | Fresh disposable PostgreSQL cycle completed through `0126`; exit 0 | PASS   |
| Static migration contracts      | documented `uv run pytest --noconftest ...` command                      | `7 passed, 1 warning`                                              | PASS   |
| Steam provider UI test          | `npm run test -- --run src/v2/components/GameDetails/providers.test.ts`  | 1 file, 1 test passed                                              | PASS   |
| Frontend compilation            | `npm run typecheck && npm run build`                                     | Both exit 0                                                        | PASS   |
| Scoped runner cleanup lint      | `trunk check backend/tools/verify_phase18_backend_tests.sh`              | `Checked 1 file`, `No issues`                                      | PASS   |

### Probe Execution

No declared or conventional `probe-*.sh` files exist for this phase.

### Requirements Coverage

| Requirement | Source Plans                             | Description                                    | Status    | Evidence                                                                                |
| ----------- | ---------------------------------------- | ---------------------------------------------- | --------- | --------------------------------------------------------------------------------------- |
| STEAM-01    | 18-01, 18-03                             | Independent no-key Storefront provider         | SATISFIED | Config, priority, heartbeat, separate SteamGridDB path, and approved UAT.               |
| STEAM-02    | 18-01, 18-02, 18-04, 18-06, 18-07, 18-09 | Localized stable-ID enrichment with safe merge | SATISFIED | Same-ID fallback, model/migration, guarded merge, and API contracts.                    |
| STEAM-03    | 18-05, 18-10                             | Hydrated IGDB-first DLC enrichment             | SATISFIED | Fail-closed hydration, validated product/parent rules, and no-call regression coverage. |
| STEAM-04    | 18-02, 18-03, 18-06, 18-12               | Separate API and v2 Steam presentation         | SATISFIED | Correct generated contract, independent provider records, UI test, and approved UAT.    |
| STEAM-05    | 18-01 through 18-05, 18-11               | Non-fatal failures and regression coverage     | SATISFIED | Typed degradation and current isolated 189-test suite.                                  |

No Phase 18 requirement is orphaned. No later milestone phase exists to defer an unmet item to.

### Anti-Patterns Found

No Phase-owned blocker or warning was found. The focused scan found only intentional typed empty results for non-fatal provider degradation, filename placeholder handling, and synthetic `xxxxxxxx` test configuration values. No actual keys, artwork payloads, unreferenced debt markers, or manual-data regressions were found. `git diff --check 173133a00^..HEAD` is clean.

### Human Verification Required

None. Plan 18-03 records approved canonical-stack UAT for independent Steam and SteamGridDB labeling, 320px/768px/1440px, light/dark themes, mouse/touch/keyboard/gamepad input, and accessibility-tree checks. This re-verification found no relevant UI regression.

### Gaps Summary

None. The former ShellCheck blocker is closed by the narrowly scoped SC2329 suppression for the intentional EXIT-trap cleanup function. Its exact scoped Trunk command now exits 0. All original Phase 18 must-haves are supported by substantive source, wired links, flowing data, and current evidence.

---

_Verified: 2026-09-25T15:33:09Z_
_Verifier: the agent (gsd-verifier)_
