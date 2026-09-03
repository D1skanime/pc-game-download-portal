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
});
