<script setup lang="ts">
// OverviewTab — summary paragraph, status badge, labeled info grid
// (genres / developer / franchise / collections) and the HLTB strip.
import type { RomHLTBMetadata } from "@/__generated__";
import HLTBStrip from "@/v2/components/GameDetails/HLTBStrip.vue";
import type { InfoGridSection } from "@/v2/components/GameDetails/InfoGrid.vue";
import InfoGrid from "@/v2/components/GameDetails/InfoGrid.vue";

defineOptions({ inheritAttrs: false });

defineProps<{
  summary: string | null | undefined;
  statusDisplay: { emoji: string; text: string } | null;
  sections: InfoGridSection[];
  hltb: RomHLTBMetadata | null | undefined;
}>();
</script>

<template>
  <section class="r-v2-det-overview">
    <p v-if="summary" class="r-v2-det-overview__summary">
      {{ summary }}
    </p>
    <p
      v-else
      class="r-v2-det-overview__summary r-v2-det-overview__summary--muted"
    >
      No summary yet. Match this ROM to a metadata source to pull in a
      description, genres, and release date.
    </p>

    <div v-if="statusDisplay" class="r-v2-det-overview__status">
      <span>{{ statusDisplay.emoji }}</span>
      {{ statusDisplay.text }}
    </div>

    <InfoGrid :sections="sections" />
    <HLTBStrip :metadata="hltb" />
  </section>
</template>

<style scoped>
.r-v2-det-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 720px;
}

.r-v2-det-overview__summary {
  font-size: 13.5px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.65);
  margin: 0;
}
.r-v2-det-overview__summary--muted {
  font-style: italic;
  color: rgba(255, 255, 255, 0.35);
}

.r-v2-det-overview__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.4);
  color: #fff;
  font-size: 12.5px;
  font-weight: var(--r-font-weight-semibold);
  align-self: flex-start;
}
</style>
