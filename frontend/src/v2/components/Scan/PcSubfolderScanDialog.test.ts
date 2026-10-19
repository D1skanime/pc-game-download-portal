import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { SimpleRom } from "@/v2/data/adapters/legacy/stores/roms";
import type { ScanningPlatform } from "@/v2/data/adapters/legacy/stores/scanning";
import PcSubfolderScanDialog from "./PcSubfolderScanDialog.vue";
import ScanPlatform from "./ScanPlatform.vue";
import ScanPlatformRow from "./ScanPlatformRow.vue";

const api = vi.hoisted(() => ({
  getMapping: vi.fn(),
  browseRoot: vi.fn(),
}));
vi.mock("@/v2/data/adapters/legacy/services/api/storage", () => ({
  default: api,
}));
vi.mock("@/v2/composables/useWebpSupport", () => ({
  useWebpSupport: () => ({ toWebp: (value: string) => value }),
}));
vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("@v2/lib", () => ({
  RDialog: { template: "<div><slot name='content' /></div>" },
  RBtn: { template: "<button><slot /></button>" },
  RIcon: { template: "<span />" },
  RImg: { template: "<img />" },
  RTag: { template: "<span />" },
  RPlatformIcon: { template: "<span />" },
  RCollapsible: { template: "<div><slot /></div>" },
  RVirtualScroller: {
    props: ["items"],
    template: "<div><slot v-for='item in items' :item='item' /></div>",
  },
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
        data: {
          id: 12,
          version: 3,
          storage_root_id: 7,
          relative_path: mapping,
        },
      });
      api.browseRoot.mockResolvedValue({
        data: {
          entries: [
            { name: "Belmonts.Curse", relative_path: child, navigable: true },
          ],
        },
      });
      const rom = {
        id: 41,
        platform_id: 3,
        platform_fs_slug: "win",
        fs_name: "Castlevania",
        fs_extension: "",
      } as SimpleRom;
      const wrapper = mount(PcSubfolderScanDialog, {
        props: { modelValue: true, rom },
      });
      await flushPromises();
      expect(api.browseRoot).toHaveBeenLastCalledWith(
        7,
        [mapping, "Castlevania"].filter(Boolean).join("/"),
      );
      await wrapper.get("button").trigger("click");
      expect(wrapper.emitted("scan")).toEqual([
        [
          {
            platformFsSlug: "win",
            relativePath: expected,
            collectionPromotion: {
              parent_rom_id: 41,
              mapping_id: 12,
              expected_revision: 3,
              parent_relative_path: "Castlevania",
              selected_child_relative_path: expected,
            },
          },
        ],
      ]);
    },
  );
  it.each(["row", "platform"])(
    "forwards explicit selection identity through the mounted %s",
    async (surface) => {
      api.getMapping.mockResolvedValue({
        data: {
          id: 12,
          version: 3,
          storage_root_id: 7,
          relative_path: "pc-Games",
        },
      });
      api.browseRoot.mockResolvedValue({
        data: {
          entries: [
            {
              name: "Belmonts.Curse",
              relative_path: "pc-Games/Castlevania/Belmonts.Curse",
              navigable: true,
            },
          ],
        },
      });
      const rom = {
        id: 41,
        platform_id: 3,
        platform_fs_slug: "win",
        fs_name: "Castlevania",
        fs_extension: "",
      } as SimpleRom;
      const wrapper =
        surface === "row"
          ? mount(ScanPlatformRow, {
              props: { rom },
              global: {
                stubs: { RouterLink: { template: "<a><slot /></a>" } },
              },
            })
          : mount(ScanPlatform, {
              props: {
                open: true,
                platform: { id: 3, roms: [rom] } as ScanningPlatform,
              },
              global: {
                stubs: { RouterLink: { template: "<a><slot /></a>" } },
              },
            });
      await wrapper.get("button").trigger("click");
      await flushPromises();
      const dialog = wrapper.getComponent(PcSubfolderScanDialog);
      await dialog.get("button").trigger("click");
      expect(wrapper.emitted("scan-subfolder")).toEqual([
        [
          {
            platformFsSlug: "win",
            relativePath: "Castlevania/Belmonts.Curse",
            collectionPromotion: {
              parent_rom_id: 41,
              mapping_id: 12,
              expected_revision: 3,
              parent_relative_path: "Castlevania",
              selected_child_relative_path: "Castlevania/Belmonts.Curse",
            },
          },
        ],
      ]);
      wrapper.unmount();
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
    const rom = {
      id: 41,
      platform_id: 3,
      platform_fs_slug: "win",
      fs_name: "Castlevania",
      fs_extension: "",
    } as SimpleRom;
    const wrapper = mount(PcSubfolderScanDialog, {
      props: { modelValue: true, rom },
    });
    await flushPromises();
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("scan")).toBeUndefined();
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });
});
