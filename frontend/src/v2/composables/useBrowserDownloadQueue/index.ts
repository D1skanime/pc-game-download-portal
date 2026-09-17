import { computed, ref } from "vue";
import type { DownloadManifestResponse } from "@/__generated__";
import configApi from "@/services/api/config";
import downloadTransfersApi from "@/services/api/downloadTransfers";
import { getBrowserDownloadQueueConcurrency } from "./config";

export type BrowserQueueItem = DownloadManifestResponse["members"][number] & {
  status: "queued" | "handed_to_browser";
};
export function useBrowserDownloadQueue() {
  const items = ref<BrowserQueueItem[]>([]);
  const sessionId = ref<string | null>(null);
  const starting = ref(false);
  const queued = computed(() =>
    items.value.filter((item) => item.status === "queued"),
  );
  async function start(manifest: DownloadManifestResponse) {
    if (starting.value || sessionId.value) return false;
    starting.value = true;
    try {
      const config = await configApi.getBrowserDownloadQueueConfig();
      const limit = getBrowserDownloadQueueConcurrency(config.data);
      const session = await downloadTransfersApi.create({
        manifest_id: manifest.id,
        mode: "standard",
      });
      sessionId.value = session.data.id;
      items.value = manifest.members.map((member) => ({
        ...member,
        status: "queued" as const,
      }));
      for (const item of items.value.slice(0, limit)) {
        const anchor = document.createElement("a");
        anchor.href = item.download;
        anchor.download = item.destination.split("/").pop() ?? "download";
        anchor.click();
        item.status = "handed_to_browser";
        const transferItem = session.data.items.find(
          (candidate) => candidate.manifest_member_id === item.file_id,
        );
        if (transferItem)
          await downloadTransfersApi.observe(session.data.id, transferItem.id, {
            event_type: "handoff",
          });
      }
      return true;
    } finally {
      starting.value = false;
    }
  }
  return { items, queued, sessionId, starting, start };
}
export { getBrowserDownloadQueueConcurrency } from "./config";
