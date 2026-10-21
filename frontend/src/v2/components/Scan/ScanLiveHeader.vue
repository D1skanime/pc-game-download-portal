<script setup lang="ts">
import { RBtn, RProgressLinear } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { ScanStatsTransport } from "@/v2/data/contracts";

const props = defineProps<{
  label: string;
  stats?: ScanStatsTransport;
  scanning: boolean;
  canManage: boolean;
}>();
defineEmits<{ stop: [] }>();
const { t } = useI18n();
const total = computed(() => props.stats?.total_roms);
const current = computed(() => props.stats?.scanned_roms);
const progress = computed(() =>
  total.value !== undefined && total.value > 0 && current.value !== undefined
    ? Math.min(100, (current.value / total.value) * 100)
    : undefined,
);
</script>
<template>
  <header class="r-v2-scan-live-header pa-4 d-flex flex-column ga-4">
    <div class="d-flex align-center justify-space-between ga-4">
      <span>{{ label }}</span>
      <RBtn
        v-if="scanning && canManage"
        icon="mdi-stop-circle-outline"
        variant="text"
        :aria-label="t('scan.abort-scan')"
        @click="$emit('stop')"
      />
    </div>
    <p v-if="total !== undefined && current !== undefined">
      {{ t("scan.recovery-progress", { current, total }) }}
    </p>
    <RProgressLinear
      v-if="scanning"
      :indeterminate="progress === undefined"
      :model-value="progress ?? 0"
      :aria-label="t('scan.recovery-running')"
    />
  </header>
</template>
<style scoped>
.r-v2-scan-live-header {
  border-bottom: 1px solid var(--r-color-border);
  font-size: 13px;
  color: var(--r-color-fg);
}
</style>
