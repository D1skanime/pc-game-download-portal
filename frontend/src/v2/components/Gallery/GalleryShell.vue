<script setup lang="ts">
// GalleryShell — shared layout for Platform / Search / Collection.
//
// Three structural sections, top to bottom:
//   1. HEADER  — the view's header. Whatever the view wants in there:
//                an InfoPanel with platform / collection metadata, a
//                plain PageHeader for Search, etc. Provided via the
//                `#header` slot. There's no notion of "header vs. info
//                panel" — they're all just headers.
//   2. TOOLBAR — search input + group/layout/dock controls. Lives once
//                as an absolute overlay; tracks scroll naturally with
//                the header until it reaches the top, then pins.
//   3. GRID / TABLE — the row-virtualised content (cards in grid mode,
//                RTable in list mode).
//
// Between HEADER and TOOLBAR sits a single `RDivider`, owned by the
// shell. Header components must NOT paint a divider of their own — the
// shell renders it exactly once. While the toolbar is pinned, the
// header is off-screen so the divider hides with it.
//
// Cross-view behaviour owned by the shell: the virtualizer, sticky
// toolbar, AlphaStrip, per-row dwell-debounced prefetch, scroll
// restoration, list-mode RTable wiring, search-input debounce, URL
// filter sync. Each view supplies its header and its own
// resource-load flow.
//
// Layout invariants:
//   * Section is `display: flex` row → [scroller (flex:1)] [AlphaStrip].
//   * Toolbar is rendered OUTSIDE the virtualizer; its `top` tracks
//     `scrollTop` until pinned. While pinned, the virtualizer is
//     `clip-path`-clipped so card rows don't appear behind it (matches
//     AppNav: scrolled content never reaches the bar's area).
//   * The header's height is auto-measured via ResizeObserver — the
//     toolbar's natural offset always matches the header's actual
//     rendered bottom, so the divider lands exactly between them
//     regardless of which header.
import { RDivider, RVirtualScroller } from "@v2/lib";
import { storeToRefs } from "pinia";
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute } from "vue-router";
import storeGalleryFilter from "@/stores/galleryFilter";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import { GameCard, GameCardSkeleton } from "@/v2/components/Gallery/GameCard";
import GameList from "@/v2/components/Gallery/GameList.vue";
import { useGalleryFilterUrl } from "@/v2/composables/useGalleryFilterUrl";
import { useGalleryMode } from "@/v2/composables/useGalleryMode";
import {
  galleryItemHeight,
  useGalleryVirtualItems,
  type GalleryItem,
} from "@/v2/composables/useGalleryVirtualItems";
import { useResponsiveColumns } from "@/v2/composables/useResponsiveColumns";
import { useWebpSupport } from "@/v2/composables/useWebpSupport";
import storeGalleryRoms from "@/v2/stores/galleryRoms";
import storeScrollRestoration from "@/v2/stores/scrollRestoration";

interface Props {
  /** Whether the header slot has content to render (drives the structural
   * `header` virtual item). False suppresses the header entirely. */
  hasHeader: boolean;
  /** Toolbar's search-input placeholder. */
  searchPlaceholder: string;
  /** Empty-state message shown when the gallery resolves with zero items. */
  emptyMessage: string;
  /** "Not found" mode — replaces all body items with a single empty row. */
  notFound?: boolean;
  /** Override the empty-state message in not-found mode. */
  notFoundMessage?: string;
  /** Whether GameCards should display the platform badge corner (Search /
   * Collection: yes; Platform: no — the cards already share a platform). */
  showPlatformBadge?: boolean;
  /** Skeleton row count painted while the very first window is loading. */
  skeletonRowCount?: number;
}

const props = withDefaults(defineProps<Props>(), {
  notFound: false,
  notFoundMessage: undefined,
  showPlatformBadge: true,
  skeletonRowCount: 4,
});

defineSlots<{
  /** View-specific header (InfoPanel / PageHeader / etc). The shell
   * wraps it in the virtualizer's `kind: 'hero'` item slot so it scrolls
   * with the rest of the content. Header components must NOT carry a
   * divider of their own — the shell paints the single divider above
   * the toolbar (where it belongs) so all three views look identical. */
  header(): unknown;
  /** Override the empty-state body. Receives `{ message }` (the
   * resolved empty / not-found message) so the override can decide
   * between text vs. a boxed illustration. Default: plain text. */
  empty(props: { message: string }): unknown;
}>();

