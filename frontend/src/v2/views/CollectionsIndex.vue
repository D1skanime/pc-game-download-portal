<script setup lang="ts">
// CollectionsIndex — full grid of every collection (regular + smart +
// virtual). Same toolbar (search / groupBy / layout) the ROM galleries
// use, with state shared via `useGalleryMode` so toggling layout here
// also flips it on the rest of the gallery surfaces. Search is local
// (per-view URL ?search=) — the collections list is small enough that
// no Pinia store is warranted.
import { RDivider, RLetterHeading, RSkeletonBlock } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";
import storeCollections, {
  type Collection,
  type SmartCollection,
  type VirtualCollection,
} from "@/stores/collections";
import CollectionListHeader from "@/v2/components/Collections/CollectionListHeader.vue";
import CollectionListRow from "@/v2/components/Collections/CollectionListRow.vue";
import CollectionTile from "@/v2/components/Collections/CollectionTile.vue";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import EmptyState from "@/v2/components/shared/EmptyState.vue";
import PageHeader from "@/v2/components/shared/PageHeader.vue";
import { useGalleryMode } from "@/v2/composables/useGalleryMode";
import { useGalleryViewModeUrl } from "@/v2/composables/useGalleryViewModeUrl";
import { useTileSearchUrl } from "@/v2/composables/useTileSearchUrl";
import { useWebpSupport } from "@/v2/composables/useWebpSupport";

type AnyCollection = Collection | VirtualCollection | SmartCollection;
type Kind = "regular" | "virtual" | "smart";
type CollectionTileEntry = {
  id: string | number;
  name: string;
  rom_count: number;
  covers: string[];
  link: string;
  kind: Kind;
};

const collectionsStore = storeCollections();
const { toWebp } = useWebpSupport();
const {
  allCollections,
  virtualCollections,
  smartCollections,
  fetchingCollections,
} = storeToRefs(collectionsStore);

const { groupBy, layout } = useGalleryMode();
useGalleryViewModeUrl();
const searchTerm = useTileSearchUrl();

onMounted(() => {
  if (allCollections.value.length === 0) collectionsStore.fetchCollections();
  if (smartCollections.value.length === 0) {
    collectionsStore.fetchSmartCollections();
  }
  if (virtualCollections.value.length === 0) {
    const type =
      localStorage.getItem("settings.virtualCollectionType") ?? "collection";
    collectionsStore.fetchVirtualCollections(type);
  }
});

function coversFor(c: AnyCollection): string[] {
  const paths = (c as { path_covers_small?: string[] }).path_covers_small ?? [];
  return paths.slice(0, 4).map(toWebp);
}

const tiles = computed<CollectionTileEntry[]>(() => {
  const out: CollectionTileEntry[] = [];
  for (const c of allCollections.value) {
    out.push({
      id: c.id,
      name: c.name,
      rom_count: c.rom_count,
      covers: coversFor(c),
      link: `/collection/${c.id}`,
      kind: "regular",
    });
  }
  for (const c of smartCollections.value) {
    out.push({
      id: c.id,
      name: c.name,
      rom_count: c.rom_count,
      covers: coversFor(c),
      link: `/collection/smart/${c.id}`,
      kind: "smart",
    });
  }
  for (const c of virtualCollections.value) {
    out.push({
      id: c.id,
      name: c.name,
      rom_count: c.rom_count,
      covers: coversFor(c),
      link: `/collection/virtual/${c.id}`,
      kind: "virtual",
    });
  }
  return out;
});

const filtered = computed<CollectionTileEntry[]>(() => {
  const term = searchTerm.value.trim().toLowerCase();
  if (!term) return tiles.value;
  return tiles.value.filter((c) => c.name.toLowerCase().includes(term));
});

const totalCount = computed(() => tiles.value.length);
const noResults = computed(
  () =>
    !fetchingCollections.value &&
    totalCount.value > 0 &&
    filtered.value.length === 0,
);

