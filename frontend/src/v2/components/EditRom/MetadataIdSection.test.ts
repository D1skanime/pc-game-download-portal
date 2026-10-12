import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { UpdateRom } from "@/v2/data/adapters/legacy/services/api/rom";
import MetadataIdSection from "./MetadataIdSection.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

describe("MetadataIdSection", () => {
  it("exposes the Steam App ID and binds its numeric value", () => {
    const wrapper = shallowMount(MetadataIdSection, {
      props: {
        rom: { steam_id: 730 } as UpdateRom,
      },
    });

    const steamField = wrapper
      .findAllComponents({ name: "RTextField" })
      .find((field) => field.props("label") === "rom.provider-steam-id");

    expect(steamField).toBeDefined();
    expect(steamField?.props("modelValue")).toBe("730");
  });
});
