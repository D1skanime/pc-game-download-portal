import { flushPromises, shallowMount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { computed, ref } from "vue";
import UserMenu from "@/v2/components/AppShell/UserMenu.vue";
import SetupStepPlatforms from "@/v2/components/Auth/SetupStepPlatforms.vue";
import FilesTab from "@/v2/components/GameDetails/FilesTab/FilesTab.vue";
import ManualSubtab from "@/v2/components/GameDetails/ManualSubtab.vue";
import MediaTab from "@/v2/components/GameDetails/MediaTab.vue";
import PatcherTab from "@/v2/components/GameDetails/PatcherTab.vue";
import ScreenshotsSubtab from "@/v2/components/GameDetails/ScreenshotsSubtab.vue";
import SettingsSidebar from "@/v2/components/Settings/SettingsSidebar.vue";
import Setup from "@/v2/views/Auth/Setup.vue";
import Home from "@/v2/views/Home.vue";

const mocks = vi.hoisted(() => ({
  uploadManuals: vi.fn(),
  uploadGalleryScreenshots: vi.fn(),
  deleteScreenshot: vi.fn(),
  setScreenshotVisibility: vi.fn(),
  createPlatforms: vi.fn(),
  createUser: vi.fn(),
}));

vi.mock("pinia", async (importOriginal) => {
  const actual = await importOriginal<typeof import("pinia")>();
  return {
    ...actual,
    storeToRefs: (store: Record<string, unknown>) =>
      Object.fromEntries(
        Object.entries(store)
          .filter(([, value]) => typeof value !== "function")
          .map(([key, value]) => [key, ref(value)]),
      ),
  };
});

vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRoute: () => ({
      params: { platform: "pc" },
      path: "/pc/game",
      query: {},
    }),
    useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  };
});
vi.mock("@/v2/composables/useCan", () => ({
  useCan: () => computed(() => true),
}));
vi.mock("@/v2/composables/useConfirm", () => ({
  useConfirm: () => vi.fn().mockResolvedValue(true),
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ error: vi.fn(), success: vi.fn(), warning: vi.fn() }),
}));
vi.mock("@/services/api/rom", () => ({
  default: {
    downloadRom: vi.fn(),
    getRom: vi.fn().mockResolvedValue({ data: {} }),
    getSoundtrackMetadata: vi.fn().mockResolvedValue({ data: [] }),
    redownloadManual: vi.fn(),
    removeManual: vi.fn(),
    uploadManuals: mocks.uploadManuals,
  },
}));
vi.mock("@/services/api/screenshot", () => ({
  default: {
    uploadGalleryScreenshots: mocks.uploadGalleryScreenshots,
    deleteScreenshot: mocks.deleteScreenshot,
    setScreenshotVisibility: mocks.setScreenshotVisibility,
  },
}));
vi.mock("@/services/api/setup", () => ({
  default: {
    getLibraryInfo: vi.fn().mockResolvedValue({
      data: {
        detected_structure: "structure_a",
        existing_platforms: [],
        supported_platforms: [],
      },
    }),
    createPlatforms: mocks.createPlatforms,
  },
}));
vi.mock("@/stores/roms", () => ({
  default: () => ({
    update: vi.fn(),
    currentRom: null,
    recentRoms: [],
    continuePlayingRoms: [],
    fetchRecentRoms: vi.fn().mockResolvedValue(undefined),
    fetchContinuePlayingRoms: vi.fn().mockResolvedValue(undefined),
  }),
}));
vi.mock("@/stores/platforms", () => ({
  default: () => ({
    allPlatforms: [],
    filledPlatforms: [],
    fetchingPlatforms: false,
    fetchPlatforms: vi.fn(),
  }),
}));
vi.mock("@/stores/collections", () => ({
  default: () => ({
    allCollections: [],
    smartCollections: [],
    virtualCollections: [],
    favoriteCollection: null,
    fetchingCollections: false,
    fetchingSmartCollections: false,
    fetchingVirtualCollections: false,
    fetchCollections: vi.fn(),
    fetchSmartCollections: vi.fn(),
    fetchVirtualCollections: vi.fn(),
  }),
}));
vi.mock("@/stores/upload", () => ({ default: () => ({ reset: vi.fn() }) }));
vi.mock("@/stores/auth", () => ({
  default: () => ({
    user: { id: 11 },
    scopes: ["me.write", "platforms.write", "roms.write"],
  }),
}));
vi.mock("@/stores/heartbeat", () => ({
  default: () => ({ value: { FRONTEND: { DISABLE_LOGS_VIEWER: false } } }),
}));
vi.mock("@/composables/useUISettings", () => ({
  useUISettings: () => ({
    showHomeWidgets: ref(false),
    showRecentRoms: ref(false),
    showContinuePlaying: ref(false),
    showPlatforms: ref(false),
    showCollections: ref(false),
    showSmartCollections: ref(false),
    showVirtualCollections: ref(false),
    virtualCollectionType: ref("recent"),
  }),
}));
vi.mock("@/v2/composables/useGridNav", () => ({ useGridNav: vi.fn() }));
vi.mock("@/v2/composables/useWebpSupport", () => ({
  useWebpSupport: () => ({
    supportsWebp: ref(false),
    toWebp: (value: string) => value,
  }),
}));
vi.mock("@/utils", () => ({
  FRONTEND_RESOURCES_PATH: "/resources",
  getDownloadLink: vi.fn(() => "/download"),
  formatBytes: vi.fn((value: number) => String(value)),
}));

