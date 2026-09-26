<script setup lang="ts">
import { RAlert, RProgressLinear, RSpinner, RTag } from "@v2/lib";
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
  (event: "cancel-item", sessionId: string, itemId: number): void;
  (event: "resume", fileId: string): void;
  (event: "restart", fileId: string): void;
  (
    event: "resume-session",
    sessionId: string,
    memberId?: string,
    restartFromZero?: boolean,
  ): void;
  (event: "remove-item", sessionId: string, itemId: number): void;
  (event: "remove", sessionId: string): void;
  (event: "remove-all"): void;
  (event: "cancel-session", sessionId: string): void;
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
  sessionStatus: string;
  manifestMemberId: string | null;
  transferItemId: number | null;
  status: string;
  mode: string;
  destination: string | null;
  observedBytes: number;
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

function progressValue(item: BrowserQueueItem) {
  if (!item.size) return 100;
  return Math.min(100, ((item.observedBytes ?? 0) / item.size) * 100);
}

function progressColor(status: BrowserQueueItem["status"]) {
  if (status === "verified")
    return "color-mix(in srgb, var(--r-color-success) 42%, transparent)";
  if (status === "failed")
    return "color-mix(in srgb, var(--r-color-danger) 42%, transparent)";
  if (status === "cancelled") return "secondary";
  return "var(--r-color-brand-primary)";
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
      return [];
    }
    return session.items.map<HistoryRow>((item) => ({
      key: `${session.id}-${item.id}`,
      sessionId: session.id,
      sessionStatus: session.status,
      manifestMemberId: item.manifest_member_id,
      transferItemId: item.id,
      status: item.status,
      mode: session.mode,
      destination: item.destination,
      observedBytes: item.observed_bytes,
      bytes: item.expected_bytes,
      timestamp: item.last_activity_at ?? session.last_activity_at,
    }));
  }),
);
const terminalRows = computed(() =>
  rows.value.filter((row) =>
    ["completed", "cancelled", "failed", "expired", "stale"].includes(
      row.sessionStatus,
    ),
  ),
);
const displayRows = computed<HistoryRow[]>(() => {
  const live = new Map(props.queueItems.map((item) => [item.file_id, item]));
  const persistedIds = new Set(
    rows.value
      .map((row) => row.manifestMemberId)
      .filter((id): id is string => id !== null),
  );
  const merged = rows.value
    .map((row) => {
      const item = row.manifestMemberId
        ? live.get(row.manifestMemberId)
        : undefined;
      return item
        ? {
            ...row,
            status: item.status,
            bytes: item.size,
            observedBytes: item.observedBytes ?? row.observedBytes,
          }
        : row;
    })
    .filter((row) => row.manifestMemberId !== null);
  return merged.concat(
    props.queueItems
      .filter((item) => !persistedIds.has(item.file_id))
      .map<HistoryRow>((item) => ({
        key: `live-${item.file_id}`,
        sessionId: "",
        sessionStatus: "active",
        manifestMemberId: item.file_id,
        transferItemId: item.transferItemId ?? null,
        status: item.status,
        mode: "enhanced",
        destination: item.destination,
        observedBytes: item.observedBytes ?? 0,
        bytes: item.size,
        timestamp: "",
      })),
  );
});
function hasLiveMember(memberId: string | null) {
  return (
    !!memberId && props.queueItems.some((item) => item.file_id === memberId)
  );
}
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
      v-if="showHistory && terminalRows.length"
      type="button"
      class="download-transfer-history__remove-all"
      @click="emit('remove-all')"
    >
      {{ t("rom.download-remove-all") }}
    </button>

    <RSpinner
      v-if="loading"
      data-testid="download-history-loading"
      :aria-label="t('rom.download-state-downloading')"
    />
    <RAlert v-else-if="error" type="error" data-testid="download-history-error">
      {{ t("rom.download-failed-description") }}
    </RAlert>
    <ul
      v-else-if="showHistory && displayRows.length"
      class="download-transfer-history__rows"
      data-testid="download-history-list"
    >
      <li v-for="row in displayRows" :key="row.key">
        <div class="download-transfer-history__row-heading">
          <span v-if="row.destination">{{
            safeFilename(row.destination)
          }}</span>
          <RTag :text="statusText(row.status, row.mode)" />
        </div>
        <RProgressLinear
          v-if="row.destination"
          class="download-transfer-history__progress"
          :model-value="
            row.bytes
              ? Math.min(100, (row.observedBytes / row.bytes) * 100)
              : 100
          "
          :indeterminate="row.status === 'active' && row.observedBytes === 0"
          :color="
            ['verified', 'served', 'completed'].includes(row.status)
              ? 'color-mix(in srgb, var(--r-color-success) 42%, transparent)'
              : ['failed', 'stale'].includes(row.status)
                ? 'color-mix(in srgb, var(--r-color-danger) 42%, transparent)'
                : 'var(--r-color-brand-primary)'
          "
          :height="10"
          :aria-label="`${formatBytes(row.observedBytes)} / ${formatBytes(row.bytes)}`"
        />
        <div class="download-transfer-history__row-footer">
          <div class="download-transfer-history__row-meta">
            <span
              >{{ formatBytes(row.observedBytes) }} /
              {{ formatBytes(row.bytes) }}</span
            >
            <time v-if="row.timestamp" :datetime="row.timestamp">{{
              timestamp(row.timestamp)
            }}</time>
          </div>
          <div class="download-transfer-history__actions">
            <button
              v-if="row.status === 'downloading' && row.manifestMemberId"
              type="button"
              :aria-label="t('rom.download-pause')"
              @click="emit('pause', row.manifestMemberId)"
            >
              {{ t("rom.download-pause") }}
            </button>
            <button
              v-if="
                row.status === 'paused' &&
                row.manifestMemberId &&
                hasLiveMember(row.manifestMemberId)
              "
              type="button"
              :aria-label="t('rom.download-resume')"
              @click="emit('resume', row.manifestMemberId)"
            >
              {{ t("rom.download-resume") }}
            </button>
            <button
              v-if="
                row.mode === 'enhanced' &&
                ['failed', 'paused'].includes(row.status) &&
                row.manifestMemberId &&
                !hasLiveMember(row.manifestMemberId)
              "
              type="button"
              :aria-label="t('rom.download-prepare-again')"
              @click="
                emit(
                  'resume-session',
                  row.sessionId,
                  row.manifestMemberId,
                  true,
                )
              "
            >
              {{ t("rom.download-prepare-again") }}
            </button>
            <button
              v-if="
                row.mode === 'enhanced' &&
                row.status === 'failed' &&
                row.manifestMemberId &&
                !hasLiveMember(row.manifestMemberId)
              "
              type="button"
              :aria-label="t('rom.download-resume')"
              @click="
                emit('resume-session', row.sessionId, row.manifestMemberId)
              "
            >
              {{ t("rom.download-resume") }}
            </button>
            <button
              v-if="
                row.sessionStatus === 'active' &&
                ['queued', 'paused'].includes(row.status) &&
                !hasLiveMember(row.manifestMemberId)
              "
              type="button"
              :aria-label="t('rom.download-resume')"
              @click="
                emit(
                  'resume-session',
                  row.sessionId,
                  row.manifestMemberId ?? undefined,
                )
              "
            >
              {{ t("rom.download-resume") }}
            </button>
            <button
              v-if="
                row.sessionStatus === 'active' &&
                row.transferItemId !== null &&
                ['active', 'queued', 'paused'].includes(row.status) &&
                !hasLiveMember(row.manifestMemberId)
              "
              type="button"
              :aria-label="t('rom.download-cancel')"
              @click="emit('cancel-item', row.sessionId, row.transferItemId)"
            >
              {{ t("rom.download-cancel") }}
            </button>
            <button
              v-if="
                ['downloading', 'paused'].includes(row.status) &&
                hasLiveMember(row.manifestMemberId)
              "
              type="button"
              :aria-label="t('rom.download-cancel')"
              @click="emit('cancel', row.manifestMemberId!)"
            >
              {{ t("rom.download-cancel") }}
            </button>
            <button
              v-if="
                row.sessionStatus !== 'active' && row.transferItemId !== null
              "
              type="button"
              :aria-label="t('rom.download-remove-entry')"
              @click="emit('remove-item', row.sessionId, row.transferItemId)"
            >
              {{ t("rom.download-remove-entry") }}
            </button>
            <button
              v-else-if="row.sessionStatus !== 'active'"
              type="button"
              :aria-label="t('rom.download-remove-entry')"
              @click="emit('remove', row.sessionId)"
            >
              {{ t("rom.download-remove-entry") }}
            </button>
          </div>
        </div>
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
  flex-direction: column;
  align-items: stretch;
  gap: var(--r-space-2);
  padding: var(--r-space-3) var(--r-space-4);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  background: color-mix(in srgb, var(--r-color-panel) 72%, transparent);
}

