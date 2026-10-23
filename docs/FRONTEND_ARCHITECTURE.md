<!-- generated-by: gsd-doc-writer -->

# RomM Frontend Architecture

Comprehensive documentation of the current Vue 3 and TypeScript frontend for browsing, enriching, managing, playing, and downloading the ROM and PC-game library.

---

## Table of Contents

1. [Overview](#1-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Directory Structure](#3-directory-structure)
4. [Application Lifecycle](#4-application-lifecycle)
5. [Routing & Navigation](#5-routing--navigation)
6. [State Management (Pinia Stores)](#6-state-management-pinia-stores)
7. [API & Data Layer](#7-api--data-layer)
8. [Component Architecture](#8-component-architecture)
9. [Views & Pages](#9-views--pages)
10. [Console Mode](#10-console-mode)
11. [Emulation Integration](#11-emulation-integration)
12. [Theming & Styling](#12-theming--styling)
13. [Internationalization (i18n)](#13-internationalization-i18n)
14. [Real-Time Communication](#14-real-time-communication)
15. [Caching Strategy](#15-caching-strategy)
16. [Utilities & Composables](#16-utilities--composables)
17. [Build & Tooling](#17-build--tooling)
18. [Type System](#18-type-system)

---

## 1. Overview

The frontend is a Vue 3 Composition API single-page application built with Vite and TypeScript. frontend/src/main.ts loads heartbeat, current-user, and configuration data, registers plugins, and mounts RomM.vue. The active router loads v2 layouts, views, and components. The client calls the backend through Axios at /api and receives live events through Socket.IO at /ws/socket.io/. Backend OpenAPI models are generated into frontend/src/**generated**.

| Area    | Current implementation                                       |
| ------- | ------------------------------------------------------------ |
| Build   | Vite 8, Vue plugin, Vuetify plugin, Tailwind CSS Vite plugin |
| State   | Pinia, focused v2 stores, and composables                    |
| Routing | Vue Router 4 with lazy v2 components                         |
| HTTP    | Axios 1.18.1, frontend/src/services/api/index.ts             |
| i18n    | vue-i18n 11 and locale JSON loaded with import.meta.glob     |
| Runtime | Node.js 24, npm >=11.10                                      |

Legacy stores and services remain as compatibility code. v2 uses them through frontend/src/v2/data/adapters/legacy.

---

## 2. High-Level Architecture

    Browser
      |
      v
    Vue Router
      |--> AuthLayout --> login, setup, registration, password reset
      |--> AppLayout --> navigation, router-view, dialogs, audio, player
                    |--> SettingsLayout --> settings and library tools
      v
    v2 views/components
      |--> composables, contracts, operation builders, useCan
      |--> Pinia stores and legacy adapters
      |--> services/api/* and services/socket.ts
      v
    FastAPI backend and generated OpenAPI models

The v2 contract layer in frontend/src/v2/data/contracts.ts models repositories, mutations, library profiles, operation scopes, policies, permissions, retries, resume, provenance, media, and downloads. frontend/src/v2/data/operations.ts builds explicit scan requests.

### Data flow

1. Bootstrap fetches heartbeat, user, and config.
2. The router applies setup, auth, scope, log-viewer, and title rules.
3. A lazy view reads stores or calls a service module. ROM and DLC guards fetch a DetailedRom when needed.
4. Axios adds x-csrftoken, tracks reachability, and returns generated types.
5. Stores and view state update; Socket.IO updates scans, tasks, permissions, or activity.
6. v2 components render the result using local R-prefixed primitives. Backend authorization remains authoritative.

---

## 3. Directory Structure

    frontend/
    ├── package.json, vite.config.js, vitest.config.ts, playwright.config.ts
    └── src/
        ├── main.ts, RomM.vue
        ├── plugins/                 # Router, Pinia, Vuetify, i18n, editor
        ├── v2/
        │   ├── layouts/             # AppLayout, AuthLayout, SettingsLayout
        │   ├── router/              # Lazy routes and route inventory
        │   ├── views/               # Active route pages
        │   ├── components/          # Feature UI
        │   ├── composables/         # Input, responsive, media, operations
        │   ├── data/                # Contracts, policies, adapters
        │   ├── lib/                 # R* primitives and stories
        │   ├── stores/              # Gallery, focus, scroll state
        │   ├── styles/, tokens/      # v2 CSS and token source
        │   ├── utils/               # Artwork, route, download helpers
        │   └── workers/             # Download hash worker
        ├── services/api/             # REST services
        ├── services/cache/           # Browser Cache API helper
        ├── services/socket.ts
        ├── stores/                   # Shared Pinia stores
        ├── locales/                  # 18 locale directories
        ├── styles/, types/, utils/
        └── __generated__/            # OpenAPI-generated models

Active v2 component groups include AppShell, Auth, Collections, Dialogs, Gallery, GameActions, GameCard, GameDetails, Home, MatchRom, Platforms, Player, Scan, Settings, shared, and Soundtrack.

---

## 4. Application Lifecycle

### Startup sequence

main.ts creates the app, registers plugins via frontend/src/plugins/index.ts, loads heartbeat/current user/config in parallel, installs a stale Vite chunk reload guard, installs the router, and mounts #app. AppLayout then installs permission hydration, scan lifecycle, breakpoint attributes, input modality, gamepad/hotkeys, reduced motion, background art, gallery provenance, collection/platform hydration, platform-icon prefetch, and streaming config.

### Request lifecycle

services/api/index.ts creates an Axios client with baseURL /api and a 120-second timeout. It repeats array query parameters, adds x-csrftoken from the romm_csrftoken cookie, and emits backend-online, backend-offline, backend-suspect, and network-quiesced DOM events. A 401 removes romm_session, refreshes CSRF, and routes to login with a next path. A CSRF 403 refreshes the token; ordinary 403 responses remain with the caller.

---

## 5. Routing & Navigation

Routes are declared in frontend/src/plugins/router.ts and lazy components in frontend/src/v2/router/routes.ts. routeInventory.test.ts and v2Boot.test.ts verify the v2 route contract.

### Layouts and main routes

AuthLayout owns /setup, /login, /reset-password, and /register. AppLayout owns authenticated / routes. SettingsLayout owns /scan, /upload, /activity, /user/:user, /user-interface, /library-management, /scan-settings, /metadata-sources, /client-api-tokens, /administration, /server-stats, /logs, and /controller-debug. Pair views are /pair and /pair/device.

| Path                                                   | View                                        |
| ------------------------------------------------------ | ------------------------------------------- |
| /                                                      | v2/views/Home.vue                           |
| /platforms                                             | v2/views/PlatformsIndex.vue                 |
| /platform/:platform                                    | v2/views/Gallery/Platform.vue               |
| /platforms/:platformId/storage                         | v2/views/Storage/PlatformStorageMapping.vue |
| /search                                                | v2/views/Gallery/Search.vue                 |
| /collection/:collection and virtual/smart variants     | v2/views/Gallery/Collection.vue             |
| /rom/:rom                                              | v2/views/GameDetails.vue                    |
| /rom/:rom/dlc/:component                               | v2/views/PcDlcDetails.vue                   |
| /rom/:rom/ejs, /ruffle, /stream                        | v2 player views                             |
| /scan, /upload, /activity                              | v2 library-tool views                       |
| /user-interface, /library-management, /scan-settings   | v2 settings views                           |
| /metadata-sources, /client-api-tokens, /administration | v2 settings views                           |
| /server-stats, /logs, /controller-debug                | v2 settings views                           |

ROM and DLC guards accept only decimal safe integers and fetch the parent ROM when it is not current. GameDetails handles ROM-to-ROM param navigation because Vue reuses the component instance. Legacy /console paths explicitly redirect to v2 destinations.

### Guards and permissions

Login, setup, reset-password, register, and pair are auth-exempt. Unauthenticated users are sent to login with the destination. SHOW_SETUP_WIZARD sends users to setup. Route scopes are checked for client tokens (me.write), scan and library management (platforms.write), upload (roms.write), administration (users.write), and logs (logs.read). Logs 404 when DISABLE_LOGS_VIEWER is enabled.

---

## 6. State Management (Pinia Stores)

Pinia is registered in frontend/src/plugins/pinia.ts. Core stores include auth/config/heartbeat for session and server state; roms/platforms/collections for catalog state; scanning/tasks/activity for operations; download/upload/streaming/playing/soundtrackPlayer for transfers and playback; galleryFilter for platform, genre, theme, franchise, collection, company, rating, region, language, player count, tags, providers, statuses, favorites, saves, states, soundtrack, missing, and verification; galleryView/language/navigation/notifications for UI; permissions/permissionGroups for grants and admin groups; pcAutomation for the review queue; and v2 stores for gallery, focus, and scroll state.

Gallery multi-select fields support any/all/none logic. VueUse localStorage persists settings.theme, ui.currentView, settings.boxartStyle, scan providers, hash-matcher switches, and metadata locale. Server data is fetched explicitly and stored.

---

## 7. API & Data Layer

### Services

frontend/src/services/api contains rom.ts for ROM detail, filters, matching, descriptions, owned media, manuals, soundtrack, notes, downloads, catalog removal, and PC metadata/media candidates; platform.ts and storage.ts for platform/filesystem/storage roots, browsing, mapping, previews, and removal consequences; config.ts for binds, versions, exclusions, scan settings, and browser downloads; identity.ts, user.ts, and permissions.ts for auth, users, scopes, groups, and hidden entities; downloadTransfers.ts for enhanced sessions; save.ts, state.ts, screenshot.ts, firmware.ts, and streaming.ts for user assets and playback; and task/activity/play-session/client-token/device-auth/export/sgdb/pcAutomation modules for jobs, sessions, tokens, pairing, exports, covers, and PC review.

Types come from frontend/src/**generated**, generated by npm run generate from the backend OpenAPI endpoint.

### Scan, storage, and mappings

Scan.vue loads filesystem platforms and metadata capabilities, persists provider and metadata-locale choices, and calls useLibraryOperation. ScanPlatform.vue owns platform panels; useScanLifecycle and stores/scanning.ts provide global live progress.

LibraryManagement.vue exposes mapping, storage, excluded, and missing tabs. StorageRootsSection, FolderMappingsSection, ExcludedSection, and MissingGamesSection render them. PlatformStorageMapping.vue uses storageApi to load roots/mappings, browse relative folders, test/save mappings, refresh previews, and inspect removal consequences. It checks useCan("app.admin"). The frontend presents backend results; filesystem authorization remains backend-owned.

### Gallery flow

Gallery views combine roms, platforms, galleryFilter, galleryView, URL/query composables, GalleryShell, GameCard/GameListRow, selection/actions, and virtualized helpers. Genre and theme values become ROM query/filter parameters.

---

## 8. Component Architecture

Views are route orchestrators. Feature components own tabs, dialogs, uploads, and emits. Reusable primitives are in frontend/src/v2/lib; shared UI is in frontend/src/v2/components/shared. AppLayout mounts AppNav, BackgroundArt, BottomNav, GlobalDialogs, SoundtrackMiniPlayer, optional DebugOverlay, and CrtOverlay.

PlatformsIndex.vue uses PlatformTile and list rows. Gallery/Platform.vue uses PlatformHead, GalleryShell, toolbar/filter, virtual rows, card/list modes, selection, and scan actions. GameDetails.vue composes CoverColumn, GameHeader, actions, and detail tabs. PcComponents.vue shows PC components and links DLC to /rom/:rom/dlc/:component. PcDlcDetails.vue resolves a parent ROM and kind dlc component, then renders PcDlcDetail, PcDlcFiles, PcDlcMediaTab, and PcDlcNotesTab. GlobalDialogs is emitter-driven; detail interactions use GameActions, MoreMenu, DownloadSelectionDialog, DownloadManager, MatchRomDialog, RefreshMetadataDialog, EditRomDialog, and DeleteRomDialog.

---

## 9. Views & Pages

### Home and platform browsing

Home.vue uses CardRow and v2 home adapters. Platform, Search, and Collection views share gallery infrastructure for card/list modes, cover ratios, alphabetical navigation, selection, virtualized rows, URL-synchronized filters, and hover background art. Theme and genre filtering is implemented in galleryFilter.ts.

### ROM detail

GameDetails.vue is a cover column plus tab panel. ?tab= is persistent. The typed resolveDescription contract in useManualDescription selects requested exact/base manual text, requested exact/base provider text, manual English, provider English, then empty. It exposes source and resolved language, labels English fallback, and never displays the scalar legacy summary as a description. Tabs cover overview, metadata/providers, files/downloads, media, saves/states, achievements, notes, patcher, related games, screenshots, artwork, soundtrack, and PC components.

### PC and DLC

PcComponents exposes parent-game components. PcDlcDetails loads the parent and selects the requested DLC. PC APIs and components support metadata candidate search/selection, local-media candidates/selection, files, media, notes, and component-local descriptions.

### Scan and library management

Scan.vue supports discovery, metadata-only, media-only, hash, update, and complete operation choices. It exposes catalog providers plus Hasheous and Playmatch gates, persists choices, displays platform statistics, and builds requests with preview, retry, cancellation, resume, separate UI/metadata locales, and fileMutation false.

### Media, saves, states, and downloads

MediaTab has manual, screenshots, artwork, and soundtrack subtabs. ManualSubtab uses PDF/Markdown viewers; ScreenshotsSubtab delegates provider and personal/community screenshot actions to one useScreenshotManagement instance. The composable retains separate provider-media and personal-gallery IDs, current-resource useCan scopes, own-user guards and danger confirmation. One provider lane includes placement, deletion confirmation and explicit refresh; 409 responses reconcile once without replaying mutations. Canonical getRom results commit through setCurrentRom and update only while the route/user generation is current, preserving gallery and detail updates without stale navigation writes. DOM/lightbox state remains in the subtab; ArtworkSubtab displays scraped/owned art; SoundtrackPanel uses the soundtrack player. SaveDataTab uploads, lists, deletes, downloads, and changes visibility for saves and states through save.ts and state.ts. DownloadSelectionDialog and DownloadManager combine useBrowserDownloadQueue with downloadTransfers.ts sessions. downloadHash.worker.ts keeps hashing off the main thread.

---

## 10. Console Mode

The old console application is not mounted as a separate runtime. /console URLs redirect to v2 home, platform, collection, ROM, or emulator destinations and routeInventory.ts records those redirects. Controller interaction remains part of v2 through useGamepad, useInputModality, useGlobalHotkeys, focus restoration, grid navigation, right-stick scrolling, and /controller-debug.

---

## 11. Emulation Integration

/rom/:rom/ejs, /rom/:rom/ruffle, and /rom/:rom/stream lazy-load the v2 player views. They use ROM data, v2/utils/emulatorjs.ts, play-session and streaming services, and save/state dialogs. services/api/streaming.ts handles capabilities, claim/release, save-and-exit, volume, mute, save-state, and load-state. Ruffle declarations are in frontend/src/types/ruffle.d.ts.

---

## 12. Theming & Styling

frontend/src/styles/themes.ts defines Vuetify dark, light, and auto themes. useThemeMode combines settings.theme with prefers-color-scheme. v2 token source is frontend/src/v2/tokens/index.ts and generated CSS is frontend/src/v2/styles/tokens.css. v2 uses CSS custom properties for colors, statuses, surfaces, borders, spacing, radii, typography, focus, overlays, and responsive dimensions.

useBreakpoint mirrors values to html[data-bp]. AppLayout reserves top and mobile bottom navigation safe-area space; AuthLayout bounds auth cards on phones; SettingsLayout removes its sidebar on small screens and supports fill mode for logs. Input modality distinguishes keyboard, pointer, touch, and gamepad. Reduced motion is mirrored as r-v2-reduced-motion. BackgroundArt uses two layers and a dwell before cross-fading.

---

## 13. Internationalization (i18n)

frontend/src/locales/index.ts creates a non-legacy vue-i18n instance with en_US locale and fallback. JSON is dynamically discovered and grouped by namespace. The current locale directories are en_US, en_GB, fr_FR, de_DE, bg_BG, cs_CZ, hu_HU, it_IT, ja_JP, ko_KR, pl_PL, pt_BR, ro_RO, ru_RU, es_ES, tr_TR, zh_CN, and zh_TW. English, German, and French are first-class locales.

Namespaces include activity, collection, common, emptyStates, gallery, home, login, logs, patcher, platform, play, rom, scan, settings, setup, and storage. language.ts matches browser locales exactly, then by language prefix, otherwise en_US. LocalizedDescriptionEditor.vue normalizes locale identifiers, selects the active locale, resolves manual/provider/fallback text, and saves a ROM or PC component description with expected_version. localeParity.test.ts checks storage.administration in every locale; the Python scripts check locale parity and sorted keys.

Administrative language selection uses `useSystemLanguage` to synchronize the existing shared scan-language priority through the v2 config adapter, with permission and compare-and-set checks. Personal-only users change their own interface preference. `useMetadataMatchLanguage` captures language and candidate ownership for search and confirmation; the server remains authoritative for provider text.

`useDescriptionEditor` owns an exact entity/locale draft and its expected version. Display fallback never becomes a manual draft. Dirty drafts survive provider refresh and failed saves; locale switching is guarded while dirty or saving. Cancel restores the draft baseline without saving; the dialog currently stays open and can be closed using its X button. This is an accepted live-UAT limitation, not a completed close-on-cancel behavior.

---

## 14. Real-Time Communication

services/socket.ts creates a Socket.IO client at /ws/socket.io/ with websocket and polling transports. useSocketEvent and feature installers consume it. useScanLifecycle updates scanning state for scan start/progress/completion/failure. Task and activity views consume live job/session state. Permission hydration can refresh on permissions:changed. REST and heartbeat remain the primary reachability/session signal. AppLayout installs scan lifecycle globally so the navigation indicator and Scan view share one store.

---

## 15. Caching Strategy

Pinia retains active user, platform, collection, ROM, scan, task, permission, and streaming state. services/cache/index.ts wraps the browser Cache API and services/cache/api.ts provides the compatibility helper. usePlatformIconCache prefetches platform icons. useBrowserDownloadQueue retains browser queue/verification state; downloadHash.worker.ts avoids main-thread hashing. localStorage persists theme, gallery mode, box-art style, scan providers, hash switches, and metadata locale. main.ts handles stale Vite chunks with one guarded reload. Views refresh ROM or transfer/session lists explicitly after mutations.

---

## 16. Utilities & Composables

Important v2 composables include useCan, useLibraryOperation, useProviderResolution, useManualDescription, useGameDetailsMedia, useBackgroundArt, useBackgroundAudio, useCoverArt, useWebpSupport, useBreakpoint, useResponsiveColumns, useInputModality, useGamepad, useGridNav, useRightStickScroll, useGallerySelectionInput, useGlobalHotkeys, useThemeMode, useReducedMotion, useCrtMode, useFullscreenPref, useGalleryFilterUrl, useGalleryViewModeUrl, useTileSearchUrl, useGalleryProvenance, usePageTitle, useServerConnection, useSnackbar, useConfirm, useSocketEvent, useScanLifecycle, useBrowserDownloadQueue, and usePlaySession. v2/utils covers route-query validation, artwork, collection covers, player helpers, ROM verification/status, download manifest paths, provider labels, CSS checks, and input helpers. frontend/src/utils contains form-data, task, cover, and IndexedDB helpers.

---

## 17. Build & Tooling

Run commands from frontend:

| Command                    | Purpose                             |
| -------------------------- | ----------------------------------- |
| npm run dev                | Vite dev server, normally port 3000 |
| npm run build              | Build tokens and production bundle  |
| npm run preview            | Serve the production build          |
| npm run build:tokens       | Generate v2 token CSS               |
| npm run typecheck          | vue-tsc without emit                |
| npm run v2:maintainability | v2 maintainability check            |
| npm run generate           | Generate OpenAPI models             |
| npm run test               | Vitest once                         |
| npm run test:watch         | Vitest watch mode                   |
| npm run test:ui            | Vitest UI                           |
| npm run storybook          | Storybook on port 6006              |
| npm run storybook:build    | Build Storybook                     |
| npm run storybook:test     | Storybook play tests                |
| npm run test:e2e           | Playwright tests                    |
| npm run test:e2e:ui        | Playwright UI mode                  |

package.json declares Node 24, npm >=11.10, and npm@11.13.0. vite.config.js defines @ and @v2, Vue/Vuetify/Tailwind/VitePWA/mkcert plugins, browser-derived CSS targets, PWA support, and proxies for /api, /ws, /netplay, and /openapi.json. DEV_PORT defaults to 5000; HTTP dev uses 3000 and DEV_HTTPS uses 8443. ROM resources are ignored by the watcher.

vitest.config.ts uses happy-dom, globals, vitest.setup.ts, Vuetify inlining, and src/test globs. Tests are colocated with v2 features; Storybook provides interaction/accessibility stories; Playwright is separate. Repository checks also use trunk fmt and trunk check.

---

## 18. Type System

@ aliases frontend/src and @v2 aliases frontend/src/v2. frontend/src/**generated** is produced from the backend OpenAPI schema. Services use generated types such as DetailedRomSchema, PcComponentSchema, StorageRootSchema, PermissionGroupSchema, SaveSchema, and StateSchema. Custom types are in types/emitter.d.ts, main.d.ts, rom.d.ts, user.d.ts, and ruffle.d.ts. v2/data/contracts.ts defines operation/repository contracts; MatchRom/types.ts and ControllerDebug/types.ts define feature contracts.

---

## Appendix: Key Design Patterns

1. Lazy route imports isolate auth, gallery, detail, settings, and player chunks.
2. Layout-owned chrome keeps navigation, dialogs, background art, audio, permissions, input, and scan lifecycle consistent.
3. Store hydration plus explicit refetch supports direct navigation and mutation refreshes.
4. URL-persisted tabs and filters make detail, media, save/state, settings, and gallery state deep-linkable.
5. Route and component checks supplement backend authorization.
6. Operation requests carry scope, providers, locales, provenance, retry/resume, and file-mutation capabilities.
7. Media UI distinguishes local files, provider media, owned media, community assets, and private assets.
8. Tokens, breakpoints, reduced-motion classes, input modality, and safe-area spacing define responsive v2 presentation.
