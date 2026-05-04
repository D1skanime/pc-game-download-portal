<script setup lang="ts">
// GalleryShell — shared layout for Platform / Search / Collection.
//
// Three structural sections, top to bottom, all sharing one scrollbar:
//   1. HEADER  — view-supplied via `#header` slot. Whatever the view
//                wants there: an InfoPanel with platform / collection
//                metadata, a plain PageHeader for Search, etc.
//   2. TOOLBAR — search input + group/layout/dock controls. Two-layer:
//                * `--inflow` lives in the scroller's `#prepend` slot
//                  (after the header). Visible at scrollTop=0; scrolls
//                  away with the header.
//                * `--overlay` is absolutely positioned at the top of
//                  the section, OUTSIDE the scroller. Transparent.
//                  Toggled on once the inflow toolbar has scrolled past
//                  the top — combined with `clip-path: inset(...)` on
//                  the scroller, cards are physically clipped from
//                  appearing in the toolbar's pixel band, so the
//                  overlay reveals only what's behind the section
//                  (BackgroundArt blur), never the cards.
//   3. GRID / TABLE — the row-virtualised content (cards in grid mode,
//                RTable in list mode).
//
// Why two-layer: the user wants the toolbar to be transparent (so the
// blurred BackgroundArt shows through) AND wants cards to disappear
// when they pass behind the toolbar. With native `position: sticky`
// inside the scroller, cards passing behind a transparent element
// remain visible. Lifting the visible toolbar OUT of the scroll
// container and clipping the scroller's top band gives both: a
// see-through toolbar AND no cards leaking behind it. The inflow
// twin keeps the natural three-section flow at scrollTop=0.
//
// Cross-view behaviour owned by the shell: the virtualizer, sticky
// toolbar (two-layer), AlphaStrip, per-row dwell-debounced prefetch,
// scroll restoration, list-mode RTable wiring, search-input debounce,
// URL filter sync. Each view supplies its header and its own
// resource-load flow.
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
  /** Whether the header slot has content to render. False suppresses
   * the header (the prepend band collapses; toolbar pins immediately). */
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
  /** View-specific header (InfoPanel / PageHeader / etc). Rendered in
   * the scroller's `#prepend` slot — scrolls naturally with the rest
   * of the content. Must NOT carry a divider of its own; the shell
   * paints the single divider at the bottom of the prepend band. */
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

const notFoundRef = computed(() => props.notFound);
const emptyMessageRef = computed(() => props.emptyMessage);
const notFoundMessageRef = computed(
  () => props.notFoundMessage ?? props.emptyMessage,
);

