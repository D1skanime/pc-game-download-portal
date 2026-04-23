<script setup lang="ts">
// LetterGroupedGrid — the shared gallery body used by Platform.vue and
// Collection.vue. Given an already-grouped list, it paints:
//   * skeletons while first-loading
//   * an empty-state message when there is nothing to render
//   * the letter-heading + RGameCard grid per group
//   * a "Load N more" button when there are more results to page in
//
// The scroll container itself lives in the parent (it also wraps
// RInfoPanel), so we only render the content. `setLetterRef` comes from
// `useLetterGroups` and is how the composable spies on scroll position.
import { RGameCard, RSkeletonBlock } from "@v2/lib";
import type { LetterGroup } from "@/v2/composables/useLetterGroups";

defineOptions({ inheritAttrs: false });

defineProps<{
  groups: LetterGroup[];
  fetching: boolean;
  hasMore: boolean;
  remaining: number;
  webp: boolean;
  showPlatformBadge?: boolean;
  emptyLabel: string;
  skeletonCount?: number;
  setLetterRef: (letter: string, el: HTMLElement | null) => void;
}>();

defineEmits<{ (e: "load-more"): void }>();
</script>

<template>
  <template v-if="fetching && groups.length === 0">
    <div class="r-v2-lgg__grid">
      <RSkeletonBlock
        v-for="n in skeletonCount ?? 18"
        :key="`sk-${n}`"
        width="158px"
        height="238px"
        rounded="md"
      />
    </div>
  </template>

  <div v-else-if="!groups.length" class="r-v2-lgg__empty">
    {{ emptyLabel }}
  </div>

  <template v-else>
    <div
      v-for="group in groups"
      :key="group.letter"
      :ref="(el) => setLetterRef(group.letter, el as HTMLElement | null)"
      class="r-v2-lgg__letter"
    >
      <div class="r-v2-lgg__heading">
        {{ group.letter }}
      </div>
      <div class="r-v2-lgg__grid">
        <RGameCard
          v-for="rom in group.games"
          :key="rom.id"
          :rom="rom"
          :webp="webp"
          :show-platform-badge="showPlatformBadge"
        />
      </div>
    </div>

    <button
      v-if="hasMore"
      type="button"
      class="r-v2-lgg__more"
      :disabled="fetching"
      @click="$emit('load-more')"
    >
      {{ fetching ? "Loading…" : `Load ${remaining} more` }}
    </button>
  </template>
</template>

<style scoped>
.r-v2-lgg__letter {
  margin-bottom: 32px;
}

.r-v2-lgg__heading {
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.22);
  margin-bottom: 12px;
}

.r-v2-lgg__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, var(--r-card-art-w));
  gap: 18px 12px;
}

.r-v2-lgg__more {
  margin: 24px auto 0;
  display: flex;
  appearance: none;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.85);
  border-radius: var(--r-radius-pill);
  padding: 8px 22px;
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  cursor: pointer;
  font-family: inherit;
}
.r-v2-lgg__more:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.14);
}
.r-v2-lgg__more:disabled {
  opacity: 0.5;
  cursor: default;
}

.r-v2-lgg__empty {
  padding: 80px 0;
  color: rgba(255, 255, 255, 0.25);
  font-size: 13.5px;
  text-align: center;
}

@media (max-width: 768px) {
  .r-v2-lgg__grid {
    grid-template-columns: repeat(auto-fill, 130px);
    gap: 12px 10px;
  }
}
</style>
