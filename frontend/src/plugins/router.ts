import { storeToRefs } from "pinia";
import {
  createRouter,
  createWebHistory,
  type NavigationGuardWithThis,
} from "vue-router";
import i18n from "@/locales";
import { startViewTransition } from "@/plugins/transition";
import romApi from "@/services/api/rom";
import storeAuth from "@/stores/auth";
import storeHeartbeat from "@/stores/heartbeat";
import storeRoms from "@/stores/roms";
import type { User } from "@/stores/users";
import { v2Layouts, v2RouteComponents } from "@/v2/router/routes";

export const ROUTES = {
  SETUP: "setup",
  LOGIN: "login",
  RESET_PASSWORD: "reset-password",
  REGISTER: "register",
  MAIN: "main",
  HOME: "home",
  SEARCH: "search",
  PLATFORM: "platform",
  PLATFORM_STORAGE_MAPPING: "platform-storage-mapping",
  COLLECTION: "collection",
  VIRTUAL_COLLECTION: "virtual-collection",
  SMART_COLLECTION: "smart-collection",
  ROM: "rom",
  EMULATORJS: "emulatorjs",
  RUFFLE: "ruffle",
  STREAM: "stream",
  SCAN: "scan",
  UPLOAD: "upload",
  ACTIVITY: "activity",
  USER_PROFILE: "user-profile",
  USER_INTERFACE: "user-interface",
  LIBRARY_MANAGEMENT: "library-management",
  SCAN_SETTINGS: "scan-settings",
  METADATA_SOURCES: "metadata-sources",
  CLIENT_API_TOKENS: "client-api-tokens",
  ADMINISTRATION: "administration",
  SERVER_STATS: "server-stats",
  LOGS: "logs",
  PAIR: "pair",
  PAIR_DEVICE: "pair-device",
  APRIL_FOOLS: "april-fools",
  CONSOLE_HOME: "console-home",
  CONSOLE_PLATFORM: "console-platform",
  CONSOLE_COLLECTION: "console-collection",
  CONSOLE_SMART_COLLECTION: "console-smart-collection",
  CONSOLE_VIRTUAL_COLLECTION: "console-virtual-collection",
  CONSOLE_ROM: "console-rom",
  CONSOLE_PLAY: "console-play",
  // V2-only routes (no v1 equivalent — v1 uses its drawer for these).
  PLATFORMS_INDEX: "platforms-index",
  COLLECTIONS_INDEX: "collections-index",
  CONTROLLER_DEBUG: "controller-debug",
  NOT_FOUND: "404",
} as const;

