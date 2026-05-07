<script setup lang="ts">
// RelatedGamesGrid — one labelled grid of IGDBRelatedGame tiles.
//
// Used by both the "Additional content" tab (Expansions / DLC) and the
// "Related" tab (Remakes / Remasters / Similar). Multiple sections per
// tab? Render this component multiple times — one per section.
import type { IGDBRelatedGame } from "@/__generated__";

defineOptions({ inheritAttrs: false });

defineProps<{
  title?: string;
  items: IGDBRelatedGame[];
}>();
</script>

<template>
  <section v-if="items.length" class="r-v2-related">
    <h3 v-if="title" class="r-v2-related__title">
      {{ title }}
    </h3>
    <div class="r-v2-related__grid">
      <div v-for="g in items" :key="g.id" class="r-v2-related__card">
        <!-- `loading="eager"` is intentional: per-ROM related-games count
             stays small (a handful per category), so paying the bytes up
             front avoids pop-in when this section scrolls into view. Stays
             eager even if this grid is later wrapped in a virtual scroller. -->
        <img
          v-if="g.cover_url"
          class="r-v2-related__cover"
          :src="g.cover_url"
          :alt="g.name"
          loading="eager"
        />
        <div v-else class="r-v2-related__cover r-v2-related__cover--empty" />
        <div class="r-v2-related__name">
          {{ g.name }}
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.r-v2-related {
  margin-bottom: 24px;
}

.r-v2-related__title {
  margin: 0 0 10px 0;
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--r-color-fg-faint);
}

.r-v2-related__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 12px;
}

.r-v2-related__card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.r-v2-related__cover {
  aspect-ratio: 2 / 3;
  width: 100%;
  height: auto;
  object-fit: cover;
  display: block;
  border-radius: var(--r-radius-art);
  box-shadow: var(--r-elev-1);
}
.r-v2-related__cover--empty {
  background: var(--r-color-bg-elevated);
}

.r-v2-related__name {
  font-size: 11.5px;
  color: var(--r-color-fg-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.3;
}
</style>
