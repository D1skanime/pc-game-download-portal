<script setup lang="ts">
// Platform gallery — single virtualised scroll surface with sparse,
// windowed loading. Architecture:
//
//   * `RVirtualScroller` (custom virtualizer) owns scroll position with
//     exact per-item offsets — `scrollToIndex` lands precisely on target
//     rows, no estimation drift.
//   * `useGalleryVirtualItems` builds the structural item list (every
//     row from position 0..total-1 exists from frame zero). Item heights
//     come from `galleryItemHeight()` per kind.
//   * `viewportRange` from the virtualizer drives BOTH AlphaStrip's lit
//     letters (computed from items intersecting the actual pixel
//     viewport — not the rendered overscan) AND a 2-second dwell-debounce
//     for cover prefetch (only rows the user actually pauses on trigger
//     a window fetch).
//   * Per-slot `getRomAt(p)` reads from the store's reactive Map at
//     render time, so a window resolution only re-renders the affected
//     row component rather than rebuilding the whole virtual list.
import { RChip, RPlatformIcon, RVirtualScroller } from "@v2/lib";
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
import storePlatforms, { type Platform } from "@/stores/platforms";
import { formatBytes } from "@/utils";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import { GameCard, GameCardSkeleton } from "@/v2/components/Gallery/GameCard";
import GameList from "@/v2/components/Gallery/GameList.vue";
import InfoPanel from "@/v2/components/Gallery/InfoPanel.vue";
import Stat from "@/v2/components/shared/Stat.vue";
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

const route = useRoute();
const platformsStore = storePlatforms();
const galleryRoms = storeGalleryRoms();
const galleryFilterStore = storeGalleryFilter();
const scrollRestoration = storeScrollRestoration();
useGalleryFilterUrl();
const { searchTerm } = storeToRefs(galleryFilterStore);
const { supportsWebp } = useWebpSupport();

const { currentPlatform, total, charIndex, byPosition, initialFetching } =
  storeToRefs(galleryRoms);

const notFound = ref(false);
const { groupBy, layout, toolbarPosition } = useGalleryMode();

const tags = computed<string[]>(() => {
  const p = currentPlatform.value as
    | (Platform & {
        category?: string | null;
        family_name?: string | null;
        generation?: number | null;
      })
    | null;
  if (!p) return [];
  const out: string[] = [];
  if (p.category) out.push(p.category);
  if (p.family_name) out.push(p.family_name);
  if (p.generation) out.push(`Generation ${p.generation}`);
  return out;
});

type StatRow = { label: string; value: string };
const platformStats = computed<StatRow[]>(() => {
  const p = currentPlatform.value as
    | (Platform & {
        fs_size_bytes?: number | null;
        firmware_count?: number | null;
      })
    | null;
  if (!p) return [];
  const rows: StatRow[] = [
    { label: "In Library", value: String(p.rom_count ?? total.value) },
  ];
  if (p.fs_size_bytes) {
    rows.push({ label: "On Disk", value: formatBytes(p.fs_size_bytes) });
  }
  if (p.firmware_count) {
    rows.push({ label: "Firmware", value: String(p.firmware_count) });
  }
  return rows;
});

// Responsive columns — measure the section to chunk roms into rows.
// Inset covers scroller padding (--r-row-pad × 2) plus the AlphaStrip column.
const sectionEl = ref<HTMLElement | null>(null);
const { columns } = useResponsiveColumns(sectionEl, {
  cardWidth: 158,
  gap: 12,
  inset: 108,
});

const loadingInitial = computed(
  () => initialFetching.value && total.value === 0,
);

const { virtualItems, letterToIndex, availableLetters } =
  useGalleryVirtualItems({
    hasHero: computed(() => !!currentPlatform.value),
    toolbarInline: computed(() => toolbarPosition.value === "header"),
    layout,
    groupBy,
    total,
    charIndex,
    columns,
    loadingInitial,
    emptyMessage: ref("No games in this platform yet."),
    notFound,
    notFoundMessage: ref("Platform not found."),
    skeletonRowCount: 4,
  });

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

// AlphaStrip lit letters — set of letters covered by items currently
// inside the viewport. Recomputes whenever viewportRange or virtualItems
// change.
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

// Topmost-letter highlight — first letter encountered scanning the
// viewport range top-to-bottom.
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

// Per-row dwell prefetch. Each row item that enters the viewport starts
// its own DWELL_MS timer; if the row stays in view that long, its
// missing positions are fetched as a ranged request (one per row,
// parallelisable). Rows that leave before the timer fires are
// cancelled — fast-scrolling / AlphaStrip fly-by triggers zero fetches.
//
// Per-row (not per-viewport-batch) means a slowly-scrolling reader gets
// rows that have been on screen ≥2s loading even while they keep
// scrolling — the timer lives with the row, not the viewport.
const DWELL_MS = 2000;
const rowDwellTimers = new Map<number, ReturnType<typeof setTimeout>>();