useGalleryFilterUrl();

const route = useRoute();
const galleryRoms = storeGalleryRoms();
const galleryFilterStore = storeGalleryFilter();
const scrollRestoration = storeScrollRestoration();
const { searchTerm } = storeToRefs(galleryFilterStore);
const { supportsWebp } = useWebpSupport();

const { total, charIndex, byPosition, initialFetching } =
  storeToRefs(galleryRoms);

const { groupBy, layout, toolbarPosition } = useGalleryMode();

// Responsive columns — measure the section to chunk roms into rows.
// Inset = scroller padding (--r-row-pad × 2) + AlphaStrip column.
const sectionEl = ref<HTMLElement | null>(null);
const { columns } = useResponsiveColumns(sectionEl, {
  cardWidth: 158,
  gap: 12,
  inset: 108,
});

const loadingInitial = computed(
  () => initialFetching.value && total.value === 0,
);

// notFound and emptyMessage need to be reactive refs for the composable.
const notFoundRef = computed(() => props.notFound);
const emptyMessageRef = computed(() => props.emptyMessage);
const notFoundMessageRef = computed(
  () => props.notFoundMessage ?? props.emptyMessage,
);
const hasHeaderRef = computed(() => props.hasHeader);
const toolbarInlineRef = computed(() => toolbarPosition.value === "header");

const { virtualItems, letterToIndex, availableLetters } =
  useGalleryVirtualItems({
    hasHero: hasHeaderRef,
    toolbarInline: toolbarInlineRef,
    layout,
    groupBy,
    total,
    charIndex,
    columns,
    loadingInitial,
    emptyMessage: emptyMessageRef,
    notFound: notFoundRef,
    notFoundMessage: notFoundMessageRef,
    skeletonRowCount: props.skeletonRowCount,
  });

// ── Header auto-measurement ────────────────────────────────────────
// The header's natural rendered height varies (InfoPanel ≈ 270, search
// PageHeader ≈ 80, future headers whatever). Rather than ask each view
// to hand-tune a `headerHeight` prop — which they kept getting wrong —
// we observe the slot wrapper. As long as the result feeds back into
// `itemHeightOf` (used by both the virtualizer's offset table and the
// toolbar offset math), the toolbar always sits exactly at the
// header's rendered bottom edge.
//
// Initial fallback is the value baked into `galleryItemHeight()` (280)
// so the first frame's offsets are roughly correct for a typical
// InfoPanel; ResizeObserver refines once mounted.
const measuredHeaderHeight = ref(galleryItemHeight({ kind: "hero", key: "" }));
let headerResizeObserver: ResizeObserver | null = null;

function bindHeaderEl(el: Element | null) {
  if (headerResizeObserver) {
    headerResizeObserver.disconnect();
    headerResizeObserver = null;
  }
  if (!el) return;
  const html = el as HTMLElement;
  const measure = () => {
    const h = html.getBoundingClientRect().height;
    if (h > 0 && h !== measuredHeaderHeight.value)
      measuredHeaderHeight.value = h;
  };
  measure();
  headerResizeObserver = new ResizeObserver(measure);
  headerResizeObserver.observe(html);
}

onBeforeUnmount(() => {
  headerResizeObserver?.disconnect();
  headerResizeObserver = null;
});

// Wrap `galleryItemHeight` so the header kind reports its measured
// size. Used both by the virtualizer (via `getItemHeight`) and by the
// toolbar offset math below — they MUST agree, otherwise the toolbar
// pin threshold drifts away from where the header actually ends.
const itemHeightOf = (item: unknown): number => {
  const it = item as GalleryItem;
  if (it.kind === "hero") return measuredHeaderHeight.value;
  return galleryItemHeight(it);
};

// Viewport range — items whose pixel rect intersects the actual visible
// viewport (NOT the rendered overscan). Drives AlphaStrip and the
// per-row dwell prefetch.
const scrollerRef = ref<InstanceType<typeof RVirtualScroller> | null>(null);
const viewportRange = ref<{ first: number; last: number }>({
  first: 0,
  last: -1,
});
function onViewportRangeChange(range: { first: number; last: number }) {
  viewportRange.value = range;
  syncRowDwell(range);
}

