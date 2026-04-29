<script setup lang="ts">
// Platform gallery — single virtualised scroll surface with sparse,
// windowed loading. Every row in the gallery exists from frame zero
// (skeleton placeholders for un-fetched positions); window fetches are
// triggered as rows enter the viewport. Hero, toolbar, content rows and
// load-more all live as items inside one RVirtualScroller.
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
import { onBeforeRouteUpdate, useRoute } from "vue-router";
import storeGalleryFilter from "@/stores/galleryFilter";
import storePlatforms, { type Platform } from "@/stores/platforms";
import { formatBytes } from "@/utils";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import { GameCard, GameCardSkeleton } from "@/v2/components/Gallery/GameCard";
import GameList from "@/v2/components/Gallery/GameList.vue";
import InfoPanel from "@/v2/components/Gallery/InfoPanel.vue";
import Stat from "@/v2/components/shared/Stat.vue";
import { useGalleryMode } from "@/v2/composables/useGalleryMode";
import {
  useGalleryVirtualItems,
  type GalleryItem,
  type GallerySlot,
} from "@/v2/composables/useGalleryVirtualItems";
import { useResponsiveColumns } from "@/v2/composables/useResponsiveColumns";
import { useWebpSupport } from "@/v2/composables/useWebpSupport";
import storeGalleryRoms from "@/v2/stores/galleryRoms";

const route = useRoute();
const platformsStore = storePlatforms();
const galleryRoms = storeGalleryRoms();
const galleryFilterStore = storeGalleryFilter();
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
    getRomAt: (p) => galleryRoms.getRomAt(p),
    loadedTick: byPosition,
    columns,
    loadingInitial,
    emptyMessage: ref("No games in this platform yet."),
    notFound,
    notFoundMessage: ref("Platform not found."),
    skeletonRowCount: 4,
  });

// Scroll-spy via IntersectionObserver on `data-spy-letters` elements.
// The same observer doubles as the prefetch trigger: rows that enter
// the viewport with skeleton slots dispatch `fetchWindowAt` for each
// missing position (the store dedupes loaded / pending windows).
const visibleLettersSet = ref<Set<string>>(new Set());
const currentLetter = ref<string>("");
const scrollerRef = ref<InstanceType<typeof RVirtualScroller> | null>(null);
let intersectionObserver: IntersectionObserver | null = null;
let mutationObserver: MutationObserver | null = null;
let observed = new WeakSet<Element>();

function recomputeVisible(root: HTMLElement) {
  const visibles: Array<{ letters: string[]; top: number }> = [];
  root
    .querySelectorAll<HTMLElement>("[data-spy-letters][data-spy-active='1']")
    .forEach((target) => {
      const raw = target.dataset.spyLetters;
      if (!raw) return;
      const letters = raw.split(",").filter(Boolean);
      if (!letters.length) return;
      visibles.push({ letters, top: target.getBoundingClientRect().top });
    });
  visibles.sort((a, b) => a.top - b.top);
  const set = new Set<string>();
  for (const v of visibles) for (const l of v.letters) set.add(l);
  visibleLettersSet.value = set;
  currentLetter.value = visibles[0]?.letters[0] ?? currentLetter.value;
}

function prefetchVisibleSkeletonRows(root: HTMLElement) {
  // For each visible row that still has skeleton slots, request the
  // window covering its first missing position. The store dedupes
  // identical / in-flight windows internally, so this is cheap.
  root
    .querySelectorAll<HTMLElement>(
      "[data-spy-active='1'][data-prefetch-position]",
    )
    .forEach((target) => {
      const pos = Number(target.dataset.prefetchPosition);
      if (!Number.isFinite(pos)) return;
      void galleryRoms.fetchWindowAt(pos);
    });
}

