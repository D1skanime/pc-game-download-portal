<script setup lang="ts">
// RVirtualScroller — windowed list/grid surface around v-virtual-scroll.
//
// Exposes:
//   * `scrollToIndex(index, { smooth })` — jumps the inner scroller to an
//     item. With `smooth: true` the destination scrollTop is computed via
//     Vuetify (which sets scrollTop synchronously), then re-applied with
//     native `scrollTo({ behavior: 'smooth' })` so the user sees an
//     animated transition instead of a hard jump.
//   * `containerEl`                       — the scrolling DOM element.
//                                           Consumers attach
//                                           IntersectionObservers, read
//                                           scrollTop, etc.
// The scroll event from the inner element is forwarded as a normal `scroll`
// event so consumers can `@scroll` directly.
import { onMounted, ref } from "vue";
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

const scrollerRef = ref<InstanceType<typeof VVirtualScroll> | null>(null);
const containerEl = ref<HTMLElement | null>(null);

interface ScrollToIndexOptions {
  smooth?: boolean;
}

function scrollToIndex(index: number, options: ScrollToIndexOptions = {}) {
  const inst = scrollerRef.value;
  if (!inst) return;
  if (!options.smooth) {
    inst.scrollToIndex(index);
    return;
  }
  // Vuetify's scrollToIndex sets scrollTop synchronously. Capture the
  // start position, let it compute the destination, then animate the
  // browser's native smooth scroll between the two.
  const root = containerEl.value;
  if (!root) {
    inst.scrollToIndex(index);
    return;
  }
  const start = root.scrollTop;
  inst.scrollToIndex(index);
  const target = root.scrollTop;
  if (target === start) return;
  root.scrollTop = start;
  root.scrollTo({ top: target, behavior: "smooth" });
}

type WithEl = { $el?: HTMLElement };
onMounted(() => {
  // VVirtualScroll's root is the scrolling element; grab it via $el.
  const inst = scrollerRef.value as WithEl | null;
  containerEl.value = inst?.$el ?? null;
});

defineExpose({ scrollToIndex, containerEl });
</script>

<template>
  <VVirtualScroll
    ref="scrollerRef"
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
