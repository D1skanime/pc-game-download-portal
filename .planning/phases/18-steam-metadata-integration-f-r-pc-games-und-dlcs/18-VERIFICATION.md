---
phase: 18-steam-metadata-integration-f-r-pc-games-und-dlcs
verified: 2026-09-25T14:12:23Z
status: gaps_found
score: 19/25 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Only one hydrated IGDB DLC identity can apply one high-confidence Steam DLC, and it updates the existing component rather than creating another component."
    status: failed
    reason: "An IGDB detail-hydration exception returns the unhydrated cached relation, so Steam lookup and persistence can still proceed."
    artifacts:
      - path: backend/handler/metadata/pc_match_handler.py
        issue: "fetch_unique_related_igdb_candidate() returns candidate in its exception path instead of failing closed."
    missing:
      - "Return None when IGDB hydration is unavailable or cannot produce a valid hydrated DLC identity."
      - "Add a regression test proving no Steam lookup follows a hydration exception."
  - truth: "Phase closure has command-backed evidence for backend behavior, both database dialect paths, generated API types, frontend test/typecheck/build, linting, and the completed responsive accessibility UAT."
    status: partial
    reason: "The verifier could not obtain passing backend or PostgreSQL migration evidence. Backend pytest stops in its global MariaDB fixture at 127.0.0.1:3306; the documented PostgreSQL verifier is already known to fail in the pre-existing 0115 enum migration."
    artifacts:
      - path: backend/tests
        issue: "63 selected Steam tests error before their assertions because MariaDB is unreachable."
      - path: backend/alembic/versions/20260831_add_pc_rom_components.py
        issue: "Fresh PostgreSQL upgrade fails before revision 0126, so the Phase 18 migration has no end-to-end PostgreSQL proof."
    missing:
      - "Provide a reachable isolated MariaDB test database and rerun the focused Phase 18 backend suite."
      - "Repair the PostgreSQL baseline enum migration, then run the disposable Phase 18 PostgreSQL verifier through upgrade, downgrade, and re-upgrade."
  - truth: "Generated TypeScript contracts are regenerated from the backend OpenAPI schema, never manually edited."
    status: partial
    reason: "The actual generated contracts contain the Steam fields, but the declared key link targets frontend/src/__generated__/models/RomSchema.ts, which does not exist in this repository. The corresponding generated ROM contract is DetailedRomSchema.ts."
    artifacts:
      - path: frontend/src/__generated__/models/RomSchema.ts
        issue: "Missing declared generated artifact."
    missing:
      - "Correct the plan key link to DetailedRomSchema.ts (or create the declared generated contract if that is the intended API)."
human_verification:
  - test: "Verify the Steam v2 provider tile and App-ID action at 320px, 768px, and 1440px in both themes, using mouse, touch, keyboard, and gamepad."
    expected: "Steam is visibly distinct from SteamGridDB, reports no-key enablement, has accessible disabled/status state, and opens the exact Storefront App-ID URL without clipping or focus traps."
    why_human: "Responsive rendering, external navigation, assistive-technology names, and real input modality cannot be established from source inspection or the focused registry unit test."
---

# Phase 18: Steam Metadata Integration fuer PC Games und DLCs Verification Report

