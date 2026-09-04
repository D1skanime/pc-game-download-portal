import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import type { DetailedRomSchema, PcComponentSchema } from "@/__generated__";
import PcDlcDetail from "./PcDlcDetail.vue";

const route = { path: "/roms/1/dlc/2", query: {} as Record<string, string> };
const replace = vi.fn();

vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRoute: () => route,
  useRouter: () => ({ replace }),
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string, values?: Record<string, string>) =>
      ({
        "rom.category-dlc": "DLC",
        "rom.pc-dlc-back-to-game": `Back to ${values?.game}`,
        "rom.pc-dlc-fallback-title": `DLC: ${values?.relativePath}`,
      })[key] ?? key,
    locale: { value: "en-US" },
  }),
}));

const selectedDlc = {
  id: 2,
  relative_path: "DLC/Expansion",
  kind: "dlc",
  component_metadata: {
    igdb_id: null,
    moby_id: null,
    sgdb_id: null,
    launchbox_id: null,
    name: "Selected expansion",
    summary: "Only selected DLC metadata is visible.",
    metadata_source: "local",
    provider_metadata: null,
    main_developer: "CD Projekt Red",
    publishers: ["CD Projekt"],
    themes: ["Cyberpunk"],
    pc_release_date: 1725148800,
  },
  local_media: [
    {
      id: 20,
      role: "cover",
      owned_path: "roms/1/components/2/cover.webp",
      source_relative_path: "DLC/Expansion/cover.webp",
      source_sha256: "a".repeat(64),
      image_type: "image/webp",
    },
    {
      id: 21,
      role: "gallery",
      owned_path: "roms/1/components/2/gallery.webp",
      source_relative_path: "DLC/Expansion/gallery.webp",
      source_sha256: "b".repeat(64),
      image_type: "image/webp",
    },
  ],
  manifest_members: [
    {
      id: 200,
      relative_path: "data/expansion.pak",
      size_bytes: 1024,
      sha256: "c".repeat(64),
    },
  ],
} satisfies PcComponentSchema;

const parent = {
  id: 1,
  name: "Parent game",
  path_cover_large: "parent-cover.webp",
  components: [
    selectedDlc,
    {
      id: 3,
      relative_path: "DLC/Sibling",
      kind: "dlc",
      local_media: [
        {
          id: 30,
          role: "cover",
          owned_path: "roms/1/components/3/cover.webp",
          source_relative_path: "DLC/Sibling/cover.webp",
          source_sha256: "d".repeat(64),
          image_type: "image/webp",
        },
      ],
      manifest_members: [],
    },
  ],
} satisfies Pick<DetailedRomSchema, "id" | "name" | "components"> & {
  path_cover_large: string;
};

function mountDetail(component: PcComponentSchema = selectedDlc) {
  return mount(PcDlcDetail, {
    props: { parent: parent as DetailedRomSchema, component },
    global: {
      stubs: {
        RBtn: { template: "<a><slot /></a>" },
        RImg: {
          props: ["src", "alt"],
          template: "<img :src='src' :alt='alt' />",
        },
        RTag: { template: "<span><slot /></span>" },
        PcDlcFiles: {
          props: ["component"],
          template: "<section data-testid='files' />",
        },
      },
    },
  });
}

