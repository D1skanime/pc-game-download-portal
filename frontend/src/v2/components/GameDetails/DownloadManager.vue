<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { DownloadTransferResponse } from "@/__generated__";
import downloadTransfersApi from "@/services/api/downloadTransfers";
import {
  isEnhancedDownloadSupported,
  type BrowserQueueItem,
} from "@/v2/composables/useBrowserDownloadQueue";
import DownloadTransferHistory from "./DownloadTransferHistory.vue";

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
  (event: "clear-terminal", fileIds: string[]): void;
}>();

const props = withDefaults(
  defineProps<{
    romId: number;
    items: BrowserQueueItem[];
    selectedManifestId?: string | null;
    sessionId?: string | null;
    componentLabels?: string[];
  }>(),
  { selectedManifestId: null, sessionId: null, componentLabels: () => [] },
);

const sessions = ref<DownloadTransferResponse[]>([]);
const loading = ref(false);
const error = ref(false);
let requestVersion = 0;
let standardRefreshTimer: ReturnType<typeof setTimeout> | undefined;

function scheduleStandardRefresh(session: DownloadTransferResponse) {
  if (standardRefreshTimer !== undefined) {
    clearTimeout(standardRefreshTimer);
    standardRefreshTimer = undefined;
  }
  if (session.mode !== "standard" || session.status !== "active") return;
  standardRefreshTimer = setTimeout(() => {
    standardRefreshTimer = undefined;
    void hydrate();
  }, 1_000);
}

function upsertSession(
  values: DownloadTransferResponse[],
  current: DownloadTransferResponse,
) {
  return [current, ...values.filter((session) => session.id !== current.id)];
}

async function hydrate() {
  const version = ++requestVersion;
  loading.value = true;
  error.value = false;
  try {
    const response = await downloadTransfersApi.list({
      romId: props.romId,
      ...(props.selectedManifestId
        ? { manifestId: props.selectedManifestId }
        : {}),
    });
    if (version !== requestVersion) return;
    const filtered = response.data.filter(
      (session) =>
        session.rom_id === props.romId &&
        (!props.selectedManifestId ||
          session.manifest_id === props.selectedManifestId),
    );
    sessions.value = filtered;
    if (props.sessionId) {
      const current = await downloadTransfersApi.get(props.sessionId);
      if (version !== requestVersion) return;
      if (
        current.data.rom_id === props.romId &&
        (!props.selectedManifestId ||
          current.data.manifest_id === props.selectedManifestId)
      ) {
        sessions.value = upsertSession(sessions.value, current.data);
        scheduleStandardRefresh(current.data);
        if (
          current.data.mode === "standard" &&
          current.data.status !== "active"
        ) {
          emit(
            "clear-terminal",
            current.data.items.map((item) => item.manifest_member_id),
          );
        }
      }
    }
  } catch {
    if (version !== requestVersion) return;
    sessions.value = [];
    error.value = true;
  } finally {
    if (version === requestVersion) loading.value = false;
  }
}

async function removeSession(sessionId: string) {
  try {
    await downloadTransfersApi.remove(sessionId);
    sessions.value = sessions.value.filter(
      (session) => session.id !== sessionId,
    );
  } catch {
    await hydrate();
  }
}

async function removeItem(sessionId: string, itemId: number) {
  try {
    await downloadTransfersApi.removeItem(sessionId, itemId);
    await hydrate();
  } catch {
    await hydrate();
  }
}

async function removeAllHistory() {
  try {
    await downloadTransfersApi.removeAll({ romId: props.romId });
    sessions.value = sessions.value.filter(
      (session) => session.status === "active",
    );
    emit(
      "clear-terminal",
      props.items
        .filter((item) =>
          ["verified", "failed", "cancelled"].includes(item.status),
        )
        .map((item) => item.file_id),
    );
  } catch {
    await hydrate();
  }
}

async function cancelSession(sessionId: string) {
  try {
    const response = await downloadTransfersApi.cancel(sessionId);
    sessions.value = sessions.value.map((session) =>
      session.id === sessionId ? response.data : session,
    );
  } catch {
    await hydrate();
  }
}

async function cancelItem(sessionId: string, itemId: number) {
  try {
    await downloadTransfersApi.observe(sessionId, itemId, {
      event_type: "cancel",
    });
    await hydrate();
  } catch {
    await hydrate();
  }
}

function resumeSession(
  sessionId: string,
  memberId?: string,
  restartFromZero = false,
) {
  emit("resume-session", sessionId, memberId, restartFromZero);
}

watch(() => [props.romId, props.selectedManifestId, props.sessionId], hydrate, {
  immediate: true,
});
onBeforeUnmount(() => {
  requestVersion += 1;
  if (standardRefreshTimer !== undefined) clearTimeout(standardRefreshTimer);
});
</script>
<template>
  <p v-if="isEnhancedDownloadSupported()" data-testid="enhanced-download-mode">
    {{ t("rom.download-enhanced-mode") }}
  </p>
  <DownloadTransferHistory
    data-testid="download-manager"
    :sessions="sessions"
    :queue-items="items"
    :component-labels="componentLabels"
    :show-history="true"
    :loading="loading"
    :error="error"
    @pause="emit('pause', $event)"
    @cancel="emit('cancel', $event)"
    @cancel-item="cancelItem"
    @resume="emit('resume', $event)"
    @restart="emit('restart', $event)"
    @resume-session="resumeSession"
    @remove="removeSession"
    @remove-item="removeItem"
    @remove-all="removeAllHistory"
    @cancel-session="cancelSession"
  />
</template>
