export type RouteOutcome =
  | { kind: "view"; component: string }
  | { kind: "redirect"; target: string }
  | { kind: "removed" };

export const routeInventory = {
  setup: { kind: "view", component: "Auth/Setup.vue" },
  login: { kind: "view", component: "Auth/Login.vue" },
  "reset-password": { kind: "view", component: "Auth/ResetPassword.vue" },
  register: { kind: "view", component: "Auth/Register.vue" },
  main: { kind: "view", component: "Home.vue" },
  home: { kind: "view", component: "Home.vue" },
  search: { kind: "view", component: "Gallery/Search.vue" },
  platform: { kind: "view", component: "Gallery/Platform.vue" },
  "platform-storage-mapping": {
    kind: "view",
    component: "Storage/PlatformStorageMapping.vue",
  },
  collection: { kind: "view", component: "Gallery/Collection.vue" },
  "virtual-collection": {
    kind: "view",
    component: "Gallery/Collection.vue",
  },
  "smart-collection": {
    kind: "view",
    component: "Gallery/Collection.vue",
  },
  rom: { kind: "view", component: "GameDetails.vue" },
  "pc-dlc": { kind: "view", component: "PcDlcDetails.vue" },
  emulatorjs: { kind: "view", component: "Player/EmulatorJS.vue" },
  ruffle: { kind: "view", component: "Player/Ruffle.vue" },
  stream: { kind: "view", component: "Player/Stream.vue" },
  scan: { kind: "view", component: "Scan.vue" },
  upload: { kind: "view", component: "Upload.vue" },
  activity: { kind: "view", component: "Activity.vue" },
  "user-profile": { kind: "view", component: "Settings/UserProfile.vue" },
  "user-interface": {
    kind: "view",
    component: "Settings/UserInterface.vue",
  },
  "library-management": {
    kind: "view",
    component: "Settings/LibraryManagement.vue",
  },
  "scan-settings": {
    kind: "view",
    component: "Settings/ScanSettings.vue",
  },
  "metadata-sources": {
    kind: "view",
    component: "Settings/MetadataSources.vue",
  },
  "client-api-tokens": {
    kind: "view",
    component: "Settings/ClientApiTokens.vue",
  },
  administration: {
    kind: "view",
    component: "Settings/Administration.vue",
  },
  "server-stats": {
    kind: "view",
    component: "Settings/ServerStats.vue",
  },
  logs: { kind: "view", component: "Settings/Logs.vue" },
  pair: { kind: "view", component: "PairDispatcher.vue" },
  "pair-device": { kind: "view", component: "PairDevice.vue" },
  "platforms-index": { kind: "view", component: "PlatformsIndex.vue" },
  "collections-index": { kind: "view", component: "CollectionsIndex.vue" },
  "controller-debug": {
    kind: "view",
    component: "ControllerDebug.vue",
  },
  "console-home": { kind: "redirect", target: "home" },
  "console-platform": { kind: "redirect", target: "platform" },
  "console-collection": { kind: "redirect", target: "collection" },
  "console-smart-collection": {
    kind: "redirect",
    target: "smart-collection",
  },
  "console-virtual-collection": {
    kind: "redirect",
    target: "virtual-collection",
  },
  "console-rom": { kind: "redirect", target: "rom" },
  "console-play": { kind: "redirect", target: "emulatorjs" },
  "april-fools": { kind: "removed" },
  "404": { kind: "view", component: "NotFound.vue" },
} as const satisfies Record<string, RouteOutcome>;
