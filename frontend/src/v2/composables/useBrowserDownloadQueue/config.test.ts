import { describe, expect, it } from "vitest";
import { getBrowserDownloadQueueConcurrency } from "./config";

describe("browser download queue config", () => {
  it("provides one original-file slot limit to either queue mode", () => {
    const config = { browser_download_queue_concurrency: 6 };

    expect(getBrowserDownloadQueueConcurrency(config)).toBe(6);
  });
});
