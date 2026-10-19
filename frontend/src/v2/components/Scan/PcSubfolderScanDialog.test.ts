import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { SimpleRom } from "@/v2/data/adapters/legacy/stores/roms";
import PcSubfolderScanDialog from "./PcSubfolderScanDialog.vue";

const api = vi.hoisted(() => ({
  getMapping: vi.fn(),
  browseRoot: vi.fn(),
}));
vi.mock("@/v2/data/adapters/legacy/services/api/storage", () => ({
  default: api,
}));
vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("@v2/lib", () => ({
  RDialog: { template: "<div><slot name='content' /></div>" },
  RBtn: { template: "<button><slot /></button>" },
  RIcon: { template: "<span />" },
}));

describe("PC child folder scan scope", () => {
  it.each([
    [
      "pc-Games",
      "pc-Games/Castlevania/Belmonts.Curse",
      "Castlevania/Belmonts.Curse",
    ],
    ["", "Castlevania/Belmonts.Curse", "Castlevania/Belmonts.Curse"],
    [
      "library/pc-Games",
      "library/pc-Games/Castlevania/Belmonts.Curse",
      "Castlevania/Belmonts.Curse",
    ],
  ])(
    "emits a mapping-relative scan scope from root %s",
    async (mapping, child, expected) => {
      api.getMapping.mockResolvedValue({
        data: { storage_root_id: 7, relative_path: mapping },
      });
      api.browseRoot.mockResolvedValue({
        data: {
          entries: [
            { name: "Belmonts.Curse", relative_path: child, navigable: true },
          ],
        },
      });
      const rom = { platform_id: 3, fs_name: "Castlevania" } as SimpleRom;
      const wrapper = mount(PcSubfolderScanDialog, {
        props: { modelValue: true, rom },
      });
      await flushPromises();
      expect(api.browseRoot).toHaveBeenLastCalledWith(
        7,
        [mapping, "Castlevania"].filter(Boolean).join("/"),
      );
      await wrapper.get("button").trigger("click");
      expect(wrapper.emitted("scan")).toEqual([[expected]]);
    },
  );
  it.each([
    "pc-Games-other/Castlevania/Belmonts.Curse",
    "pc-Games/../escape",
    "/pc-Games/Castlevania/Belmonts.Curse",
    "pc-Games/Castlevania/./child",
  ])("rejects an invalid root-relative selection %s", async (child) => {
    api.getMapping.mockResolvedValue({
      data: { storage_root_id: 7, relative_path: "pc-Games" },
    });
    api.browseRoot.mockResolvedValue({
      data: {
        entries: [{ name: "invalid", relative_path: child, navigable: true }],
      },
    });
    const rom = { platform_id: 3, fs_name: "Castlevania" } as SimpleRom;
    const wrapper = mount(PcSubfolderScanDialog, {
      props: { modelValue: true, rom },
    });
    await flushPromises();
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("scan")).toBeUndefined();
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });
});