const { virtualItems, letterToIndex, availableLetters } =
  useGalleryVirtualItems({
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

const scrollerRef = ref<InstanceType<typeof RVirtualScroller> | null>(null);

// ── Toolbar two-layer state ─────────────────────────────────────────
// `inflowToolbarEl` is the toolbar inside the scroller's prepend.
// `inflowToolbarTop` is its `offsetTop` within the scroller — the
// scroll threshold at which the overlay takes over. `toolbarHeight`
// drives both `scrollToIndex({ stickyOffset })` (so AlphaStrip lands
// rows below the pinned toolbar) and the scroller's clip-path inset
// (so the band the overlay covers is empty of cards).
const inflowToolbarEl = ref<HTMLElement | null>(null);
const inflowToolbarTop = ref(0);
const toolbarHeight = ref(0);
let inflowResizeObserver: ResizeObserver | null = null;

function bindInflowToolbarEl(el: HTMLElement | null) {
  inflowResizeObserver?.disconnect();
  inflowResizeObserver = null;
  inflowToolbarEl.value = el;
  if (!el) {
    inflowToolbarTop.value = 0;
    toolbarHeight.value = 0;
    return;
  }
  const measure = () => {
    inflowToolbarTop.value = el.offsetTop;
    toolbarHeight.value = el.getBoundingClientRect().height;
  };
  measure();
  // Observe the toolbar itself (height changes) and its prior siblings
  // inside the prepend (header / divider — their height shifts the
  // toolbar's `offsetTop`).
  inflowResizeObserver = new ResizeObserver(measure);
  inflowResizeObserver.observe(el);
  let prev = el.previousElementSibling;
  while (prev) {
    inflowResizeObserver.observe(prev);
    prev = prev.previousElementSibling;
  }
}

// `isStuck` flips to true the moment the inflow toolbar's top edge
// reaches the scroller's visible top. At that moment the overlay
// becomes visible and the scroller's top band is clipped, so cards
// scrolling up never reach the overlay's pixel area. Both layers
// render the toolbar UI at the same viewport y, so the swap is
// visually seamless.
const isStuck = computed(() => {
  if (toolbarPosition.value !== "header") return false;
  const scrollTop = scrollerRef.value?.scrollTop ?? 0;
  const threshold = inflowToolbarTop.value;
  if (threshold <= 0) return scrollTop > 0;
  return scrollTop >= threshold;
});

// Width / horizontal alignment of the absolute overlay needs to track
// the scroller column (which is narrowed by the AlphaStrip when it's
// rendered).
const hasAlphaStrip = computed(() => availableLetters.value.size > 0);

// ── Viewport range / AlphaStrip / dwell prefetch ────────────────────
const viewportRange = ref<{ first: number; last: number }>({
  first: 0,
  last: -1,
});
function onViewportRangeChange(range: { first: number; last: number }) {
  viewportRange.value = range;
  syncRowDwell(range);
}

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
  scrollerRef.value?.scrollToIndex(idx, {
    smooth: true,
    stickyOffset: toolbarHeight.value,
  });
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
  inflowResizeObserver?.disconnect();
  inflowResizeObserver = null;
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
  <section
    ref="sectionEl"
    class="r-v2-shell"
    :class="{
      'r-v2-shell--stuck': isStuck,
      'r-v2-shell--has-strip': hasAlphaStrip,
    }"
    :style="{ '--r-v2-shell-toolbar-h': `${toolbarHeight}px` }"
  >
    <RVirtualScroller
      ref="scrollerRef"
      :items="virtualItems"
      :get-item-height="galleryItemHeight"
      :overscan="25"
      class="r-v2-shell__scroller r-v2-scroll-hidden"
      @update:viewport-range="onViewportRangeChange"
    >
      <!-- HEADER (Section 1) + INFLOW TOOLBAR (Section 2 — first
           layer). Both live in the scroller's flow. The header
           scrolls away naturally; the inflow toolbar is what the user
           sees at scrollTop=0 and during the early scroll until its
           top edge reaches y=0. After that, the OVERLAY twin (below)
           takes over visually and this inflow toolbar is hidden by
           the scroller's clip-path. -->
      <template #prepend>
        <template v-if="hasHeader">
          <div class="r-v2-shell__header">
            <slot name="header" />
          </div>
          <RDivider class="r-v2-shell__header-divider" />
        </template>

        <div
          v-if="toolbarPosition === 'header'"
          :ref="(el) => bindInflowToolbarEl(el as HTMLElement | null)"
          class="r-v2-shell__toolbar r-v2-shell__toolbar--inflow"
        >
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
      </template>

      <!-- GRID / TABLE (Section 3) — letter-headers + rows of cards in
           grid/grouped mode, or a single RTable in list mode. Skeleton
           rows render while the first window is in flight. The empty
           / not-found state replaces everything below the toolbar
           with a single message. -->
      <template #default="{ item }">
        <div class="r-v2-shell__item">
          <div
            v-if="itemKind(item as GalleryItem) === 'letter-header'"
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

    <!-- TOOLBAR OVERLAY (Section 2 — second layer). Absolute against
         the section, OUTSIDE the scroller. Transparent — through it,
         the BackgroundArt blur shows. Cards never appear here because
         the scroller's clip strips its top `--r-v2-shell-toolbar-h`
         band when `--stuck`.
         Mounted alongside the rest of the shell (`v-if` gates only on
         dock position) and toggled visible via `v-show` so the
         GalleryToolbar's children — RSliderBtnGroup, RTextField — run
         their initialisation animation ONCE on first render, not on
         every stuck transition. -->
    <div
      v-if="toolbarPosition === 'header'"
      v-show="isStuck"
      class="r-v2-shell__toolbar r-v2-shell__toolbar--overlay"
    >
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
      v-if="hasAlphaStrip"
      :available="availableLetters"
      :current="currentLetter"
      :visible="visibleLettersSet"
      @pick="scrollToLetter"
    />

    <!-- FLOATING-DOCK TOOLBAR — the alternative dock; sits permanently
         in the top-right and never scrolls. Mutually exclusive with
         the in-scroller header dock above. -->
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
  height: 100%;
  position: relative;
}

