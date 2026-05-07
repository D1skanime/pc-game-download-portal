<script setup lang="ts">
// CollectionListHeader — column-header strip for the Collections
// list-mode view. Mirrors GameListHeader's anatomy without sortable
// columns; collection ordering follows the store's natural order today.
import { COLLECTION_LIST_GRID_TEMPLATE } from "./collectionListColumns";

const gridStyle = { gridTemplateColumns: COLLECTION_LIST_GRID_TEMPLATE };
</script>

<template>
  <div class="coll-list-header" :style="gridStyle" role="row">
    <div class="coll-list-header__cell">
      <span class="coll-list-header__label">Name</span>
    </div>
    <div class="coll-list-header__cell">
      <span class="coll-list-header__label">Kind</span>
    </div>
    <div class="coll-list-header__cell coll-list-header__cell--end">
      <span class="coll-list-header__label">Games</span>
    </div>
  </div>
</template>

<style scoped>
.coll-list-header {
  display: grid;
  align-items: center;
  gap: 0 var(--r-space-3);
  padding: 0 var(--r-space-3);
  height: var(--r-list-header-h);
  background: var(--r-color-bg-elevated);
  border-bottom: 1px solid var(--r-color-border);
}

.coll-list-header__cell {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  height: 100%;
}

.coll-list-header__cell--end {
  justify-content: flex-end;
}

.coll-list-header__label {
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
