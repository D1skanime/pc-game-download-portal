<script setup lang="ts">
// Platform gallery — single virtualised scroll surface.
// Hero, toolbar, content rows and load-more all live as items inside one
// RVirtualScroller. ALL galleries virtualise (premise: a library can have
// thousands of ROMs, every gallery must scale).
import {
  RChip,
  RPlatformIcon,
  RSkeletonBlock,
  RVirtualScroller,
} from "@v2/lib";
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
import storeRoms from "@/stores/roms";
import { formatBytes } from "@/utils";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import { GameCard } from "@/v2/components/Gallery/GameCard";
import GameList from "@/v2/components/Gallery/GameList.vue";
import InfoPanel from "@/v2/components/Gallery/InfoPanel.vue";
import LoadMore from "@/v2/components/Gallery/LoadMore.vue";
import Stat from "@/v2/components/shared/Stat.vue";
import { useGalleryMode } from "@/v2/composables/useGalleryMode";
import {
  useGalleryVirtualItems,
  type GalleryItem,
} from "@/v2/composables/useGalleryVirtualItems";
import { useLetterGroups } from "@/v2/composables/useLetterGroups";
import { useResponsiveColumns } from "@/v2/composables/useResponsiveColumns";
import { useWebpSupport } from "@/v2/composables/useWebpSupport";

const route = useRoute();
const platformsStore = storePlatforms();
const romsStore = storeRoms();
const galleryFilterStore = storeGalleryFilter();
const { searchTerm } = storeToRefs(galleryFilterStore);
const { supportsWebp } = useWebpSupport();

const {
  _allRoms: allRoms,
  currentPlatform,
  fetchingRoms,
  fetchTotalRoms,
} = storeToRefs(romsStore);

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
    { label: "In Library", value: String(p.rom_count ?? allRoms.value.length) },
  ];
  if (p.fs_size_bytes) {
    rows.push({ label: "On Disk", value: formatBytes(p.fs_size_bytes) });
  }
  if (p.firmware_count) {
    rows.push({ label: "Firmware", value: String(p.firmware_count) });
  }
  return rows;
});

// Letter grouping (only consulted when groupBy === 'letter').
const { letterGroups } = useLetterGroups(allRoms);

// Responsive columns — measure the row rail to chunk roms into rows
// matching the CSS grid that the non-virtualised version drew. Inset
// covers the scroller's horizontal padding (--r-row-pad each side) and
// the AlphaStrip column on the right of the section.
const sectionEl = ref<HTMLElement | null>(null);
// 36px row-pad × 2 + ~36px alpha-strip column = 108px total chrome.
const { columns } = useResponsiveColumns(sectionEl, {
  cardWidth: 158,
  gap: 12,
  inset: 108,
});

const hasMore = computed(() => allRoms.value.length < fetchTotalRoms.value);
const remaining = computed(() => fetchTotalRoms.value - allRoms.value.length);
const fetchingMore = computed(
  () => fetchingRoms.value && allRoms.value.length > 0,
);
const loadingInitial = computed(
  () => fetchingRoms.value && allRoms.value.length === 0,
);

const { virtualItems, letterToIndex, availableLetters } =
  useGalleryVirtualItems({
    hasHero: computed(() => !!currentPlatform.value),
    toolbarInline: computed(() => toolbarPosition.value === "header"),
    layout,
    groupBy,
    roms: allRoms,
    letterGroups,
    columns,
    loadingInitial,
    hasMore,
    remaining,
    fetchingMore,
    emptyMessage: ref("No games in this platform yet."),
    notFound,
    notFoundMessage: ref("Platform not found."),
    skeletonRowCount: 4,
  });

// Scroll-spy via IntersectionObserver on `data-spy-letter` elements
// rendered by the virtualiser. Lit letters drive AlphaStrip highlight.
const visibleLettersSet = ref<Set<string>>(new Set());
const currentLetter = ref<string>("");
const scrollerRef = ref<InstanceType<typeof RVirtualScroller> | null>(null);
let intersectionObserver: IntersectionObserver | null = null;
let mutationObserver: MutationObserver | null = null;

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
  // WeakSet has no clear(); replace it (the previous one will be GC'd
  // along with its tracked elements).
  observedReset();
}

let observed = new WeakSet<Element>();
function observedReset() {
  observed = new WeakSet<Element>();
}

