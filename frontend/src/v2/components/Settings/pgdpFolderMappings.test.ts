import { AxiosHeaders } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import storageApi from "@/services/api/storage";
import type { Platform } from "@/v2/data/adapters/legacy/stores/platforms";
import { loadPgdPFolderMappings } from "./pgdpFolderMappings";

vi.mock("@/services/api/storage", () => ({
  default: { getMapping: vi.fn() },
}));

function platform(id: number, displayName = "Windows"): Platform {
  return {
    id,
    slug: "win",
    fs_slug: "win",
    name: "Windows",
    display_name: displayName,
    rom_count: 0,
    igdb_slug: null,
    moby_slug: null,
    hltb_slug: null,
    libretro_slug: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    fs_size_bytes: 0,
    is_unidentified: false,
    is_identified: true,
    missing_from_fs: false,
    firmware_count: 0,
  };
}

function mapping(platformId: number, relativePath: string) {
  return {
    data: {
      id: platformId,
      platform_id: platformId,
      storage_root_id: 1,
      relative_path: relativePath,
      active: true,
      version: 1,
    },
    status: 200,
    statusText: "OK",
    headers: new AxiosHeaders(),
    config: { headers: new AxiosHeaders() },
  };
}

describe("saved folder mappings", () => {
  const getMapping = vi.mocked(storageApi.getMapping);

  beforeEach(() => {
    getMapping.mockReset();
  });

  it("sorts saved relative paths and preserves display names with a name fallback", async () => {
    getMapping.mockImplementation(async (id) =>
      mapping(id, id === 1 ? "Zulu" : "Alpha"),
    );

    expect(
      await loadPgdPFolderMappings([platform(1, "Custom"), platform(2, "")]),
    ).toEqual([
      { fsSlug: "Alpha", slug: "win", displayName: "Windows", type: "auto" },
      { fsSlug: "Zulu", slug: "win", displayName: "Custom", type: "auto" },
    ]);
  });

  it("retains successful mappings when another platform request fails", async () => {
    getMapping.mockImplementation(async (id) => {
      if (id === 2) throw new Error("unavailable mapping");
      return mapping(id, id === 1 ? "Zulu" : "Alpha");
    });

    expect(
      await loadPgdPFolderMappings([platform(1), platform(2), platform(3)]),
    ).toEqual([
      { fsSlug: "Alpha", slug: "win", displayName: "Windows", type: "auto" },
      { fsSlug: "Zulu", slug: "win", displayName: "Windows", type: "auto" },
    ]);
  });

  it("skips unsaved platforms instead of requesting their mappings", async () => {
    getMapping.mockImplementation(async (id) => mapping(id, "PC"));

    expect(
      await loadPgdPFolderMappings([platform(0), platform(-1), platform(1)]),
    ).toEqual([
      { fsSlug: "PC", slug: "win", displayName: "Windows", type: "auto" },
    ]);
    expect(getMapping.mock.calls).toEqual([[1]]);
  });

  it("returns no rows for empty input or when every mapping request fails", async () => {
    expect(await loadPgdPFolderMappings([])).toEqual([]);
    getMapping.mockRejectedValue(new Error("unavailable mapping"));
    expect(await loadPgdPFolderMappings([platform(1), platform(2)])).toEqual(
      [],
    );
  });
});
