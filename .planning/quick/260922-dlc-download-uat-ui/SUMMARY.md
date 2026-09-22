---
title: DLC download UAT and selection UI clarity
status: complete
date: 2026-09-22
commit: a7c0b2bee
---

# Result

- Chromium UAT confirmed that deleting one terminal item sends a successful delete and stays removed after reload.
- Chromium UAT confirmed that deleting all terminal items leaves no persisted history after reload.
- The enhanced DLC fixture completed all 40 ZIP transfers into a temporary local test directory.
- Component rows now keep file details collapsed until requested. Individual file checkboxes remain available after expanding details, and the selected size stays in the dialog footer.
- Global resume and cancel controls were removed because the row-level controls are the authoritative, unambiguous actions.

## Verification

- `npm run test -- --run src/v2/components/GameDetails/DownloadAccessibility.test.ts src/v2/components/GameDetails/DownloadTransferHistory.test.ts`
- `npm run typecheck`
- `npm run build`
- Chromium visual UAT at `http://127.0.0.1:3344/rom/10?tab=pc-components`