**Phase Goal:** Add the official Steam Storefront provider to eligible PC games and safely identified DLC components, with German-first text while preserving IGDB relationships, manual data, and SteamGridDB's artwork-only role.
**Verified:** 2026-09-25T14:12:23Z
**Status:** gaps_found
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                             | Status    | Evidence                                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | No-key Steam provider can be enabled independently.                                               | VERIFIED  | `config/__init__.py:123-127` exposes flag and locale settings, and `watcher.py:65-80` independently registers Steam.                            |
| 2   | German-first reads use only the resolved App ID for English fallback.                             | VERIFIED  | `steam_handler.py:87-104` calls `get_app_details(steam_id)` for both locales, with no fallback name search.                                     |
| 3   | Storefront faults are non-fatal.                                                                  | VERIFIED  | `steam.py:32-59` turns client, JSON, value, and exhausted-429 failures into typed empty results.                                                |
| 4   | Automatic name search is platform-gated, while explicit IDs can refresh on excluded PC platforms. | VERIFIED  | `steam_handler.py:58-80,106-118` gates name search; `scan_handler.py:168-197` allows stored IDs for the limited explicit-PC set.                |
| 5   | ROMs and components retain nullable Steam identity/provenance.                                    | VERIFIED  | `models/rom.py:330-337,558,655-657` and migration `0126:17-35` add nullable fields without a Steam uniqueness index.                            |
| 6   | Migration graph is one-headed and Steam persistence is reversible.                                | UNCERTAIN | Static chain is `0125 -> 0126` with reverse drops, but Alembic cannot execute in this host and PostgreSQL baseline proof is blocked.            |
| 7   | Steam and SteamGridDB remain separate in priority and heartbeat paths.                            | VERIFIED  | Separate handlers, config slugs, heartbeat branches, and provider entries exist; SGDB files have no Storefront references.                      |
| 8   | V2 settings and provider links show Steam separately.                                             | UNCERTAIN | Source wiring is present in `MetadataSources.vue:114-122` and `providers.ts:65-70`; responsive/accessibility behavior needs live UAT.           |
| 9   | Registry omissions have focused regression coverage.                                              | UNCERTAIN | Focused tests exist, but backend pytest cannot reach its required MariaDB fixture.                                                              |
| 10  | Eligible PC main games get field-safe Steam metadata while IGDB relations remain intact.          | VERIFIED  | Both scan and selected-candidate paths use `normalize_steam`; it only writes display/provenance fields, not IGDB relationship fields.           |
| 11  | Automatic and manual selection share the non-empty, manual-safe merge policy.                     | VERIFIED  | `scan_handler.py:197` and `pc_metadata.py:475-492` both call `normalize_steam`.                                                                 |
| 12  | Steam artwork is candidate-only and cannot silently replace selected artwork.                     | VERIFIED  | Normalizer emits candidate media; automatic scan copies only metadata fields, and selection validates explicit media IDs.                       |
| 13  | IGDB remains the required authority for automatic DLC discovery.                                  | VERIFIED  | Scan starts with `fetch_unique_related_igdb_candidate()` before any Steam call.                                                                 |
| 14  | Only a hydrated, unique IGDB DLC identity can permit Steam DLC enrichment.                        | FAILED    | `pc_match_handler.py:108-112` returns the non-hydrated cached candidate after IGDB lookup failure, then `scan.py:133` may invoke Steam.         |
| 15  | Unsafe DLC types, ambiguity, malformed parents, and parent mismatches preserve state.             | VERIFIED  | `pc_match_handler.py:145-188` rejects all except one validated DLC; scan only persists a non-None validated result.                             |
| 16  | Safe DLC receives same-App-ID locale fallback.                                                    | VERIFIED  | DLC details use the same `get_rom_by_id()` localized builder as main games.                                                                     |
| 17  | Existing API surfaces expose Steam ID and provenance.                                             | VERIFIED  | `responses/rom.py:311-316,521-526`; generated component and detailed-ROM contracts include both fields.                                         |
| 18  | Generated contracts are connected to the declared OpenAPI artifact.                               | FAILED    | `PcComponentMetadataSchema.ts` and `DetailedRomSchema.ts` contain fields, but declared `RomSchema.ts` is absent.                                |
| 19  | Stored IDs refresh by ID and reject mismatched responses.                                         | VERIFIED  | `scan_handler.py:181-185` resolves stored ID first and rejects identity mismatch.                                                               |
| 20  | Classic ROMs never enter Steam lookup.                                                            | VERIFIED  | Steam resolver is only invoked from PC scan handling and rejects non-explicit platform slugs.                                                   |
| 21  | Steam failure leaves other provider output usable.                                                | VERIFIED  | Resolver catches exceptions and returns `{}`; provider fetches use isolated `asyncio.gather(..., return_exceptions=True)`.                      |
| 22  | Upstream versus fork-only behavior is documented.                                                 | VERIFIED  | `docs/superpowers/specs/2026-09-24-steam-metadata-integration-design.md` exists and records the boundary.                                       |
| 23  | Closure has complete command-backed backend, dialect, lint, and UAT evidence.                     | FAILED    | Current backend tests are infrastructure-blocked, fresh PostgreSQL is baseline-blocked, and no independently verifiable live UAT record exists. |
| 24  | Existing components retain Steam provenance without duplication.                                  | VERIFIED  | `apply_pc_component_metadata_candidate()` selects by existing component and test coverage asserts two components may share an App ID.           |
| 25  | Steam component persistence cannot erase IGDB structured data or become display authority.        | VERIFIED  | `roms_handler.py:1865-1891` merges provider metadata and only IGDB updates IGDB structured fields.                                              |