describe("PcDlcDetail", () => {
  it("limits the query-synced detail shell to DLC-specific tabs", () => {
    const source = readFileSync(
      "src/v2/components/GameDetails/PcDlcDetail.vue",
      "utf8",
    );

    expect(source).toContain('id: "overview"');
    expect(source).toContain('id: "files"');
    expect(source).toContain('id: "media"');
    expect(source).toContain('id: "notes"');
    expect(source).not.toContain("save-data");
  });

  it("renders selected DLC identity and owned media without parent or sibling artwork", () => {
    const wrapper = mountDetail();

    expect(wrapper.get("a").text()).toBe("Back to Parent game");
    expect(wrapper.text()).toContain("Selected expansion");
    expect(wrapper.text()).toContain("Only selected DLC metadata is visible.");
    expect(wrapper.html()).toContain(
      "/assets/romm/resources/roms/1/components/2/cover.webp",
    );
    expect(wrapper.html()).toContain(
      "/assets/romm/resources/roms/1/components/2/gallery.webp",
    );
    expect(wrapper.html()).not.toContain("parent-cover.webp");
    expect(wrapper.html()).not.toContain("components/3/cover.webp");
  });

  it("uses the parent detail canvas so tabs and content share its fixed panel", () => {
    const wrapper = mountDetail();

    expect(wrapper.classes()).toContain("r-v2-det");
    const tabs = wrapper.get(".r-v2-det__tabs");
    const panel = wrapper.get(".r-v2-det__panel");
    expect(tabs.element.compareDocumentPosition(panel.element)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });

  it("keeps the header above tabs to the title and DLC tag, with overview details below", () => {
    const wrapper = mountDetail();
    const hero = wrapper.get(".pc-dlc-detail__hero");
    const titleRow = wrapper.get(".pc-dlc-detail__title-row");
    const title = titleRow.get("h1");
    const tag = titleRow.get("span");
    const panel = wrapper.get(".r-v2-det__panel");
    const summary = panel.get(".pc-dlc-detail__summary");
    const facts = panel.get(".pc-dlc-detail__facts");

    expect(hero.element.firstElementChild).toBe(titleRow.element);
    expect(hero.element.childElementCount).toBe(1);
    expect(title.text()).toBe("Selected expansion");
    expect(title.element.compareDocumentPosition(tag.element)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    expect(tag.attributes("text")).toBe("DLC");
    expect(hero.find(".pc-dlc-detail__summary").exists()).toBe(false);
    expect(hero.find(".pc-dlc-detail__facts").exists()).toBe(false);
    expect(summary.text()).toBe("Only selected DLC metadata is visible.");
    expect(facts.text()).toContain("DLC/Expansion");
    expect(facts.text()).toContain("1");
    expect(facts.text()).toContain("1 KB");
  });

  it("uses a localized path title and neutral cover placeholder when selected media is absent", () => {
    const wrapper = mountDetail({
      ...selectedDlc,
      component_metadata: null,
      local_media: [],
    });

    expect(wrapper.text()).toContain("DLC: DLC/Expansion");
    expect(
      wrapper
        .get("[data-testid='pc-dlc-cover-placeholder']")
        .attributes("aria-label"),
    ).toContain("DLC: DLC/Expansion");
    expect(wrapper.find("[data-testid='pc-dlc-media']").exists()).toBe(false);
  });

  it("renders a provider-owned cover when no local cover is available", () => {
    const wrapper = mountDetail({
      ...selectedDlc,
      local_media: [],
      owned_media: [
        {
          id: 42,
          role: "cover",
          mime_type: "image/jpeg",
          owned_path: "roms/1/pc-owned-media/2/provider-cover.jpg",
          origin: "provider",
          provider: "igdb",
          provider_media_id: "provider-cover",
          created_at: "2026-09-03T00:00:00+00:00",
          updated_at: "2026-09-03T00:00:00+00:00",
        },
      ],
    });

    expect(wrapper.get("img").attributes("src")).toBe(
      "/assets/romm/resources/roms/1/pc-owned-media/2/provider-cover.jpg",
    );
    expect(
      wrapper.find("[data-testid='pc-dlc-cover-placeholder']").exists(),
    ).toBe(false);
  });

  it("renders only this DLC's owned screenshots and structured PC metadata", () => {
    const wrapper = mountDetail({
      ...selectedDlc,
      owned_media: [
        {
          id: 43,
          role: "screenshot",
          mime_type: "image/jpeg",
          owned_path: "roms/1/pc-owned-media/2/provider-shot.jpg",
          origin: "provider",
          provider: "igdb",
          provider_media_id: "provider-shot",
          created_at: "2026-09-03T00:00:00+00:00",
          updated_at: "2026-09-03T00:00:00+00:00",
        },
      ],
    });

    expect(wrapper.text()).toContain("rom.pc-release");
    expect(wrapper.text()).toContain("2024");
    expect(wrapper.text()).toContain("rom.main-developer");
    expect(wrapper.text()).toContain("CD Projekt Red");
    expect(wrapper.text()).toContain("rom.publishers");
    expect(wrapper.text()).toContain("CD Projekt");
    expect(wrapper.text()).toContain("rom.themes");
    expect(wrapper.text()).toContain("Cyberpunk");
    expect(wrapper.html()).toContain("pc-owned-media/2/provider-shot.jpg");
    expect(wrapper.html()).not.toContain("components/3/cover.webp");
    expect(wrapper.html()).not.toContain("parent-cover.webp");
  });

  it("omits PC groups and screenshots when the selected DLC has none", () => {
    const wrapper = mountDetail({
      ...selectedDlc,
      component_metadata: {
        ...selectedDlc.component_metadata,
        main_developer: null,
        publishers: [],
        themes: [],
        pc_release_date: null,
      },
      owned_media: [],
    });

    expect(wrapper.text()).not.toContain("rom.pc-release");
    expect(wrapper.text()).not.toContain("rom.main-developer");
    expect(wrapper.find("[data-testid='pc-dlc-screenshots']").exists()).toBe(
      false,
    );
  });
});
