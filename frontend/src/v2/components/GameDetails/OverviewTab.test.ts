import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { DetailedRom } from "@/stores/roms";
import { resolveDescription } from "@/v2/composables/useManualDescription";
import OverviewTab from "./OverviewTab.vue";
import ScreenshotsTab from "./ScreenshotsTab.vue";

const permissionState = vi.hoisted(() => ({ value: true }));
const activeLocale = vi.hoisted(() => ({ value: "en-US" }));

vi.mock("pinia", async (importOriginal) => ({
  ...(await importOriginal<typeof import("pinia")>()),
  getActivePinia: () => ({}),
}));
vi.mock("@/v2/composables/useCan", () => ({
  useCan: () => permissionState,
}));
vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, string>) =>
      key +
      (key.startsWith("rom.description-") && params
        ? JSON.stringify(params)
        : ""),
    locale: activeLocale,
  }),
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
  platform_id: 4,
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

describe("OverviewTab", () => {
  it("keeps a permitted edit action for legacy-only empty data", () => {
    const wrapper = mount(OverviewTab, {
      props: {
        rom: { ...rom, summary: "Unknown legacy prose" },
        description: resolveDescription({ provider: null, locale: "de-DE" }),
        parentRomId: 42,
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
      },
      global: { stubs: { RBtn: { template: "<button />" } } },
    });
    expect(wrapper.text()).not.toContain("Unknown legacy prose");
    expect(wrapper.text()).toContain("rom.description-empty");
    expect(
      wrapper.find("[data-testid='overview-description-edit']").exists(),
    ).toBe(true);
  });

  it.each([
    ["manual", "en", "english_fallback"],
    ["steam", "en", "english_fallback"],
    ["screenscraper", "de", "base"],
  ] as const)(
    "renders safe %s prose with actual %s language and %s provenance",
    async (source, resolvedLocale, match) => {
      const text = "<img src=x onerror=alert(1)>";
      const description = {
        text,
        requestedLocale: "de-DE",
        resolvedLocale,
        source,
        match,
      };
      const wrapper = mount(OverviewTab, {
        props: {
          rom,
          description,
          parentRomId: 42,
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
        },
      });
      expect(wrapper.get(".overview-tab__summary").text()).toBe(text);
      expect(wrapper.get(".overview-tab__summary").attributes("lang")).toBe(
        resolvedLocale,
      );
      expect(wrapper.find("img").exists()).toBe(false);
      expect(wrapper.text()).toContain(
        resolvedLocale === "en" ? "English" : "German",
      );
      expect(wrapper.text()).toContain(
        source === "steam"
          ? "Steam"
          : source === "screenscraper"
            ? "ScreenScraper"
            : "rom.description-manual-label",
      );
      expect(wrapper.text()).toContain(
        match === "english_fallback"
          ? "rom.description-language-fallback"
          : "rom.description-source-localized",
      );
      await wrapper.setProps({
        rom: { ...rom, id: 99 },
        description: resolveDescription({ provider: null }),
      });
      expect(wrapper.text()).not.toContain(text);
    },
  );

  it("renders a local DLC overview section without IGDB suggestions", () => {
    const wrapper = mount(OverviewTab, {
      props: {
        rom,
        description: resolveDescription({ provider: null }),
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
        description: resolveDescription({ provider: null }),
        sections: [
          {
            label: "rom.genres",
            filter: "genres",
            items: [{ id: "igdb:31", label: "Action" }],
          },
          {
            label: "rom.themes",
            filter: "themes",
            items: [{ id: "igdb:42", label: "Cyberpunk" }],
          },
          {
            label: "rom.main-developer",
            items: [{ id: "igdb:7", label: "CD Projekt Red" }],
          },
          {
            label: "rom.publishers",
            items: [{ id: "igdb:8", label: "CD Projekt" }],
          },
        ],
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

  it("formats the single PC release field for the selected locale", () => {
    const locales = ["en-US", "de-DE", "fr-FR"];
    const formattedDates = locales.map((selectedLocale) => {
      activeLocale.value = selectedLocale;
      const wrapper = mount(OverviewTab, {
        props: {
          rom: pcMetadataRom,
          description: resolveDescription({ provider: null }),
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
      const releaseRows = wrapper
        .findAll(".overview-tab__row")
        .filter((row) => row.text().includes("rom.pc-release"));

      expect(releaseRows).toHaveLength(1);
      return releaseRows[0].text();
    });

    expect(new Set(formattedDates).size).toBe(3);
    expect(formattedDates[0]).toContain(
      new Date(1725148800 * 1000).toLocaleDateString("en-US", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
    );
    expect(formattedDates[1]).toContain(
      new Date(1725148800 * 1000).toLocaleDateString("de-DE", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
    );
    expect(formattedDates[2]).toContain(
      new Date(1725148800 * 1000).toLocaleDateString("fr-FR", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
    );
  });

  it("keeps translated chip labels separate from canonical IDs and PC scope", () => {
    activeLocale.value = "de-DE";
    const wrapper = mount(OverviewTab, {
      props: {
        rom: pcMetadataRom,
        description: resolveDescription({ provider: null }),
        sections: [
          {
            label: "rom.genres",
            filter: "genres",
            items: [{ id: "igdb:31", label: "Action" }],
          },
          {
            label: "rom.themes",
            filter: "themes",
            items: [{ id: "igdb:42", label: "Cyberpunk" }],
          },
        ],
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
          RouterLink: {
            props: ["to"],
            template: "<a :href='JSON.stringify(to)'><slot /></a>",
          },
        },
      },
    });

    const links = wrapper.findAll("a.r-v2-det-infogrid__chip--link");
    expect(links).toHaveLength(2);
    expect(links[0].attributes("href")).toContain('"genres":"igdb:31"');
    expect(links[1].attributes("href")).toContain('"themes":"igdb:42"');
    for (const link of links) {
      expect(link.attributes("href")).toContain('"platforms":"4"');
      expect(link.attributes("href")).not.toContain("Action");
      expect(link.attributes("href")).not.toContain("Cyberpunk");
    }
  });

  it("does not invent role labels for a roleless provider company", () => {
    const wrapper = mount(OverviewTab, {
      props: {
        rom: pcMetadataRom,
        description: resolveDescription({ provider: null }),
        sections: [
          {
            label: "rom.companies",
            items: [{ id: "igdb:99", label: "Neutral Provider Company" }],
          },
        ],
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

    expect(wrapper.text()).toContain("Neutral Provider Company");
    expect(wrapper.text()).not.toContain("rom.main-developer");
    expect(wrapper.text()).not.toContain("rom.publishers");
  });

  it("renders selected owned screenshots through the protected media endpoint", () => {
    const wrapper = mount(OverviewTab, {
      props: {
        rom,
        description: resolveDescription({ provider: null }),
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
  it("uses the Overview screenshot layout while keeping provider images excluded", () => {
    const wrapper = mount(OverviewTab, {
      props: {
        rom,
        description: resolveDescription({ provider: null }),
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

    expect(wrapper.findComponent(ScreenshotsTab).props("layout")).toBe(
      "overview",
    );
    expect(wrapper.findAll("img")).toHaveLength(1);
    expect(wrapper.html()).not.toContain("provider-only.webp");
  });

  it("renders a privacy-mode YouTube iframe and fallback link for a valid ID", () => {
    const wrapper = mount(OverviewTab, {
      props: {
        rom: {
          ...rom,
          manual_metadata: { youtube_video_id: "dQw4w9WgXcQ" },
        } as DetailedRom,
        description: resolveDescription({ provider: null }),
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

    const frame = wrapper.get("iframe");
    expect(frame.attributes("src")).toBe(
      "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
    );
    expect(frame.attributes("loading")).toBe("lazy");
    expect(wrapper.get("a.overview-tab__youtube-link").attributes("href")).toBe(
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    );
  });

  it("keeps the translated invalid-ID state without rendering an iframe", () => {
    const wrapper = mount(OverviewTab, {
      props: {
        rom: {
          ...rom,
          manual_metadata: { youtube_video_id: "invalid" },
        } as DetailedRom,
        description: resolveDescription({ provider: null }),
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

    expect(wrapper.find("iframe").exists()).toBe(false);
    expect(wrapper.text()).toContain("rom.youtube-invalid");
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
        description: resolveDescription({
          provider: null,
          manualMetadata: { descriptions: { en: "Resolved description" } },
        }),
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
        description: resolveDescription({
          provider: null,
          manualMetadata: {
            descriptions: { en: "Visible without permission" },
          },
        }),
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

afterEach(() => (activeLocale.value = "en-US"));
