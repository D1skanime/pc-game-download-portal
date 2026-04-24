<script setup lang="ts">
// Collection gallery — mirror of Platform.vue with a CollectionMosaic in
// the info panel. Shares the same useGalleryMode-driven grid/list/grouped
// orchestration.
import { RChip } from "@v2/lib";
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
import storeHeartbeat from "@/stores/heartbeat";
import storeRoms from "@/stores/roms";
import CollectionMosaic from "@/v2/components/Collections/CollectionMosaic.vue";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import GameGrid from "@/v2/components/Gallery/GameGrid.vue";
import GameList from "@/v2/components/Gallery/GameList.vue";
import InfoPanel from "@/v2/components/Gallery/InfoPanel.vue";
import LetterGroupedGrid from "@/v2/components/Gallery/LetterGroupedGrid.vue";
import LoadMore from "@/v2/components/Gallery/LoadMore.vue";
import Stat from "@/v2/components/shared/Stat.vue";
import { useGalleryMode } from "@/v2/composables/useGalleryMode";
import { useLetterGroups } from "@/v2/composables/useLetterGroups";

type AnyCollection = Collection | VirtualCollection | SmartCollection;
type CollectionKind = "regular" | "virtual" | "smart";

const route = useRoute();
const collectionsStore = storeCollections();
const romsStore = storeRoms();
const heartbeatStore = storeHeartbeat();
const galleryFilterStore = storeGalleryFilter();
const { searchTerm } = storeToRefs(galleryFilterStore);

const {
  _allRoms: allRoms,
  fetchingRoms,
  fetchTotalRoms,
  characterIndex,
  romIdIndex,
} = storeToRefs(romsStore);

const notFound = ref(false);
const currentKind = ref<CollectionKind>("regular");
const currentCollection = ref<AnyCollection | null>(null);
const { groupBy, layout, toolbarPosition } = useGalleryMode();

const supportsWebp = computed<boolean>(() =>
  Boolean(
    (
      heartbeatStore.value as unknown as {
        FRONTEND?: { IMAGES_WEBP?: boolean };
      }
    )?.FRONTEND?.IMAGES_WEBP,
  ),
);

const mosaicCovers = computed<string[]>(() => {
  const paths =
    (currentCollection.value as { path_covers_small?: string[] } | null)
      ?.path_covers_small ?? [];
  return paths
    .slice(0, 4)
    .map((p) =>
      supportsWebp.value ? p.replace(/\.(png|jpg|jpeg)$/i, ".webp") : p,
    );
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

const {
  scrollEl,
  letterGroups,
  availableLetters,
  currentLetter,
  visibleLetters,
  setLetterRef,
  scrollToLetter,
  onGridScroll,
} = useLetterGroups(allRoms, { characterIndex, romIdIndex });

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
  onGridScroll();
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

watch(allRoms, () => onGridScroll(), { deep: false });

const hasMore = computed(() => allRoms.value.length < fetchTotalRoms.value);
const remaining = computed(() => fetchTotalRoms.value - allRoms.value.length);
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
onBeforeUnmount(() => {
  if (searchDebounce) clearTimeout(searchDebounce);
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
</script>

<template>
  <section class="r-v2-coll">
    <div
      :ref="(el) => (scrollEl = el as HTMLElement | null)"
      class="r-v2-coll__scroll r-v2-scroll-hidden"
      @scroll="onGridScroll"
    >
      <InfoPanel v-if="currentCollection" :title="currentCollection.name">
        <template #cover>
          <div class="r-v2-coll__panel-cover">
            <CollectionMosaic :covers="mosaicCovers" aspect-ratio="140 / 188" />
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

      <GalleryToolbar
        v-if="toolbarPosition === 'header'"
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

      <div v-if="notFound" class="r-v2-coll__empty">Collection not found.</div>

      <LetterGroupedGrid
        v-else-if="layout === 'grid' && groupBy === 'letter'"
        :groups="letterGroups"
        :fetching="fetchingRoms"
        :has-more="hasMore"
        :remaining="remaining"
        :webp="supportsWebp"
        empty-label="This collection is empty."
        :skeleton-count="12"
        :set-letter-ref="setLetterRef"
        @load-more="loadMore"
      />

      <template v-else-if="layout === 'grid'">
        <GameGrid
          :roms="allRoms"
          :loading="fetchingRoms"
          :webp="supportsWebp"
        />
        <LoadMore
          v-if="hasMore"
          :loading="fetchingRoms"
          :remaining="remaining"
          @load="loadMore"
        />
      </template>

      <GameList
        v-else
        :roms="allRoms"
        :total-roms="fetchTotalRoms"
        :loading="fetchingRoms"
        :webp="supportsWebp"
        @update:options="onListSort"
      />
    </div>

    <AlphaStrip
      v-if="letterGroups.length > 0"
      :available="availableLetters"
      :current="currentLetter"
      :visible="visibleLetters"
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

.r-v2-coll__scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 32px var(--r-row-pad) 60px;
}

.r-v2-coll__panel-cover {
  width: 140px;
  height: 188px;
  border-radius: var(--r-radius-lg);
  overflow: hidden;
  box-shadow: var(--r-elev-2);
}

.r-v2-coll__empty {
  padding: 80px 0;
  color: rgba(255, 255, 255, 0.25);
  font-size: 13.5px;
  text-align: center;
}

@media (max-width: 768px) {
  .r-v2-coll__scroll {
    padding: 16px 14px 80px;
  }
  .r-v2-coll__panel-cover {
    width: 100px;
    height: 134px;
  }
}
</style>
