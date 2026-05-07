<script setup lang="ts">
// PlatformListRow — single row of the Platforms list-mode index.
//
// Anatomy mirrors GameListRow: thumb (RPlatformIcon at the same 48px
// scale used in the ROM list cover slot) + name stack on the left, game
// count column on the right. Click navigates to /platform/<id> with the
// same shared-element morph as PlatformTile so switching between grid
// and list modes lands on the same destination animation.
import { RPlatformIcon } from "@v2/lib";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import {
  pendingMorphName,
  useViewTransition,
} from "@/v2/composables/useViewTransition";
import { PLATFORM_LIST_GRID_TEMPLATE } from "./platformListColumns";

defineOptions({ inheritAttrs: false });

interface Props {
  id: number | string;
  slug: string;
  fsSlug?: string;
  displayName: string;
  romCount?: number | null;
}

const props = withDefaults(defineProps<Props>(), {
  fsSlug: undefined,
  romCount: null,
});

const router = useRouter();
const iconEl = ref<HTMLElement | null>(null);
const { morphTransition } = useViewTransition();

const href = computed(() => `/platform/${props.id}`);

const morphName = computed(() => `platform-icon-${props.id}`);

const morphStyle = computed(() =>
  pendingMorphName.value === morphName.value
    ? { viewTransitionName: morphName.value }
    : undefined,
);

const gridStyle = { gridTemplateColumns: PLATFORM_LIST_GRID_TEMPLATE };

function onRowClick(e: MouseEvent) {
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) {
    return;
  }
  if (!iconEl.value) return;
  e.preventDefault();
  morphTransition({ el: iconEl.value, name: morphName.value }, async () => {
    await router.push(href.value);
  });
}
</script>

<template>
  <a
    class="plat-list-row"
    :style="gridStyle"
    :href="href"
    :aria-label="`Open ${displayName}`"
    @click="onRowClick"
  >
    <div class="plat-list-row__cell plat-list-row__title">
      <div ref="iconEl" class="plat-list-row__thumb" :style="morphStyle">
        <RPlatformIcon
          :slug="slug"
          :fs-slug="fsSlug"
          :alt="displayName"
          :size="40"
        />
      </div>
      <div class="plat-list-row__meta">
        <div class="plat-list-row__name">{{ displayName }}</div>
        <div class="plat-list-row__slug">{{ slug }}</div>
      </div>
    </div>

    <div class="plat-list-row__cell plat-list-row__cell--end">
      <span v-if="romCount != null">
        {{ romCount }}
        <span class="plat-list-row__count-unit">{{
          romCount === 1 ? "game" : "games"
        }}</span>
      </span>
      <span v-else class="plat-list-row__count-unit">—</span>
    </div>
  </a>
</template>

<style scoped>
.plat-list-row {
  display: grid;
  align-items: center;
  gap: 0 var(--r-space-3);
  padding: 0 var(--r-space-3);
  height: var(--r-list-row-h);
  border-bottom: 1px solid var(--r-color-border);
  font-size: var(--r-font-size-md);
  color: var(--r-color-fg-secondary);
  text-decoration: none;
  cursor: pointer;
  transition: background var(--r-motion-fast) var(--r-motion-ease-out);
}

.plat-list-row:hover {
  background: var(--r-color-bg-elevated);
}

.plat-list-row:focus-visible {
  outline: none;
  background: var(--r-color-bg-elevated);
  box-shadow: inset 0 0 0 2px var(--r-color-brand-primary);
}

.plat-list-row__cell {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.plat-list-row__cell--end {
  display: flex;
  justify-content: flex-end;
}

.plat-list-row__title {
  display: flex;
  align-items: center;
  gap: var(--r-space-3);
  min-width: 0;
}

.plat-list-row__thumb {
  width: var(--r-list-cover-w);
  height: var(--r-list-cover-w);
  flex-shrink: 0;
  border-radius: var(--r-radius-sm);
  background: var(--r-color-surface);
  display: grid;
  place-items: center;
}

.plat-list-row__thumb :deep(.r-platform-icon__img) {
  opacity: 0.9;
}

.plat-list-row__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.plat-list-row__name {
  font-size: var(--r-font-size-md);
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.plat-list-row__slug {
  font-size: var(--r-font-size-sm);
  color: var(--r-color-fg-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.plat-list-row__count-unit {
  color: var(--r-color-fg-muted);
}
</style>
