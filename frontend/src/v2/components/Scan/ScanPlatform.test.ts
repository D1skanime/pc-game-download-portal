import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { ScanningPlatform } from "@/stores/scanning";
import type { SimpleRom } from "@/v2/data/adapters/legacy/stores/roms";
import type { ScanOperationItemResult } from "@/v2/data/contracts";
import ScanPlatform from "./ScanPlatform.vue";
import ScanPlatformRow from "./ScanPlatformRow.vue";

vi.mock("@/v2/composables/useWebpSupport", () => ({
  useWebpSupport: () => ({ toWebp: (url: string) => url }),
}));
vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

function mountPlatform(overrides: Partial<ScanningPlatform> = {}) {
  const platform: ScanningPlatform = {
    id: 1,
    name: "Game Boy Color",
    display_name: "Game Boy Color",
    slug: "gbc",
    fs_slug: "gbc",
    is_identified: true,
    roms: [],
    new_firmware_count: 0,
    ...overrides,
  };

  return mount(ScanPlatform, {
    props: { platform, open: true },
    global: {
      stubs: {
        RCollapsible: {
          template: "<div><slot /><slot name='header-append' /></div>",
        },
        RPlatformIcon: true,
        RTag: {
          props: ["text"],
          template: "<span class='r-tag'>{{ text }}</span>",
        },
        RVirtualScroller: true,
      },
    },
  });
}

describe("ScanPlatform", () => {
  // Firmware already in the library is not a scan result: the header used to
  // show the platform's total firmware count, so every re-scan looked like it
  // had discovered firmware (issue #4049).
  it("hides the firmware tag when the scan found no new firmware", () => {
    const wrapper = mountPlatform({ new_firmware_count: 0 });

    expect(wrapper.findAll(".r-tag")).toHaveLength(1);
  });

  it("shows the count of firmware discovered by this scan", () => {
    const wrapper = mountPlatform({ new_firmware_count: 2 });

    const tags = wrapper.findAll(".r-tag");
    expect(tags).toHaveLength(2);
    expect(tags[1].text()).toBe("2");
  });

  // The body only lists ROMs, so a firmware-only platform rendered an empty
  // panel instead of the "no new roms" message.
  it("reports no new roms even when firmware was found", () => {
    const wrapper = mountPlatform({ new_firmware_count: 2 });

    expect(wrapper.text()).toContain("scan.no-new-roms");
  });
});

const result: ScanOperationItemResult = {
  id: 90,
  mapping_id: 2,
  expected_revision: 1,
  relative_path: "Collection/Unknown",
  target_key: "unknown",
  provider: "steam",
  attempt_id: "attempt",
  outcome: "completed",
  inventory: {
    rom_id: 9,
    inventory_state: "unchanged",
    identified_windows: false,
    existing_game: true,
    retry_state: "budget_deferred",
  },
  provider_execution: { state: "no_request", invoked: false, requests: 0 },
};
function row(item: ScanOperationItemResult) {
  return mount(ScanPlatformRow, {
    props: {
      rom: {
        id: 9,
        name: "Unknown",
        fs_name: "Unknown",
        platform_fs_slug: "win",
        fs_extension: "zip",
        is_identifying: true,
        is_unidentified: true,
      } as SimpleRom,
      item,
    },
    global: {
      stubs: {
        RouterLink: { template: "<a><slot /></a>" },
        RImg: true,
        RBtn: true,
        RTag: { props: ["text"], template: "<span>{{ text }}</span>" },
        PcSubfolderScanDialog: true,
      },
    },
  });
}
describe("durable row status", () => {
  it.each(["no_request", "cached", "no_match", "failed"] as const)(
    "does not animate terminal %s despite legacy identifying state",
    (state) => {
      const wrapper = row({
        ...result,
        provider_execution: { state, invoked: false, requests: 0 },
      });
      expect(wrapper.text()).toContain("scan.not-identified");
      expect(wrapper.find(".r-v2-scan-platform__identifying").exists()).toBe(
        false,
      );
      expect(wrapper.find(".r-v2-scan-platform__badge-pop").exists()).toBe(
        false,
      );
    },
  );
  it("animates only observed provider requests and keeps Steam identity authoritative", async () => {
    const wrapper = row({
      ...result,
      provider_execution: {
        state: "requested",
        invoked: true,
        requests: 1,
        is_identifying: true,
      },
    });
    expect(wrapper.find(".r-v2-scan-platform__identifying").exists()).toBe(
      true,
    );
    await wrapper.setProps({
      item: {
        ...result,
        inventory: { ...result.inventory!, identified_windows: true },
      },
    });
    expect(wrapper.text()).not.toContain("scan.not-identified");
    expect(wrapper.find(".r-v2-scan-platform__identifying").exists()).toBe(
      false,
    );
  });
});
