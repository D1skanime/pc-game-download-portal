<script setup lang="ts">
// PlatformListHeader — column-header strip for the Platforms list-mode
// view. Mirrors GameListHeader's anatomy (sticky title row above the
// rows, shared CSS-grid template) but without sortable columns — the
// platforms index is small enough that fixed alphabetical order is
// fine. Kept as a separate component for visual parity with the ROM
// gallery and so the grid template lives next to its consumers.
import { PLATFORM_LIST_GRID_TEMPLATE } from "./platformListColumns";

const gridStyle = { gridTemplateColumns: PLATFORM_LIST_GRID_TEMPLATE };
</script>

<template>
  <div class="plat-list-header" :style="gridStyle" role="row">
    <div class="plat-list-header__cell">
      <span class="plat-list-header__label">Name</span>
    </div>
    <div class="plat-list-header__cell plat-list-header__cell--end">
      <span class="plat-list-header__label">Games</span>
    </div>
  </div>
</template>

<style scoped>
.plat-list-header {
  display: grid;
  align-items: center;
  gap: 0 var(--r-space-3);
  padding: 0 var(--r-space-3);
  height: var(--r-list-header-h);
  background: var(--r-color-bg-elevated);
  border-bottom: 1px solid var(--r-color-border);
}

.plat-list-header__cell {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  height: 100%;
}

.plat-list-header__cell--end {
  justify-content: flex-end;
}

.plat-list-header__label {
  font-size: var(--r-font-size-xs);
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--r-color-fg-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
