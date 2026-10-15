import { beforeEach, describe, expect, it, vi } from "vitest";
import storageApi from "@/services/api/storage";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock("@/services/api", () => ({
  default: {
    get: mocks.apiGet,
    post: mocks.apiPost,
    delete: mocks.apiDelete,
  },
}));

const mapping = {
  id: 41,
  platform_id: 17,
  storage_root_id: 9,
  relative_path: "pc",
  active: true,
  version: 2,
};

const root = {
  id: 9,
  name: "Games",
  mode: "external_read_only",
  active: true,
  created_at: "2026-10-15T00:00:00Z",
  updated_at: "2026-10-15T00:00:00Z",
  health: {
    reachable: true,
    readable: true,
    non_writable: true,
    checked_at: "2026-10-15T00:00:00Z",
    error: null,
  },
};

describe("storage service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("confirms mapping removal in the delete request body", () => {
    storageApi.removeMapping(41, 3, 7);

    expect(mocks.apiDelete).toHaveBeenCalledWith("/storage/mappings/41", {
      data: {
        expected_version: 3,
        expected_unreachable_catalog_count: 7,
        confirmed: true,
      },
    });
  });

  it("reports ready only from the server mapping and healthy root", async () => {
    mocks.apiGet
      .mockResolvedValueOnce({ data: mapping })
      .mockResolvedValueOnce({ data: [root] });

    await expect(storageApi.getMappingReadiness(17)).resolves.toEqual({
      ready: true,
      mapping,
      root,
    });
    expect(mocks.apiGet).toHaveBeenNthCalledWith(
      1,
      "/storage/mappings/platforms/17",
    );
    expect(mocks.apiGet).toHaveBeenNthCalledWith(2, "/storage/roots");
    expect(mocks.apiPost).not.toHaveBeenCalled();
  });

  it.each([
    ["inactive mapping", { ...mapping, active: false }, root],
    ["missing root", mapping, undefined],
    ["inactive root", mapping, { ...root, active: false }],
    [
      "unreachable root",
      mapping,
      { ...root, health: { ...root.health, reachable: false } },
    ],
    [
      "unreadable root",
      mapping,
      { ...root, health: { ...root.health, readable: false } },
    ],
    [
      "writable root",
      mapping,
      { ...root, health: { ...root.health, non_writable: false } },
    ],
    [
      "unknown root write state",
      mapping,
      { ...root, health: { ...root.health, non_writable: null } },
    ],
  ])(
    "reports not-ready for %s",
    async (_case, mappingResponse, rootResponse) => {
      mocks.apiGet
        .mockResolvedValueOnce({ data: mappingResponse })
        .mockResolvedValueOnce({ data: rootResponse ? [rootResponse] : [] });

      await expect(storageApi.getMappingReadiness(17)).resolves.toMatchObject({
        ready: false,
        mapping: mappingResponse,
        root: rootResponse ?? null,
      });
      expect(mocks.apiPost).not.toHaveBeenCalled();
    },
  );

  it("treats a missing server mapping as not-ready without mutation", async () => {
    mocks.apiGet.mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 404 },
    });

    await expect(storageApi.getMappingReadiness(17)).resolves.toEqual({
      ready: false,
      mapping: null,
      root: null,
    });
    expect(mocks.apiGet).toHaveBeenCalledWith("/storage/mappings/platforms/17");
    expect(mocks.apiPost).not.toHaveBeenCalled();
  });
});
