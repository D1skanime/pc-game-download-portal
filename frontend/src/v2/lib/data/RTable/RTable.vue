<script setup lang="ts">
// RTable — v2 wrapper around Vuetify's `v-data-table-server`. Keeps full
// Vuetify capability (sortable headers, server-side pagination, multi-
// select, row-click, hover, per-row slots) and applies RomM v2 visuals:
// translucent glass container, subtle row separators, hover tint, bold
// uppercase header row.
//
// Usage mirrors v-data-table-server — consumers pass `headers`, `items`,
// `items-length`, and listen for `@update:options` / `@click:row`. Any
// Vuetify slot or prop passes through.
import { computed } from "vue";
import {
  VDataTableServer,
  VDataTableVirtual,
  VDataTable,
} from "vuetify/components/VDataTable";

defineOptions({ inheritAttrs: false });

type Variant = "server" | "virtual" | "client";

interface Props {
  /** Backing component. "server" = server-paginated (v1 gallery table),
   *  "virtual" = virtualised client list, "client" = basic client-side. */
  variant?: Variant;
  density?: "default" | "comfortable" | "compact";
  rounded?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: "server",
  density: "compact",
  rounded: true,
});

const backing = computed(() => {
  if (props.variant === "virtual") return VDataTableVirtual;
  if (props.variant === "client") return VDataTable;
  return VDataTableServer;
});
</script>

<template>
  <component
    :is="backing"
    v-bind="$attrs"
    class="r-table"
    :class="{ 'r-table--rounded': rounded }"
    :density="density"
  >
    <template v-for="(_, slot) in $slots" #[slot]="slotProps">
      <slot :name="slot" v-bind="slotProps || {}" />
    </template>
  </component>
</template>

<style scoped>
.r-table {
  background: rgba(255, 255, 255, 0.03);
  color: var(--r-color-fg);
  font-size: 13px;
}

.r-table--rounded {
  border-radius: var(--r-radius-md);
  overflow: hidden;
}

/* Header row — bold uppercase, letter-spaced. Vuetify's fixed-header paints
   `thead th` with a solid `rgb(var(--v-theme-surface))` so rows don't bleed
   through on scroll; override with a translucent tint + blur so the header
   reads as glass instead of a flat bar. */
.r-table :deep(thead),
.r-table :deep(thead tr) {
  background: transparent !important;
}

.r-table :deep(thead th) {
  font-size: 10.5px !important;
  font-weight: var(--r-font-weight-bold) !important;
  letter-spacing: 0.07em !important;
  text-transform: uppercase !important;
  color: rgba(255, 255, 255, 0.55) !important;
  background: rgba(255, 255, 255, 0.02) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.r-table :deep(thead th .v-data-table-header__sort-icon) {
  color: rgba(255, 255, 255, 0.5);
}

/* Body rows — thin separators, hover tint, cursor pointer (rows are clickable). */
.r-table :deep(tbody td) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
  color: rgba(255, 255, 255, 0.85);
}

.r-table :deep(tbody tr:hover td) {
  background: rgba(255, 255, 255, 0.04) !important;
}

.r-table :deep(tbody tr.v-data-table__tr--selected td),
.r-table :deep(tbody tr[aria-selected="true"] td) {
  background: rgba(139, 116, 232, 0.12) !important;
  border-left: 2px solid var(--r-color-brand-primary) !important;
}

/* Footer */
.r-table :deep(.v-data-table-footer) {
  background: rgba(255, 255, 255, 0.03);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

/* Loader sits across the top */
.r-table :deep(.v-data-table__progress) {
  background: transparent;
}

/* Light theme */
:global(.r-v2.r-v2-light) .r-table {
  background: rgba(17, 17, 23, 0.03);
}
:global(.r-v2.r-v2-light) .r-table :deep(thead th) {
  color: rgba(17, 17, 23, 0.55) !important;
  background: rgba(17, 17, 23, 0.02) !important;
  border-bottom-color: rgba(17, 17, 23, 0.08) !important;
}
:global(.r-v2.r-v2-light) .r-table :deep(tbody td) {
  color: rgba(17, 17, 23, 0.85);
  border-bottom-color: rgba(17, 17, 23, 0.06) !important;
}
:global(.r-v2.r-v2-light) .r-table :deep(tbody tr:hover td) {
  background: rgba(17, 17, 23, 0.05) !important;
}
</style>
