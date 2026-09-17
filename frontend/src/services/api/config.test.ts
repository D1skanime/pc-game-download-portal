import { describe, expect, it, vi } from "vitest";
import configApi from "@/services/api/config";

describe("configApi", () => {
  it("fetches the deployment-owned browser queue limit", async () => {
    const response = { data: { browser_download_queue_concurrency: 6 } };
    vi.spyOn(configApi, "get").mockResolvedValue(response as never);

    await configApi.getBrowserDownloadQueueConfig();

    expect(configApi.get).toHaveBeenCalledWith("/config");
  });
});