const rom = {
  id: 7,
  platform_id: 2,
  platform_slug: "pc",
  fs_name: "example",
  full_path: "pc/example",
  name: "Example",
  updated_at: "2026-08-13T00:00:00Z",
  has_simple_single_file: false,
  has_manual: true,
  path_manual: "pc/example/manual.pdf",
  url_manual: "https://example.invalid/manual.pdf",
  has_soundtrack: true,
  files: [
    {
      id: 101,
      file_name: "game.bin",
      full_path: "pc/example/game.bin",
      category: "game",
    },
    {
      id: 102,
      file_name: "guide.pdf",
      full_path: "pc/example/manual/guide.pdf",
      category: "manual",
    },
    {
      id: 103,
      file_name: "track.flac",
      full_path: "pc/example/soundtrack/track.flac",
      category: "soundtrack",
    },
    {
      id: 104,
      file_name: "shared.png",
      full_path: "pc/example/screenshots/shared.png",
      category: "screenshot",
    },
  ],
  all_user_screenshots: [
    {
      id: 201,
      user_id: 11,
      download_path: "/screenshots/201/content",
      is_public: false,
    },
  ],
};

const stubs = {
  RBtn: {
    props: ["disabled"],
    emits: ["click"],
    template:
      '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
  },
  RCheckbox: { template: '<input type="checkbox" />' },
  RDropzone: {
    emits: ["files"],
    template:
      '<section data-dropzone><slot /><slot name="actions" /></section>',
  },
  REmptyState: { template: "<div data-empty />" },
  RIcon: { template: "<i />" },
  RSelect: { template: "<select data-manual-select />" },
  RTooltip: { template: "<span />" },
  FileRow: { template: "<li />" },
  FilesSummary: { template: "<div />" },
  MarkdownViewer: {
    props: ["deletable"],
    template: '<div data-manual-viewer :data-deletable="deletable" />',
  },
  PdfViewer: {
    props: ["deletable"],
    template: '<div data-manual-viewer :data-deletable="deletable" />',
  },
  SoundtrackPanel: {
    props: ["deletable"],
    template: '<div data-soundtrack :data-deletable="deletable" />',
  },
  ScreenshotsTab: {
    props: ["deletable", "togglable"],
    template:
      '<div data-screenshots :data-deletable="deletable" :data-togglable="togglable" />',
  },
};

function mountPanel(component: object) {
  return shallowMount(component, { props: { rom }, global: { stubs } });
}

describe("maximum-grant source mutation controls", () => {
  it("keeps generic ROM files read and download only", () => {
    const wrapper = mountPanel(FilesTab);
    expect(wrapper.html()).not.toContain("common.upload");
    expect(wrapper.html()).not.toContain("common.delete");
    expect(wrapper.findAll("li")).toHaveLength(9);
  });

  it("keeps manuals resources-only", () => {
    const wrapper = mountPanel(ManualSubtab);
    expect(wrapper.find("[data-manual-select]").exists()).toBe(false);
    expect(wrapper.html()).toContain("common.upload");
    expect(wrapper.html()).not.toContain("guide.pdf");
    expect(wrapper.html()).not.toContain("rom.convert-to-folder");
  });

  it("keeps shared screenshots and soundtracks read-only while assets remain mutable", async () => {
    const screenshots = mountPanel(ScreenshotsSubtab);
    const screenshotPanels = screenshots.findAll("[data-screenshots]");
    expect("data-deletable" in screenshotPanels[0].attributes()).toBe(false);
    expect("data-deletable" in screenshotPanels[1].attributes()).toBe(true);
    expect("data-togglable" in screenshotPanels[1].attributes()).toBe(true);
    expect(screenshots.findAll("[data-dropzone]")).toHaveLength(1);

    const media = mountPanel(MediaTab);
    await flushPromises();
    expect(media.findAll("[data-dropzone]")).toHaveLength(0);
    expect(media.html()).not.toContain("common.upload");
  });
});

