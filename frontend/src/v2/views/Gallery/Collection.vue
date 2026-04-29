<script setup lang="ts">
// Collection gallery — same single-virtualiser architecture as Platform /
// Search, hero is a CollectionMosaic-fronted InfoPanel.
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
import { onBeforeRouteUpdate, useRoute } from "vue-router";
import storeCollections, {
  type Collection,
  type SmartCollection,
  type VirtualCollection,
} from "@/stores/collections";
import storeGalleryFilter from "@/stores/galleryFilter";
import storeRoms from "@/stores/roms";
import CollectionMosaic from "@/v2/components/Collections/CollectionMosaic.vue";
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

type AnyCollection = Collection | VirtualCollection | SmartCollection;
type CollectionKind = "regular" | "virtual" | "smart";

const route = useRoute();
const collectionsStore = storeCollections();
const romsStore = storeRoms();
const galleryFilterStore = storeGalleryFilter();
const { searchTerm } = storeToRefs(galleryFilterStore);
const { supportsWebp, toWebp } = useWebpSupport();

const {
  _allRoms: allRoms,
  fetchingRoms,
  fetchTotalRoms,
} = storeToRefs(romsStore);

const notFound = ref(false);
const currentKind = ref<CollectionKind>("regular");
const currentCollection = ref<AnyCollection | null>(null);
const { groupBy, layout, toolbarPosition } = useGalleryMode();

const mosaicCovers = computed<string[]>(() => {
  const paths =
    (currentCollection.value as { path_covers_small?: string[] } | null)
      ?.path_covers_small ?? [];
  return paths.slice(0, 4).map(toWebp);
});

const description = computed(
  () =>
    (currentCollection.value as { description?: string | null } | null)
      ?.description ?? "",
);

const kindLabel = computed(() => {
  if (currentKind.value === "virtual") return "Virtual collection";
  if (currentKind.value === "smart") return "Smart collection";
  return "Collection";
});

const { letterGroups } = useLetterGroups(allRoms);

const sectionEl = ref<HTMLElement | null>(null);
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
    hasHero: computed(() => !!currentCollection.value),
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
    emptyMessage: ref("This collection is empty."),
    notFound,
    notFoundMessage: ref("Collection not found."),
    skeletonRowCount: 4,
  });

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

function kindFromRoute(
  name: string | symbol | null | undefined,
): CollectionKind {
  if (name === "virtual-collection") return "virtual";
  if (name === "smart-collection") return "smart";
  return "regular";
}

async function ensureLoaded(kind: CollectionKind) {
  if (kind === "regular" && collectionsStore.allCollections.length === 0) {
    await collectionsStore.fetchCollections();
  } else if (
    kind === "virtual" &&
    collectionsStore.virtualCollections.length === 0
  ) {
    const type =
      localStorage.getItem("settings.virtualCollectionType") ?? "collection";
    await collectionsStore.fetchVirtualCollections(type);
  } else if (
    kind === "smart" &&
    collectionsStore.smartCollections.length === 0
  ) {
    await collectionsStore.fetchSmartCollections();
  }
}

function findById(kind: CollectionKind, id: string): AnyCollection | undefined {
  if (kind === "regular") {
    return collectionsStore.allCollections.find((c) => String(c.id) === id);
  }
  if (kind === "virtual") {
    return collectionsStore.virtualCollections.find((c) => String(c.id) === id);
  }
  return collectionsStore.smartCollections.find((c) => String(c.id) === id);
}

async function loadForRoute(kind: CollectionKind, id: string) {
  currentKind.value = kind;
  await ensureLoaded(kind);

  const collection = findById(kind, id);
  if (!collection) {
    notFound.value = true;
    currentCollection.value = null;
    return;
  }
  notFound.value = false;
  currentCollection.value = collection;

  // Full reset() — drops every `current*` field (so a prior Platform
  // doesn't leak a platform_ids filter into this collection request),
  // clears _allRoms + pagination, and resets `fetchingRoms` so the
  // fetchRoms re-entrancy guard doesn't silently drop this call while
  // a previous view's fetch is still in flight. Matches v1's
  // resetGallery() pattern.
  romsStore.reset();

  if (kind === "regular") {
    romsStore.setCurrentCollection(collection as Collection);
  } else if (kind === "virtual") {
    romsStore.setCurrentVirtualCollection(collection as VirtualCollection);
  } else {
    romsStore.setCurrentSmartCollection(collection as SmartCollection);
  }

  document.title = collection.name;
  await romsStore.fetchRoms();
  await nextTick();
  setupSpy();
}

