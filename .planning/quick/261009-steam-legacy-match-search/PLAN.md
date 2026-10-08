---
name: 261009-steam-legacy-match-search
description: Fix Steam discovery and persistence in the legacy ROM matching dialog
status: complete
---

## Objective

Make the existing ROM assignment dialog query Steam for Windows PC ROMs and persist the selected Steam identity, localized metadata, cover, and screenshots without changing the dedicated PC component matching flow.

## Tasks

1. Add Steam candidates and Steam-only provider availability to the legacy search endpoint.
2. Extend the legacy ROM update contract and dialog payload with `steam_id` and Steam cover handling.
3. Add a regression test for Steam name matching and verify the live Dwarf Fortress flow.

## Verification

- Live UI: Steam-only search found Dwarf Fortress App 975370.
- Live UI: selection persisted German Steam metadata, Steam cover, and 20 screenshots.
- Frontend typecheck passed.
- Backend focused pytest remains blocked by the existing host-loopback MariaDB test infrastructure.
