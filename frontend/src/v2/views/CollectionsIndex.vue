<script setup lang="ts">
// CollectionsIndex — full grid of every collection (regular + smart +
// virtual). Each item is a CollectionTile in the "grid" variant, with
// the kind badge driven by a prop.
import { RSkeletonBlock } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";
import storeCollections, {
  type Collection,
  type SmartCollection,
  type VirtualCollection,
} from "@/stores/collections";
import CollectionTile from "@/v2/components/Collections/CollectionTile.vue";
import EmptyState from "@/v2/components/shared/EmptyState.vue";
import PageHeader from "@/v2/components/shared/PageHeader.vue";
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

const count = computed(() => tiles.value.length);
</script>

<template>
  <section class="r-v2-cidx">
    <PageHeader title="Collections" :count="count" />

    <div v-if="fetchingCollections && !count" class="r-v2-cidx__grid">
      <RSkeletonBlock
        v-for="n in 12"
        :key="`sk-${n}`"
        width="100%"
        height="150px"
        rounded="lg"
      />
    </div>

    <EmptyState
      v-else-if="!count"
      message="You don't have any collections yet. Favourite a game or create one from any ROM's action bar to populate this view."
    />

    <div v-else class="r-v2-cidx__grid">
      <CollectionTile
        v-for="c in tiles"
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

.r-v2-cidx__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 20px 16px;
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
