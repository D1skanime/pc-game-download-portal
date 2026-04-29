<script setup lang="ts">
// Search — global ROM search with the same single-virtualiser architecture
// as Platform / Collection. Hero (PageHeader), toolbar, content rows and
// load-more all flow through one RVirtualScroller.
import { RChip, RSkeletonBlock, RVirtualScroller } from "@v2/lib";
import { storeToRefs } from "pinia";
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import storeGalleryFilter from "@/stores/galleryFilter";
import storeRoms from "@/stores/roms";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import { GameCard } from "@/v2/components/Gallery/GameCard";
import GameList from "@/v2/components/Gallery/GameList.vue";
import LoadMore from "@/v2/components/Gallery/LoadMore.vue";
import EmptyState from "@/v2/components/shared/EmptyState.vue";
import PageHeader from "@/v2/components/shared/PageHeader.vue";
import { useGalleryMode } from "@/v2/composables/useGalleryMode";
import {
  useGalleryVirtualItems,
  type GalleryItem,
} from "@/v2/composables/useGalleryVirtualItems";
import { useLetterGroups } from "@/v2/composables/useLetterGroups";
import { useResponsiveColumns } from "@/v2/composables/useResponsiveColumns";
import { useWebpSupport } from "@/v2/composables/useWebpSupport";

const romsStore = storeRoms();
const galleryFilterStore = storeGalleryFilter();
const { supportsWebp } = useWebpSupport();

const {
  _allRoms: allRoms,
  fetchingRoms,
  fetchTotalRoms,
  initialSearch,
} = storeToRefs(romsStore);
const { searchTerm } = storeToRefs(galleryFilterStore);
const { groupBy, layout, toolbarPosition } = useGalleryMode();

const searchInput = ref(searchTerm.value ?? "");
let searchDebounce: ReturnType<typeof setTimeout> | null = null;

const remaining = computed(() =>
  Math.max(0, fetchTotalRoms.value - allRoms.value.length),
);
const hasMore = computed(() => remaining.value > 0);
const fetchingMore = computed(
  () => fetchingRoms.value && allRoms.value.length > 0,
);
const loadingInitial = computed(
  () => fetchingRoms.value && allRoms.value.length === 0,
);

const { letterGroups } = useLetterGroups(allRoms);

const sectionEl = ref<HTMLElement | null>(null);
const { columns } = useResponsiveColumns(sectionEl, {
  cardWidth: 158,
  gap: 12,
  inset: 108,
});

const { virtualItems, letterToIndex, availableLetters } =
  useGalleryVirtualItems({
    hasHero: ref(true),
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
    emptyMessage: computed(() =>
      searchTerm.value
        ? `No games match "${searchTerm.value}".`
        : "No games match your search.",
    ),
    skeletonRowCount: 4,
  });

// Scroll-spy via IntersectionObserver on `data-spy-letter` elements.
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
  observed = new WeakSet<Element>();
}

function scrollToLetter(letter: string) {
  const idx = letterToIndex.value.get(letter);
  if (idx == null) return;
  scrollerRef.value?.scrollToIndex(idx, { smooth: true });
  currentLetter.value = letter;
}

function setSearch(value: string) {
  searchInput.value = value;
  if (searchDebounce) clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    const normalized = value.trim();
    if (normalized === (searchTerm.value ?? "")) return;
    searchTerm.value = normalized || null;
    romsStore.resetPagination();
    romsStore._allRoms = [];
    romsStore.fetchRoms();
    romsStore.initialSearch = true;
  }, 300);
}

function loadMore() {
  if (fetchingRoms.value || !hasMore.value) return;
  romsStore.fetchRoms();
}

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

watch(virtualItems, () => nextTick().then(setupSpy));

onMounted(async () => {
  // Global search — drop ALL gallery scoping from previous views
  // (platform + any collection kind) AND the fetching/pagination state
  // via reset(). The old two-line `setCurrentPlatform(null)` +
  // `setCurrentCollection(null)` clear missed the virtual/smart
  // collection fields and left the re-entrancy guard untouched, so
  // arriving on /search from a virtual/smart collection either sent a
  // stale id or got its fetchRoms silently dropped.
  romsStore.reset();
  await romsStore.fetchRoms();
  romsStore.initialSearch = true;
  await nextTick();
  setupSpy();
});

