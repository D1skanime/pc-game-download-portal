import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { DetailedRom, SimpleRom } from "@/stores/roms";
import OverviewTab from "./OverviewTab.vue";

vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("@/stores/collections", () => ({ default: () => ({}) }));
vi.mock("@/v2/composables/useWebpSupport", () => ({
  useWebpSupport: () => ({ toWebp: (value: string) => value }),
}));

const rom = {
  id: 42,
  metadatum: null,
  url_cover: null,
  files: [],
} as DetailedRom;
const dlc = {
  id: 123,
  name: "Phantom Liberty",
  slug: "cyberpunk-2077-phantom-liberty",
  type: "dlc",
  cover_url: null,
} as SimpleRom;

describe("OverviewTab", () => {
  it("passes its parent ROM id to the local DLC grid", () => {
    const wrapper = mount(OverviewTab, {
      props: {
        rom,
        summary: null,
        sections: [],
        playerCount: null,
        userCollections: [],
        hltb: null,
        lastPlayed: null,
        revision: null,
        screenshots: [],
        expansions: [],
        dlcs: [dlc],
        localDlcComponentIds: { 123: 7 },
        remakes: [],
        remasters: [],
        similarGames: [],
        parentRomId: 42,
      },
      global: {
        stubs: {
          RCollapsible: { template: "<section><slot /></section>" },
          RelatedGamesGrid: {
            props: ["parentRomId"],
            template:
              "<div data-testid='dlc-grid' :data-parent-rom-id='parentRomId' />",
          },
        },
      },
    });

    expect(
      wrapper.get("[data-testid='dlc-grid']").attributes("data-parent-rom-id"),
    ).toBe("42");
  });
});
