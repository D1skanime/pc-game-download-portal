import { flushPromises, shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { computed, ref } from "vue";
import FilesTab from "@/v2/components/GameDetails/FilesTab/FilesTab.vue";
import ManualSubtab from "@/v2/components/GameDetails/ManualSubtab.vue";
import MediaTab from "@/v2/components/GameDetails/MediaTab.vue";
import ScreenshotsSubtab from "@/v2/components/GameDetails/ScreenshotsSubtab.vue";

const mocks = vi.hoisted(() => ({
  uploadManuals: vi.fn(),
  uploadGalleryScreenshots: vi.fn(),
  deleteScreenshot: vi.fn(),
  setScreenshotVisibility: vi.fn(),
}));

vi.mock("pinia", async (importOriginal) => {
  const actual = await importOriginal<typeof import("pinia")>();
  return {
    ...actual,
    storeToRefs: (store: { user: unknown }) => ({ user: ref(store.user) }),
  };
});

vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("vue-router", () => ({
  useRoute: () => ({ params: { platform: "pc" }, path: "/pc/game", query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));
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
vi.mock("@/stores/roms", () => ({
  default: () => ({ update: vi.fn(), currentRom: null }),
}));
vi.mock("@/stores/upload", () => ({ default: () => ({ reset: vi.fn() }) }));
vi.mock("@/stores/auth", () => ({ default: () => ({ user: { id: 11 } }) }));
vi.mock("@/utils", () => ({
  FRONTEND_RESOURCES_PATH: "/resources",
  getDownloadLink: vi.fn(() => "/download"),
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
    expect(screenshotPanels[0].attributes("data-deletable")).toBe("false");
    expect(screenshotPanels[1].attributes("data-deletable")).toBe("true");
    expect(screenshotPanels[1].attributes("data-togglable")).toBe("true");
    expect(screenshots.findAll("[data-dropzone]")).toHaveLength(1);

    const media = mountPanel(MediaTab);
    await flushPromises();
    expect(media.findAll("[data-dropzone]")).toHaveLength(0);
    expect(media.html()).not.toContain("common.upload");
  });
});