onBeforeUnmount(() => {
  if (searchDebounce) clearTimeout(searchDebounce);
  teardownSpy();
});

function spyLetters(item: GalleryItem): string | undefined {
  if (item.kind === "letter-header") return item.letter;
  if (item.kind === "row") return item.letters.join(",");
  return undefined;
}

// Narrowing helpers — see Platform.vue for the rationale.
type RowItem = Extract<GalleryItem, { kind: "row" }>;
type LetterHeaderItem = Extract<GalleryItem, { kind: "letter-header" }>;
type LoadMoreItem = Extract<GalleryItem, { kind: "load-more" }>;
type EmptyItem = Extract<GalleryItem, { kind: "empty" }>;
const asRow = (i: GalleryItem) => i as RowItem;
const asLetterHeader = (i: GalleryItem) => i as LetterHeaderItem;
const asLoadMore = (i: GalleryItem) => i as LoadMoreItem;
const asEmpty = (i: GalleryItem) => i as EmptyItem;
const itemKind = (i: GalleryItem) => i.kind;

// See Platform.vue — `1fr` tracks make gaps grow with window width.
const rowGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${Math.max(1, columns.value)}, minmax(var(--r-card-art-w), 1fr))`,
}));

const showStandaloneEmpty = computed(
  () => !fetchingRoms.value && allRoms.value.length === 0 && !!searchTerm.value,
);
</script>

<template>
  <section ref="sectionEl" class="r-v2-search">
    <RVirtualScroller
      ref="scrollerRef"
      :items="virtualItems"
      class="r-v2-search__scroller r-v2-scroll-hidden"
    >
      <template #default="{ item }">
        <div
          class="r-v2-search__item"
          :data-spy-letters="spyLetters(item as GalleryItem)"
        >
          <template v-if="itemKind(item as GalleryItem) === 'hero'">
            <PageHeader title="Search">
              <template #count>
                <RChip
                  v-if="initialSearch && !fetchingRoms"
                  size="small"
                  variant="tonal"
                >
                  {{ fetchTotalRoms }} results
                </RChip>
              </template>
            </PageHeader>
          </template>

          <GalleryToolbar
            v-else-if="itemKind(item as GalleryItem) === 'toolbar'"
            :group-by="groupBy"
            :layout="layout"
            :position="toolbarPosition"
            show-search
            :search="searchInput"
            search-placeholder="Search by name, filename, hash…"
            @update:group-by="groupBy = $event"
            @update:layout="layout = $event"
            @update:search="setSearch"
          />

          <div
            v-else-if="itemKind(item as GalleryItem) === 'letter-header'"
            class="r-v2-search__letter-heading"
          >
            {{ asLetterHeader(item as GalleryItem).letter }}
          </div>

          <div
            v-else-if="itemKind(item as GalleryItem) === 'row'"
            class="r-v2-search__row"
            :style="rowGridStyle"
          >
            <GameCard
              v-for="rom in asRow(item as GalleryItem).roms"
              :key="rom.id"
              :rom="rom"
              :webp="supportsWebp"
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
            class="r-v2-search__empty-row"
          >
            <EmptyState
              v-if="showStandaloneEmpty"
              variant="boxed"
              icon="mdi-emoticon-confused-outline"
              :message="asEmpty(item as GalleryItem).message"
            />
            <span v-else>{{ asEmpty(item as GalleryItem).message }}</span>
          </div>

          <div
            v-else-if="itemKind(item as GalleryItem) === 'skeleton-row'"
            class="r-v2-search__row"
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
.r-v2-search {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: calc(100vh - var(--r-nav-h));
  position: relative;
}

.r-v2-search__scroller {
  flex: 1;
  height: 100%;
  padding: 32px var(--r-row-pad) 60px;
}

.r-v2-search__item {
  width: 100%;
}

.r-v2-search__letter-heading {
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--r-color-fg-faint);
  padding: 20px 0 12px;
}

.r-v2-search__row {
  display: grid;
  gap: 18px 12px;
  padding-bottom: 18px;
}

.r-v2-search__empty-row {
  padding: 40px 0;
  color: var(--r-color-fg-faint);
  font-size: 13.5px;
  text-align: center;
}

@media (max-width: 768px) {
  .r-v2-search__scroller {
    padding: 16px 14px 80px;
  }
  .r-v2-search__row {
    gap: 12px 10px;
  }
}
</style>