function scrollToLetter(letter: string) {
  const idx = letterToIndex.value.get(letter);
  if (idx == null) return;
  scrollerRef.value?.scrollToIndex(idx, { smooth: true });
  currentLetter.value = letter;
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
  // Mirror v1's Platform.vue: a full reset() before switching context
  // clears every `current*` field (so a prior Collection's id doesn't
  // bleed into the next platform request), wipes _allRoms, resets
  // pagination, AND drops the `fetchingRoms` flag — otherwise the
  // re-entrancy guard in fetchRoms silently swallows the new call when
  // the user navigates between galleries mid-fetch and the new gallery
  // renders empty.
  if (currentPlatform.value?.id !== platform.id) {
    romsStore.reset();
    romsStore.setCurrentPlatform(platform);
  }
  document.title = platform.display_name;
  await romsStore.fetchRoms();
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
// (mode switch, search, fetched page) so newly-rendered rows are observed.
watch(virtualItems, () => nextTick().then(setupSpy));

onBeforeUnmount(teardownSpy);

function loadMore() {
  if (fetchingRoms.value || !hasMore.value) return;
  romsStore.fetchRoms();
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
    romsStore.resetPagination();
    romsStore._allRoms = [];
    // fetchRoms() supersedes any in-flight request via seq; no need to
    // wait for it to finish first.
    romsStore.fetchRoms();
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
function onListSort(options: { sortBy: SortEntry[] }) {
  const first = options.sortBy[0];
  if (!first) return;
  romsStore.resetPagination();
  romsStore.setOrderBy(first.key);
  romsStore.setOrderDir(first.order);
  romsStore.fetchRoms();
}

// Spy attribute helper — broadcast every letter the item covers.
// A row spanning M/N/O lights up all three in AlphaStrip; a letter-header
// covers exactly one letter. Returned as a comma-joined string so the
// IntersectionObserver callback can split it back out.
function spyLetters(item: GalleryItem): string | undefined {
  if (item.kind === "letter-header") return item.letter;
  if (item.kind === "row") return item.letters.join(",");
  return undefined;
}

// Narrowing helpers — the template's v-if chain checks .kind first, so
// these casts always land on the matching variant. Hoisted out of the
// template so the inline `Extract<…>` syntax stays in script land where
// the Vue compiler / Trunk HTML lexer don't trip on it.
type RowItem = Extract<GalleryItem, { kind: "row" }>;
type LetterHeaderItem = Extract<GalleryItem, { kind: "letter-header" }>;
type LoadMoreItem = Extract<GalleryItem, { kind: "load-more" }>;
type EmptyItem = Extract<GalleryItem, { kind: "empty" }>;
const asRow = (i: GalleryItem) => i as RowItem;
const asLetterHeader = (i: GalleryItem) => i as LetterHeaderItem;
const asLoadMore = (i: GalleryItem) => i as LoadMoreItem;
const asEmpty = (i: GalleryItem) => i as EmptyItem;
const itemKind = (i: GalleryItem) => i.kind;

// Stretching tracks (`1fr`) keep the card itself at --r-card-art-w but
// distribute any extra horizontal space across the row, so the visible
// gap between cards grows accordion-style as the window resizes.
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
            <GameCard
              v-for="rom in asRow(item as GalleryItem).roms"
              :key="rom.id"
              :rom="rom"
              :webp="supportsWebp"
              :show-platform-badge="false"
            />
          </div>

          <GameList
            v-else-if="itemKind(item as GalleryItem) === 'list-table'"
            :roms="allRoms"
            :total-roms="fetchTotalRoms"
            :loading="fetchingRoms"
            :webp="supportsWebp"
            @update:options="onListSort"
          />

          <LoadMore
            v-else-if="itemKind(item as GalleryItem) === 'load-more'"
            :loading="asLoadMore(item as GalleryItem).loading"
            :remaining="asLoadMore(item as GalleryItem).remaining"
            @load="loadMore"
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
            <RSkeletonBlock
              v-for="n in Math.max(1, columns)"
              :key="`sk-${n}`"
              width="var(--r-card-art-w)"
              height="var(--r-card-art-h)"
              rounded="md"
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
  /* Items the virtualiser stacks vertically. The padding-x lives on the
     scroller so card rows align flush with hero / toolbar at the same
     left edge. */
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
