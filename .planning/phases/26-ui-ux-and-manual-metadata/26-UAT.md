*** Add File: .planning/phases/26-ui-ux-and-manual-metadata/26-UAT.md
+# Phase 26 Linux Dev UAT +
+Status: BLOCKED before authenticated application scenarios +
+This record belongs to Phase 26 Plan 03 and was produced on the canonical
+Linux checkout /home/d1sk/romm on team4s-linux. No Windows checkout files were
+edited. No speculative product change was made in response to a failed gate or
+an unavailable UAT prerequisite. +
+## Automated regression gates +
+Commands were run against the canonical checkout. Backend tests ran inside the
+already-running romm-dev container, whose /app/backend and /app/frontend mounts
+resolve directly to /home/d1sk/romm/backend and /home/d1sk/romm/frontend. +
+| Gate | Command | Result | Evidence |
+| --- | --- | --- | --- |
+| Focused backend regression, repository configuration | docker exec -w /app romm-dev sh -lc "uv run pytest backend/tests/handler/metadata/test_manual_description.py backend/tests/handler/metadata/test_rom_media.py backend/tests/handler/database/test_rom_media.py backend/tests/endpoints/roms/test_pc_metadata.py backend/tests/endpoints/roms/test_media.py -q" | BLOCKED, exit 1 | 90 setup errors before assertions. backend/pytest.ini forces DB_HOST=127.0.0.1; the container cannot reach the Compose-only MariaDB there. Exact error: mariadb.OperationalError: Can't connect to server on '127.0.0.1' (115). |
+| Focused backend regression, explicit Compose host probe | docker exec -w /app -e ROMM_BASE_PATH=romm_test -e DB_HOST=romm-db-dev -e DB_PORT=3306 -e DB_NAME=romm_test -e DB_USER=romm_test -e DB_PASSWD=passwd -e ROMM_DB_DRIVER=mariadb -e ROMM_AUTH_SECRET_KEY=phase26-regression-secret romm-dev sh -lc "uv run pytest -c /dev/null backend/tests/handler/metadata/test_manual_description.py -q" | BLOCKED, exit 1 | 3 setup errors before assertions. MariaDB resolves as romm-db-dev, but rejects the configured test principal: Access denied for user 'romm_test'@'172.19.0.4' (using password: YES). No database user or service was changed. |
+| Frontend typecheck | cd frontend && npm run typecheck | PASS, exit 0 | vue-tsc --noEmit completed successfully. |
+| Locale parity | python3 frontend/src/locales/check_i18n_locales.py | FAIL, exit 1 | Existing locale drift: missing account-exists in setup.json; missing media-only, media-only-desc, and media-only-existing-platforms in scan.json; missing refreshing-media in rom.json across the reported non-source locale files. |
+| Locale sorted keys | python3 frontend/src/locales/check_i18n_sorted.py | FAIL, exit 1 | Reported unsorted files: bg_BG/rom.json, cs_CZ/rom.json, de_DE/rom.json, de_DE/scan.json, de_DE/setup.json, en_GB/rom.json, en_US/rom.json, en_US/scan.json, en_US/setup.json, es_ES/rom.json, fr_FR/rom.json, hu_HU/rom.json, it_IT/rom.json, ja_JP/rom.json, ko_KR/rom.json, pl_PL/rom.json, pt_BR/rom.json, ro_RO/rom.json, ru_RU/rom.json, tr_TR/rom.json, zh_CN/rom.json, and zh_TW/rom.json. |
+| Focused frontend regression | cd frontend && npm run test -- --run [Plan 26-02 focused files] | FAIL, exit 1 | 11 files: 10 passed, 1 failed. 87 tests: 86 passed, 1 failed. Failure: PcDlcFiles.test.ts, identifies owned image downloads by role and MIME type, expected [data-testid='pc-dlc-owned-media-downloads'] was absent. The exact expanded command and output are retained in /tmp/phase26-03-frontend-focused-tests.log on team4s-linux. |
+| Full frontend regression | cd frontend && npm run test -- --run | FAIL, exit 1 | 109 files: 107 passed, 2 failed. 914 tests: 912 passed, 2 failed. Failures were the PcDlcFiles selector above and sourceMutationInventory.test.ts, which reports unclassified authority importer=v2/composables/useManualDescription/index.ts call=updateRomDescription:api.put method=PUT route=/roms/{rom_id}/description payload=none operation=UNKNOWN storage=unknown. |
+| Default production build | cd frontend && npm run build | BLOCKED, exit 1 | Vite transformed 3821 modules, then vite-plugin-pwa failed to write /home/d1sk/romm/frontend/dist/sw.js: EACCES: permission denied. The mounted dist volume is not writable by the checkout owner. |
+| Isolated production build | cd frontend && ./node_modules/.bin/vite build --outDir /tmp/phase26-03-dist | PASS, exit 0 | Vite 8.0.16 built successfully. PWA generated 608 precache entries and /tmp/phase26-03-dist/sw.js plus Workbox output. Existing warnings: stale Browserslist data, large chunks, and direct eval in third-party vue3-pdf-app. |
+| v2 maintainability | cd frontend && npm run v2:maintainability | FAIL, exit 1 | Existing rule violation: composables/useManualDescription/index.ts: direct legacy store/service import. |
+| Planning artifact whitespace | git diff --check -- .planning/phases/26-ui-ux-and-manual-metadata/26-03-PLAN.md .planning/phases/26-ui-ux-and-manual-metadata/26-CONTEXT.md | PASS, exit 0 | No whitespace errors. | +
+The locale failures, frontend regression failures, maintainability failure, and
+backend test setup failures were observed without editing working features.
+They are carried forward as actionable blockers or pre-existing limitations,
+not relabeled as passes. +
+## Browser UAT matrix +
+The approved in-app browser reached the Linux Dev app at +http://localhost:3100, but the only observed application state was: +
+- URL: http://localhost:3100/login?next=/
+- Title: Einloggen
+- Visible controls: German Benutzername and Passwort fields, Passwort anzeigen,