const routeStub = {
  props: ["to"],
  template: '<a :data-route="to && to.name"><slot /></a>',
};

function source(path: string) {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

describe("external source mutation authority inventory", () => {
  it("renders no upload route in Settings under maximum grants", () => {
    const wrapper = shallowMount(SettingsSidebar, {
      global: {
        stubs: {
          RouterLink: routeStub,
          RChip: true,
          RIcon: true,
        },
      },
    });

    expect(wrapper.find('[data-route="upload"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("common.upload-roms");
  });

  it("renders the empty Home without an upload route", async () => {
    const wrapper = shallowMount(Home, {
      global: {
        stubs: {
          RouterLink: routeStub,
          RChip: true,
          RDivider: true,
          RIcon: true,
          RSkeletonBlock: true,
        },
      },
    });

    await flushPromises();
    expect(wrapper.find('[data-route="upload"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("common.upload-roms");
  });

  it("renders detected setup state without platform creation selection", () => {
    const wrapper = shallowMount(SetupStepPlatforms, {
      props: {
        libraryInfo: {
          detected_structure: "structure_a",
          existing_platforms: [{ fs_slug: "pc", rom_count: 2 }],
          supported_platforms: [
            {
              id: 1,
              slug: "pc",
              fs_slug: "pc",
              name: "PC",
              display_name: "PC",
            },
          ],
        },
        selectedNewPlatforms: [],
      },
      global: {
        stubs: {
          RCheckbox: {
            template: '<input data-platform-create type="checkbox" />',
          },
        },
      },
    });

    expect(wrapper.find("[data-platform-create]").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("setup.select-platforms");
  });

  it("removes upload and creation services without replacing them with raw clients", () => {
    const files = {
      rom: source("src/services/api/rom.ts"),
      platform: source("src/services/api/platform.ts"),
      setup: source("src/services/api/setup.ts"),
      upload: source("src/v2/views/Upload.vue"),
      setupView: source("src/v2/views/Auth/Setup.vue"),
      platformView: source("src/v2/views/Gallery/Platform.vue"),
      userMenu: source("src/v2/components/AppShell/UserMenu.vue"),
    };

    expect(files.rom).not.toMatch(/\buploadRoms\b/);
    expect(files.platform).not.toMatch(/\buploadPlatform\b/);
    expect(files.setup).not.toMatch(/\bcreatePlatforms\b/);
    expect(files.upload).not.toMatch(/api\.(post|put|patch|delete)\s*\(/);
    expect(files.setupView).not.toMatch(/createPlatforms|selectedNewPlatforms/);
    expect(files.platformView).not.toContain("ROUTES.UPLOAD");
    expect(files.userMenu).not.toContain("ROUTES.UPLOAD");
  });

  it("classifies the retained raw patch call by method, route, and authority", () => {
    const patcher = source("src/v2/components/GameDetails/PatcherTab.vue");
    const endpoint = source("../backend/endpoints/roms/patch.py");
    const inventory = [
      {
        method: "POST",
        route: "/roms/{id}/patch",
        input: "READ/external",
        output: "PATCH/TEMP",
      },
    ];

    expect(patcher).toMatch(
      /api\.post\(\s*`\/roms\/\$\{selectedRomFile\.value\.id\}\/patch`/,
    );
    expect(endpoint).toContain(
      "StorageOperation.READ, legacy_external_storage",
    );
    expect(endpoint).toContain("StorageOperation.PATCH");
    expect(endpoint).toContain("OwnedStorageKind.TEMP");
    expect(inventory).toEqual([
      expect.objectContaining({
        method: "POST",
        route: "/roms/{id}/patch",
        input: "READ/external",
        output: "PATCH/TEMP",
      }),
    ]);
  });

  it("keeps only local browser download on the patch surface", () => {
    const patcher = source("src/v2/components/GameDetails/PatcherTab.vue");
    expect(patcher).not.toMatch(
      /saveIntoRomM|uploadRoms|scanPlatform|platformId/,
    );
    expect(patcher).toMatch(/URL\.createObjectURL|downloadPatchedFile/);
  });
});
