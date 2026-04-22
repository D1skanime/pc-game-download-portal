<script setup lang="ts">
import { RBtn, RChip, RGameGrid, RIcon, RLoadMore } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import { onBeforeRouteUpdate, useRoute } from "vue-router";
import storeCollections, {
  type Collection,
  type SmartCollection,
  type VirtualCollection,
} from "@/stores/collections";
import storeHeartbeat from "@/stores/heartbeat";
import storeRoms from "@/stores/roms";

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

const remaining = computed(() =>
  Math.max(0, fetchTotalRoms.value - allRoms.value.length),
);
const hasMore = computed(() => remaining.value > 0);

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
}

function loadMore() {
  if (fetchingRoms.value || !hasMore.value) return;
  romsStore.fetchRoms();
}

onMounted(() => {
  const kind = kindFromRoute(route.name);
  loadForRoute(kind, String(route.params.collection));
});

onBeforeRouteUpdate((to) => {
  const kind = kindFromRoute(to.name);
  loadForRoute(kind, String(to.params.collection));
});

watch(
  () => [route.name, route.params.collection] as const,
  ([name, id]) => {
    if (id == null) return;
    loadForRoute(kindFromRoute(name), String(id));
  },
);

const kindLabel = computed(() => {
  if (currentKind.value === "virtual") return "Virtual";
  if (currentKind.value === "smart") return "Smart";
  return "Collection";
});
</script>

<template>
  <section class="r-v2-gallery">
    <header v-if="currentCollection" class="r-v2-gallery__head">
      <div class="r-v2-gallery__cover">
        <RIcon
          :icon="
            currentKind === 'smart' ? 'mdi-filter' : 'mdi-bookmark-multiple'
          "
          size="28"
          color="primary"
        />
      </div>
      <div>
        <div class="r-v2-gallery__eyebrow">
          {{ kindLabel }}
        </div>
        <h1 class="r-v2-gallery__title">
          {{ currentCollection.name }}
        </h1>
        <div class="r-v2-gallery__meta">
          <RChip size="small" variant="tonal">
            {{ currentCollection.rom_count }} games
          </RChip>
        </div>
      </div>
    </header>

    <div v-if="notFound" class="r-v2-gallery__empty">
      <RIcon icon="mdi-alert-circle-outline" size="36" />
      <p>Collection not found.</p>
      <RBtn to="/" variant="outlined" prepend-icon="mdi-home">
        Back to home
      </RBtn>
    </div>

    <template v-else>
      <RGameGrid
        :roms="allRoms"
        :loading="fetchingRoms"
        :webp="supportsWebp"
        :show-platform="true"
      />

      <div
        v-if="!fetchingRoms && allRoms.length === 0 && !notFound"
        class="r-v2-gallery__empty"
      >
        <RIcon icon="mdi-bookmark-outline" size="36" />
        <p>This collection is empty.</p>
      </div>

      <RLoadMore
        v-if="hasMore"
        :loading="fetchingRoms"
        :remaining="remaining"
        @load="loadMore"
      />
    </template>
  </section>
</template>

<style scoped>
.r-v2-gallery {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-5);
}

.r-v2-gallery__head {
  display: flex;
  align-items: center;
  gap: var(--r-space-4);
}

.r-v2-gallery__cover {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  background: linear-gradient(
    135deg,
    var(--r-color-surface),
    var(--r-color-bg)
  );
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}

.r-v2-gallery__eyebrow {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-xs);
  font-weight: var(--r-font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.r-v2-gallery__title {
  margin: 2px 0 0 0;
  font-size: var(--r-font-size-3xl);
  font-weight: var(--r-font-weight-bold);
  line-height: var(--r-line-height-tight);
}

.r-v2-gallery__meta {
  display: flex;
  gap: var(--r-space-2);
  margin-top: var(--r-space-2);
}

.r-v2-gallery__empty {
  padding: var(--r-space-8);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--r-space-3);
  color: var(--r-color-fg-muted);
  background: var(--r-color-bg-elevated);
  border: 1px dashed var(--r-color-border);
  border-radius: var(--r-radius-md);
  text-align: center;
}
</style>
