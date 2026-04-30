<script setup lang="ts">
// RVirtualScroller — custom windowed list with exact-offset positioning.
//
// Replaces the previous Vuetify v-virtual-scroll wrapper. We own the
// math: heights are reported by the consumer per item (via
// `getItemHeight`), the prefix-sum offset table is built once per items
// change, and `scrollToIndex` is `containerEl.scrollTop = offsets[index]`
// — no estimation, no drift, lands exactly on target items.
//
// Two ranges are exposed:
//   * `renderedRange` = items in the DOM = viewport ± overscan. Drives
//     the slot rendering.
//   * `viewportRange` = items whose pixel rect actually intersects the
//     visible viewport. Drives consumers that care about "what the user
//     is looking at right now" — AlphaStrip highlight, dwell-debounced
//     prefetch, etc.
//
// Performance contract:
//   * Rendered items are absolutely positioned via `transform: translateY`.
//     The container has `height: <total>px` so the native scrollbar
//     reflects total content, but only ~viewport+overscan items live in
//     the DOM at any time.
//   * Computeds re-evaluate only on scrollTop / containerHeight / items
//     changes. Binary searches make per-scroll work O(log n).
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

defineOptions({ inheritAttrs: false });

interface Props {
  /** Array of items to virtualise. The slot receives `{ item, index }`. */
  items: readonly unknown[];
  /** Returns the item's height in pixels. Called once per item per
   * structural change (items array swap or items.length change). Heights
   * are cached in an offset table; if a height value depends on dynamic
   * state, bump items by reference to force a recompute. */
  getItemHeight: (item: unknown, index: number) => number;
  /** Items kept rendered above/below the visible viewport for smooth
   * scrolling. Default 25 → ~50 extra rendered + visible. */
  overscan?: number;
  /** Viewport height. Number = px, string = any CSS length, undefined =
   * fill parent (the wrapper element gets `height: 100%`). */
  height?: number | string;
}

const props = withDefaults(defineProps<Props>(), {
  overscan: 25,
  height: undefined,
});

const emit = defineEmits<{
  /** Fires whenever the viewport-visible range changes (after scroll
   * settles, on resize, on items change). The payload's `last` is
   * exclusive-of: a range with `first === last` means zero items. */
  (e: "update:viewportRange", range: { first: number; last: number }): void;
}>();

defineSlots<{
  default(props: { item: unknown; index: number }): unknown;
}>();

const containerEl = ref<HTMLElement | null>(null);
const scrollTop = ref(0);
const containerHeight = ref(0);

// Offset table: offsets[i] = top-y of item i. offsets[N] = totalHeight.
// Size N+1 so we can answer "bottom of item i" as offsets[i+1].
const offsets = computed<number[]>(() => {
  const len = props.items.length;
  const out = new Array<number>(len + 1);
  out[0] = 0;
  for (let i = 0; i < len; i++) {
    const h = props.getItemHeight(props.items[i], i);
    out[i + 1] = out[i] + (Number.isFinite(h) && h > 0 ? h : 0);
  }
  return out;
});

const totalHeight = computed(() => {
  const offs = offsets.value;
  return offs[offs.length - 1] ?? 0;
});

// Smallest i in [0, N) where offsets[i+1] > top — first item whose
// bottom edge is past the top of the viewport (so it's at least
// partially visible).
function findFirstVisible(offs: number[], top: number): number {
  let lo = 0;
  let hi = offs.length - 2;
  if (hi < 0) return 0;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (offs[mid + 1] > top) hi = mid;
    else lo = mid + 1;
  }
  return lo;
}

