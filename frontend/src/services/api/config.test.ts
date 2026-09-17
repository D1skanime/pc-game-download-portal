import { describe, expect, it, vi } from "vitest";
import api from "@/services/api";
import configApi from "@/services/api/config";

describe("configApi", () => {
  it("fetches the deployment-owned browser queue limit", async () => {
    const response = { data: { browser_download_queue_concurrency: 6 } };
    vi.spyOn(api, "get").mockResolvedValue(response as never);

    await configApi.getBrowserDownloadQueueConfig();

    expect(api.get).toHaveBeenCalledWith("/config");
  });
});
