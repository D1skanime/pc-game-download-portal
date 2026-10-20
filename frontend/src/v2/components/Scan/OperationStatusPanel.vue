<script setup lang="ts">
import { RAlert, RBtn, RCheckbox, RProgressLinear } from "@v2/lib";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import InventoryStatusSummary from "@/v2/components/Scan/InventoryStatusSummary.vue";
import type { ScanOperationSnapshot } from "@/v2/data/contracts";

interface Props {
  snapshot: ScanOperationSnapshot | null;
  checking: boolean;
  uncertain: boolean;
  disconnected: boolean;
  reconciling: boolean;
  actionError: string | null;
  status: string;
  canManage: boolean;
  hasMore?: boolean;
  loadingMore?: boolean;
}
const props = defineProps<Props>();
const emit = defineEmits<{
  loadMore: [];
  stop: [];
  resume: [];
  retryStatus: [];
  retry: [ids: string[]];
}>();
const { t } = useI18n();
const selected = ref<number[]>([]);
watch(
  () => props.snapshot?.attempt_id,
  () => {
    selected.value = [];
  },
);
const warnings = computed(() =>
  (props.snapshot?.items ?? []).filter(
    (item) => item.outcome === "warning" || item.outcome === "failed",
  ),
);
const running = computed(() =>
  ["accepted", "queued", "running", "recovering", "stopping"].includes(
    props.status,
  ),
);
const label = computed(() =>
  props.checking
    ? "checking"
    : props.snapshot
      ? props.status
      : props.actionError
        ? "failed"
        : "idle",
);
const stats = computed(() => props.snapshot?.scan_stats ?? {});
const total = computed(() => stats.value.total_roms ?? 0);
const progress = computed(() =>
  total.value > 0 && stats.value.scanned_roms !== undefined
    ? Math.min(100, (100 * (stats.value.scanned_roms ?? 0)) / total.value)
    : undefined,
);
const cause = computed(() => {
  const code = props.snapshot?.cause_code;
  if (props.uncertain || props.actionError === "acceptance-uncertain")
    return "uncertain";
  if (props.actionError === "permission-denied") return "permission";
  if (
    code?.startsWith("metadata_") ||
    code === "malformed_provider_response" ||
    code === "cache_publication_failed"
  )
    return "metadata";
  if (
    code === "dispatch_unavailable" ||
    code === "worker_lost" ||
    code === "worker_stop_unconfirmed"
  )
    return "worker";
  if (code === "mapping_changed") return "mapping";
  if (code?.startsWith("source_")) return "source";
  if (
    code ||
    props.actionError ||
    props.status === "failed" ||
    props.status === "blocked"
  )
    return "failed";
  return null;
});
function select(id: number, value: boolean | null) {
  selected.value = value
    ? [...new Set([...selected.value, id])]
    : selected.value.filter((item) => item !== id);
}
</script>

<template>
  <section
    class="d-flex flex-column ga-4 pa-4"
    aria-live="polite"
    aria-atomic="false"
    data-testid="operation-status"
  >
    <h2 role="status">{{ t("scan.recovery-" + label) }}</h2>
    <p v-if="disconnected">{{ t("scan.recovery-disconnected") }}</p>
    <p v-else-if="reconciling">{{ t("scan.recovery-reconciling") }}</p>
    <RProgressLinear
      v-if="running"
      :indeterminate="progress === undefined"
      :model-value="progress ?? 0"
      :aria-label="t('scan.recovery-running')"
    />
    <p v-if="total > 0 && stats.scanned_roms !== undefined">
      {{
        t("scan.recovery-progress", { current: stats.scanned_roms ?? 0, total })
      }}
    </p>
    <InventoryStatusSummary
      v-if="snapshot"
      :stats="snapshot.scan_stats"
      :items="snapshot.items ?? []"
      :has-more="hasMore"
      :loading-more="loadingMore"
      @load-more="emit('loadMore')"
    />
    <RAlert v-if="cause" type="warning" role="alert">
      <p>{{ t("scan.recovery-cause-" + cause) }}</p>
      <p>{{ t("scan.recovery-action-" + cause) }}</p>
    </RAlert>
    <div class="d-flex flex-wrap ga-3">
      <RBtn
        v-if="cause === 'permission'"
        :to="{ name: 'login', query: { next: '/scan' } }"
        >{{ t("scan.recovery-action-permission") }}</RBtn
      >
      <RBtn
        v-if="uncertain || disconnected || actionError"
        :disabled="checking"
        @click="emit('retryStatus')"
        >{{ t("scan.recovery-retry-status") }}</RBtn
      >
      <RBtn
        v-if="
          canManage && (running || ['blocked', 'interrupted'].includes(status))
        "
        :disabled="status === 'stopping' || checking"
        @click="emit('stop')"
        >{{ t("scan.recovery-stop") }}</RBtn
      >
      <RBtn
        v-if="canManage && ['cancelled', 'interrupted'].includes(status)"
        @click="emit('resume')"
        >{{ t("scan.recovery-resume") }}</RBtn
      >
    </div>
    <fieldset v-if="warnings.length" class="pa-3">
      <legend>{{ t("scan.recovery-warnings") }}</legend>
      <div
        v-for="item in warnings"
        :key="item.id"
        class="d-flex align-center ga-2"
      >
        <RCheckbox
          :model-value="selected.includes(item.id)"
          :disabled="!canManage"
          :label="
            t('scan.recovery-item', {
              game: item.target_key,
              provider: item.provider,
            })
          "
          @update:model-value="select(item.id, $event)"
        />
      </div>
      <RBtn
        v-if="canManage"
        :disabled="!selected.length || running"
        @click="emit('retry', selected.map(String))"
        >{{ t("scan.recovery-retry-metadata") }}</RBtn
      >
    </fieldset>
  </section>
</template>