**Score:** 19/25 truths verified

### Required Artifacts

| Artifact                                                         | Expected                               | Status    | Details                                                               |
| ---------------------------------------------------------------- | -------------------------------------- | --------- | --------------------------------------------------------------------- |
| `backend/adapters/services/steam.py`                             | Bounded public transport               | VERIFIED  | Bounded retries and typed empty degradation.                          |
| `backend/handler/metadata/steam_handler.py`                      | Localized platform-gated normalization | VERIFIED  | Same-ID fallback and Store type validation.                           |
| `backend/handler/metadata/steam_merge.py`                        | Shared guarded merge                   | VERIFIED  | Non-empty updates, per-field manual protection, candidate-only media. |
| `backend/handler/metadata/pc_match_handler.py`                   | Safe DLC validation                    | HOLLOW    | Hydration exception is fail-open to cached candidate.                 |
| `backend/alembic/versions/0126_add_steam_metadata.py`            | Portable reversible persistence        | UNCERTAIN | Code is substantive, but dialect execution is blocked.                |
| `frontend/src/__generated__/models/PcComponentMetadataSchema.ts` | Component contract                     | VERIFIED  | Includes `steam_id` and `steam_metadata`.                             |
| `frontend/src/__generated__/models/RomSchema.ts`                 | Declared generated ROM contract        | MISSING   | Actual generated contract is `DetailedRomSchema.ts`.                  |

### Key Link Verification

| From            | To                  | Via                            | Status    | Details                                                                    |
| --------------- | ------------------- | ------------------------------ | --------- | -------------------------------------------------------------------------- |
| Steam handler   | Steam service       | Search and App-ID details      | WIRED     | Calls service search and exact-ID detail methods.                          |
| Steam config    | Steam handler       | Locale constants               | WIRED     | Imported constants control all detail/search locale calls.                 |
| Heartbeat       | Steam handler       | Steam dispatch                 | WIRED     | Dedicated `MetadataSource.STEAM` branch.                                   |
| PC selection    | Steam merge         | Re-resolve then normalize      | WIRED     | Candidate is re-resolved server-side before merge.                         |
| Scan            | Steam handler/merge | Stored-ID-first resolution     | WIRED     | Direct ID refresh precedes eligible name lookup.                           |
| DLC scan        | PC matcher/database | Existing-component application | PARTIAL   | Existing component is used, but hydration failure can still reach Steam.   |
| Response schema | `RomSchema.ts`      | OpenAPI generation             | NOT_WIRED | Target file does not exist; `DetailedRomSchema.ts` is the actual artifact. |

### Data-Flow Trace (Level 4)

| Artifact      | Data Variable                                  | Source                                        | Produces Real Data                   | Status  |
| ------------- | ---------------------------------------------- | --------------------------------------------- | ------------------------------------ | ------- |
| Steam handler | `SteamRom`                                     | Storefront detail response                    | Bounded remote data, normalized      | FLOWING |
| PC scan       | `steam_updates`                                | Stored ID or eligible search, then normalizer | Real handler result, no empty clears | FLOWING |
| DLC scan      | `steam_candidate`                              | IGDB relation then Steam detail               | Unsafe on IGDB hydration exception   | HOLLOW  |
| V2 settings   | `heartbeat.METADATA_SOURCES.STEAM_API_ENABLED` | `/heartbeat` contract                         | API/type wiring present              | FLOWING |

