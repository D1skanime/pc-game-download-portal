<script setup lang="ts">
// Collection gallery — mirror of Platform.vue but with a CollectionMosaic
// in the info panel instead of an RPlatformIcon. Uses the same
// LetterGroupedGrid + useLetterGroups primitives.
import { RChip } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { onBeforeRouteUpdate, useRoute } from "vue-router";
import storeCollections, {
  type Collection,
  type SmartCollection,
  type VirtualCollection,
} from "@/stores/collections";
import storeHeartbeat from "@/stores/heartbeat";
import storeRoms from "@/stores/roms";
import CollectionMosaic from "@/v2/components/Collections/CollectionMosaic.vue";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import InfoPanel from "@/v2/components/Gallery/InfoPanel.vue";
import LetterGroupedGrid from "@/v2/components/Gallery/LetterGroupedGrid.vue";
import BackBtn from "@/v2/components/shared/BackBtn.vue";
import Stat from "@/v2/components/shared/Stat.vue";
import { useLetterGroups } from "@/v2/composables/useLetterGroups";

type AnyCollection = Collection | VirtualCollection | SmartCollection;
type CollectionKind = "regular" | "virtual" | "smart";

const route = useRoute();
const collectionsStore = storeCollections();
const romsStore = storeRoms();
const heartbeatStore = storeHeartbeat();

const {
  _allRoms: allRoms,
  fetchingRoms,
  fetchTotalRoms,
} = storeToRefs(romsStore);

const notFound = ref(false);
const currentKind = ref<CollectionKind>("regular");
const currentCollection = ref<AnyCollection | null>(null);

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
  setLetterRef,
  scrollToLetter,
  onGridScroll,
} = useLetterGroups(allRoms);

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

  romsStore.resetPagination();
  romsStore._allRoms = [];

  if (kind === "regular") {
    romsStore.setCurrentCollection(collection as Collection);
    romsStore.setCurrentVirtualCollection(null);
    romsStore.setCurrentSmartCollection(null);
  } else if (kind === "virtual") {
    romsStore.setCurrentCollection(null);
    romsStore.setCurrentVirtualCollection(collection as VirtualCollection);
    romsStore.setCurrentSmartCollection(null);
  } else {
    romsStore.setCurrentCollection(null);
    romsStore.setCurrentVirtualCollection(null);
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
</script>

<template>
  <section class="r-v2-coll">
    <header class="r-v2-coll__header">
      <BackBtn to="/collections" label="Collections" />
    </header>

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

      <div v-if="notFound" class="r-v2-coll__empty">Collection not found.</div>

      <LetterGroupedGrid
        v-else
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
    </div>

    <AlphaStrip
      v-if="letterGroups.length"
      :available="availableLetters"
      :current="currentLetter"
      @pick="scrollToLetter"
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

.r-v2-coll__header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2;
  padding: 20px var(--r-row-pad) 0;
  display: flex;
  align-items: center;
  gap: 14px;
  pointer-events: none;
}
.r-v2-coll__header > * {
  pointer-events: auto;
}

.r-v2-coll__scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 56px var(--r-row-pad) 60px;
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
    padding: 48px 14px 80px;
  }
  .r-v2-coll__panel-cover {
    width: 100px;
    height: 134px;
  }
}
</style>
