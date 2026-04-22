// v2 Route Registry
//
// As each wave migrates a view to v2, add its lazy-imported component here
// under the matching route name. The main router (src/plugins/router.ts)
// injects these into the v1 route config as Vuetify named views:
//
//   components: { default: v1Component, v2: v2RouteComponents[name] }
//
// When the user's uiVersion is "v2" the named <router-view name="v2"> in the
// v2 AppLayout renders the v2 component. Routes without a v2 entry fall
// through to the `fallbackComponent` so the user sees a helpful "not ready
// yet" screen instead of a blank page.
//
// NOTE: We use string keys instead of importing ROUTES from @/plugins/router
// to avoid a circular import (router.ts ↔ v2/router/routes.ts). Keys here
// MUST match the string values in the ROUTES constant in plugins/router.ts.
import type { Component } from "vue";

export type V2Route = () => Promise<Component>;

export const v2RouteComponents: Partial<Record<string, V2Route>> = {
  home: () => import("@/v2/views/Home.vue"),
  // Wave 1 — Auth flows
  login: () => import("@/v2/views/Auth/Login.vue"),
  "reset-password": () => import("@/v2/views/Auth/ResetPassword.vue"),
  register: () => import("@/v2/views/Auth/Register.vue"),
  // Wave 3 — Gallery
  platform: () => import("@/v2/views/Gallery/Platform.vue"),
  search: () => import("@/v2/views/Gallery/Search.vue"),
  collection: () => import("@/v2/views/Gallery/Collection.vue"),
  "virtual-collection": () => import("@/v2/views/Gallery/Collection.vue"),
  "smart-collection": () => import("@/v2/views/Gallery/Collection.vue"),
  // Setup wizard deferred — remains v1-only for now
  // Wave 4 onwards adds the remaining routes.
};

export const fallbackComponent: V2Route = () =>
  import("@/v2/views/NotReady.vue");

export const v2Layouts = {
  main: () => import("@/v2/layouts/AppLayout.vue"),
  auth: () => import("@/v2/layouts/AuthLayout.vue"),
};
