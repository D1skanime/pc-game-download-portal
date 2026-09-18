<script setup lang="ts">
import { RAlert, REmptyState, RSpinner, RTag } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { DownloadTransferResponse } from "@/__generated__";
import { formatBytes } from "@/utils";
import type { BrowserQueueItem } from "@/v2/composables/useBrowserDownloadQueue";

const props = withDefaults(
  defineProps<{
    sessions: DownloadTransferResponse[];
    queueItems?: BrowserQueueItem[];
    componentLabels?: string[];
    loading?: boolean;
    error?: boolean;
  }>(),
  {
    queueItems: () => [],
    componentLabels: () => [],
    loading: false,
    error: false,
  },
);
const { t } = useI18n();

const STATUS_KEYS: Record<string, string> = {
  queued: "rom.download-queued",
  handed_to_browser: "rom.download-handed-to-browser",
  served: "rom.download-served",
  verified: "rom.download-verified",
  stale: "rom.download-stale",
  cancelled: "rom.download-cancelled",
  expired: "rom.download-expired",
  failed: "rom.download-failed",
  paused: "rom.download-state-paused",
  downloading: "rom.download-state-downloading",
  active: "rom.download-queued",
};

type HistoryRow = {
  key: string;
  status: string;
  mode: string;
  bytes: number;
  timestamp: string;
};

function statusText(status: string, mode: string) {
  const safeStatus =
    status === "verified" && mode !== "enhanced" ? "failed" : status;
  return t(STATUS_KEYS[safeStatus] ?? "rom.download-failed");
}

function safeFilename(destination: string) {
  return destination.split("/").at(-1) || t("rom.download-file");
}

function timestamp(value: string | null) {
  return value ? new Date(value).toLocaleString() : "";
}

const rows = computed<HistoryRow[]>(() =>
  props.sessions.flatMap((session) => {
    if (session.items.length === 0) {
      return [
        {
          key: session.id,
          status: session.status,
          mode: session.mode,
          bytes: session.selected_bytes,
          timestamp: session.last_activity_at,
        },
      ];
    }
    return session.items.map((item, index) => ({
      key: `${session.id}-${index}`,
      status: item.status,
      mode: session.mode,
      bytes: item.expected_bytes,
      timestamp: item.last_activity_at ?? session.last_activity_at,
    }));
  }),
);
</script>

<template>
  <section class="download-transfer-history" data-testid="download-history">
    <div
      v-if="componentLabels.length"
      class="download-transfer-history__components"
    >
      {{ componentLabels.join(", ") }}
    </div>

    <ul
      v-if="queueItems.length"
      class="download-transfer-history__queue"
      data-testid="download-queue"
    >
      <li v-for="item in queueItems" :key="item.file_id">
        <span>{{ safeFilename(item.destination) }}</span>
        <RTag
          :text="
            statusText(
              item.status,
              item.status === 'verified' ? 'enhanced' : 'standard',
            )
          "
        />
      </li>
    </ul>

    <RSpinner
      v-if="loading"
      data-testid="download-history-loading"
      :aria-label="t('rom.download-state-downloading')"
    />
    <RAlert v-else-if="error" type="error" data-testid="download-history-error">
      {{ t("rom.download-failed-description") }}
    </RAlert>
    <REmptyState
      v-else-if="rows.length === 0"
      data-testid="download-history-empty"
      icon="mdi-download-outline"
      :title="t('rom.download-no-complete-set')"
    />
    <ul
      v-else
      class="download-transfer-history__rows"
      data-testid="download-history-list"
    >
      <li v-for="row in rows" :key="row.key">
        <RTag :text="statusText(row.status, row.mode)" />
        <span>{{ formatBytes(row.bytes) }}</span>
        <time v-if="row.timestamp" :datetime="row.timestamp">{{
          timestamp(row.timestamp)
        }}</time>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.download-transfer-history {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
}

.download-transfer-history__components,
.download-transfer-history li {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--r-space-3);
}

.download-transfer-history__components {
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-sm);
}

.download-transfer-history ul {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.download-transfer-history li {
  min-height: var(--r-touch-target);
  padding: var(--r-space-2) 0;
}

.download-transfer-history li > span:first-child {
  flex: 1 1 12rem;
  overflow-wrap: anywhere;
}

.download-transfer-history time {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
}
</style>