// AlphaStrip lit letters — items currently inside the actual viewport.
const visibleLettersSet = computed<Set<string>>(() => {
  const set = new Set<string>();
  const r = viewportRange.value;
  if (r.last < r.first) return set;
  const items = virtualItems.value;
  for (let i = r.first; i <= r.last; i++) {
    const it = items[i];
    if (!it) continue;
    if (it.kind === "letter-header") set.add(it.letter);
    else if (it.kind === "row") for (const l of it.letters) set.add(l);
  }
  return set;
});

const currentLetter = computed<string>(() => {
  const r = viewportRange.value;
  if (r.last < r.first) return "";
  const items = virtualItems.value;
  for (let i = r.first; i <= r.last; i++) {
    const it = items[i];
    if (!it) continue;
    if (it.kind === "letter-header") return it.letter;
    if (it.kind === "row" && it.letters.length > 0) return it.letters[0];
  }
  return "";
});

// Per-row dwell prefetch. Each row that enters the viewport arms its
// own DWELL_MS timer; if the row stays in view that long, its missing
// positions fetch as a ranged request (one per row, parallelisable).
// Rows that leave before the timer fires are cancelled — fast-scrolling
// / AlphaStrip fly-by triggers zero fetches.
const DWELL_MS = 2000;
const rowDwellTimers = new Map<number, ReturnType<typeof setTimeout>>();

function clearAllRowDwell() {
  for (const t of rowDwellTimers.values()) clearTimeout(t);
  rowDwellTimers.clear();
}

function syncRowDwell(range: { first: number; last: number }) {
  for (const idx of [...rowDwellTimers.keys()]) {
    if (idx < range.first || idx > range.last) {
      clearTimeout(rowDwellTimers.get(idx)!);
      rowDwellTimers.delete(idx);
    }
  }
  if (range.last < range.first) return;
  const items = virtualItems.value;
  for (let i = range.first; i <= range.last; i++) {
    if (rowDwellTimers.has(i)) continue;
    const item = items[i];
    if (!item || item.kind !== "row") continue;
    let missing = false;
    for (let p = item.startPosition; p < item.endPosition; p++) {
      if (!galleryRoms.byPosition.has(p)) {
        missing = true;
        break;
      }
    }
    if (!missing) continue;
    const start = item.startPosition;
    const len = item.endPosition - start;
    rowDwellTimers.set(
      i,
      setTimeout(() => {
        rowDwellTimers.delete(i);
        const r = viewportRange.value;
        if (i < r.first || i > r.last) return;
        void galleryRoms.fetchRange(start, len);
      }, DWELL_MS),
    );
  }
}

watch(virtualItems, () => {
  clearAllRowDwell();
  syncRowDwell(viewportRange.value);
});

function scrollToLetter(letter: string) {
  const idx = letterToIndex.value.get(letter);
  if (idx == null) return;
  scrollerRef.value?.scrollToIndex(idx, { smooth: true });
  // Express user intent: prefetch the destination row NOW (don't wait
  // the 2s dwell — they explicitly asked to go there).
  const items = virtualItems.value;
  const target =
    items[idx]?.kind === "row"
      ? items[idx]
      : items[idx]?.kind === "letter-header"
        ? items[idx + 1]
        : null;
  if (target?.kind === "row") {
    void galleryRoms.fetchRange(
      target.startPosition,
      target.endPosition - target.startPosition,
    );
  }
}

// ── Search filter (debounced) ───────────────────────────────────────
const searchInput = ref(searchTerm.value ?? "");
let searchDebounce: ReturnType<typeof setTimeout> | null = null;
function setSearch(value: string) {
  searchInput.value = value;
  if (searchDebounce) clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    const normalized = value.trim();
    if (normalized === (searchTerm.value ?? "")) return;
    searchTerm.value = normalized || null;
    galleryRoms.invalidateWindows();
    void galleryRoms.fetchWindowAt(0);
  }, 300);
}

type SortEntry = {
  key: keyof import("@/stores/roms").SimpleRom;
  order: "asc" | "desc";
};
function onListOptions(options: { sortBy: SortEntry[]; page?: number }) {
  const first = options.sortBy?.[0];
  if (first) {
    galleryRoms.setOrderBy(first.key);
    galleryRoms.setOrderDir(first.order);
    galleryRoms.invalidateWindows();
    void galleryRoms.fetchWindowAt(0);
    return;
  }
  if (options.page !== undefined) {
    void galleryRoms.fetchWindowAt((options.page - 1) * 72);
  }
}