onMounted(() => {
  loadForRoute(kindFromRoute(route.name), String(route.params.collection));
});

onBeforeRouteUpdate((to) => {
  loadForRoute(kindFromRoute(to.name), String(to.params.collection));
});

watch(
  () => [route.name, route.params.collection] as const,
  ([name, id]) => {
    if (id == null) return;
    loadForRoute(kindFromRoute(name), String(id));
  },
);

watch(virtualItems, () => nextTick().then(setupSpy));

onBeforeUnmount(() => {
  if (searchDebounce) clearTimeout(searchDebounce);
  searchTerm.value = null;
  teardownSpy();
});

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
    romsStore.fetchRoms();
  }, 300);
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
</script>

<template>
  <section ref="sectionEl" class="r-v2-coll">
    <RVirtualScroller
      ref="scrollerRef"
      :items="virtualItems"
      class="r-v2-coll__scroller r-v2-scroll-hidden"
    >
      <template #default="{ item }">
        <div
          class="r-v2-coll__item"
          :data-spy-letters="spyLetters(item as GalleryItem)"
        >
          <template v-if="itemKind(item as GalleryItem) === 'hero'">
            <InfoPanel v-if="currentCollection" :title="currentCollection.name">
              <template #cover>
                <div
                  class="r-v2-coll__panel-cover"
                  :style="{
                    viewTransitionName: `coll-cover-${currentKind}-${currentCollection.id}`,
                  }"
                >
                  <CollectionMosaic
                    :covers="mosaicCovers"
                    aspect-ratio="140 / 188"
                  />
                </div>
              </template>
              <template #eyebrow>
                <span class="r-eyebrow">{{ kindLabel }}</span>
              </template>
              <template v-if="description" #tags>
                <RChip size="small" variant="tonal" :rounded="20">
                  {{ description }}
                </RChip>
              </template>
              <template #stats>
                <Stat :value="currentCollection.rom_count" label="Games" />
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
            search-placeholder="Filter this collection…"
            @update:group-by="groupBy = $event"
            @update:layout="layout = $event"
            @update:search="setSearch"
          />

          <div
            v-else-if="itemKind(item as GalleryItem) === 'letter-header'"
            class="r-v2-coll__letter-heading"
          >
            {{ asLetterHeader(item as GalleryItem).letter }}
          </div>

          <div
            v-else-if="itemKind(item as GalleryItem) === 'row'"
            class="r-v2-coll__row"
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
            class="r-v2-coll__empty"
          >
            {{ asEmpty(item as GalleryItem).message }}
          </div>

          <div
            v-else-if="itemKind(item as GalleryItem) === 'skeleton-row'"
            class="r-v2-coll__row"
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
.r-v2-coll {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: calc(100vh - var(--r-nav-h));
  position: relative;
}

.r-v2-coll__scroller {
  flex: 1;
  height: 100%;
  padding: 32px var(--r-row-pad) 60px;
}

.r-v2-coll__item {
  width: 100%;
}

.r-v2-coll__panel-cover {
  width: 140px;
  height: 188px;
  border-radius: var(--r-radius-lg);
  overflow: hidden;
  box-shadow: var(--r-elev-2);
}

.r-v2-coll__letter-heading {
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--r-color-fg-faint);
  padding: 20px 0 12px;
}

.r-v2-coll__row {
  display: grid;
  gap: 18px 12px;
  padding-bottom: 18px;
}

.r-v2-coll__empty {
  padding: 80px 0;
  color: var(--r-color-fg-faint);
  font-size: 13.5px;
  text-align: center;
}

@media (max-width: 768px) {
  .r-v2-coll__scroller {
    padding: 16px 14px 80px;
  }
  .r-v2-coll__panel-cover {
    width: 100px;
    height: 134px;
  }
  .r-v2-coll__row {
    gap: 12px 10px;
  }
}
</style>