/* Scroller: padding-top moved into the prepend's first child via
   `padding-top` on the header so the inflow toolbar's `offsetTop`
   measurement isn't perturbed by the scroller's own padding. The
   horizontal pads stay here so all in-flow content (header,
   toolbar, rows) shares one column. */
.r-v2-shell__scroller {
  flex: 1;
  height: 100%;
  padding: 0 var(--r-row-pad) 60px;
}

.r-v2-shell__item {
  width: 100%;
}

/* Header band — `display: flow-root` establishes a new
   block-formatting context so child margins don't collapse out
   visually. The 32px `padding-top` provides the breathing space at
   the very top of the gallery (replacing what used to live on the
   scroller). */
.r-v2-shell__header {
  display: flow-root;
  padding-top: 32px;
}

/* Divider between header and toolbar. Lives at the bottom of the
   prepend band so it scrolls away with the header — the toolbar's
   stuck state shows no separator above it. */
.r-v2-shell__header-divider {
  margin-bottom: 16px;
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

/* Toolbar — both layers share the same internal styling. Transparent
   by default; the BackgroundArt behind the section shows through.
   `padding-bottom` reserves breathing space between the toolbar UI
   and the first card row in flow. */
.r-v2-shell__toolbar {
  padding-bottom: 16px;
}

/* Inflow layer — `position: sticky; top: 0` so the compositor pins
   it smoothly as the user scrolls past the header. This makes the
   inflow's pinned position match the overlay's `top: 0` exactly,
   eliminating the sub-pixel jump that an in-flow → snap-to-zero
   swap would otherwise produce. The clip-path on the scroller hides
   the inflow once `--stuck` is true, leaving only the overlay
   visible (transparent — BackgroundArt shows through, no cards). */
.r-v2-shell__toolbar--inflow {
  position: sticky;
  top: 0;
  z-index: 4;
}

/* Overlay layer — absolute against the section, mirrors the
   scroller's column (narrowed when AlphaStrip is present). z-index
   above the inflow so when both paint at y=0 (transition frame), the
   overlay stacks cleanly on top. */
.r-v2-shell__toolbar--overlay {
  position: absolute;
  top: 0;
  left: var(--r-row-pad);
  right: var(--r-row-pad);
  z-index: 5;
}
.r-v2-shell--has-strip .r-v2-shell__toolbar--overlay {
  /* AlphaStrip is a flex sibling of the scroller; the overlay must
     stop short of it so it doesn't paint over the strip. */
  right: calc(var(--r-row-pad) + 36px);
}

/* While stuck, clip the scroller's top toolbar-band so cards
   scrolling underneath the overlay are physically removed from
   that pixel area. The transparent overlay then reveals only the
   section's background (BackgroundArt blur) — never the cards. */
.r-v2-shell--stuck .r-v2-shell__scroller {
  clip-path: inset(var(--r-v2-shell-toolbar-h, 64px) 0 0 0);
}

@media (max-width: 768px) {
  .r-v2-shell__scroller {
    padding: 0 14px 80px;
  }
  .r-v2-shell__header {
    padding-top: 16px;
  }
  .r-v2-shell__row {
    gap: 12px 10px;
  }
}
</style>