.download-transfer-history__components {
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-sm);
}

.download-transfer-history__remove-all {
  position: sticky;
  top: var(--r-space-2);
  z-index: 2;
  align-self: flex-end;
  min-height: var(--r-touch-target);
  padding: 0 var(--r-space-3);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-sm);
  background: color-mix(in srgb, var(--r-color-panel) 92%, transparent);
  color: var(--r-color-fg);
  cursor: pointer;
}

.download-transfer-history ul {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.download-transfer-history__row-heading,
.download-transfer-history__row-footer,
.download-transfer-history__row-meta {
  display: flex;
  align-items: center;
  gap: var(--r-space-2);
}

.download-transfer-history__row-heading {
  justify-content: space-between;
  min-height: var(--r-touch-target);
}

.download-transfer-history__row-heading > span:first-child {
  flex: 1 1 12rem;
  overflow-wrap: anywhere;
}

.download-transfer-history__row-footer {
  justify-content: space-between;
  flex-wrap: wrap;
}

.download-transfer-history__row-meta {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
}

.download-transfer-history__progress {
  width: 100%;
  flex: 0 0 auto;
  min-height: 10px;
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
  justify-content: flex-end;
  gap: var(--r-space-2);
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

.download-transfer-history__actions button:hover {
  background: var(--r-color-panel);
}

.download-transfer-history time {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
}
</style>
