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

watch(
  () => [
    props.romId,
    props.selectedManifestId,
    props.sessionId,
    props.items.map((item) => `${item.file_id}:${item.status}`).join(","),
  ],
  hydrate,
  { immediate: true },
);
onBeforeUnmount(() => {
  requestVersion += 1;
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
    :loading="loading"
    :error="error"
  />
</template>
