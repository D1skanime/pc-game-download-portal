import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { SimpleRom } from "@/stores/roms";
import GameActions from "./GameActions.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

vi.mock("@/v2/composables/useBreakpoint", () => ({
  useBreakpoint: () => ({ smAndDown: { value: false } }),
}));

vi.mock("@/v2/composables/useGridNav", () => ({
  useGridNav: vi.fn(),
}));

vi.mock("@/v2/composables/useGameActions", () => ({
  useGameActions: (getRom: () => SimpleRom) => ({
    canPlay: { value: false },
    canShowCopyDownloadLink: {
      get value() {
        const rom = getRom();
        return rom.platform_fs_slug !== "pc" && rom.platform_slug !== "pc";
      },
    },
    canShareQR: { value: false },
    canOpenInFlashpoint: { value: false },
    setScore: vi.fn(),
  }),
}));

const GameActionBtn = {
  props: ["action"],
  template: '<button class="action-btn" :data-action="action" />',
};

const MetricMenuBtn = { template: '<div class="metric-btn" />' };

function makeRom(platform: Partial<SimpleRom>): SimpleRom {
  return {
    id: 1,
    name: "Chrono Trigger",
    fs_name_no_ext: "Chrono Trigger",
    platform_slug: "snes",
    platform_fs_slug: "snes",
    ...platform,
  } as SimpleRom;
}

function mountActions(platform: Partial<SimpleRom>) {
  return mount(GameActions, {
    props: { rom: makeRom(platform) },
    global: { stubs: { GameActionBtn, MetricMenuBtn } },
  });
}

function actionNames(wrapper: ReturnType<typeof mountActions>) {
  return wrapper
    .findAll(".action-btn")
    .map((button) => button.attributes("data-action"));
}

describe("GameActions - copy-link visibility", () => {
  it("hides copy-link while keeping download and other actions for a real PC ROM", () => {
    const wrapper = mountActions({
      platform_slug: "win",
      platform_fs_slug: "pc",
    });

    expect(actionNames(wrapper)).not.toContain("copy-link");
    expect(actionNames(wrapper)).toEqual(
      expect.arrayContaining([
        "download",
        "favorite",
        "collection",
        "status",
        "more",
      ]),
    );
  });

  it("keeps copy-link for a non-PC ROM", () => {
    const wrapper = mountActions({
      platform_slug: "snes",
      platform_fs_slug: "snes",
    });

    expect(actionNames(wrapper)).toContain("copy-link");
    expect(actionNames(wrapper)).toContain("download");
  });
});
