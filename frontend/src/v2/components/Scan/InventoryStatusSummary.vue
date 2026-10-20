<script setup lang="ts">
import { RBtn } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import InventoryStatusDetail from "@/v2/components/Scan/InventoryStatusDetail.vue";
import type {
  ScanOperationItemResult,
  ScanStatsTransport,
} from "@/v2/data/contracts";

const props = defineProps<{
  stats?: ScanStatsTransport;
  items: ScanOperationItemResult[];
  hasMore?: boolean;
  loadingMore?: boolean;
}>();
defineEmits<{ loadMore: [] }>();
const { t } = useI18n();
const metrics = [
  ["inventory_checked", "inventory-checked"],
  ["inventory_unchanged", "inventory-unchanged"],
  ["inventory_changed", "inventory-changed"],
  ["inventory_refresh_required", "inventory-refresh-required"],
  ["inventory_incomplete", "inventory-incomplete"],
  ["unresolved_games", "not-identified"],
  ["metadata_retry_games", "metadata-retry-games"],
  ["provider_requests", "provider-requests"],
] as const;
const available = computed(() =>
  metrics.filter(([field]) => props.stats?.[field] !== undefined),
);
const details = computed(() =>
  props.items.filter((item) => item.inventory || item.provider_execution),
);
</script>
<template>
  <div class="r-v2-inventory-summary" aria-live="off">
    <dl v-if="available.length" class="r-v2-inventory-summary__metrics">
      <div v-for="[field, label] in available" :key="field">
        <dt>{{ t("scan." + label) }}</dt>
        <dd>
          {{
            t(
              field === "provider_requests"
                ? "scan.provider-requests-count"
                : "scan.games-count",
              { n: stats![field] },
              stats![field],
            )
          }}
        </dd>
      </div>
    </dl>
    <ul v-if="details.length" class="r-v2-inventory-summary__details">
      <InventoryStatusDetail
        v-for="item in details"
        :key="item.id"
        :item="item"
      />
    </ul>
    <RBtn
      v-if="hasMore"
      :loading="loadingMore"
      :disabled="loadingMore"
      variant="outlined"
      @click="$emit('loadMore')"
      >{{ t("gallery.load-more") }}</RBtn
    >
  </div>
</template>
<style scoped>
.r-v2-inventory-summary {
  color: var(--r-color-fg-secondary);
  font-size: 13px;
  line-height: 1.4;
}
.r-v2-inventory-summary__metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 192px), 1fr));
  gap: 16px;
  margin: 0 0 16px;
}
.r-v2-inventory-summary__metrics dd {
  margin: 4px 0 0;
  color: var(--r-color-fg);
}
.r-v2-inventory-summary__details {
  padding: 0;
  margin: 0 0 16px;
  list-style: none;
}
</style>
