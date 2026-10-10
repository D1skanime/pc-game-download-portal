import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { IGDBRelatedGame } from "@/__generated__";
import type { DetailedRom } from "@/stores/roms";
import OverviewTab from "./OverviewTab.vue";

const permissionState = vi.hoisted(() => ({ value: true }));

vi.mock("pinia", async (importOriginal) => ({
  ...(await importOriginal<typeof import("pinia")>()),
  getActivePinia: () => ({}),
}));
vi.mock("@/v2/composables/useCan", () => ({
  useCan: () => permissionState,
}));
vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key, locale: { value: "en-US" } }),
}));
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

const pcMetadataRom = {
  ...rom,
  metadatum: {
    rom_id: 42,
    genres: [],
    franchises: [],
    collections: [],
    companies: [],
    main_developer: "CD Projekt Red",
    publishers: ["CD Projekt"],
    themes: ["Cyberpunk"],
    game_modes: [],
    pc_release_date: 1725148800,
    first_release_date: 1590969600000,
    age_ratings: [],
    player_count: "",
    average_rating: null,
  },
} as Partial<DetailedRom> as DetailedRom;
const dlc = {
  id: 123,
  name: "Phantom Liberty",
  slug: "cyberpunk-2077-phantom-liberty",
  type: "dlc",
  cover_url: "",
} as IGDBRelatedGame;

