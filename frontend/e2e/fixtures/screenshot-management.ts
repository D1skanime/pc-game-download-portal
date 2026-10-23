import { expect, type Page } from "@playwright/test";
import type {
  DetailedRomSchema,
  RomOwnedMediaSchema,
} from "../../src/__generated__";

export const evidence =
  "../.planning/phases/37-zockarchive-screenshot-management-ui-redesign/evidence";
const image = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><defs><linearGradient id="g"><stop stop-color="#302755"/><stop offset="1" stop-color="#207581"/></linearGradient></defs><path fill="url(#g)" d="M0 0h640v360H0z"/><path fill="#98b4bc" d="m0 300 150-170 120 90 160-160 210 240v60H0z"/><text x="30" y="50" fill="white" font-size="24">ZockArchive screenshot fixture</text></svg>`;
type GalleryMedia = RomOwnedMediaSchema & {
  placements: NonNullable<RomOwnedMediaSchema["placements"]>;
};
type GalleryRom = Omit<DetailedRomSchema, "owned_media"> & {
  owned_media: GalleryMedia[];
};
export function fixtureRom(count = 12): GalleryRom {
  const media = Array.from({ length: count }, (_, n): GalleryMedia => ({
    id: n + 7,
    mime_type: "image/svg+xml",
    owned_path: `/fixture/provider${n}.svg`,
    provider_media_id: String(n + 7),
    created_at: "2026-10-23T09:00:00Z",
    updated_at: "2026-10-23T10:00:00Z",
    role: "screenshot",
    origin: "provider",
    state: "active",
    provider:
      n === 0 ? "IGDB long provider label <script>escaped</script>" : "IGDB",
    display_label: `Screenshot ${n + 7} with a long accessible title`,
    placements:
      n < 2
        ? [
            {
              id: n * 2 + 1,
              media_id: n + 7,
              surface: "overview",
              position: n,
            },
            {
              id: n * 2 + 2,
              media_id: n + 7,
              surface: "background",
              position: n,
            },
          ]
        : [],
  }));
  return {
    igdb_id: null,
    sgdb_id: null,
    moby_id: null,
    ss_id: null,
    ra_id: null,
    launchbox_id: null,
    hasheous_id: null,
    tgdb_id: null,
    flashpoint_id: null,
    hltb_id: null,
    gamelist_id: null,
    libretro_id: null,
    steam_id: null,
    platform_fs_slug: "snes",
    platform_custom_name: null,
    fs_name_no_tags: "gallery.zip",
    fs_path: "fixture",
    name_sort_key: "gallery",
    slug: "gallery",
    alternative_names: [],
    youtube_video_id: null,
    igdb_metadata: null,
    moby_metadata: null,
    ss_metadata: null,
    launchbox_metadata: null,
    hasheous_metadata: null,
    flashpoint_metadata: null,
    hltb_metadata: null,
    gamelist_metadata: null,
    manual_metadata: null,
    has_manual: false,
    has_soundtrack: false,
    path_video: null,
    is_unidentified: false,
    is_identified: true,
    revision: null,
    regions: [],
    languages: [],
    tags: [],
    crc_hash: null,
    md5_hash: null,
    sha1_hash: null,
    ra_hash: null,
    has_simple_single_file: true,
    has_nested_single_file: false,
    has_multiple_files: false,
    full_path: "/fixture/gallery.zip",
    missing_from_fs: false,
    has_notes: false,
    rom_user: {
      id: 1,
      user_id: 1,
      rom_id: 1,
      created_at: "2026-10-23T09:00:00Z",
      updated_at: "2026-10-23T10:00:00Z",
      last_played: null,
      is_main_sibling: true,
      backlogged: false,
      now_playing: false,
      hidden: false,
      rating: 0,
      difficulty: 0,
      completion: 0,
      status: null,
    },
    merged_screenshots: [],
    merged_ra_metadata: null,
    sibling_roms: [],
    steam_metadata: null,
    all_user_saves: [],
    all_user_states: [],
    user_collections: [],
    all_user_notes: [],
    id: 1,
    name: "ZockArchive Gallery Adventure",
    fs_name: "gallery.zip",
    fs_name_no_ext: "gallery",
    fs_extension: "zip",
    fs_size_bytes: 1024,
    platform_id: 1,
    platform_slug: "snes",
    platform_display_name: "Super Nintendo",
    updated_at: "2026-10-23T10:00:00Z",
    created_at: "2026-10-23T09:00:00Z",
    summary: "Isolated screenshot management browser fixture.",
    path_cover_small: "",
    path_cover_large: "",
    url_cover: "",
    url_manual: "",
    path_manual: "",
    files: [],
    user_saves: [],
    user_states: [],
    user_screenshots: [],
    metadatum: {
      rom_id: 1,
      genres: [],
      collections: [],
      companies: [],
      main_developer: null,
      game_modes: [],
      player_count: "1",
      first_release_date: null,
      pc_release_date: null,
      average_rating: null,
      genre_options: [],
      theme_options: [],
      franchises: [],
      company_roles: [],
      age_ratings: [],
    },
    owned_media: media,
    owned_media_placements: [],
    all_user_screenshots: [
      {
        id: 10,
        rom_id: 1,
        user_id: 1,
        username: "Fixture owner",
        is_public: true,
        download_path: "/fixture/mine10.svg",
      },
      {
        id: 11,
        rom_id: 1,
        user_id: 1,
        username: "Fixture owner",
        is_public: false,
        download_path: "/fixture/mine11.svg",
      },
      {
        id: 7,
        rom_id: 1,
        user_id: 2,
        username: "Community long username",
        is_public: true,
        download_path: "/fixture/community7.svg",
      },
    ].map((shot) => ({
      file_name: "fixture.svg",
      file_name_no_tags: "fixture.svg",
      file_name_no_ext: "fixture",
      file_extension: "svg",
      file_path: "/fixture",
      file_size_bytes: 100,
      full_path: "/fixture/fixture.svg",
      missing_from_fs: false,
      created_at: "2026-10-23T09:00:00Z",
      updated_at: "2026-10-23T10:00:00Z",
      ...shot,
    })),
  };
}

/** Local transport owns only fixture responses; unknown traffic never reaches a backend. */
export async function mountGallery(
  page: Page,
  options: {
    count?: number;
    ownCount?: number;
    viewer?: boolean;
    theme?: "dark" | "light";
    locale?: string;
  } = {},
) {
  const state = {
    rom: fixtureRom(options.count),
    errors: [] as string[],
    blocked: [] as string[],
    unexpected: [] as string[],
    mutations: [] as {
      method: string;
      path: string;
      body: Record<string, unknown> | null;
      query: string;
    }[],
    reads: 0,
    conflict: false,
    uploadFailure: false,
    refreshFailure: false,
    uploadBarrier: null as Promise<void> | null,
    mediaBarrier: null as Promise<void> | null,
  };
  page.on("pageerror", (error) =>
    state.errors.push(error.stack ?? error.message),
  );
  if (options.ownCount) {
    const extra = Array.from({ length: options.ownCount - 2 }, (_, n) => ({
      ...state.rom.all_user_screenshots[0],
      id: n + 20,
      download_path: `/fixture/own${n}.svg`,
    }));
    state.rom.all_user_screenshots.splice(2, 0, ...extra);
  }
  await page.addInitScript(
    ({ theme, locale }) => {
      localStorage.setItem("settings.uiVersion", "v2");
      localStorage.setItem("settings.theme", theme);
      localStorage.setItem("settings.locale", locale);
    },
    { theme: options.theme ?? "dark", locale: options.locale ?? "en_US" },
  );
  await page.context().routeWebSocket("**/*", (ws) => {
    (ws.url().startsWith("ws://127.0.0.1:4177/ws/socket.io/")
      ? state.blocked
      : state.unexpected
    ).push("WebSocket " + ws.url());
    ws.close();
  });
  await page.context().route("**/*", async (route) => {
    const req = route.request(),
      url = new URL(req.url()),
      path = url.pathname;
    const json = (body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    if (url.origin !== "http://127.0.0.1:4177") {
      (req.url() ===
      "https://api.github.com/repos/D1skanime/pc-game-download-portal/releases/latest"
        ? state.blocked
        : state.unexpected
      ).push(req.url());
      return route.abort();
    }
    if (
      path === "/assets/default/user.svg" ||
      path.startsWith("/fixture/") ||
      /^\/api\/roms\/1\/media\/\d+\/content$/.test(path)
    )
      return route.fulfill({ contentType: "image/svg+xml", body: image });
    if (!path.startsWith("/api/") && !path.startsWith("/ws"))
      return route.continue();
    if (req.method() !== "GET")
      state.mutations.push({
        method: req.method(),
        path,
        body: req.headers()["content-type"]?.includes("application/json")
          ? req.postDataJSON()
          : null,
        query: url.search,
      });
    if (path === "/api/users/me")
      return json({
        id: 1,
        username: "Fixture owner",
        role: options.viewer ? "viewer" : "admin",
        enabled: true,
        oauth_scopes: [
          "roms.read",
          "roms.write",
          "assets.read",
          "assets.write",
        ],
        ui_settings: {
          uiVersion: "v2",
          theme: options.theme ?? "dark",
          locale: options.locale ?? "en_US",
        },
      });
    if (path === "/api/permissions/me")
      return json({
        is_admin: !options.viewer,
        grants: [],
        hidden: { platforms: [], roms: [] },
      });
    if (path === "/api/setup/status")
      return json({
        enrolled: true,
        setup_complete: true,
        current_step: "complete",
        saved_assignments: [],
        missing_assignments: [],
        root_health: { reachable: true, readable: true, non_writable: true },
        cause_code: null,
        next_action: "start_first_scan",
      });
    if (
      ["/api/collections", "/api/collections/smart", "/api/platforms"].includes(
        path,
      )
    )
      return json([]);
    if (path === "/api/streaming/config")
      return json({ enabled: false, containers: [] });
    if (path === "/api/scan-operations/active") return json(null);
    if (path === "/api/heartbeat")
      return json({ SYSTEM: { VERSION: "fixture", SHOW_SETUP_WIZARD: false } });
    if (path === "/api/config")
      return json({
        SCAN_METADATA_PRIORITY: [],
        SCAN_ARTWORK_PRIORITY: [],
        SCAN_ARTWORK_PRIORITY_OVERRIDES: {},
        SCAN_REGION_PRIORITY: [],
        SCAN_LANGUAGE_PRIORITY: [],
        SCAN_MEDIA: [],
        PLATFORMS_BINDING: {},
        PLATFORMS_VERSIONS: {},
        EJS_SETTINGS: {},
        EJS_CONTROLS: {},
        browser_download_queue_concurrency: 3,
      });
    if (path === "/api/roms" && req.method() === "GET")
      return json({ items: [state.rom], total: 1, char_index: {} });
    if (path === "/api/roms/1" && req.method() === "GET") {
      state.reads++;
      return state.refreshFailure && state.reads > 1
        ? json({ detail: "Canonical refresh failed" }, 500)
        : json(state.rom);
    }
    if (path === "/api/screenshots" && req.method() === "POST") {
      if (state.uploadBarrier) await state.uploadBarrier;
      if (state.uploadFailure && req.postData()?.includes("fail.png"))
        return json({ detail: "Fixture upload failed" }, 500);
      const shot = {
        ...state.rom.all_user_screenshots[0],
        id: 100 + state.rom.all_user_screenshots.length,
        rom_id: 1,
        user_id: 1,
        username: "Fixture owner",
        is_public: false,
        download_path: "/fixture/upload.svg",
      };
      state.rom.all_user_screenshots.unshift(shot);
      return json(shot);
    }
    if (
      /^\/api\/screenshots\/\d+$/.test(path) &&
      ["PUT", "DELETE"].includes(req.method())
    ) {
      const id = Number(path.split("/").pop());
      if (req.method() === "DELETE")
        state.rom.all_user_screenshots = state.rom.all_user_screenshots.filter(
          (s) => s.id !== id,
        );
      else
        Object.assign(
          state.rom.all_user_screenshots.find((s) => s.id === id)!,
          req.postDataJSON(),
        );
      return json({});
    }
    if (
      (path === "/api/roms/1/media/placements" && req.method() === "POST") ||
      (/^\/api\/roms\/1\/media\/placements\/\d+$/.test(path) &&
        req.method() === "DELETE") ||
      (/^\/api\/roms\/1\/media\/\d+$/.test(path) &&
        req.method() === "DELETE") ||
      (path === "/api/roms/1/media/refresh" && req.method() === "POST")
    ) {
      if (state.mediaBarrier) await state.mediaBarrier;
      if (state.conflict) {
        state.conflict = false;
        state.rom.updated_at = "2026-10-23T11:00:00Z";
        return json({ detail: "Version conflict" }, 409);
      }
      if (path.includes("placements")) {
        const body =
          req.method() === "POST"
            ? req.postDataJSON()
            : {
                media_id: Number(path.split("/").pop()),
                surface: url.searchParams.get("surface"),
              };
        const item = state.rom.owned_media.find((m) => m.id === body.media_id)!;
        if (req.method() === "DELETE")
          item.placements = item.placements.filter(
            (p) => p.surface !== body.surface,
          );
        else
          item.placements.push({
            surface: body.surface,
            position: state.rom.owned_media.filter((m) =>
              m.placements.some((p) => p.surface === body.surface),
            ).length,
          } as never);
      } else if (req.method() === "DELETE")
        state.rom.owned_media = state.rom.owned_media.filter(
          (m) => m.id !== Number(path.split("/").pop()),
        );
      return json(state.rom);
    }
    state.unexpected.push(req.method() + " " + path);
    return route.abort();
  });
  await page.goto("/rom/1?tab=media&subtab=screenshots&fixture=preserved");
  await expect(page.locator(".za-shots__toolbar button"))
    .toBeVisible()
    .catch((error) => {
      throw new Error(error.message + "\n" + state.errors.join("\n"));
    });
  return state;
}
export const file = (name: string) => ({
  name,
  mimeType: "image/png",
  buffer: Buffer.from("fixture image upload"),
});
export const shots = (page: Page) => page.locator(".za-shots");
export const card = (page: Page, key: string) =>
  shots(page).locator(`[data-shot-key="${key}"]`);
export const upload = (page: Page) => page.locator(".za-shots__toolbar button");
export async function pick(page: Page, names: string[]) {
  const chooser = page.waitForEvent("filechooser");
  await upload(page).click();
  await (await chooser).setFiles(names.map(file));
}
