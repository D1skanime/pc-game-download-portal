<script setup lang="ts">
// GameListSkeletonRow — bootstrap-phase placeholder row for list-mode.
//
// Painted by `GalleryShell` while the first metadata window is in
// flight (no `total` yet). Same wrapper class + grid template + height
// as a real `GameListRow` so the row swap to live data doesn't reflow
// the scroller. Each non-title column's skeleton width comes from
// `LIST_COLUMNS`, and the title column's cover dimensions come from
// the design tokens — there are no magic numbers in this file.
//
// `GameListRow` paints its own per-cell skeletons (when a row mounts
// before its position resolves) using the same per-column widths, so
// both skeleton flavours stay visually identical without sharing a
// component layer.
import { RSkeletonBlock } from "@v2/lib";
import {
  LIST_COLUMNS,
  LIST_COVER_HEIGHT_PX,
  LIST_COVER_WIDTH_PX,
  LIST_GRID_TEMPLATE,
} from "./listColumns";

defineOptions({ inheritAttrs: false });

const gridStyle = { gridTemplateColumns: LIST_GRID_TEMPLATE };
</script>

<template>
  <div class="game-list-row game-list-row--skeleton" :style="gridStyle">
    <template v-for="col in LIST_COLUMNS" :key="String(col.key)">
      <div
        v-if="col.key === 'name'"
        class="game-list-row__cell game-list-row__title"
      >
        <RSkeletonBlock
          :width="LIST_COVER_WIDTH_PX"
          :height="LIST_COVER_HEIGHT_PX"
        />
        <div class="game-list-row__meta">
          <RSkeletonBlock width="60%" height="12" />
          <RSkeletonBlock width="40%" height="10" />
        </div>
      </div>

      <div
        v-else-if="col.key === 'actions'"
        class="game-list-row__cell game-list-row__cell--end"
      />

      <div v-else class="game-list-row__cell">
        <RSkeletonBlock :width="col.skeletonWidth ?? 60" height="10" />
      </div>
    </template>
  </div>
</template>
