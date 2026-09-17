import type { ConfigResponse } from "@/__generated__";

export type BrowserDownloadQueueConfig = Pick<
  ConfigResponse,
  "browser_download_queue_concurrency"
>;

/** Return the deployment-owned number of original files that may be active. */
export function getBrowserDownloadQueueConcurrency(
  config: BrowserDownloadQueueConfig,
): number {
  return config.browser_download_queue_concurrency;
}