// List mode reads a contiguous projection of `byPosition` sorted by
// position. Whatever's loaded shows in RTable; page changes trigger a
// window fetch via `onListOptions`.
const loadedRoms = computed(() => {
  const entries = [...byPosition.value.entries()].sort((a, b) => a[0] - b[0]);
  return entries.map(([, rom]) => rom);
});

// ── Toolbar overlay positioning ─────────────────────────────────────
// Single toolbar element rendered outside the virtualizer; tracks the
// virtualizer's scrollTop until the toolbar's natural offset crosses
// the section's top, then pins. While pinned, the virtualizer is
// clipped at the toolbar's height so card rows never paint behind it.
//
// The scroller has `padding-top: 32px` (= --r-row-pad-top), which
// pushes the inline content down by that amount on screen. The overlay
// is `position: absolute` against the section, NOT the scroller's
// content area, so we add the padding to its top math — otherwise the
// overlay sits 32px ABOVE where the inline header actually renders and
// ends up clipping the title.
const SCROLLER_PADDING_TOP_PX = 32;
const toolbarHeightPx = galleryItemHeight({ kind: "toolbar", key: "" });
const toolbarOffsetPx = computed(() => {
  const items = virtualItems.value;
  let sum = 0;
  for (let i = 0; i < items.length; i++) {
    if (items[i].kind === "toolbar") return sum;
    sum += itemHeightOf(items[i]);
  }
  return -1;
});
const toolbarTopPx = computed(() => {
  const offset = toolbarOffsetPx.value;
  if (offset < 0) return 0;
  const top = scrollerRef.value?.scrollTop ?? 0;
  return Math.max(0, SCROLLER_PADDING_TOP_PX + offset - top);
});
const toolbarStuck = computed(() => {
  const offset = toolbarOffsetPx.value;
  if (offset < 0) return false;
  return (
    (scrollerRef.value?.scrollTop ?? 0) >= SCROLLER_PADDING_TOP_PX + offset
  );
});

// ── Scroll restoration ─────────────────────────────────────────────
async function applyRestoredScroll() {
  const saved = scrollRestoration.restore(route.fullPath);
  if (saved == null) return;
  const root = scrollerRef.value?.containerEl;
  if (!root) return;
  await nextTick();
  root.scrollTop = saved;
}

function saveCurrentScroll(routeFullPath: string) {
  const root = scrollerRef.value?.containerEl;
  if (root) scrollRestoration.save(routeFullPath, root.scrollTop);
}

// Save scroll on every route change — universal across views. The view
// owns the corresponding load-on-update flow (it knows which resource
// to fetch); we just persist the scroll position before it runs.
onBeforeRouteUpdate((_to, from) => {
  saveCurrentScroll(from.fullPath);
});
onBeforeRouteLeave((_to, from) => {
  saveCurrentScroll(from.fullPath);
});

onMounted(() => {
  // No-op anchor — keeps lifecycle hooks colocated for future hooks.
});

onBeforeUnmount(() => {
  if (searchDebounce) clearTimeout(searchDebounce);
  clearAllRowDwell();
});

// ── Slot helpers ────────────────────────────────────────────────────
function getRomAt(p: number) {
  return galleryRoms.getRomAt(p);
}

function rowPositions(row: {
  startPosition: number;
  endPosition: number;
}): number[] {
  const out: number[] = [];
  for (let p = row.startPosition; p < row.endPosition; p++) out.push(p);
  return out;
}

type RowItem = Extract<GalleryItem, { kind: "row" }>;
type LetterHeaderItem = Extract<GalleryItem, { kind: "letter-header" }>;
type EmptyItem = Extract<GalleryItem, { kind: "empty" }>;
const asRow = (i: GalleryItem) => i as RowItem;
const asLetterHeader = (i: GalleryItem) => i as LetterHeaderItem;
const asEmpty = (i: GalleryItem) => i as EmptyItem;
const itemKind = (i: GalleryItem) => i.kind;

const rowGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${Math.max(1, columns.value)}, minmax(var(--r-card-art-w), 1fr))`,
}));

// View-facing surface. Methods only — internal state stays internal.
defineExpose({
  /** Re-apply the previously-saved scroll position for the current route
   * (typically called by the view at the end of its load flow). */
  applyRestoredScroll,
  /** Force-save the current scrollTop to a specific routeFullPath.
   * The shell already saves on `onBeforeRouteUpdate` / `onBeforeRouteLeave`
   * automatically; this is for one-off checkpoints. */
  saveCurrentScroll,
});
</script>

<template>
  <section ref="sectionEl" class="r-v2-shell">
    <!-- VIRTUALISED CONTENT — header + toolbar spacer + rows / list /
         empty. The toolbar and AlphaStrip live OUTSIDE the virtualizer
         (below) so their positioning isn't tied to scroll-driven
         offsets. -->
    <RVirtualScroller
      ref="scrollerRef"
      :items="virtualItems"
      :get-item-height="itemHeightOf"
      :overscan="25"
      class="r-v2-shell__scroller r-v2-scroll-hidden"
      :class="{ 'r-v2-shell__scroller--toolbar-stuck': toolbarStuck }"
      :style="{ '--r-v2-shell-toolbar-h': `${toolbarHeightPx}px` }"
      @update:viewport-range="onViewportRangeChange"
    >
      <template #default="{ item }">
        <div class="r-v2-shell__item">
          <!-- ┌─ HEADER (Section 1) ─ view-supplied via `#header` slot;
                 the wrapper is what we measure for
                 `measuredHeaderHeight` so the toolbar overlay below
                 sits exactly at the header's rendered bottom edge. -->
          <div
            v-if="itemKind(item as GalleryItem) === 'hero'"
            :ref="(el) => bindHeaderEl(el as Element | null)"
            class="r-v2-shell__header"
          >
            <slot name="header" />
          </div>

          <!-- TOOLBAR (Section 2) reserves its layout band here as an
               empty placeholder (matches `HEIGHT_BY_KIND.toolbar` —
               divider + toolbar + breathing). The visible toolbar is
               rendered as an absolute overlay below the virtualizer so
               it can smoothly transition from in-flow to pinned-at-top. -->
          <div
            v-else-if="itemKind(item as GalleryItem) === 'toolbar'"
            class="r-v2-shell__toolbar-spacer"
            aria-hidden="true"
          />

          <!-- GRID / TABLE (Section 3) ─ letter-headers + rows of
               cards in grid/grouped mode, or a single RTable in list
               mode. Skeleton rows render here while the first window
               is in flight. The empty / not-found state replaces
               everything below the toolbar with a single message. -->
          <div
            v-else-if="itemKind(item as GalleryItem) === 'letter-header'"
            class="r-v2-shell__letter-heading"
          >
            {{ asLetterHeader(item as GalleryItem).letter }}
          </div>

          <div
            v-else-if="itemKind(item as GalleryItem) === 'row'"
            class="r-v2-shell__row"
            :style="rowGridStyle"
          >
            <template
              v-for="(p, slotIdx) in rowPositions(asRow(item as GalleryItem))"
              :key="p"
            >
              <GameCard
                v-if="getRomAt(p)"
                class="r-v2-shell__card-fade"
                :style="{ '--card-fade-i': slotIdx }"
                :rom="getRomAt(p)!"
                :webp="supportsWebp"
                :show-platform-badge="showPlatformBadge"
              />
              <GameCardSkeleton v-else />
            </template>
          </div>

          <GameList
            v-else-if="itemKind(item as GalleryItem) === 'list-table'"
            :roms="loadedRoms"
            :total-roms="total"
            :loading="loadingInitial"
            :webp="supportsWebp"
            @update:options="onListOptions"
          />

          <div
            v-else-if="itemKind(item as GalleryItem) === 'empty'"
            class="r-v2-shell__empty"
          >
            <slot name="empty" :message="asEmpty(item as GalleryItem).message">
              {{ asEmpty(item as GalleryItem).message }}
            </slot>
          </div>

          <div
            v-else-if="itemKind(item as GalleryItem) === 'skeleton-row'"
            class="r-v2-shell__row"
            :style="rowGridStyle"
          >
            <GameCardSkeleton
              v-for="n in Math.max(1, columns)"
              :key="`sk-${n}`"
            />
          </div>
        </div>
      </template>
    </RVirtualScroller>

    <!-- TOOLBAR OVERLAY — single element. `top` tracks scroll until it
         hits 0, then pins. The `<RDivider />` above the toolbar is the
         single source of truth for the boundary between header and
         toolbar; it scrolls with the overlay until pinned and is hidden
         once stuck (the header is gone with it). When pinned, a
         `border-bottom` on the toolbar separates it from the cards
         scrolling underneath (clipped) for the AppNav-like chrome. -->
    <div
      v-if="toolbarPosition === 'header'"
      class="r-v2-shell__toolbar"
      :class="{
        'r-v2-shell__toolbar--has-strip': availableLetters.size > 0,
        'r-v2-shell__toolbar--stuck': toolbarStuck,
      }"
      :style="{ top: toolbarTopPx + 'px' }"
    >
      <RDivider v-if="!toolbarStuck" class="r-v2-shell__toolbar-divider" />
      <GalleryToolbar
        :group-by="groupBy"
        :layout="layout"
        :position="toolbarPosition"
        show-search
        :search="searchInput"
        :search-placeholder="searchPlaceholder"
        @update:group-by="groupBy = $event"
        @update:layout="layout = $event"
        @update:search="setSearch"
      />
    </div>

    <!-- ALPHASTRIP — A-Z jump column on the right edge of the section. -->
    <AlphaStrip
      v-if="availableLetters.size > 0"
      :available="availableLetters"
      :current="currentLetter"
      :visible="visibleLettersSet"
      @pick="scrollToLetter"
    />

    <!-- FLOATING-DOCK TOOLBAR — the alternative dock; sits permanently
         in the top-right and never scrolls. Mutually exclusive with the
         header-dock overlay above. -->
    <GalleryToolbar
      v-if="toolbarPosition === 'floating'"
      :group-by="groupBy"
      :layout="layout"
      :position="toolbarPosition"
      @update:group-by="groupBy = $event"
      @update:layout="layout = $event"
    />
  </section>
