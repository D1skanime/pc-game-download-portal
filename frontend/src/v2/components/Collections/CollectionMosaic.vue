<script setup lang="ts">
// CollectionMosaic — 2×2 cover grid for collection artwork. Feature
// component used by CollectionTile and the collection info panel.
// Behaviour:
//   * 0 covers → empty state with a bookmark glyph
//   * 1 cover  → fills the whole square
//   * 2-4 covers → 2x2 grid; missing slots fill with an empty-tile bg
import { RIcon } from "@v2/lib";
import { computed } from "vue";

defineOptions({ inheritAttrs: false });

interface Props {
  covers?: (string | null | undefined)[];
  aspectRatio?: string;
  radius?: string;
}

const props = withDefaults(defineProps<Props>(), {
  covers: () => [],
  aspectRatio: "1 / 1",
  radius: "var(--r-radius-lg)",
});

const displayCovers = computed(() => (props.covers ?? []).filter(Boolean));
</script>

<template>
  <div
    class="coll-mosaic"
    :class="{ 'coll-mosaic--single': displayCovers.length <= 1 }"
    :style="{ aspectRatio, borderRadius: radius }"
  >
    <template v-if="!displayCovers.length">
      <div class="coll-mosaic__empty">
        <RIcon icon="mdi-bookmark-outline" size="40" />
      </div>
    </template>
    <template v-else-if="displayCovers.length === 1">
      <img :src="displayCovers[0] ?? undefined" alt="" />
    </template>
    <template v-else>
      <template v-for="i in 4" :key="`m-${i}`">
        <img
          v-if="displayCovers[i - 1]"
          :src="displayCovers[i - 1] ?? undefined"
          alt=""
        />
        <div v-else class="coll-mosaic__empty-cell" />
      </template>
    </template>
  </div>
</template>

<style scoped>
.coll-mosaic {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.04);
  width: 100%;
}

.coll-mosaic--single {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
}

.coll-mosaic img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.coll-mosaic__empty {
  grid-column: 1 / -1;
  grid-row: 1 / -1;
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.15);
}

.coll-mosaic__empty-cell {
  background: rgba(255, 255, 255, 0.04);
}

:global(.r-v2.r-v2-light) .coll-mosaic,
:global(.r-v2.r-v2-light) .coll-mosaic__empty-cell {
  background: rgba(17, 17, 23, 0.05);
}
:global(.r-v2.r-v2-light) .coll-mosaic__empty {
  color: rgba(17, 17, 23, 0.2);
}
</style>
