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
    showHistory?: boolean;
    loading?: boolean;
    error?: boolean;
  }>(),
  {
    queueItems: () => [],
    componentLabels: () => [],
    showHistory: true,
    loading: false,
    error: false,
  },
);
const { t } = useI18n();
const emit = defineEmits<{
  (event: "pause", fileId: string): void;
  (event: "cancel", fileId: string): void;
  (event: "resume", fileId: string): void;
  (event: "remove", sessionId: string): void;
  (event: "remove-all"): void;
}>();

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
  active: "rom.download-state-downloading",
};

type HistoryRow = {
  key: string;
  sessionId: string;
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

function statusClass(status: string) {
  return `download-transfer-history__status--${status}`;
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
          sessionId: session.id,
          status: session.status,
          mode: session.mode,
          bytes: session.selected_bytes,
          timestamp: session.last_activity_at,
        },
      ];
    }
    return session.items.map((item, index) => ({
      key: `${session.id}-${index}`,
      sessionId: session.id,
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

    <button
      v-if="showHistory && rows.length"
      type="button"
      class="download-transfer-history__remove-all"
      @click="emit('remove-all')"
    >
      {{ t("rom.clear-all") }}
    </button>

    <ul
      v-if="queueItems.length"
      class="download-transfer-history__queue"
      data-testid="download-queue"
    >
      <li
        v-for="item in queueItems"
        :key="item.file_id"
        :class="statusClass(item.status)"
      >
        <span>{{ safeFilename(item.destination) }}</span>
        <template
          v-if="
            item.status === 'downloading' ||
            item.status === 'verified' ||
            item.status === 'failed' ||
            item.status === 'paused'
          "
        >
          <progress
            class="download-transfer-history__progress"
            :max="item.size"
            :value="item.observedBytes ?? 0"
            :aria-label="`${formatBytes(item.observedBytes ?? 0)} / ${formatBytes(item.size)}`"
          />
          <small
            >{{ formatBytes(item.observedBytes ?? 0) }} /
            {{ formatBytes(item.size) }}</small
          >
        </template>
        <RTag
          :text="
            statusText(
              item.status,
              item.status === 'verified' ? 'enhanced' : 'standard',
            )
          "
        />
        <div class="download-transfer-history__actions">
          <button
            v-if="item.status === 'downloading'"
            type="button"
            :aria-label="t('rom.download-pause')"
            @click="emit('pause', item.file_id)"
          >
            {{ t("rom.download-pause") }}
          </button>
          <button
            v-if="item.status === 'paused'"
            type="button"
            :aria-label="t('rom.download-resume')"
            @click="emit('resume', item.file_id)"
          >
            {{ t("rom.download-resume") }}
          </button>
          <button
            v-if="item.status === 'downloading' || item.status === 'paused'"
            type="button"
            :aria-label="t('rom.download-cancel')"
            @click="emit('cancel', item.file_id)"
          >
            {{ t("rom.download-cancel") }}
          </button>
        </div>
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
      v-else-if="rows.length === 0 && !queueItems.length"
      data-testid="download-history-empty"
      icon="mdi-download-outline"
      :title="t('rom.download-no-complete-set')"
    />
    <ul
      v-else-if="showHistory && rows.length"
      class="download-transfer-history__rows"
      data-testid="download-history-list"
    >
      <li v-for="row in rows" :key="row.key">
        <RTag :text="statusText(row.status, row.mode)" />
        <span>{{ formatBytes(row.bytes) }}</span>
        <time v-if="row.timestamp" :datetime="row.timestamp">{{
          timestamp(row.timestamp)
        }}</time>
        <button
          v-if="!['active', 'queued', 'paused'].includes(row.status)"
          type="button"
          :aria-label="t('rom.delete-file')"
          @click="emit('remove', row.sessionId)"
        >
          {{ t("rom.delete-file") }}
        </button>
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

.download-transfer-history__progress {
  width: 100%;
  flex: 1 1 100%;
  height: 0.7rem;
  accent-color: var(--r-color-primary);
}

.download-transfer-history__status--verified
  .download-transfer-history__progress {
  accent-color: var(--r-color-success);
}

.download-transfer-history__status--downloading
  .download-transfer-history__progress {
  accent-color: var(--r-color-primary);
}

.download-transfer-history__status--failed
  .download-transfer-history__progress {
  accent-color: var(--r-color-danger);
}

.download-transfer-history__queue li {
  position: relative;
}

.download-transfer-history__queue li:has(.download-transfer-history__progress) {
  display: grid;
  grid-template-columns: minmax(12rem, 1fr) auto;
}

.download-transfer-history__queue
  li:has(.download-transfer-history__progress)
  small,
.download-transfer-history__queue
  li:has(.download-transfer-history__progress)
  .r-tag {
  grid-row: 2;
}

.download-transfer-history__queue
  li:has(.download-transfer-history__progress)
  .download-transfer-history__progress {
  grid-column: 1 / -1;
  grid-row: 1;
}

.download-transfer-history__queue
  li:has(.download-transfer-history__progress)
  > span:first-child {
  grid-row: 2;
}

.download-transfer-history__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--r-space-1);
}

.download-transfer-history__actions button {
  min-height: var(--r-touch-target);
  padding: 0 var(--r-space-2);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-sm);
  background: transparent;
  color: var(--r-color-fg);
  cursor: pointer;
}

.download-transfer-history time {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
}
</style>