function v2For(routeName: string) {
  const component = v2RouteComponents[routeName];
  if (!component) throw new Error("Missing v2 route component: " + routeName);
  return component;
}
const routes = [
  {
    path: "/setup",
    component: v2Layouts.auth,
    children: [
      {
        path: "",
        name: ROUTES.SETUP,
        meta: {
          title: i18n.global.t("login.setup-wizard"),
        },
        component: v2For(ROUTES.SETUP),
      },
    ],
  },
  {
    path: "/login",
    component: v2Layouts.auth,
    children: [
      {
        path: "",
        name: ROUTES.LOGIN,
        meta: {
          title: i18n.global.t("login.login"),
        },
        component: v2For(ROUTES.LOGIN),
      },
    ],
  },
  {
    path: "/reset-password",
    component: v2Layouts.auth,
    children: [
      {
        path: "",
        name: ROUTES.RESET_PASSWORD,
        meta: {
          title: i18n.global.t("login.reset-password"),
        },
        component: v2For(ROUTES.RESET_PASSWORD),
      },
    ],
  },
  {
    path: "/register",
    component: v2Layouts.auth,
    children: [
      {
        path: "",
        name: ROUTES.REGISTER,
        meta: {
          title: i18n.global.t("login.register"),
        },
        component: v2For(ROUTES.REGISTER),
      },
    ],
  },
  {
    path: "/",
    name: ROUTES.MAIN,
    meta: {
      title: "RomM",
    },
    component: v2Layouts.main,
    children: [
      {
        path: "",
        name: ROUTES.HOME,
        meta: {
          title: i18n.global.t("settings.home"),
        },
        component: v2For(ROUTES.HOME),
      },
      {
        path: "search",
        name: ROUTES.SEARCH,
        meta: {
          title: i18n.global.t("common.search"),
        },
        component: v2For(ROUTES.SEARCH),
      },

      {
        path: "platform/:platform",
        name: ROUTES.PLATFORM,
        component: v2For(ROUTES.PLATFORM),
      },
      {
        path: "platforms/:platformId/storage",
        name: ROUTES.PLATFORM_STORAGE_MAPPING,
        meta: {
          title: i18n.global.t(
            "storage.administration",
            "Storage administration",
          ),
        },
        component: v2For(ROUTES.PLATFORM_STORAGE_MAPPING),
      },
      {
        path: "collection/:collection",
        name: ROUTES.COLLECTION,
        component: v2For(ROUTES.COLLECTION),
      },
      {
        path: "collection/virtual/:collection",
        name: ROUTES.VIRTUAL_COLLECTION,
        component: v2For(ROUTES.VIRTUAL_COLLECTION),
      },
      {
        path: "collection/smart/:collection",
        name: ROUTES.SMART_COLLECTION,
        component: v2For(ROUTES.SMART_COLLECTION),
      },
      {
        path: "rom/:rom",
        name: ROUTES.ROM,
        component: v2For(ROUTES.ROM),
        beforeEnter: (async (to, _from, next) => {
          const romsStore = storeRoms();

          if (
            !romsStore.currentRom ||
            romsStore.currentRom.id !== parseInt(to.params.rom as string)
          ) {
            try {
              const data = await romApi.getRom({
                romId: parseInt(to.params.rom as string),
              });
              romsStore.setCurrentRom(data.data);
            } catch (error) {
              console.error(error);
            }
          }
          next();
        }) as NavigationGuardWithThis<undefined>,
      },
      {
        path: "rom/:rom/ejs",
        name: ROUTES.EMULATORJS,
        component: v2For(ROUTES.EMULATORJS),
      },
      {
        path: "rom/:rom/ruffle",
        name: ROUTES.RUFFLE,
        component: v2For(ROUTES.RUFFLE),
      },
      {
        path: "april-fools",
        name: ROUTES.APRIL_FOOLS,
        component: v2For(ROUTES.APRIL_FOOLS),
      },
      {
        path: "rom/:rom/stream",
        name: ROUTES.STREAM,
        component: v2For(ROUTES.STREAM),
      },
      // Settings group — every settings route shares the same v2
      // sub-layout (sidebar + content panel). Library Tools (Scan /
      // Upload / Patcher) live here too so they share the settings
      // sidebar shell. v1 keeps its existing per-view structure via the
      // `passthrough` default named view.
      {
        path: "",
        component: v2Layouts.settings,
        children: [
          {
            path: "scan",
            name: ROUTES.SCAN,
            meta: {
              title: i18n.global.t("scan.scan"),
              bare: true,
            },
            component: v2For(ROUTES.SCAN),
          },
          {
            path: "upload",
            name: ROUTES.UPLOAD,
            meta: {
              title: i18n.global.t("common.upload-roms", "Upload ROMs"),
            },
            component: v2For(ROUTES.UPLOAD),
          },
          {
            path: "activity",
            name: ROUTES.ACTIVITY,
            meta: {
              title: i18n.global.t("activity.active-sessions"),
              bare: true,
            },
            component: v2For(ROUTES.ACTIVITY),
          },
          {
            path: "user/:user",
            name: ROUTES.USER_PROFILE,
            meta: { bare: true },
            component: v2For(ROUTES.USER_PROFILE),
          },
          {
            path: "user-interface",
            name: ROUTES.USER_INTERFACE,
            meta: {
              title: i18n.global.t("common.user-interface"),
              bare: true,
            },
            component: v2For(ROUTES.USER_INTERFACE),
          },
          {
            path: "library-management",
            name: ROUTES.LIBRARY_MANAGEMENT,
            meta: {
              title: i18n.global.t("common.library-management"),
              bare: true,
            },
            component: v2For(ROUTES.LIBRARY_MANAGEMENT),
          },
          {
            path: "scan-settings",
            name: ROUTES.SCAN_SETTINGS,
            meta: {
              title: i18n.global.t("settings.scan-settings"),
              bare: true,
            },
            component: v2For(ROUTES.SCAN_SETTINGS),
          },
          {
            path: "metadata-sources",
            name: ROUTES.METADATA_SOURCES,
            meta: {
              title: i18n.global.t("scan.metadata-sources"),
              bare: true,
            },
            component: v2For(ROUTES.METADATA_SOURCES),
          },
          {
            path: "client-api-tokens",
            name: ROUTES.CLIENT_API_TOKENS,
            meta: {
              title: i18n.global.t("settings.client-api-tokens"),
              bare: true,
            },
            component: v2For(ROUTES.CLIENT_API_TOKENS),
          },
          {
            path: "administration",
            name: ROUTES.ADMINISTRATION,
            meta: {
              title: i18n.global.t("common.administration"),
              bare: true,
            },
            component: v2For(ROUTES.ADMINISTRATION),
          },
          {
            path: "server-stats",
            name: ROUTES.SERVER_STATS,
            meta: {
              title: i18n.global.t("common.server-stats"),
              bare: true,
            },
            component: v2For(ROUTES.SERVER_STATS),
          },
          {
            path: "logs",
            name: ROUTES.LOGS,
            meta: {
              title: i18n.global.t("common.logs"),
              bare: true,
              // The log panel fills the viewport and scrolls internally
              // instead of growing the document — see SettingsLayout `fill`.
              fill: true,
            },
            component: v2For(ROUTES.LOGS),
          },
          {
            // Controller-debug lives outside the Settings sidebar
            // but reuses the same chrome (sidebar layout + bare
            // body) so the input system inspector reads as another
            // settings-adjacent tool rather than a standalone view.
            path: "controller-debug",
            name: ROUTES.CONTROLLER_DEBUG,
            meta: { title: "Controller debug", bare: true },
            component: v2For(ROUTES.CONTROLLER_DEBUG),
          },
        ],
      },
      {
        // V2-only index of platforms. V1 uses its drawer for navigation so
        // it redirects this URL home; v2 renders PlatformsIndex.vue.
        path: "platforms",
        name: ROUTES.PLATFORMS_INDEX,
        meta: { title: i18n.global.t("common.platforms") },
        component: v2For(ROUTES.PLATFORMS_INDEX),
      },
      {
        path: "collections",
        name: ROUTES.COLLECTIONS_INDEX,
        meta: { title: i18n.global.t("common.collections") },
        component: v2For(ROUTES.COLLECTIONS_INDEX),
      },
      {
        path: ":pathMatch(.*)*",
        name: ROUTES.NOT_FOUND,
        component: v2For(ROUTES.NOT_FOUND),
      },
    ],
  },
  {
    path: "/pair/device",
    name: ROUTES.PAIR_DEVICE,
    component: () => import("@/v2/views/DevicePairShell.vue"),
  },
  {
    path: "/pair",
    name: ROUTES.PAIR,
    component: () => import("@/v2/views/PairDispatcher.vue"),
  },
  // Console mode (separate UI namespace under /console) — v1 only; v2 merges
  // console behavior into the main UI via the universal input system.
  {
    path: "/console",
    component: () => import("@/console/Layout.vue"),
    children: [
      {
        path: "",
        name: ROUTES.CONSOLE_HOME,
        component: () => import("@/console/views/Home.vue"),
      },
      {
        path: "platform/:id",
        name: ROUTES.CONSOLE_PLATFORM,
        component: () => import("@/console/views/GamesList.vue"),
      },
      {
        path: "collection/:id",
        name: ROUTES.CONSOLE_COLLECTION,
        component: () => import("@/console/views/GamesList.vue"),
      },
      {
        path: "collection/smart/:id",
        name: ROUTES.CONSOLE_SMART_COLLECTION,
        component: () => import("@/console/views/GamesList.vue"),
      },
      {
        path: "collection/virtual/:id",
        name: ROUTES.CONSOLE_VIRTUAL_COLLECTION,
        component: () => import("@/console/views/GamesList.vue"),
      },
      {
        path: "rom/:rom",
        name: ROUTES.CONSOLE_ROM,
        component: () => import("@/console/views/Game.vue"),
      },
      {
        path: "rom/:rom/play",
        name: ROUTES.CONSOLE_PLAY,
        component: () => import("@/console/views/Play.vue"),
      },
    ],
  },
];

