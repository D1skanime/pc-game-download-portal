<script setup lang="ts">
// GameGrid — responsive grid of ROM covers with skeleton placeholders on
// initial load. Feature composition around GameCard + RSkeletonBlock;
// Search is the main caller.
import { RSkeletonBlock } from "@v2/lib";
import { computed } from "vue";
import type { SimpleRom } from "@/stores/roms";
import { GameCard } from "@/v2/components/Gallery/GameCard";

defineOptions({ inheritAttrs: false });

interface Props {
  roms: SimpleRom[];
  loading?: boolean;
  skeletonCount?: number;
  minCardWidth?: string;
  webp?: boolean;
  showPlatformIcon?: boolean;
  showTitle?: boolean;
  selectedIds?: Set<number>;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  skeletonCount: 12,
  minCardWidth: "160px",
  webp: false,
  showPlatformIcon: true,
  showTitle: true,
  selectedIds: () => new Set<number>(),
});

const isInitialLoad = computed(() => props.loading && props.roms.length === 0);

const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(${props.minCardWidth}, 1fr))`,
}));
</script>

<template>
  <div class="game-grid" :style="gridStyle">
    <template v-if="isInitialLoad">
      <div
        v-for="n in skeletonCount"
        :key="`sk-${n}`"
        class="game-grid__skeleton"
      >
        <RSkeletonBlock width="100%" height="100%" rounded="md" />
        <RSkeletonBlock :width="120" :height="14" class="mt-2" />
      </div>
    </template>
    <template v-else>
      <GameCard
        v-for="rom in roms"
        :key="rom.id"
        :rom="rom"
        :webp="webp"
        :show-platform-icon="showPlatformIcon"
        :show-title="showTitle"
        :selected="selectedIds.has(rom.id)"
      />
    </template>
  </div>
</template>

<style scoped>
.game-grid {
  display: grid;
  gap: var(--r-space-5) var(--r-space-4);
}

.game-grid__skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  aspect-ratio: 2 / 3;
}

.game-grid__skeleton > :first-child {
  flex: 1;
  min-height: 0;
}

.mt-2 {
  margin-top: var(--r-space-2);
}
</style>
