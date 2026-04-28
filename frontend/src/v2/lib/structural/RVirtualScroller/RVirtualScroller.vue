<script setup lang="ts">
import { VVirtualScroll } from "vuetify/components/VVirtualScroll";

defineOptions({ inheritAttrs: false });

interface Props {
  /** Array of items to render. Only the visible window is in the DOM. */
  items: readonly unknown[];
  /** Fixed item height in pixels. Required for accurate windowing.
   * Pass undefined for dynamic measurement (slower; use only if items vary). */
  itemHeight?: number;
  /** Viewport height. Numeric is pixels; string accepts any CSS length.
   * Omit when the wrapper has its own size and should fill it. */
  height?: number | string;
  maxHeight?: number | string;
  minHeight?: number | string;
  /** Render a placeholder slot when items are not in the visible window. */
  renderless?: boolean;
}

defineProps<Props>();

defineSlots<{
  default(props: { item: unknown; index: number }): unknown;
}>();
</script>

<template>
  <VVirtualScroll
    v-bind="$attrs"
    class="r-virtual-scroller"
    :items="items as unknown[]"
    :item-height="itemHeight"
    :height="height"
    :max-height="maxHeight"
    :min-height="minHeight"
    :renderless="renderless"
  >
    <template #default="slotProps">
      <slot :item="slotProps.item" :index="slotProps.index" />
    </template>
  </VVirtualScroll>
</template>

<style scoped>
.r-virtual-scroller {
  background-color: transparent;
}
</style>