function clearAllRowDwell() {
  for (const t of rowDwellTimers.values()) clearTimeout(t);
  rowDwellTimers.clear();
}

function syncRowDwell(range: { first: number; last: number }) {
  // Cancel timers for rows that left the viewport.
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
    // Skip if every slot in the row is already loaded — nothing to do.
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
        // Paranoid re-check: row must still be in viewport at fire time.
        const r = viewportRange.value;
        if (i < r.first || i > r.last) return;
        void galleryRoms.fetchRange(start, len);
      }, DWELL_MS),
    );
  }
}

// Structural changes to virtualItems (mode swap / search / new platform)
// invalidate row indices — drop all timers and re-arm against the new
// items.
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

async function ensurePlatforms() {
  if (platformsStore.allPlatforms.length === 0) {
    await platformsStore.fetchPlatforms();
  }
}

async function loadForId(platformId: number) {
  await ensurePlatforms();
  const platform = platformsStore.allPlatforms.find((p) => p.id === platformId);
  if (!platform) {
    notFound.value = true;
    return;
  }
  notFound.value = false;
  // Switching platform — full reset of the gallery state.
  if (currentPlatform.value?.id !== platform.id) {
    galleryRoms.resetGallery();
    galleryRoms.setCurrentPlatform(platform);
  }
  document.title = platform.display_name;
  await galleryRoms.fetchWindowAt(0);
  await nextTick();
  applyRestoredScroll();
}

// Restore the previously-saved scrollTop (if any) for this route. Called
// after the first window has loaded — by then virtualItems has
// `total`-many rows and the virtualizer's offset table covers the full
// scrollable height. The viewport-range watcher catches the rows
// revealed at the restored position; dwell debounce prefetches their
// windows after 2s.
async function applyRestoredScroll() {
  const saved = scrollRestoration.restore(route.fullPath);
  if (saved == null) return;
  const root = scrollerRef.value?.containerEl;
  if (!root) return;
  await nextTick();
  root.scrollTop = saved;
}

onMounted(() => {
  loadForId(Number(route.params.platform));
});

onBeforeRouteUpdate((to, from) => {
  // Save the current scroll position before the route swap so navigating
  // platform A → B → A lands back at A's last position.
  const root = scrollerRef.value?.containerEl;
  if (root) scrollRestoration.save(from.fullPath, root.scrollTop);
  if (to.name === "platform") loadForId(Number(to.params.platform));
});

onBeforeRouteLeave((_to, from) => {
  const root = scrollerRef.value?.containerEl;
  if (root) scrollRestoration.save(from.fullPath, root.scrollTop);
});

watch(
  () => route.params.platform,
  (next) => {
    if (next != null) loadForId(Number(next));
  },
);

onBeforeUnmount(clearAllRowDwell);

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
onBeforeUnmount(() => {
  if (searchDebounce) clearTimeout(searchDebounce);
  // Note: `searchTerm` is NOT cleared here — `useGalleryFilterUrl`
  // owns the URL ↔ store sync, and the next gallery view's mount will
  // re-apply whatever its own URL holds (usually nothing → null).
});

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

// Inline ROM lookup — read `byPosition` per slot inside the row template
// rather than building `slots` upfront. Vue tracks the specific Map key
// each call reads, so when a window resolves only the rows whose
// positions just appeared re-render.
function getRomAt(p: number) {
  return galleryRoms.getRomAt(p);
}

// Position list for a row — the template iterates this and asks
// `getRomAt(p)` per slot.
function rowPositions(row: {
  startPosition: number;
  endPosition: number;
}): number[] {
  const out: number[] = [];
  for (let p = row.startPosition; p < row.endPosition; p++) out.push(p);
  return out;
}

// Narrowing helpers — see src/v2/composables/useGalleryVirtualItems.
type RowItem = Extract<GalleryItem, { kind: "row" }>;
type LetterHeaderItem = Extract<GalleryItem, { kind: "letter-header" }>;
type EmptyItem = Extract<GalleryItem, { kind: "empty" }>;
const asRow = (i: GalleryItem) => i as RowItem;
const asLetterHeader = (i: GalleryItem) => i as LetterHeaderItem;
const asEmpty = (i: GalleryItem) => i as EmptyItem;
const itemKind = (i: GalleryItem) => i.kind;

