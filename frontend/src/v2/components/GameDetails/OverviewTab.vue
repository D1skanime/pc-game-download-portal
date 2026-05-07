<script setup lang="ts">
// OverviewTab — single landing surface for everything that doesn't get
// its own tab. Top to bottom:
//   1. Summary paragraph
//   2. Last-played row (TODO: move into a SaveData tab once it lands)
//   3. Info grid (genres / developer / franchise / collections)
//   4. HLTB strip
//   5. Related games — a single RCollapsible collapsing all of:
//      Expansions, DLC, Remakes, Remasters, Similar games.
//
// Status enum + flags (now_playing / backlogged / hidden) and personal
// metrics (rating / difficulty / completion) live in the action ribbon
// — see GameActionBtn (status) and MetricMenuBtn.
import { RCollapsible, RIcon } from "@v2/lib";
import { computed } from "vue";
import type { IGDBRelatedGame, RomHLTBMetadata } from "@/__generated__";
import type { DetailedRom } from "@/stores/roms";
import HLTBStrip from "@/v2/components/GameDetails/HLTBStrip.vue";
import type { InfoGridSection } from "@/v2/components/GameDetails/InfoGrid.vue";
import InfoGrid from "@/v2/components/GameDetails/InfoGrid.vue";
import RelatedGamesGrid from "@/v2/components/GameDetails/RelatedGamesGrid.vue";

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  rom: DetailedRom;
  summary: string | null | undefined;
  sections: InfoGridSection[];
  hltb: RomHLTBMetadata | null | undefined;
  lastPlayed: string | null;
  expansions: IGDBRelatedGame[];
  dlcs: IGDBRelatedGame[];
  remakes: IGDBRelatedGame[];
  remasters: IGDBRelatedGame[];
  similarGames: IGDBRelatedGame[];
}>();

const romUser = computed(() => props.rom.rom_user);

// Related — show the panel only if at least one section has items.
const hasRelated = computed(
  () =>
    props.expansions.length +
      props.dlcs.length +
      props.remakes.length +
      props.remasters.length +
      props.similarGames.length >
    0,
);
</script>

<template>
  <section class="overview-tab">
    <!-- 1. Summary -->
    <p v-if="summary" class="overview-tab__summary">{{ summary }}</p>

    <!-- 2. Last played (will move into a SaveData tab once it lands) -->
    <div v-if="romUser" class="overview-tab__personal">
      <div class="overview-tab__row">
        <div class="overview-tab__label">Last played</div>
        <div class="overview-tab__field">
          <span v-if="lastPlayed">{{ lastPlayed }}</span>
          <span v-else class="overview-tab__muted">Never</span>
        </div>
      </div>
    </div>

    <!-- 3. Info grid + 4. HLTB -->
    <InfoGrid :sections="sections" />
    <HLTBStrip :metadata="hltb" />

    <!-- 5. Related games (single collapsible, every section labelled) -->
    <RCollapsible
      v-if="hasRelated"
      default-open
      title="Related games"
      icon="mdi-gamepad-square-outline"
    >
      <div class="overview-tab__related">
        <div v-if="expansions.length" class="overview-tab__related-section">
          <h4 class="overview-tab__related-heading">
            <RIcon icon="mdi-puzzle-outline" size="14" />
            Expansions
          </h4>
          <RelatedGamesGrid title="" :items="expansions" />
        </div>
        <div v-if="dlcs.length" class="overview-tab__related-section">
          <h4 class="overview-tab__related-heading">
            <RIcon icon="mdi-package-variant-closed" size="14" />
            DLC
          </h4>
          <RelatedGamesGrid title="" :items="dlcs" />
        </div>
        <div v-if="remakes.length" class="overview-tab__related-section">
          <h4 class="overview-tab__related-heading">
            <RIcon icon="mdi-refresh" size="14" />
            Remakes
          </h4>
          <RelatedGamesGrid title="" :items="remakes" />
        </div>
        <div v-if="remasters.length" class="overview-tab__related-section">
          <h4 class="overview-tab__related-heading">
            <RIcon icon="mdi-image-auto-adjust" size="14" />
            Remasters
          </h4>
          <RelatedGamesGrid title="" :items="remasters" />
        </div>
        <div v-if="similarGames.length" class="overview-tab__related-section">
          <h4 class="overview-tab__related-heading">
            <RIcon icon="mdi-shape-outline" size="14" />
            Similar games
          </h4>
          <RelatedGamesGrid title="" :items="similarGames" />
        </div>
      </div>
    </RCollapsible>
  </section>
</template>

<style scoped>
.overview-tab {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.overview-tab__summary {
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--r-color-fg-secondary);
  margin: 0;
}
.overview-tab__summary--muted {
  font-style: italic;
  color: var(--r-color-fg-muted);
}

/* Personal — label/value rows. */
.overview-tab__personal {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.overview-tab__row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.overview-tab__label {
  width: 120px;
  flex-shrink: 0;
  font-size: 10.5px;
  font-weight: var(--r-font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--r-color-fg-faint);
}
.overview-tab__field {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}
.overview-tab__muted {
  color: var(--r-color-fg-faint);
  font-style: italic;
}

/* Related expansion content */
.overview-tab__related {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 10px;
}
.overview-tab__related-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.overview-tab__related-heading {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--r-color-fg-faint);
}
</style>