type LetterGroup = { letter: string; items: CollectionTileEntry[] };
const letterGroups = computed<LetterGroup[]>(() => {
  const sorted = [...filtered.value].sort((a, b) =>
    a.name.localeCompare(b.name),
  );
  const map = new Map<string, CollectionTileEntry[]>();
  for (const c of sorted) {
    const ch = c.name.charAt(0).toUpperCase();
    const key = /[A-Z]/.test(ch) ? ch : "#";
    const bucket = map.get(key);
    if (bucket) bucket.push(c);
    else map.set(key, [c]);
  }
  return [...map.entries()]
    .sort(([a], [b]) => {
      if (a === "#") return 1;
      if (b === "#") return -1;
      return a.localeCompare(b);
    })
    .map(([letter, items]) => ({ letter, items }));
});

const showLetterGroups = computed(
  () => layout.value === "grid" && groupBy.value === "letter",
);
</script>

<template>
  <section class="r-v2-cidx">
    <PageHeader title="Collections" :count="totalCount" />

    <RDivider class="r-v2-cidx__header-divider" />

    <GalleryToolbar
      :group-by="groupBy"
      :layout="layout"
      :search="searchTerm"
      show-search
      search-placeholder="Search collections…"
      @update:group-by="groupBy = $event"
      @update:layout="layout = $event"
      @update:search="searchTerm = $event"
    />

    <div v-if="fetchingCollections && !totalCount" class="r-v2-cidx__grid">
      <RSkeletonBlock
        v-for="n in 12"
        :key="`sk-${n}`"
        width="100%"
        height="150px"
        rounded="lg"
      />
    </div>

    <EmptyState
      v-else-if="!totalCount"
      message="You don't have any collections yet. Favourite a game or create one from any ROM's action bar to populate this view."
    />

    <EmptyState
      v-else-if="noResults"
      :message="`No collections match “${searchTerm}”.`"
    />

    <div v-else-if="layout === 'list'" class="r-v2-cidx__list">
      <CollectionListHeader />
      <CollectionListRow
        v-for="c in filtered"
        :id="c.id"
        :key="`${c.kind}-${c.id}`"
        :to="c.link"
        :name="c.name"
        :rom-count="c.rom_count"
        :covers="c.covers"
        :kind="c.kind"
      />
    </div>

    <div v-else-if="showLetterGroups">
      <template v-for="g in letterGroups" :key="g.letter">
        <RLetterHeading :label="g.letter" />
        <div class="r-v2-cidx__grid">
          <CollectionTile
            v-for="c in g.items"
            :id="c.id"
            :key="`${c.kind}-${c.id}`"
            :to="c.link"
            :name="c.name"
            :rom-count="c.rom_count"
            :covers="c.covers"
            :kind="c.kind"
            variant="grid"
          />
        </div>
      </template>
    </div>

    <div v-else class="r-v2-cidx__grid">
      <CollectionTile
        v-for="c in filtered"
        :id="c.id"
        :key="`${c.kind}-${c.id}`"
        :to="c.link"
        :name="c.name"
        :rom-count="c.rom_count"
        :covers="c.covers"
        :kind="c.kind"
        variant="grid"
      />
    </div>
  </section>
</template>

<style scoped>
.r-v2-cidx {
  padding: 32px var(--r-row-pad) 60px;
}

/* Mirror the gallery shell's header→toolbar separator so the visual
   rhythm matches Search / Platform / Collection ROM views. */
.r-v2-cidx__header-divider {
  margin-bottom: 16px;
}

.r-v2-cidx__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 20px 16px;
}

.r-v2-cidx__list :deep(.coll-list-row:last-child) {
  border-bottom: 0;
}

@media (max-width: 768px) {
  .r-v2-cidx {
    padding: 16px 14px 80px;
  }
  .r-v2-cidx__grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 16px 10px;
  }
}
</style>
