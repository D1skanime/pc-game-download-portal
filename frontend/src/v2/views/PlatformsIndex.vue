<script setup lang="ts">
// PlatformsIndex — full grid of every platform, with the same toolbar
// (search / groupBy / layout) the ROM galleries use. Toolbar state lives
// in `useGalleryMode` so toggling layout here also affects Platform /
// Collection / Search ROM views — one consistent reading mode across
// every main surface. Search is local (per-view URL ?search=) since the
// platforms list is small enough that no Pinia store is warranted.
import { RDivider, RLetterHeading, RSkeletonBlock } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";
import storePlatforms, { type Platform } from "@/stores/platforms";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import PlatformListHeader from "@/v2/components/Platforms/PlatformListHeader.vue";
import PlatformListRow from "@/v2/components/Platforms/PlatformListRow.vue";
import PlatformTile from "@/v2/components/Platforms/PlatformTile.vue";
import EmptyState from "@/v2/components/shared/EmptyState.vue";
import PageHeader from "@/v2/components/shared/PageHeader.vue";
import { useGalleryMode } from "@/v2/composables/useGalleryMode";
import { useGalleryViewModeUrl } from "@/v2/composables/useGalleryViewModeUrl";
import { useTileSearchUrl } from "@/v2/composables/useTileSearchUrl";

const platformsStore = storePlatforms();
const { filledPlatforms, fetchingPlatforms } = storeToRefs(platformsStore);

const { groupBy, layout } = useGalleryMode();
useGalleryViewModeUrl();
const searchTerm = useTileSearchUrl();

onMounted(() => {
  if (platformsStore.allPlatforms.length === 0) {
    platformsStore.fetchPlatforms();
  }
});

const filtered = computed<Platform[]>(() => {
  const term = searchTerm.value.trim().toLowerCase();
  if (!term) return filledPlatforms.value;
  return filledPlatforms.value.filter((p) =>
    p.display_name.toLowerCase().includes(term),
  );
});

const totalCount = computed(() => filledPlatforms.value.length);
const noResults = computed(
  () =>
    !fetchingPlatforms.value &&
    totalCount.value > 0 &&
    filtered.value.length === 0,
);

// Letter buckets for groupBy=letter. Non-alpha first chars roll up under
// "#" so Greek / numeric / symbol-prefixed platform names still land in
// a stable section.
type LetterGroup = { letter: string; items: Platform[] };
const letterGroups = computed<LetterGroup[]>(() => {
  const sorted = [...filtered.value].sort((a, b) =>
    a.display_name.localeCompare(b.display_name),
  );
  const map = new Map<string, Platform[]>();
  for (const p of sorted) {
    const ch = p.display_name.charAt(0).toUpperCase();
    const key = /[A-Z]/.test(ch) ? ch : "#";
    const bucket = map.get(key);
    if (bucket) bucket.push(p);
    else map.set(key, [p]);
  }
  return [...map.entries()]
    .sort(([a], [b]) => {
      // "#" sorts after letters so the alphabetical run is unbroken.
      if (a === "#") return 1;
      if (b === "#") return -1;
      return a.localeCompare(b);
    })
    .map(([letter, items]) => ({ letter, items }));
});

// In list mode grouping is meaningless; the toolbar disables the
// groupBy toggle in this case but the URL might still carry it from a
// shared link, so mirror the same constraint when picking a render
// branch.
const showLetterGroups = computed(
  () => layout.value === "grid" && groupBy.value === "letter",
);
</script>

<template>
  <section class="r-v2-pidx">
    <PageHeader title="Platforms" :count="totalCount" />

    <RDivider class="r-v2-pidx__header-divider" />

    <GalleryToolbar
      :group-by="groupBy"
      :layout="layout"
      :search="searchTerm"
      show-search
      search-placeholder="Search platforms"
      @update:group-by="groupBy = $event"
      @update:layout="layout = $event"
      @update:search="searchTerm = $event"
    />

    <div v-if="fetchingPlatforms && !totalCount" class="r-v2-pidx__grid">
      <RSkeletonBlock
        v-for="n in 16"
        :key="`sk-${n}`"
        width="100%"
        height="140px"
        rounded="card"
      />
    </div>

    <EmptyState
      v-else-if="!totalCount"
      message="No platforms found. Run a scan to populate your library."
    />

    <EmptyState
      v-else-if="noResults"
      :message="`No platforms match “${searchTerm}”.`"
    />

    <!-- List mode — rows underneath a sticky-style column header. -->
    <div v-else-if="layout === 'list'" class="r-v2-pidx__list">
      <PlatformListHeader />
      <PlatformListRow
        v-for="p in filtered"
        :key="p.id"
        :id="p.id"
        :slug="p.slug"
        :fs-slug="p.fs_slug"
        :display-name="p.display_name"
        :rom-count="p.rom_count"
      />
    </div>

    <!-- Grid mode, grouped by letter. -->
    <div v-else-if="showLetterGroups">
      <template v-for="g in letterGroups" :key="g.letter">
        <RLetterHeading :label="g.letter" />
        <div class="r-v2-pidx__grid">
          <PlatformTile
            v-for="p in g.items"
            :id="p.id"
            :key="p.id"
            :slug="p.slug"
            :fs-slug="p.fs_slug"
            :display-name="p.display_name"
            :rom-count="p.rom_count"
            variant="grid"
          />
        </div>
      </template>
    </div>

    <!-- Grid mode, flat. -->
    <div v-else class="r-v2-pidx__grid">
      <PlatformTile
        v-for="p in filtered"
        :id="p.id"
        :key="p.id"
        :slug="p.slug"
        :fs-slug="p.fs_slug"
        :display-name="p.display_name"
        :rom-count="p.rom_count"
        variant="grid"
      />
    </div>
  </section>
</template>

<style scoped>
.r-v2-pidx {
  padding: 32px var(--r-row-pad) 60px;
}

/* Mirror the gallery shell's header→toolbar separator so the visual
   rhythm matches Search / Platform / Collection ROM views. */
.r-v2-pidx__header-divider {
  margin-bottom: 16px;
}

.r-v2-pidx__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
}

.r-v2-pidx__list :deep(.plat-list-row:last-child) {
  border-bottom: 0;
}

@media (max-width: 768px) {
  .r-v2-pidx {
    padding: 16px 14px 80px;
  }
  .r-v2-pidx__grid {
    grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
    gap: 10px;
  }
}
</style>