### Behavioral Spot-Checks

| Behavior                     | Command                                                                                | Result                                                      | Status                  |
| ---------------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ----------------------- |
| Steam provider-link registry | `cd frontend && npm run test -- --run src/v2/components/GameDetails/providers.test.ts` | 1 test passed                                               | PASS                    |
| Focused backend Steam suite  | `cd backend && uv run pytest ... -q`                                                   | 63 setup errors, MariaDB `127.0.0.1:3306` unreachable       | BLOCKED, infrastructure |
| Alembic heads                | `ROMM_AUTH_SECRET_KEY=... uv run alembic heads`                                        | Cannot create configured `/romm/assets` in host environment | BLOCKED, infrastructure |

### Probe Execution

No phase-declared or conventional `probe-*.sh` scripts were found. Step 7c skipped.

### Requirements Coverage

| Requirement | Source Plans               | Description                                                          | Status    | Evidence                                                                                              |
| ----------- | -------------------------- | -------------------------------------------------------------------- | --------- | ----------------------------------------------------------------------------------------------------- |
| STEAM-01    | 01, 03, 08                 | Independent no-key provider, German-first defaults, priority, health | SATISFIED | Config, registration, heartbeat, and separate v2 registry are wired.                                  |
| STEAM-02    | 01, 02, 04, 06, 07, 09     | Stable ID, safe localized metadata, field-level merge                | PARTIAL   | Implementation is wired, but migration execution evidence and declared generated link are incomplete. |
| STEAM-03    | 05                         | IGDB-first safe DLC enrichment                                       | BLOCKED   | Hydration failure does not fail closed before Steam lookup.                                           |
| STEAM-04    | 02, 03, 04, 06, 07, 09     | Separate API and v2 provenance surfaces                              | SATISFIED | Existing response surfaces and generated active contracts contain distinct Steam fields.              |
| STEAM-05    | 01, 02, 03, 04, 05, 07, 08 | Non-fatal failures and regression checks                             | PARTIAL   | Failure isolation is implemented, but backend/dialect checks lack successful current execution.       |

### Anti-Patterns Found

| File                                           | Line    | Pattern                            | Severity | Impact                                         |
| ---------------------------------------------- | ------- | ---------------------------------- | -------- | ---------------------------------------------- |
| `backend/handler/metadata/pc_match_handler.py` | 108-112 | Exception returns cached candidate | BLOCKER  | Breaks the required hydrated-IGDB safety gate. |

No unreferenced `TBD`, `FIXME`, or `XXX` markers were found in Phase 18 source files.

### Human Verification Required

### 1. Responsive Steam provider UI

**Test:** Verify the v2 Steam settings tile and Steam App-ID action at 320px, 768px, and 1440px, in light and dark themes, with mouse, touch, keyboard, and gamepad.

**Expected:** Steam and SteamGridDB remain clearly distinct; the no-key state is accessible; the link opens the exact App-ID Storefront URL; controls have sensible focus order with no clipping or trap.

**Why human:** Runtime visual layout, actual external navigation, assistive-technology naming, and input modality are not proven by source or the focused unit test.

### Gaps Summary

The feature is largely implemented: Storefront transport, exact-App-ID locale fallback, separate SGDB behavior, merge protection, stored-ID refresh, component provenance, API contracts, and the unit provider registry are present and wired.

It does not meet the phase contract yet. The DLC safety boundary is fail-open when IGDB hydration raises, which permits a Steam lookup from an unhydrated relation. In addition, the promised closure evidence is not reproducible in this checkout: backend test setup has no reachable MariaDB, and the documented fresh PostgreSQL run fails before the Phase 18 migration in a baseline enum migration. The missing `RomSchema.ts` target is a declared key-link mismatch, even though equivalent active generated contracts exist.

---

_Verified: 2026-09-25T14:12:23Z_
_Verifier: the agent (gsd-verifier)_
