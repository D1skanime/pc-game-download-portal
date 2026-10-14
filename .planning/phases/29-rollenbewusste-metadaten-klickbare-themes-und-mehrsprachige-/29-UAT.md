# Phase 29 UAT

Date: 2026-10-14
Status: APPROVED

## Browser acceptance

- [x] Light and dark mode verified.
- [x] Theme and genre chips are keyboard accessible.
- [x] Theme navigation preserves the PC platform scope and filters the result list by stable IGDB theme ID. Verified with Horror (themes=igdb:19&platforms=2).
- [x] Witcher 3 company roles are separated correctly: developer, publisher, and other participating companies are not conflated.
- [x] Another game verified in German, English, and French.
- [x] Witcher 3 verified in English.

## Automated verification

- [x] Focused frontend tests: 24 passed.
- [x] Frontend typecheck passed.
- [x] Backend endpoint syntax validated inside the dev container.
- [x] Dev stack reachable at http://127.0.0.1:3100/.

## Known environment limitations

- Full frontend suite still has one pre-existing source-mutation inventory failure in PcDlcMediaTab.vue (togglePlacement DELETE route classification).
- Focused backend tests were not executable because the test MariaDB on 127.0.0.1:3306 timed out.
