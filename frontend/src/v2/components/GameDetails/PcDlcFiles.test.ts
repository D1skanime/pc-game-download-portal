import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { PcComponentSchema } from "@/__generated__";
import PcDlcFiles from "./PcDlcFiles.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string) =>
      ({
        "rom.pc-dlc-local-files": "Local files",
        "rom.pc-dlc-empty-files-title": "No local files found",
        "rom.pc-dlc-empty-files-body":
          "This DLC has no immutable file entries to show.",
      })[key] ?? key,
  }),
}));

const component = {
  id: 2,
  relative_path: "DLC/Expansion",
  kind: "dlc",
  manifest_members: [
    {
      id: 20,
      relative_path: "packs/expansion.pak",
      size_bytes: 1536,
      sha256: "a".repeat(64),
    },
    {
      id: 21,
      relative_path: "readme.txt",
      size_bytes: 512,
      sha256: "b".repeat(64),
    },
  ],
} satisfies PcComponentSchema;

describe("PcDlcFiles", () => {
  it("renders every immutable manifest member as read-only local evidence", () => {
    const wrapper = mount(PcDlcFiles, { props: { component, romId: 1 } });

    expect(wrapper.get("[data-testid='pc-dlc-manifest']").element.tagName).toBe(
      "UL",
    );
    expect(wrapper.text()).toContain("packs/expansion.pak");
    expect(wrapper.text()).toContain("1.5 KB");
    expect(wrapper.text()).toContain("a".repeat(64));
    expect(wrapper.text()).toContain("readme.txt");
    expect(wrapper.text()).toContain("512 B");
    expect(wrapper.text()).toContain("b".repeat(64));
    expect(wrapper.findAll("button, a")).toHaveLength(2);
  });

  it("keeps component-owned media out of the component-scoped Files surface", () => {
    const wrapper = mount(PcDlcFiles, {
      props: {
        component: {
          ...component,
          owned_media: [
            {
              id: 22,
              role: "screenshot",
              mime_type: "image/webp",
              owned_path: "roms/1/components/2/screenshot.webp",
              origin: "upload",
              provider: null,
              provider_media_id: null,
              created_at: "2026-09-14T00:00:00Z",
              updated_at: "2026-09-14T00:00:00Z",
            },
          ],
        },
        romId: 1,
      },
    });

    expect(
      wrapper.find("[data-testid='pc-dlc-owned-media-downloads']").exists(),
    ).toBe(false);
    expect(wrapper.findAll("img")).toHaveLength(0);
    expect(wrapper.text()).not.toContain("screenshot");
    expect(wrapper.text()).not.toContain("image/webp");

    const downloads = wrapper.findAll("a");
    expect(downloads).toHaveLength(2);
    expect(downloads[0].attributes("href")).toBe(
      "/api/roms/1/pc-components/2/manifest-members/20/content",
    );
    expect(downloads[1].attributes("href")).toBe(
      "/api/roms/1/pc-components/2/manifest-members/21/content",
    );
  });
});
