# Phase 21 Validation Matrix

**Created:** 2026-09-30
**Status:** Planned evidence, execute before declaring Phase 21 complete

## Revision addressed

This artifact closes the Nyquist evidence gap found in `21-PLAN-CHECK.md`. It makes every D-10 behavior, migration boundary, source-immutability proof, and D-11 UAT result explicitly recordable. A blocked authorized dependency is evidence, not a pass.

## Automated Evidence Matrix

| Locked behavior                                                     | Test location                                                                                                                                                          | Command                                                                                                                                                                 | Evidence required                                                                                                                                                                         |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D-01 shared pure admin/targeted enrichment boundary                 | `backend/tests/handler/metadata/test_pc_steam_enrichment.py`, `backend/tests/endpoints/roms/test_pc_metadata.py`                                                       | `cd backend && uv run pytest tests/handler/metadata/test_pc_steam_enrichment.py tests/endpoints/roms/test_pc_metadata.py -x`                                            | Targeted selection and scan request produce the same normalized patch without ORM mutation in the helper.                                                                                 |
| D-02 persisted-ID first, German-first same-ID fallback              | `backend/tests/handler/metadata/test_pc_steam_enrichment.py`, `backend/tests/handler/metadata/test_steam_handler.py`                                                   | `cd backend && uv run pytest tests/handler/metadata/test_pc_steam_enrichment.py tests/handler/metadata/test_steam_handler.py -x`                                        | Stored ID avoids name search; win/linux/mac use one lookup; German values win and English fills only missing values of that App ID.                                                       |
| D-03 new/update/complete only, excluded paths unchanged             | `backend/tests/handler/test_scan_handler.py`, `backend/tests/endpoints/sockets/test_scan.py`                                                                           | `cd backend && uv run pytest tests/handler/test_scan_handler.py tests/endpoints/sockets/test_scan.py -x`                                                                | New, UPDATE, COMPLETE parity plus no new Quick/Hashes/classic/excluded-platform Steam calls.                                                                                              |
| D-04/D-05 manual/provenance and IGDB boundary                       | `backend/tests/handler/metadata/test_steam_merge.py`, `backend/tests/endpoints/roms/test_pc_metadata.py`                                                               | `cd backend && uv run pytest tests/handler/metadata/test_steam_merge.py tests/endpoints/roms/test_pc_metadata.py -x`                                                    | Manual title, summary, developer, publisher, release, and selected media survive; no DLC/IGDB relationship behavior changes.                                                              |
| D-06 unavailable, malformed, ambiguous, invalid, rate-limited no-op | `backend/tests/handler/metadata/test_pc_steam_enrichment.py`, `backend/tests/handler/test_scan_handler.py`, `backend/tests/handler/metadata/test_steam_owned_media.py` | `cd backend && uv run pytest tests/handler/metadata/test_pc_steam_enrichment.py tests/handler/test_scan_handler.py tests/handler/metadata/test_steam_owned_media.py -x` | Explicit ambiguous/no-match and rate-limit cases return `{}`, make no second lookup/reconciliation call, and preserve text/media/placements.                                              |
| D-07 candidate identity, idempotence, tombstone and upload safety   | `backend/tests/handler/database/test_rom_media.py`, `backend/tests/handler/metadata/test_steam_owned_media.py`                                                         | `cd backend && uv run pytest tests/handler/database/test_rom_media.py tests/handler/metadata/test_steam_owned_media.py -x`                                              | Two identical inventories retain one catalog row/path and placements, create no orphan or cleanup intent; stale provider candidates tombstone only after full inventory; uploads survive. |
| D-08 unclaimed-only placement                                       | `backend/tests/handler/database/test_rom_media.py`                                                                                                                     | `cd backend && uv run pytest tests/handler/database/test_rom_media.py -x`                                                                                               | Empty overview/background receives compatible Steam candidate; occupied/manual surfaces are neither replaced, removed, appended, nor reordered.                                           |
| D-09 existing Media review path                                     | `backend/tests/endpoints/roms/test_media.py`                                                                                                                           | `cd backend && uv run pytest tests/endpoints/roms/test_media.py -x`                                                                                                     | Existing catalog/placement response remains consumable without a new route or client transport.                                                                                           |
| D-10 source-library safety                                          | `backend/tests/integration/test_scan_source_immutability.py`                                                                                                           | `cd backend && uv run pytest tests/integration/test_scan_source_immutability.py -x`                                                                                     | Isolated source snapshot before/after the new Steam scan branch is identical.                                                                                                             |

## Migration Evidence

| Check                               | Required execution                                                                                                                                                 | PASS evidence                                                                                                                      | BLOCKED evidence                                                                   |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Migration identity                  | Inspect `backend/alembic/versions/0132_steam_scan_owned_media_state.py`                                                                                            | `revision = "0132_steam_scan_owned_media_state"`, `down_revision = "0131_owned_background_audio"`; no existing migration modified. | Not applicable after source inspection.                                            |
| MariaDB/MySQL upgrade and downgrade | Authorized disposable database: upgrade from `0131_owned_background_audio` to `0132_steam_scan_owned_media_state`, then downgrade to `0131_owned_background_audio` | Commands, dialect, revision transitions, and clean result recorded in `21-VALIDATION.md` execution evidence.                       | Record exact missing authorized disposable database, no Docker Compose startup.    |
| PostgreSQL upgrade and downgrade    | Authorized disposable PostgreSQL: same revision transitions                                                                                                        | Commands, dialect, revision transitions, and clean result recorded in execution evidence.                                          | Record exact missing authorized disposable database/credentials, no Team4s change. |

## Final Focused Suite

Run after all implementation tasks:

```text
cd backend && uv run pytest \
  tests/handler/test_scan_handler.py \
  tests/handler/metadata/test_pc_steam_enrichment.py \
  tests/handler/metadata/test_steam_handler.py \
  tests/handler/metadata/test_steam_merge.py \
  tests/handler/metadata/test_steam_owned_media.py \
  tests/handler/database/test_rom_media.py \
  tests/endpoints/roms/test_pc_metadata.py \
  tests/endpoints/roms/test_media.py \
  tests/endpoints/sockets/test_scan.py \
  tests/integration/test_scan_source_immutability.py -x
```

Run applicable Trunk checks for changed backend files after the focused suite. Preserve a failing command's exact output summary; never treat unavailable database/browser infrastructure as a passing test.

## D-11 Witcher-only UAT Evidence

`21-04-PLAN.md` ends with the blocking human-verify checkpoint. The executor creates `21-UAT.md` using this minimal record:

```text
# Phase 21 UAT

Fixture: isolated Witcher-style fixture only
Environment authorization: <approved isolated environment or BLOCKED reason>
Source snapshot: <before/after result>
New-game scan: <German text and automatic unclaimed media result>
Existing UPDATE/COMPLETE refresh: <result>
Manual text/overview/background protection: <result>
Phase 20 Media visibility/editability: <result>
Outcome: PASS | FAIL | BLOCKED
Evidence: <commands, screenshots, or exact blocker>
```

UAT must never use a NAS mount, Team4s service, Docker Compose, or an external source-library path. If no authorized isolated browser/database environment exists, record `Outcome: BLOCKED` with the missing dependency and stop short of a UAT pass.

## Execution Evidence

Append only after executing the planned checks. Until then, every item above is planned rather than passed.
