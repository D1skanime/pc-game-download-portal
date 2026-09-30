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

Source snapshot: before the UAT, the complete source manifest was enumerated with
`find . -type f -print0 | sort -z | xargs -0 sha256sum` from the source root.
After the runs, the equivalent manifest fingerprint was
`0ed2f1583cf9c9a4afb2fc0067aed0c8822c57a38dc8ba9eef6eaf9347b2a802`
(103 files, 36 directories). The app also confirmed `/romm/library/roms` is not
writable. `cd /app/backend && uv run pytest
tests/integration/test_scan_source_immutability.py -x` passed (2 tests).

New-game scan: FAIL. A Steam-only `NEW_PLATFORMS` invocation correctly left the
existing `pc` platform unscanned (0 ROMs), so it could not provide the required
new-ROM evidence. The existing platform fixture was then exercised by COMPLETE.

Existing UPDATE/COMPLETE refresh: FAIL. An isolated Steam-only COMPLETE scan
found six ROM fixtures and reached Witcher, but persistence failed before a valid
German text or media result could be observed. MariaDB reported:
`Column 'main_developer' is not updatable` for the `roms_metadata` view. The
view derives `main_developer`, `publishers`, and `pc_release_date` from
`roms.igdb_metadata`, so the Phase 21 Steam structured metadata cannot be
persisted through that view in this UAT database.

Manual text/overview/background protection: FAIL. The pre-existing Witcher rows
showed two upload candidates and existing overview/background placements, but the
failed COMPLETE transaction prevented a valid post-refresh preservation check.

Phase 20 Media visibility/editability: FAIL. The existing catalog rows were
queried in the isolated database, but no reconciled Steam candidate could be
produced after the persistence error, so Media-tab verification cannot pass.

Outcome: FAIL

Evidence: commands executed in the authorized stack were the isolated app restart,
`uv run alembic current`, direct `execute_mapping_scans(...,
metadata_sources=["steam"])` for NEW_PLATFORMS and COMPLETE, source manifest
snapshots, and the isolated source-immutability pytest command. The failing
database error is recorded above exactly; no PASS is claimed.