// Largest i in [0, N) where offsets[i] < bottom — last item whose top
// edge is before the bottom of the viewport.
function findLastVisible(offs: number[], bottom: number): number {
  let lo = 0;
  let hi = offs.length - 2;
  if (hi < 0) return -1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1; // bias up to terminate
    if (offs[mid] < bottom) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

const viewportRange = computed<{ first: number; last: number }>(() => {
  const len = props.items.length;
  if (len === 0 || containerHeight.value === 0) {
    return { first: 0, last: -1 };
  }
  const top = scrollTop.value;
  const bottom = top + containerHeight.value;
  const first = findFirstVisible(offsets.value, top);
  const last = findLastVisible(offsets.value, bottom);
  return { first, last };
});

const renderedRange = computed<{ first: number; last: number }>(() => {
  const len = props.items.length;
  if (len === 0) return { first: 0, last: -1 };
  const v = viewportRange.value;
  if (v.last < v.first) return { first: 0, last: -1 };
  const overscan = Math.max(0, props.overscan);
  return {
    first: Math.max(0, v.first - overscan),
    last: Math.min(len - 1, v.last + overscan),
  };
});

interface RenderedEntry {
  item: unknown;
  index: number;
  top: number;
}

const renderedItems = computed<RenderedEntry[]>(() => {
  const r = renderedRange.value;
  if (r.last < r.first) return [];
  const offs = offsets.value;
  const items = props.items;
  const out: RenderedEntry[] = [];
  for (let i = r.first; i <= r.last; i++) {
    out.push({ item: items[i], index: i, top: offs[i] });
  }
  return out;
});

// Scroll handling — passive listener; reads scrollTop and lets Vue's
// reactivity batch downstream computeds into the next microtask.
function onScroll(e: Event) {
  scrollTop.value = (e.target as HTMLElement).scrollTop;
}

// Container size tracking (ResizeObserver — fires on initial mount and
// every layout change).
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  const el = containerEl.value;
  if (!el) return;
  containerHeight.value = el.clientHeight;
  scrollTop.value = el.scrollTop;
  resizeObserver = new ResizeObserver(() => {
    containerHeight.value = el.clientHeight;
  });
  resizeObserver.observe(el);
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
});

// Re-emit viewportRange whenever it changes. Computed memoises on
// shallow equality of its return value — but {first,last} is a fresh
// object each time, so we need a manual diff.
let lastEmittedFirst = -2;
let lastEmittedLast = -2;
watch(
  viewportRange,
  (next) => {
    if (next.first === lastEmittedFirst && next.last === lastEmittedLast) {
      return;
    }
    lastEmittedFirst = next.first;
    lastEmittedLast = next.last;
    emit("update:viewportRange", { first: next.first, last: next.last });
  },
  { immediate: true },
);

interface ScrollToIndexOptions {
  smooth?: boolean;
}

function scrollToIndex(index: number, options: ScrollToIndexOptions = {}) {
  const root = containerEl.value;
  if (!root) return;
  const offs = offsets.value;
  if (index < 0 || index >= offs.length - 1) return;
  const target = offs[index];
  if (!Number.isFinite(target)) return;
  if (options.smooth) {
    root.scrollTo({ top: target, behavior: "smooth" });
  } else {
    root.scrollTop = target;
  }
}

defineExpose({ scrollToIndex, containerEl, scrollTop });

const wrapperStyle = computed(() => {
  const h = props.height;
  if (h === undefined) return { height: "100%" } as const;
  if (typeof h === "number") return { height: `${h}px` } as const;
  return { height: h } as const;
});

const innerStyle = computed(() => ({
  height: `${totalHeight.value}px`,
  position: "relative" as const,
  width: "100%",
}));
</script>

<template>
  <div
    ref="containerEl"
    v-bind="$attrs"
    class="r-virtual-scroller"
    :style="wrapperStyle"
    @scroll.passive="onScroll"
  >
    <div class="r-virtual-scroller__inner" :style="innerStyle">
      <div
        v-for="entry in renderedItems"
        :key="entry.index"
        class="r-virtual-scroller__item"
        :style="{ transform: `translateY(${entry.top}px)` }"
      >
        <slot :item="entry.item" :index="entry.index" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.r-virtual-scroller {
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  background-color: transparent;
}

.r-virtual-scroller__item {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  /* `transform` triggers a compositor layer; the scroll-position-driven
     re-positioning then bypasses paint costs. */
  will-change: transform;
}
</style>