function setupSpy() {
  const root = scrollerRef.value?.containerEl;
  if (!root) return;
  teardownSpy();

  intersectionObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        (entry.target as HTMLElement).dataset.spyActive = entry.isIntersecting
          ? "1"
          : "0";
      }
      recomputeVisible(root);
      prefetchVisibleSkeletonRows(root);
    },
    { root, threshold: 0 },
  );

  const observeAll = () => {
    root.querySelectorAll<HTMLElement>("[data-spy-letters]").forEach((el) => {
      if (observed.has(el)) return;
      observed.add(el);
      intersectionObserver?.observe(el);
    });
  };
  observeAll();
  mutationObserver = new MutationObserver(observeAll);
  mutationObserver.observe(root, { childList: true, subtree: true });
}

function teardownSpy() {
  intersectionObserver?.disconnect();
  intersectionObserver = null;
  mutationObserver?.disconnect();
  mutationObserver = null;
  observed = new WeakSet<Element>();
}

function scrollToLetter(letter: string) {
  const idx = letterToIndex.value.get(letter);
  if (idx == null) return;
  scrollerRef.value?.scrollToIndex(idx, { smooth: true });
  currentLetter.value = letter;
  // The destination row may be all-skeleton if its window isn't loaded
  // yet; kick the fetch immediately so cards arrive while the smooth
  // scroll is animating.
  const cols = Math.max(1, columns.value);
  const cellSize = letter.charCodeAt(0); // unused noop to silence warn
  void cellSize;
  // The row at virtualItems[idx] knows its startPosition; pull it.
  const item = virtualItems.value[idx];
  if (item?.kind === "row") void galleryRoms.fetchWindowAt(item.startPosition);
  else if (item?.kind === "letter-header") {
    // First row of the group lives at idx + 1.
    const next = virtualItems.value[idx + 1];
    if (next?.kind === "row") {
      void galleryRoms.fetchWindowAt(next.startPosition);
    }
  }
  // The cols variable is only used inside the prefetch math above;
  // referenced here to keep TS happy across edits.
  void cols;
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
  setupSpy();
}

onMounted(() => {
  loadForId(Number(route.params.platform));
});

onBeforeRouteUpdate((to) => {
  if (to.name === "platform") loadForId(Number(to.params.platform));
});

watch(
  () => route.params.platform,
  (next) => {
    if (next != null) loadForId(Number(next));
  },
);

// Re-attach the spy when the virtualised item list mutates substantially
// (mode switch, search, fetched window) so newly-rendered rows are
// observed AND so the just-rendered visible band re-prefetches.
watch(virtualItems, () => nextTick().then(setupSpy));

onBeforeUnmount(teardownSpy);

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
  // Don't leak the term to the next gallery — clear on leave.
  searchTerm.value = null;
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

// Spy attribute helper — broadcast every letter the item covers.
function spyLetters(item: GalleryItem): string | undefined {
  if (item.kind === "letter-header") return item.letter;
  if (item.kind === "row") return item.letters.join(",");
  return undefined;
}

// Prefetch position for a skeleton row — the IntersectionObserver
// reads `data-prefetch-position` to know which window to fetch.
function prefetchPosition(item: GalleryItem): number | undefined {
  if (item.kind !== "row" || !item.hasMissing) return undefined;
  const skel = item.slots.find((s) => s.kind === "skeleton") as
    | Extract<GallerySlot, { kind: "skeleton" }>
    | undefined;
  return skel?.position;
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
</script>

<template>
  <section ref="sectionEl" class="r-v2-plat">
    <RVirtualScroller
      ref="scrollerRef"
      :items="virtualItems"
      class="r-v2-plat__scroller r-v2-scroll-hidden"
    >
      <template #default="{ item }">
        <div
          class="r-v2-plat__item"
          :data-spy-letters="spyLetters(item as GalleryItem)"
          :data-prefetch-position="prefetchPosition(item as GalleryItem)"
        >
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

          <GalleryToolbar
            v-else-if="itemKind(item as GalleryItem) === 'toolbar'"
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
              v-for="(slot, slotIdx) in asRow(item as GalleryItem).slots"
              :key="slot.position"
            >
              <GameCard
                v-if="slot.kind === 'rom'"
                class="r-v2-plat__card-fade"
                :style="{ '--card-fade-i': slotIdx }"
                :rom="slot.rom"
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
