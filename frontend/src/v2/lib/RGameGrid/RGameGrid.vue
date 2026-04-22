<script setup lang="ts">
import { RGameCard, RSkeletonBlock } from "@v2/lib";
import { computed } from "vue";
import type { SimpleRom } from "@/stores/roms";

defineOptions({ inheritAttrs: false });

// RGameGrid — responsive grid of game covers. Caller controls density via
// `minCardWidth` (CSS grid auto-fill). Shows skeletons during initial load.
interface Props {
  roms: SimpleRom[];
  loading?: boolean;
  skeletonCount?: number;
  minCardWidth?: string;
  webp?: boolean;
  showPlatform?: boolean;
  showTitle?: boolean;
  selectedIds?: Set<number>;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  skeletonCount: 12,
  minCardWidth: "160px",
  webp: false,
  showPlatform: true,
  showTitle: true,
  selectedIds: () => new Set<number>(),
});

const isInitialLoad = computed(() => props.loading && props.roms.length === 0);

const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(${props.minCardWidth}, 1fr))`,
}));
</script>

<template>
  <div class="r-game-grid" :style="gridStyle">
    <template v-if="isInitialLoad">
      <div
        v-for="n in skeletonCount"
        :key="`sk-${n}`"
        class="r-game-grid__skeleton"
      >
        <RSkeletonBlock width="100%" height="100%" rounded="md" />
        <RSkeletonBlock :width="120" :height="14" class="mt-2" />
      </div>
    </template>
    <template v-else>
      <RGameCard
        v-for="rom in roms"
        :key="rom.id"
        :rom="rom"
        :webp="webp"
        :show-platform="showPlatform"
        :show-title="showTitle"
        :selected="selectedIds.has(rom.id)"
      />
    </template>
  </div>
</template>

<style scoped>
.r-game-grid {
  display: grid;
  gap: var(--r-space-5) var(--r-space-4);
}

.r-game-grid__skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  aspect-ratio: 2 / 3;
}

.r-game-grid__skeleton > :first-child {
  flex: 1;
  min-height: 0;
}

.mt-2 {
  margin-top: var(--r-space-2);
}
</style>
