# Phase 21 UAT

Fixture: authorized isolated stack `phase9-uat-3344-1788090387`, Windows `pc`
mapping, ROM `TheWitcher3WildHunt` (database ID 13, Steam App ID 292030), UI
`http://127.0.0.1:3344`.

Environment authorization: authorized isolated app and MariaDB only. The source
mount `/tmp/phase9-uat-3344.0e0RyN/source-library -> /romm/library/roms` was
confirmed read-only. No NAS, Team4s service, Docker Compose, or external
source-library write was used.

Migration: the isolated app startup applied
`0131_owned_background_audio -> 0132_steam_scan_owned_media_state`. `alembic
current` then reported `0132_steam_scan_owned_media_state (head)`.

Source snapshot: the source manifest before the repaired runs and after their
UPDATE/COMPLETE scans was
`f510419dc429fa057226ec8dcda7e13e994258297abf418178e09c3cb02d2b86`
(103 files, 36 directories), generated with `find . -type f -printf '%P\\0' |
sort -z | xargs -0 sha256sum | sha256sum` from the source root. The app also
confirmed `/romm/library/roms` is not writable. The source-immutability suite
previously passed (2 tests). The broader host pytest suite cannot run because
the canonical checkout has no local MariaDB on `127.0.0.1`; the focused
view-safety regression was run directly in the isolated app process instead.

New-game scan: FAIL. A Steam-only `NEW_PLATFORMS` invocation correctly left the
existing `pc` platform unscanned (0 ROMs), so it could not provide the required
new-ROM evidence. The existing platform fixture was then exercised by COMPLETE.

Existing UPDATE/COMPLETE refresh: PASS. After the view-safe persistence repair,
both isolated Steam-only COMPLETE and UPDATE scans processed Witcher without
`main_developer` or `created_at` view-update errors. The persisted Witcher row
has Steam App ID `292030`, German Steam name `The Witcher 3: Wild Hunt`, and
structured developer/publisher `CD PROJEKT RED`. The COMPLETE run reconciled 21
new `provider=steam` image candidates (IDs 263 through 283) while retaining the
existing two upload candidates (IDs 176 and 177) and all existing overview,
background, and soundtrack placements. Existing surfaces were already claimed,
so no automatic placement was added, as required by the unclaimed-surface rule.

Manual text/overview/background protection: PARTIAL. Existing upload candidates
and all manual/legacy overview and background placements remained after COMPLETE
and UPDATE. A fresh operator-edited title/developer/publisher/release override
could not be exercised in this fixture without changing the pre-existing UAT
record, so it is not claimed as verified.

Phase 20 Media visibility/editability: PARTIAL. The unchanged owned-media
catalog contains the reconciled Steam candidates and retained uploads/placements.
No authenticated browser session was available to inspect the Media tab itself,
so visual visibility/editability is not claimed as verified.

Outcome: FAIL

Evidence: commands executed in the authorized stack were the isolated app reload,
`uv run alembic current`, direct `execute_mapping_scans(...,
metadata_sources=["steam"])` for NEW_PLATFORMS, COMPLETE, and UPDATE, MariaDB
queries of `roms`, `roms_metadata`, `rom_owned_media`, and
`rom_owned_media_placements`, source manifest snapshots, and the focused
view-safety regression. The outcome remains FAIL because NEW and the browser
manual-override/Media-tab checks lack evidence; no PASS is claimed.
