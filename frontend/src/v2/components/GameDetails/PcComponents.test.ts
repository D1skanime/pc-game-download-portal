import { flushPromises, mount } from "@vue/test-utils";
import mitt from "mitt";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PcComponentSchema } from "@/__generated__";
import { ROUTES } from "@/plugins/router";
import PcComponents from "./PcComponents.vue";

vi.mock("@/services/api", () => ({
  default: { post: vi.fn() },
}));

const { push, resumeSession, snackbarError } = vi.hoisted(() => ({
  push: vi.fn(),
  resumeSession: vi.fn(),
  snackbarError: vi.fn(),
}));

vi.mock("@/v2/composables/useBrowserDownloadQueue", () => ({
  isEnhancedDownloadSupported: () => false,
  useBrowserDownloadQueue: () => ({
    items: { value: [] },
    sessionId: { value: null },
    pause: vi.fn(),
    cancel: vi.fn(),
    clearTerminal: vi.fn(),
    resume: vi.fn(),
    resumeSession,
  }),
}));

vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ error: snackbarError }),
}));

vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRouter: () => ({ push }),
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string) =>
      ({
        "rom.pc-components": "PC components",
        "rom.game-downloads": "Game downloads",
        "rom.pc-base-game": "Main game",
        "rom.pc-updates": "Updates",
        "rom.category-dlc": "DLC",
        "rom.pc-hotfixes": "Hotfixes",
        "rom.pc-language-packs": "Language packs",
        "rom.pc-extras": "Extras",
        "rom.pc-needs-classification": "Needs classification",
        "rom.download-expired":
          "This download has expired. Start a new download.",
        "rom.download-failed-description": "Download failed.",
      })[key] ?? key,
  }),
}));

const componentGroups = [
  {
    id: 1,
    relative_path: "Game",
    kind: "base",
    manifest_members: [
      {
        id: 1,
        relative_path: "Game/game.exe",
        size_bytes: 1024,
        sha256: "a".repeat(64),
      },
    ],
  },
  { id: 2, relative_path: "Updates", kind: "update", manifest_members: [] },
  { id: 3, relative_path: "DLC", kind: "dlc", manifest_members: [] },
  { id: 4, relative_path: "Hotfix", kind: "hotfix", manifest_members: [] },
  {
    id: 5,
    relative_path: "Language",
    kind: "language_pack",
    manifest_members: [],
  },
  { id: 6, relative_path: "Extras", kind: "extra", manifest_members: [] },
  { id: 7, relative_path: "Unknown", kind: "unresolved", manifest_members: [] },
] satisfies PcComponentSchema[];

describe("PcComponents", () => {
  beforeEach(() => {
    push.mockReset();
    resumeSession.mockReset();
    snackbarError.mockReset();
  });

  it("uses the player-facing game downloads heading", () => {
    const wrapper = mount(PcComponents, {
      props: { components: [], romId: 1 },
    });

    expect(wrapper.get(".pc-components__heading").text()).toBe(
      "Game downloads",
    );
  });

  it("keeps the download action aligned with the component content", () => {
    const wrapper = mount(PcComponents, {
      props: { components: [], romId: 1 },
    });

    expect(
      wrapper.get("[data-testid='download-components']").classes(),
    ).toContain("align-self-start");
  });

  it("uses the main game label instead of the technical base folder name", () => {
    const wrapper = mount(PcComponents, {
      props: {
        components: [
          {
            id: 1,
            relative_path: "base",
            kind: "base",
            manifest_members: [],
          },
        ],
        romId: 1,
      },
      global: {
        stubs: {
          RCollapsible: {
            props: ["title"],
            template: "<section :data-title='title'><slot /></section>",
          },
        },
      },
    });

    expect(
      wrapper.get("[data-testid='pc-component-base']").attributes("data-title"),
    ).toBe("Main game");
  });

  it("opens the shared matcher only for classified component targets", async () => {
    const emitter = mitt();
    const showMatcher = vi.fn();
    emitter.on("showPcMatchRomDialog", showMatcher);
    const wrapper = mount(PcComponents, {
      props: { components: componentGroups, romId: 1 },
      global: {
        provide: { emitter },
        stubs: {
          RCollapsible: false,
        },
      },
    });

    expect(wrapper.text()).toContain("Main game");
    expect(wrapper.text()).toContain("Needs classification");
    expect(
      wrapper
        .findAll("[data-testid='pc-component-group']")
        .map((group) => group.get(".pc-components__group-heading").text()),
    ).toEqual([
      "Main game",
      "Updates",
      "DLC",
      "Hotfixes",
      "Language packs",
      "Extras",
      "Needs classification",
    ]);

    await wrapper.get("[data-testid='pc-component-Game']").trigger("click");
    expect(wrapper.text()).toContain("Game/game.exe");
    expect(wrapper.text()).toContain("1 KB");
    expect(wrapper.text()).toContain("a".repeat(64));
    const launchers = wrapper.findAll(
      "[data-testid^='find-pc-component-metadata-']",
    );
    expect(launchers).toHaveLength(6);
    expect(
      wrapper.find("[data-testid='find-pc-component-metadata-7']").exists(),
    ).toBe(false);
    await launchers[2].trigger("click");
    expect(showMatcher).toHaveBeenCalledWith(
      expect.objectContaining({
        target: expect.objectContaining({
          kind: "component",
          romId: 1,
          componentId: 3,
          componentKind: "dlc",
        }),
      }),
    );
  });

  it("opens only DLC components at their parent-owned detail routes", async () => {
    const wrapper = mount(PcComponents, {
      props: { components: componentGroups, romId: 42 },
      global: {
        stubs: {
          RCollapsible: { template: "<section><slot /></section>" },
          RBtn: {
            template: "<button @click='$emit(\"click\")'><slot /></button>",
          },
        },
      },
    });

    const controls = wrapper.findAll("[data-testid='open-pc-dlc-details']");
    expect(controls).toHaveLength(1);
    await controls[0].trigger("click");

    expect(push).toHaveBeenCalledWith({
      name: ROUTES.PC_DLC,
      params: { rom: 42, component: 3 },
    });
    expect(wrapper.text()).not.toContain("DetailsUpdates");
  });

  it("passes the visible ROM identity into the download manager", () => {
    const wrapper = mount(PcComponents, {
      props: { components: componentGroups, romId: 99 },
      global: {
        stubs: {
          DownloadManager: {
            props: ["romId"],
            template:
              "<output data-testid='download-manager-rom'>{{ romId }}</output>",
          },
          RCollapsible: { template: "<section><slot /></section>" },
        },
      },
    });

    expect(wrapper.get("[data-testid='download-manager-rom']").text()).toBe(
      "99",
    );
  });

  it("explains that an expired manifest cannot be resumed", async () => {
    resumeSession.mockRejectedValue({
      isAxiosError: true,
      response: { status: 410, data: { detail: { code: "manifest_expired" } } },
    });
    const wrapper = mount(PcComponents, {
      props: { components: [], romId: 1 },
      global: {
        stubs: {
          DownloadManager: {
            emits: ["resume-session"],
            template:
              "<button data-testid=\"resume-session\" @click=\"$emit('resume-session', 'session', 'member')\">Resume</button>",
          },
        },
      },
    });

    await wrapper.get("[data-testid='resume-session']").trigger("click");
    await flushPromises();

    expect(snackbarError).toHaveBeenCalledWith(
      "This download has expired. Start a new download.",
    );
  });
});