- disabled Einloggen, Passwort vergessen?, locale Deutsch, environment
- development
  +- No documented seeded account or credential was present in the Phase 26 UAT
- materials.
-

+The scenarios below were therefore not executed. They are explicitly blocked
+by the missing approved authenticated UAT identity, not treated as passing: +
+| Surface / scenario | Status | Blocker |
+| --- | --- | --- |
+| Parent game: locale-scoped manual description save, immediate update, reset, and provider refresh preservation | BLOCKED | No authenticated UAT account |
+| DLC: locale-scoped manual description save/reset and provider refresh preservation | BLOCKED | No authenticated UAT account |
+| Expansion: locale-scoped manual description save/reset and provider refresh preservation | BLOCKED | No authenticated UAT account |
+| Screenshot deletion from Media, Overview, and Background placement, owned-file removal, persistence after normal scan | BLOCKED | No authenticated UAT account and no approved destructive UI confirmation session |
+| Direct cover search discoverability and explicit SteamGridDB-disabled messaging | BLOCKED | No authenticated UAT account or provider state |
+| Crawled release date/genres visibility and manual override provenance | BLOCKED | No authenticated UAT account |
+| Valid YouTube ID observable result and invalid ID actionable validation | BLOCKED | No authenticated UAT account |
+| Logical mapped paths using active StorageRoot/PlatformStorageMapping, with no /romm/library presentation | BLOCKED | No authenticated UAT account and no seeded mapping view |
+| PC header download opens Game Download selection; non-PC behavior and hidden copy-link action remain unchanged | BLOCKED | No authenticated UAT account |
+| DLC component-scoped edit/save, cover search from overflow, Game Download, Media placement/delete, inherited parent background, clickable overview gallery, Files-only manifest | BLOCKED | No authenticated UAT account |
+| Expansion component-scoped edit/save, cover search from overflow, Game Download, Media placement/delete, inherited parent background, clickable overview gallery, Files-only manifest | BLOCKED | No authenticated UAT account |
+| Existing animation default, sharp backgrounds, soundtrack background versus playlist distinction, Steam filtering, and scan results | BLOCKED | No authenticated UAT account |
+| Light and dark themes | BLOCKED | No authenticated UAT account |
+| Responsive sweep, including phone and desktop breakpoints | BLOCKED | No authenticated UAT account |
+| Keyboard, mouse, and touch input | BLOCKED | No authenticated UAT account | +
+### Required follow-up +
+Provide an approved seeded Linux Dev account or an approved way to seed the
+disposable UAT database, then rerun this matrix without changing product code.
+The current browser blocker is exact and reproducible: the app serves the login
+route, and no permitted credentials are available to continue.

## Live browser attempt

At 2026-10-09T23:34Z, the approved in-app browser opened the Linux Dev
endpoint successfully, but it redirected to the unauthenticated login route.
No credentials were entered, no form was submitted, and no application data was
changed. The browser UAT task is therefore blocked rather than approved.

## Live UAT follow-up — 2026-10-10

The authenticated Linux Dev browser session is now available as `admin`. The following Phase 26 flows were rechecked live on the canonical app:

| Scenario                                                                        | Result              | Evidence                                                                                                     |
| ------------------------------------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------ |
| Parent overview description is read-only by default and exposes a pencil action | PASS                | `overview-description-edit` is present; clicking it opens the existing Description dialog.                   |
| DLC overview description is read-only by default and exposes a pencil action    | PASS                | `Bearbeiten` is present; clicking it opens the scoped Description dialog.                                    |
| DLC Game Download surface                                                       | PASS                | Download tab shows the DLC selector and existing manifest member with size/hash.                             |
| DLC Media surface                                                               | PASS                | Media tab loads the component-scoped screenshot list and delete controls.                                    |
| DLC Files surface                                                               | PASS                | Files tab shows only the scoped manifest member and mapped content link.                                     |
| Overview gallery viewer                                                         | PASS                | Screenshot 1 opens the shared viewer with 1/40 navigation and Previous/Next/Close controls.                  |
| Browser runtime errors during these flows                                       | PASS                | No current console errors observed after a clean route load.                                                 |
| Provider cover/metadata search                                                  | BLOCKED / NOT A BUG | Provider credentials/API configuration are absent; per UAT instruction this is ignored as environment setup. |

No genuine product bug was found in these live checks, so no additional `gsd-quick` fix was created from this UAT pass.

| Platform API/live library | PASS | `/platform/2` loads Windows metadata and ROM links; no current browser console errors or API-500 signal observed after the schema migration. |
