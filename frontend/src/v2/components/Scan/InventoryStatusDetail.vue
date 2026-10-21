<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useScanInventoryStatus } from "@/v2/composables/useScanInventoryStatus";
import type { ScanOperationItemResult } from "@/v2/data/contracts";

const props = defineProps<{ item: ScanOperationItemResult }>();
const { t, locale } = useI18n();
const facts = useScanInventoryStatus(() => props.item);
const inventoryKeys = {
  unchanged: "inventory-unchanged",
  changed: "inventory-changed",
  refresh_required: "inventory-refresh-required",
  incomplete: "inventory-incomplete",
};
const providerKeys = {
  no_request: "provider-no-request",
  cached: "provider-cached",
  matched: "provider-matched",
  no_match: "provider-no-match",
  failed: "provider-failed",
  requested: "provider-waiting",
};
const retryKeys = {
  not_scheduled: "metadata-retry-not-scheduled",
  due: "metadata-retry-eligible",
  budget_deferred: "metadata-retry-deferred",
  configuration_blocked: "metadata-retry-config-required",
  baseline_required: "inventory-refresh-required",
  not_selected: "metadata-retry-not-scheduled",
  explicit: "metadata-retry-eligible",
  initial: "provider-waiting",
};
const retry = computed(() => {
  const state = facts.value.inventory?.retry_state;
  if (state === "cooldown") {
    const instant = facts.value.nextEligibleAt;
    if (!instant || !Number.isFinite(Date.parse(instant))) return undefined;
    const time = new Intl.DateTimeFormat(locale.value.replace("_", "-"), {
      dateStyle: "medium",
      timeStyle: "long",
      timeZone: "UTC",
    }).format(new Date(instant));
    return t("scan.metadata-retry-available-after", { time });
  }
  return state ? t("scan." + retryKeys[state]) : undefined;
});
</script>
<template>
  <li class="r-v2-inventory-detail">
    <p>
      {{
        t("scan.recovery-item", {
          game: item.relative_path,
          provider: item.provider,
        })
      }}
    </p>
    <p v-if="facts.unresolved === true">{{ t("scan.not-identified") }}</p>
    <p v-if="facts.inventory">
      {{ t("scan." + inventoryKeys[facts.inventory.inventory_state]) }}
    </p>
    <p v-if="facts.inventory?.inventory_state === 'incomplete'">
      {{ t("scan.inventory-incomplete-help") }}
    </p>
    <p v-if="facts.provider">
      {{
        facts.isIdentifying
          ? t("scan.provider-requesting", { provider: item.provider })
          : t("scan." + providerKeys[facts.provider.state])
      }}
    </p>
    <p v-if="facts.requests !== undefined">
      {{
        t("scan.provider-requests-count", { n: facts.requests }, facts.requests)
      }}
    </p>
    <p v-if="retry">{{ retry }}</p>
    <p v-if="facts.unresolved && facts.provider?.state === 'no_request'">
      {{ t("scan.unidentified-no-request-help") }}
    </p>
  </li>
</template>
<style scoped>
.r-v2-inventory-detail {
  padding: 16px 0;
  border-top: 1px solid var(--r-color-border);
  overflow-wrap: anywhere;
}
.r-v2-inventory-detail p {
  margin: 0 0 4px;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.4;
}
</style>