// Stretching tracks keep cards at --r-card-art-w but distribute extra
// horizontal space — accordion-style gap growth on resize.
const rowGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${Math.max(1, columns.value)}, minmax(var(--r-card-art-w), 1fr))`,
}));

// Single-toolbar sticky behaviour. The toolbar is ALWAYS rendered as an
// overlay-sibling of the virtualizer (not as a duplicate of the inline
// virtual item). Inside the virtualizer the toolbar slot renders an
// empty placeholder so its 64px of vertical space is reserved in the
// scroll content; the actual GalleryToolbar element sits absolute on
// top of the section and tracks the scroll until it reaches the top:
//
//   * scrollTop < toolbarOffset → toolbar.top = toolbarOffset - scrollTop
//                                  (scrolls naturally with the hero).
//   * scrollTop ≥ toolbarOffset → toolbar.top = 0 (pinned).
//
// While pinned, the virtualizer is clipped (`clip-path: inset(64px ...)`)
// so card rows don't render behind the toolbar — matches AppNav, where
// the scroll simply doesn't reach the bar's area. The toolbar's
// backdrop-filter then only sees the BackgroundArt (no card content
// bleeding through), exactly like AppNav.
const toolbarHeightPx = galleryItemHeight({ kind: "toolbar", key: "" });
const toolbarOffsetPx = computed(() => {
  const items = virtualItems.value;
  let sum = 0;
  for (let i = 0; i < items.length; i++) {
    if (items[i].kind === "toolbar") return sum;
    sum += galleryItemHeight(items[i]);
  }
  return -1;
});
const toolbarTopPx = computed(() => {
  const offset = toolbarOffsetPx.value;
  if (offset < 0) return 0;
  const top = scrollerRef.value?.scrollTop ?? 0;
  return Math.max(0, offset - top);
});
const toolbarStuck = computed(() => {
  const offset = toolbarOffsetPx.value;
  if (offset < 0) return false;
  return (scrollerRef.value?.scrollTop ?? 0) >= offset;
});
</script>

<template>
  <section ref="sectionEl" class="r-v2-plat">
    <RVirtualScroller
      ref="scrollerRef"
      :items="virtualItems"
      :get-item-height="galleryItemHeight"
      :overscan="25"
      class="r-v2-plat__scroller r-v2-scroll-hidden"
      :class="{ 'r-v2-plat__scroller--toolbar-stuck': toolbarStuck }"
      :style="{ '--r-v2-plat-toolbar-h': `${toolbarHeightPx}px` }"
      @update:viewport-range="onViewportRangeChange"
    >
      <template #default="{ item }">
        <div class="r-v2-plat__item">
          <template v-if="itemKind(item as GalleryItem) === 'hero'">
            <InfoPanel
              v-if="currentPlatform"
              :title="currentPlatform.display_name"
            >
              <template #cover>
                <div
                  class="r-v2-plat__panel-icon"
                  :style="{
                    viewTransitionName: `platform-icon-${currentPlatform.id}`,
                  }"
                >
                  <RPlatformIcon
                    :slug="currentPlatform.slug"
                    :fs-slug="currentPlatform.fs_slug"
                    :alt="currentPlatform.display_name"
                    :size="148"
                  />
                </div>
              </template>
              <template v-if="tags.length" #tags>
                <RChip
                  v-for="t in tags"
                  :key="t"
                  size="small"
                  variant="tonal"
                  :rounded="20"
                >
                  {{ t }}
                </RChip>
              </template>
              <template v-if="platformStats.length" #stats>
                <Stat
                  v-for="s in platformStats"
                  :key="s.label"
                  :value="s.value"
                  :label="s.label"
                />
              </template>
            </InfoPanel>
          </template>

          <!-- Toolbar slot — empty placeholder. The actual GalleryToolbar
               lives outside the virtualizer (see overlay below) so it
               can transition cleanly between in-flow and pinned without
               rendering twice. The placeholder reserves the toolbar's
               height in the virtualiser's offset table. -->
          <div
            v-else-if="itemKind(item as GalleryItem) === 'toolbar'"
            class="r-v2-plat__toolbar-spacer"
            aria-hidden="true"
          />

          <div
            v-else-if="itemKind(item as GalleryItem) === 'letter-header'"
            class="r-v2-plat__letter-heading"
          >
            {{ asLetterHeader(item as GalleryItem).letter }}
          </div>

          <div
            v-else-if="itemKind(item as GalleryItem) === 'row'"
            class="r-v2-plat__row"
            :style="rowGridStyle"
          >
            <template
              v-for="(p, slotIdx) in rowPositions(asRow(item as GalleryItem))"
              :key="p"
            >
              <GameCard
                v-if="getRomAt(p)"
                class="r-v2-plat__card-fade"
                :style="{ '--card-fade-i': slotIdx }"
                :rom="getRomAt(p)!"
                :webp="supportsWebp"
                :show-platform-badge="false"
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
            class="r-v2-plat__empty"
          >
            {{ asEmpty(item as GalleryItem).message }}
          </div>

          <div
            v-else-if="itemKind(item as GalleryItem) === 'skeleton-row'"
            class="r-v2-plat__row"
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

    <!-- Header-dock toolbar overlay — always rendered, position tracks
         the natural offset until it reaches y=0 then sticks. From the
         user's POV it's a single toolbar that scrolls with the hero
         and stops at the top. While stuck, the virtualizer is clipped
         so card rows don't render behind it (see CSS) — matches AppNav,
         where scrolled content never reaches the bar's area. -->
    <div
      v-if="toolbarPosition === 'header'"
      class="r-v2-plat__toolbar"
      :class="{
        'r-v2-plat__toolbar--has-strip': availableLetters.size > 0,
        'r-v2-plat__toolbar--stuck': toolbarStuck,
      }"
      :style="{ top: toolbarTopPx + 'px' }"
    >
      <GalleryToolbar
        :group-by="groupBy"
        :layout="layout"
        :position="toolbarPosition"
        show-search
        :search="searchInput"
        search-placeholder="Filter this platform…"
        @update:group-by="groupBy = $event"
        @update:layout="layout = $event"
        @update:search="setSearch"
      />
    </div>

    <AlphaStrip
      v-if="availableLetters.size > 0"
      :available="availableLetters"
      :current="currentLetter"
      :visible="visibleLettersSet"
      @pick="scrollToLetter"
    />

    <!-- Floating toolbar — positioned outside the scroller so it stays put. -->
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
.r-v2-plat {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: calc(100vh - var(--r-nav-h));
  position: relative;
}

.r-v2-plat__scroller {
  flex: 1;
  height: 100%;
  padding: 32px var(--r-row-pad) 60px;
}

.r-v2-plat__item {
  width: 100%;
}

.r-v2-plat__panel-icon {
  width: 200px;
  height: 148px;
  display: grid;
  place-items: center;
}

.r-v2-plat__letter-heading {
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--r-color-fg-faint);
  padding: 20px 0 12px;
}

.r-v2-plat__row {
  display: grid;
  gap: 18px 12px;
  padding-bottom: 18px;
}

/* Cards fade in on first paint after a window resolves — masks the
   skeleton→card swap so it reads as a fill rather than a hard pop.
   `--card-fade-i` is the slot index inside the row; we stagger ~30ms
   between cards so the row reads as a left-to-right wave rather than
   a single batch flash. */
.r-v2-plat__card-fade {
  animation: r-v2-plat-card-fade 280ms ease-out both;
  animation-delay: calc(var(--card-fade-i, 0) * 30ms);
}
@keyframes r-v2-plat-card-fade {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.r-v2-plat__empty {
  padding: 80px 0;
  color: var(--r-color-fg-faint);
  font-size: 13.5px;
  text-align: center;
}

/* Toolbar overlay — single element that tracks scroll until pinned.
   Same visual language as AppNav: transparent, blurred backdrop. While
   stuck, the virtualizer is clipped at the toolbar's height (see
   below) so card rows never render in the toolbar's area; the
   backdrop-filter then only sees the page's BackgroundArt, exactly
   like AppNav. */
.r-v2-plat__toolbar {
  position: absolute;
  left: var(--r-row-pad);
  right: var(--r-row-pad);
  z-index: 5;
}
.r-v2-plat__toolbar--has-strip {
  /* Don't cover the AlphaStrip on the right (24px column + 12px margin). */
  right: calc(var(--r-row-pad) + 36px);
}
.r-v2-plat__toolbar--stuck {
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-bottom: 1px solid var(--r-color-border);
}

/* Clip the virtualizer's painted output at the toolbar's height while
   stuck. Cards still scroll naturally inside the virtualizer; clip-path
   just hides anything painted in the top `--r-v2-plat-toolbar-h` band
   so the toolbar sits over a clean BackgroundArt — matches AppNav. */
.r-v2-plat__scroller--toolbar-stuck {
  clip-path: inset(var(--r-v2-plat-toolbar-h, 64px) 0 0 0);
}

/* Toolbar's height-reserving placeholder inside the virtualizer. The
   actual visuals are rendered by the overlay above. */
.r-v2-plat__toolbar-spacer {
  width: 100%;
  height: 100%;
}

@media (max-width: 768px) {
  .r-v2-plat__scroller {
    padding: 16px 14px 80px;
  }
  .r-v2-plat__panel-icon {
    width: 80px;
    height: 60px;
  }
  .r-v2-plat__row {
    gap: 12px 10px;
  }
}
</style>
