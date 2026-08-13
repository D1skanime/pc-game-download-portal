import { shallowMount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import type { FirmwareSchema } from "@/__generated__";
import type { Platform } from "@/stores/platforms";
import DeleteFirmwareDialog from "@/v2/components/Gallery/DeleteFirmwareDialog.vue";
import HashChip from "@/v2/components/shared/HashChip.vue";
import FirmwareTab from "./FirmwareTab.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string, fallback?: string) => fallback ?? key }),
}));

vi.mock("@/services/api/firmware", () => ({
  default: {
    getFirmware: vi.fn(),
    uploadFirmware: vi.fn(),
    deleteFirmware: vi.fn(),
  },
}));

vi.mock("@/stores/platforms", () => ({
  default: () => ({ update: vi.fn() }),
}));

vi.mock("@/v2/stores/galleryRoms", () => ({
  default: () => ({ currentPlatform: null, setCurrentPlatform: vi.fn() }),
}));

vi.mock("@/v2/composables/useCan", () => ({
  useCan: () => ({ value: true }),
}));

vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ error: vi.fn(), success: vi.fn(), warning: vi.fn() }),
}));

const CRC = "aabbccdd";
const MD5 = "0123456789abcdef0123456789abcdef";
const SHA1 = "0123456789abcdef0123456789abcdef01234567";

function firmware(overrides: Partial<FirmwareSchema> = {}): FirmwareSchema {
  return {
    id: 1,
    file_name: "disksys.rom",
    file_name_no_tags: "disksys",
    file_name_no_ext: "disksys",
    file_extension: "rom",
    file_path: "fds",
    file_size_bytes: 8192,
    full_path: "fds/disksys.rom",
    is_verified: true,
    crc_hash: CRC,
    md5_hash: MD5,
    sha1_hash: SHA1,
    missing_from_fs: false,
    platform_id: 1,
    created_at: "",
    updated_at: "",
    ...overrides,
  } as FirmwareSchema;
}

function platform(firmwareList: FirmwareSchema[]): Platform {
  return {
    id: 1,
    slug: "fds",
    fs_slug: "fds",
    name: "Family Computer Disk System",
    display_name: "Family Computer Disk System",
    rom_count: 0,
    firmware_count: firmwareList.length,
    firmware: firmwareList,
  } as Platform;
}

function mountTab(firmwareList: FirmwareSchema[]) {
  return shallowMount(FirmwareTab, {
    props: { platform: platform(firmwareList) },
    global: {
      // The whole tab is wrapped in a dropzone whose default slot holds
      // the list, and a stubbed component does not render its slots.
      stubs: { RDropzone: { template: "<div><slot /></div>" } },
    },
  });
}

function chipEntries(wrapper: ReturnType<typeof mountTab>) {
  return wrapper
    .findAllComponents(HashChip)
    .map((c) => [c.props("label"), c.props("value")]);
}

describe("FirmwareTab", () => {
  it("exposes read, download, and catalog removal without source mutation", () => {
    const wrapper = mountTab([firmware()]);
    const tabSource = readFileSync(
      "src/v2/components/Gallery/FirmwareTab.vue",
      "utf8",
    );
    const dialogSource = readFileSync(
      "src/v2/components/Gallery/DeleteFirmwareDialog.vue",
      "utf8",
    );
    const serviceSource = readFileSync("src/services/api/firmware.ts", "utf8");

    expect(wrapper.findAllComponents({ name: "RDropzone" })).toHaveLength(0);
    expect(tabSource).not.toMatch(/uploadFirmware|pendingFiles|RDropzone/);
    expect(dialogSource).not.toMatch(/deleteFromFs|filesystem|from disk/);
    expect(serviceSource).not.toMatch(/uploadFirmware|delete_from_fs/);
    expect(serviceSource).toMatch(/firmware:\s*firmware\.map/);
    expect(DeleteFirmwareDialog.props).toBeDefined();
  });

  // #4082: the MD5 used to render as a plain chip with no copy affordance
  // and `user-select: none`, and CRC / SHA-1 were never shown at all.
  it("renders a copyable chip for every stored hash", () => {
    const wrapper = mountTab([firmware()]);

    expect(chipEntries(wrapper)).toEqual([
      ["SHA-1", SHA1],
      ["MD5", MD5],
      ["CRC", CRC],
    ]);
  });

  it("skips hashes the firmware record does not carry", () => {
    const wrapper = mountTab([firmware({ crc_hash: "", sha1_hash: "" })]);

    expect(chipEntries(wrapper)).toEqual([["MD5", MD5]]);
  });
});