describe("OverviewTab", () => {
  it("renders a local DLC overview section without IGDB suggestions", () => {
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
        dlcs: [],
        localDlcCandidates: [
          {
            igdbId: 123,
            componentId: 7,
            name: "Phantom Liberty",
            coverUrl: "/assets/romm/resources/roms/42/components/7/cover.webp",
          },
        ],
        localExpansionCandidates: [],
        remakes: [],
        remasters: [],
        similarGames: [],
        parentRomId: 42,
      },
      global: {
        stubs: {
          RCollapsible: { template: "<section><slot /></section>" },
          RelatedGamesGrid: {
            props: ["parentRomId", "localCandidates"],
            template:
              "<div data-testid='dlc-grid' :data-parent-rom-id='parentRomId' :data-local-count='localCandidates.length' />",
          },
        },
      },
    });

    expect(
      wrapper.get("[data-testid='dlc-grid']").attributes("data-parent-rom-id"),
    ).toBe("42");
    expect(
      wrapper.get("[data-testid='dlc-grid']").attributes("data-local-count"),
    ).toBe("1");
  });

  it("prefers the PC release and renders distinct PC metadata groups", () => {
    const wrapper = mount(OverviewTab, {
      props: {
        rom: pcMetadataRom,
        summary: null,
        sections: [],
        playerCount: null,
        userCollections: [],
        hltb: null,
        lastPlayed: null,
        revision: null,
        screenshots: [],
        expansions: [],
        dlcs: [],
        localDlcCandidates: [],
        localExpansionCandidates: [],
        remakes: [],
        remasters: [],
        similarGames: [],
        parentRomId: 42,
      },
    });

    expect(wrapper.text()).toContain("rom.pc-release");
    expect(wrapper.text()).toContain("2024");
    expect(wrapper.text()).not.toContain("2020");
    expect(wrapper.text()).toContain("rom.main-developer");
    expect(wrapper.text()).toContain("CD Projekt Red");
    expect(wrapper.text()).toContain("rom.publishers");
    expect(wrapper.text()).toContain("CD Projekt");
    expect(wrapper.text()).toContain("rom.themes");
    expect(wrapper.text()).toContain("Cyberpunk");
  });

  it("renders selected owned screenshots through the protected media endpoint", () => {
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
        screenshots: [
          "/api/roms/42/media/7/content",
          "https://images.igdb.com/provider-only.webp",
        ],
        expansions: [],
        dlcs: [],
        localDlcCandidates: [],
        localExpansionCandidates: [],
        remakes: [],
        remasters: [],
        similarGames: [],
        parentRomId: 42,
      },
    });

    expect(wrapper.html()).toContain("/api/roms/42/media/7/content");
    expect(wrapper.html()).not.toContain("provider-only.webp");
    expect(wrapper.text()).not.toContain("rom.pc-release");
    expect(wrapper.text()).not.toContain("rom.main-developer");
  });
  it("keeps the resolved description read-only until the authorized pencil is activated", async () => {
    permissionState.value = true;
    const editableRom = {
      ...rom,
      updated_at: "version-7",
      manual_metadata: { descriptions: { en: "Manual text" } },
      steam_metadata: { fields: ["summary"] },
    } as Partial<DetailedRom> as DetailedRom;
    const wrapper = mount(OverviewTab, {
      props: {
        rom: editableRom,
        summary: "Resolved description",
        sections: [],
        playerCount: null,
        userCollections: [],
        hltb: null,
        lastPlayed: null,
        revision: null,
        screenshots: [],
        expansions: [],
        dlcs: [],
        localDlcCandidates: [],
        localExpansionCandidates: [],
        remakes: [],
        remasters: [],
        similarGames: [],
        parentRomId: 42,
      },
      global: {
        stubs: {
          RBtn: {
            inheritAttrs: false,
            template:
              "<button v-bind='$attrs' @click='$emit(\"click\")'><slot /></button>",
          },
          RDialog: {
            props: ["modelValue"],
            template:
              "<div v-if='modelValue' data-testid='description-dialog'><slot name='header' /><slot name='content' /></div>",
          },
          LocalizedDescriptionEditor: {
            name: "LocalizedDescriptionEditor",
            props: [
              "romId",
              "expectedVersion",
              "manualMetadata",
              "steamMetadata",
              "fallbackDescription",
              "providerSummaryIsAuthoritative",
            ],
            template: "<div data-testid='localized-editor' />",
          },
        },
      },
    });

    expect(wrapper.get(".overview-tab__summary").text()).toBe(
      "Resolved description",
    );
    expect(wrapper.find("[data-testid='localized-editor']").exists()).toBe(
      false,
    );
    expect(
      wrapper
        .get("[data-testid='overview-description-edit']")
        .attributes("aria-label"),
    ).toBe("common.edit");

    await wrapper
      .get("[data-testid='overview-description-edit']")
      .trigger("click");

    expect(wrapper.find("[data-testid='localized-editor']").exists()).toBe(
      true,
    );
    expect(
      wrapper.getComponent({ name: "LocalizedDescriptionEditor" }).props(),
    ).toMatchObject({
      romId: editableRom.id,
      expectedVersion: "version-7",
      manualMetadata: editableRom.manual_metadata,
      steamMetadata: editableRom.steam_metadata,
      fallbackDescription: editableRom.summary,
      providerSummaryIsAuthoritative: true,
    });
  });

  it("keeps the description read-only without an edit grant", () => {
    permissionState.value = false;
    const wrapper = mount(OverviewTab, {
      props: {
        rom,
        summary: "Visible without permission",
        sections: [],
        playerCount: null,
        userCollections: [],
        hltb: null,
        lastPlayed: null,
        revision: null,
        screenshots: [],
        expansions: [],
        dlcs: [],
        localDlcCandidates: [],
        localExpansionCandidates: [],
        remakes: [],
        remasters: [],
        similarGames: [],
        parentRomId: 42,
      },
      global: {
        stubs: {
          RBtn: { template: "<button><slot /></button>" },
          RDialog: {
            props: ["modelValue"],
            template: "<div v-if='modelValue'><slot /></div>",
          },
        },
      },
    });

    expect(wrapper.get(".overview-tab__summary").text()).toBe(
      "Visible without permission",
    );
    expect(
      wrapper.find("[data-testid='overview-description-edit']").exists(),
    ).toBe(false);
    permissionState.value = true;
  });
});