interface RoutePermissions {
  path: string;
  requiredScopes: string[];
}

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // popstate (back/forward) — restore the saved offset.
    if (savedPosition) return savedPosition;
    // Same path → only query/hash changed (e.g., the v2 GameDetails
    // tab/subtab params, gallery filter syncs). The user's view should
    // stay where it is; scrolling to top would make the URL update
    // visible as a UX jump.
    if (to.path === from.path) return false;
    // Genuine route change — start fresh from the top.
    return { left: 0, top: 0 };
  },
});

const routePermissions: RoutePermissions[] = [
  { path: ROUTES.CLIENT_API_TOKENS, requiredScopes: ["me.write"] },
  { path: ROUTES.SCAN, requiredScopes: ["platforms.write"] },
  { path: ROUTES.UPLOAD, requiredScopes: ["roms.write"] },
  { path: ROUTES.LIBRARY_MANAGEMENT, requiredScopes: ["platforms.write"] },
  { path: ROUTES.SCAN_SETTINGS, requiredScopes: ["platforms.write"] },
  { path: ROUTES.ADMINISTRATION, requiredScopes: ["users.write"] },
  { path: ROUTES.LOGS, requiredScopes: ["logs.read"] },
];

const authExemptRoutes = [
  ROUTES.LOGIN,
  ROUTES.SETUP,
  ROUTES.RESET_PASSWORD,
  ROUTES.REGISTER,
  ROUTES.PAIR,
] as const;

