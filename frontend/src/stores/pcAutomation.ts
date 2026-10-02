import { defineStore } from "pinia";
import type {
  PcAutomationQueueItemSchema,
  PcAutomationTargetKind,
} from "@/__generated__";
import pcAutomationApi from "@/services/api/pcAutomation";

const FETCH_LIMIT = 50;

function errorMessage(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  return detail ?? "pc-automation.request-failed";
}

export default defineStore("pcAutomation", {
  state: () => ({
    items: [] as PcAutomationQueueItemSchema[],
    total: 0,
    offset: 0,
    fetchLimit: FETCH_LIMIT,
    initialTotal: 0,
    loading: false,
    error: null as string | null,
    actionLoadingIds: new Set<number>(),
    batchLoading: false,
    selection: new Set<number>(),
  }),

  getters: {
    hasMore: (state) => state.items.length < state.total,
    outstandingCount: (state) => state.total,
    progress: (state) =>
      state.initialTotal === 0
        ? 0
        : Math.max(
            0,
            Math.min(
              100,
              ((state.initialTotal - state.total) / state.initialTotal) * 100,
            ),
          ),
    selectedItems: (state) =>
      state.items.filter((item) => state.selection.has(item.id)),
    selectedGroupIsSafe(): boolean {
      if (this.selectedItems.length === 0) return false;
      const [first] = this.selectedItems;
      return this.selectedItems.every(
        (item) =>
          item.candidate_fingerprint === first.candidate_fingerprint &&
          item.target_kind === first.target_kind,
      );
    },
  },

  actions: {
    async fetchQueue({ reset = false }: { reset?: boolean } = {}) {
      if (this.loading) return;
      this.loading = true;
      this.error = null;
      const offset = reset ? 0 : this.items.length;
      try {
        const { data } = await pcAutomationApi.getReviewQueue(
          this.fetchLimit,
          offset,
        );
        this.items = reset
          ? data.items
          : [
              ...this.items,
              ...data.items.filter(
                (item) => !this.items.some((current) => current.id === item.id),
              ),
            ];
        this.total = data.total;
        this.offset = data.offset;
        if (reset) this.selection = new Set();
        this.initialTotal = Math.max(this.initialTotal, this.total);
      } catch (error) {
        this.error = errorMessage(error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    toggleSelection(queueId: number) {
      const selection = new Set(this.selection);
      if (selection.has(queueId)) selection.delete(queueId);
      else selection.add(queueId);
      this.selection = selection;
    },

    clearSelection() {
      this.selection = new Set();
    },

    async accept(item: PcAutomationQueueItemSchema) {
      this.actionLoadingIds = new Set(this.actionLoadingIds).add(item.id);
      try {
        await pcAutomationApi.acceptReviewItem(item.id, {
          expected_queue_version: item.expected_queue_version,
          expected_target_version: item.expected_target_version,
          candidate_fingerprint: item.candidate_fingerprint,
        });
        await this.fetchQueue({ reset: true });
      } finally {
        const loading = new Set(this.actionLoadingIds);
        loading.delete(item.id);
        this.actionLoadingIds = loading;
      }
    },

    async skip(item: PcAutomationQueueItemSchema) {
      this.actionLoadingIds = new Set(this.actionLoadingIds).add(item.id);
      try {
        await pcAutomationApi.skipReviewItem(item.id, {
          expected_queue_version: item.expected_queue_version,
          expected_target_version: item.expected_target_version,
          candidate_fingerprint: item.candidate_fingerprint,
        });
        await this.fetchQueue({ reset: true });
      } finally {
        const loading = new Set(this.actionLoadingIds);
        loading.delete(item.id);
        this.actionLoadingIds = loading;
      }
    },

    async batchAccept() {
      if (!this.selectedGroupIsSafe) return;
      const [first] = this.selectedItems;
      this.batchLoading = true;
      try {
        await pcAutomationApi.batchAcceptReviewItems({
          target_kind: first.target_kind as PcAutomationTargetKind,
          candidate_fingerprint: first.candidate_fingerprint,
          items: this.selectedItems.map((item) => ({
            queue_id: item.id,
            expected_queue_version: item.expected_queue_version,
            expected_target_version: item.expected_target_version,
          })),
        });
        await this.fetchQueue({ reset: true });
      } finally {
        this.batchLoading = false;
      }
    },
  },
});
