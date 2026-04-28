<script setup lang="ts">
// GameGrid — virtualized responsive grid of ROM covers. The component is
// self-scrolling: only the rows in the visible window mount cards, so
// libraries with thousands of ROMs no longer pay the cost of mounting
// every GameCard upfront. Skeletons cover the initial-load empty state.
// Search, Platform and Collection views host this directly.
import { RSkeletonBlock, RVirtualScroller } from "@v2/lib";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import type { SimpleRom } from "@/stores/roms";
import { GameCard } from "@/v2/components/Gallery/GameCard";

defineOptions({ inheritAttrs: false });

interface Props {
  roms: SimpleRom[];
  loading?: boolean;
  skeletonCount?: number;
  /** Card art width in pixels (matches --r-card-art-w by default). */
  cardWidth?: number;
  /** Total card height (cover + title band) in pixels. */
  cardHeight?: number;
  /** Pixel gap between rows and columns. */
  gap?: number;
  webp?: boolean;
  showPlatform?: boolean;
  showTitle?: boolean;
  selectedIds?: Set<number>;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  skeletonCount: 12,
  cardWidth: 158,
  cardHeight: 244,
  gap: 18,
  webp: false,
  showPlatform: true,
  showTitle: true,
  selectedIds: () => new Set<number>(),
});

const root = ref<HTMLElement | null>(null);
const containerWidth = ref(0);

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (!root.value) return;
  containerWidth.value = root.value.clientWidth;
  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      containerWidth.value = entry.contentRect.width;
    }
  });
  resizeObserver.observe(root.value);
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
});

const cols = computed(() => {
  if (!containerWidth.value) return 1;
  // (width + gap) absorbs the trailing gap an auto-fill grid would have hidden.
  const c = Math.floor(
    (containerWidth.value + props.gap) / (props.cardWidth + props.gap),
  );
  return Math.max(1, c);
});

const rows = computed<SimpleRom[][]>(() => {
  const out: SimpleRom[][] = [];
  const c = cols.value;
  for (let i = 0; i < props.roms.length; i += c) {
    out.push(props.roms.slice(i, i + c));
  }
  return out;
});

const rowHeight = computed(() => props.cardHeight + props.gap);

const isInitialLoad = computed(() => props.loading && props.roms.length === 0);
</script>

<template>
  <div ref="root" class="game-grid">
    <div
      v-if="isInitialLoad"
      class="game-grid__skeletons"
      :style="{ gap: `${gap}px` }"
    >
      <div
        v-for="n in skeletonCount"
        :key="`sk-${n}`"
        class="game-grid__skeleton"
        :style="{ width: `${cardWidth}px`, height: `${cardHeight}px` }"
      >
        <RSkeletonBlock width="100%" height="100%" rounded="md" />
      </div>
    </div>
    <RVirtualScroller
      v-else
      :items="rows"
      :item-height="rowHeight"
      height="100%"
      class="game-grid__scroller"
    >
      <template #default="{ item }">
        <div
          class="game-grid__row"
          :style="{ gap: `${gap}px`, height: `${rowHeight}px` }"
        >
          <GameCard
            v-for="rom in item as SimpleRom[]"
            :key="rom.id"
            :rom="rom"
            :webp="webp"
            :show-platform="showPlatform"
            :show-title="showTitle"
            :selected="selectedIds.has(rom.id)"
          />
        </div>
      </template>
    </RVirtualScroller>
  </div>
</template>

<style scoped>
.game-grid {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.game-grid__scroller {
  flex: 1;
  min-height: 0;
}

.game-grid__row {
  display: flex;
  flex-wrap: nowrap;
  align-items: flex-start;
}

.game-grid__skeletons {
  display: flex;
  flex-wrap: wrap;
}

.game-grid__skeleton {
  flex: 0 0 auto;
}
</style>
