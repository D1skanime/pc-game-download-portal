<script setup lang="ts">
// ServerStats — v2 chrome around the v1 SummaryStats + PlatformsStats
// components. Data fetch is a single /stats call; the response shape is
// unchanged.
import { onBeforeMount, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { MetadataCoverageItem } from "@/__generated__/models/MetadataCoverageItem";
import type { RegionBreakdownItem } from "@/__generated__/models/RegionBreakdownItem";
import PlatformsStats from "@/components/Settings/ServerStats/PlatformsStats.vue";
import SummaryStats from "@/components/Settings/ServerStats/SummaryStats.vue";
import api from "@/services/api";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";

const { t } = useI18n();

const stats = ref({
  PLATFORMS: 0,
  ROMS: 0,
  SAVES: 0,
  STATES: 0,
  SCREENSHOTS: 0,
  TOTAL_FILESIZE_BYTES: 0,
  METADATA_COVERAGE: {} as Record<string, MetadataCoverageItem[]>,
  REGION_BREAKDOWN: {} as Record<string, RegionBreakdownItem[]>,
});

onBeforeMount(() => {
  api
    .get("/stats", { params: { include_platform_stats: true } })
    .then(({ data }) => {
      stats.value = data;
    });
});
</script>

<template>
  <SettingsShell
    :title="t('common.server-stats')"
    subtitle="Library-wide totals and per-platform breakdowns."
    icon="mdi-chart-bar"
    bare
  >
    <SummaryStats :stats="stats" />
    <PlatformsStats
      :total-filesize="stats.TOTAL_FILESIZE_BYTES"
      :metadata-coverage="stats.METADATA_COVERAGE"
      :region-breakdown="stats.REGION_BREAKDOWN"
    />
  </SettingsShell>
</template>
