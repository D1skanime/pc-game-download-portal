import { beforeEach, describe, expect, it, vi } from "vitest";
import storageApi from "@/services/api/storage";

const mocks = vi.hoisted(() => ({
  apiDelete: vi.fn(),
}));

vi.mock("@/services/api", () => ({
  default: {
    delete: mocks.apiDelete,
  },
}));

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
});
