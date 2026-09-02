import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { IGDBRelatedGame } from "@/__generated__";
import type { DetailedRom } from "@/stores/roms";
import OverviewTab from "./OverviewTab.vue";

vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("@/stores/collections", () => ({ default: () => ({}) }));
vi.mock("@/v2/composables/useWebpSupport", () => ({
  useWebpSupport: () => ({ toWebp: (value: string) => value }),
}));

const rom = {
  id: 42,
  metadatum: undefined,
  url_cover: null,
  fs_name: "parent-game",
  fs_size_bytes: 0,
  crc_hash: null,
  md5_hash: null,
  sha1_hash: null,
  ra_hash: null,
  has_simple_single_file: false,
  files: [],
} as Partial<DetailedRom> as DetailedRom;
const dlc = {
  id: 123,
  name: "Phantom Liberty",
  slug: "cyberpunk-2077-phantom-liberty",
  type: "dlc",
  cover_url: "",
} as IGDBRelatedGame;

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