</template>

<style scoped>
.r-v2-shell {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: calc(100vh - var(--r-nav-h));
  position: relative;
}

.r-v2-shell__scroller {
  flex: 1;
  height: 100%;
  padding: 32px var(--r-row-pad) 60px;
}

.r-v2-shell__item {
  width: 100%;
}

/* The header wrapper has no chrome of its own — header components own
   their padding. `display: flow-root` establishes a new block-formatting
   context so child margins DON'T collapse out of the wrapper's
   `getBoundingClientRect().height`; without it, a margin-bottom on the
   header (e.g., older PageHeader styling) would silently disappear from
   the measurement and the toolbar's divider would land too high. */
.r-v2-shell__header {
  display: flow-root;
}

.r-v2-shell__toolbar-spacer {
  width: 100%;
  height: 100%;
}

.r-v2-shell__letter-heading {
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--r-color-fg-faint);
  padding: 20px 0 12px;
}

.r-v2-shell__row {
  display: grid;
  gap: 18px 12px;
  padding-bottom: 18px;
}

.r-v2-shell__card-fade {
  animation: r-v2-shell-card-fade 280ms ease-out both;
  animation-delay: calc(var(--card-fade-i, 0) * 30ms);
}
@keyframes r-v2-shell-card-fade {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.r-v2-shell__empty {
  padding: 80px 0;
  color: var(--r-color-fg-faint);
  font-size: 13.5px;
  text-align: center;
}

/* Toolbar overlay — the `<RDivider />` rendered inline above the
   `<GalleryToolbar />` is the single source of truth for the boundary
   between header and toolbar. While stuck, the divider is removed
   (the header is gone) and a `border-bottom` paints the chrome
   separator over the clipped content area. */
.r-v2-shell__toolbar {
  position: absolute;
  left: var(--r-row-pad);
  right: var(--r-row-pad);
  z-index: 5;
  transition: border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-shell__toolbar--has-strip {
  /* Don't cover the AlphaStrip column on the right. */
  right: calc(var(--r-row-pad) + 36px);
}
.r-v2-shell__toolbar-divider {
  margin-bottom: 16px;
}

.r-v2-shell__scroller--toolbar-stuck {
  /* Hide whatever the virtualizer paints in the toolbar's pixel band so
     card rows never bleed behind the pinned toolbar — same effect as
     AppNav (scrolled content never reaches the bar's area). */
  clip-path: inset(var(--r-v2-shell-toolbar-h, 64px) 0 0 0);
}

@media (max-width: 768px) {
  .r-v2-shell__scroller {
    padding: 16px 14px 80px;
  }
  .r-v2-shell__row {
    gap: 12px 10px;
  }
}
</style>