type AuthExemptRoute = (typeof authExemptRoutes)[number];

export function isAuthExemptRoute(route: string): route is AuthExemptRoute {
  return (authExemptRoutes as readonly string[]).includes(route);
}

function checkRoutePermissions(route: string, user: User | null): boolean {
  // No checks needed for login and setup pages
  if (isAuthExemptRoute(route)) {
    return true;
  }

  // No user, no access
  if (!user) return false;

  // Check if route has permissions requirements
  const routeConfig = routePermissions.find((config) => config.path === route);
  if (!routeConfig) return true;

  // Check if user has required scopes
  return routeConfig.requiredScopes.every((scope) =>
    user.oauth_scopes.includes(scope),
  );
}

router.beforeEach(async (to, _from, next) => {
  const heartbeat = storeHeartbeat();
  const auth = storeAuth();
  const { user } = storeToRefs(auth);
  const currentRoute = to.name?.toString();

  try {
    // Backend unreachable/broken — we can't trust the setup/auth state, and
    // bouncing to /login would just strand the user on a page that can't work
    // either. Let them stay on (and navigate within) whatever the cached state
    // allows; the offline notice explains it and the connection layer
    // re-routes correctly once the backend answers again.
    if (!heartbeat.connected) {
      document.title = to.meta.title
        ? i18n.global.t(to.meta.title as string)
        : "RomM";
      return next();
    }

    // Handle setup wizard
    if (heartbeat.value.SYSTEM.SHOW_SETUP_WIZARD) {
      return currentRoute !== "setup" ? next({ name: ROUTES.SETUP }) : next();
    }

    // Handle authentication — unauth'd users visiting a non-exempt route
    // land on /login. Without this branch, they fall through to the
    // permission check below, fail it, get redirected to the catch-all 404
    // (which matches /), and the guard re-runs forever.
    if (!user.value && (!currentRoute || !isAuthExemptRoute(currentRoute))) {
      return next({
        name: ROUTES.LOGIN,
        query: {
          next: to.query.next ?? to.fullPath,
        },
      });
    }

    // SHOW_SETUP_WIZARD is false here, so setup is already done — nobody
    // belongs on /setup anymore. `/setup` is auth-exempt (so the block above
    // won't bounce an unauthenticated visitor), so redirect both cases:
    // authenticated users go home, everyone else to login. Without covering
    // the unauth case, a stale link / manual nav to /setup would strand the
    // user on the wizard, whose API then 403s once an admin exists.
    if (currentRoute === ROUTES.SETUP) {
      return next({ name: user.value ? ROUTES.HOME : ROUTES.LOGIN });
    }

    // Check permissions
    if (currentRoute && !checkRoutePermissions(currentRoute, user.value)) {
      return next({ name: ROUTES.NOT_FOUND });
    }

    // The logs viewer can be turned off entirely via DISABLE_LOGS_VIEWER; the
    // backend endpoint/stream are then gone, so direct navigation must 404 too.
    if (
      currentRoute === ROUTES.LOGS &&
      heartbeat.value.FRONTEND.DISABLE_LOGS_VIEWER
    ) {
      return next({ name: ROUTES.NOT_FOUND });
    }

    if (to.meta.title) {
      document.title = i18n.global.t(to.meta.title as string);
    } else {
      document.title = "RomM";
    }
    next();
  } catch (error) {
    console.error("Navigation guard error:", error);
    document.title = "RomM";
    next({ name: ROUTES.LOGIN });
  }
});

router.beforeResolve(async (to, from) => {
  // Query/hash-only changes (same path — e.g. the v2 GameDetails `?tab=`
  // param) aren't a real view change. Running a view transition would
  // snapshot every `view-transition-name` element (like the details cover)
  // into the browser's top layer for the crossfade, briefly floating it over
  // the fixed navbar. Skip them — matching `scrollBehavior` above.
  if (to.path === from.path) return;
  const viewTransition = startViewTransition();
  await viewTransition.captured;
});

export default router;
