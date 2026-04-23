<script setup lang="ts">
// Search — same gallery controls as Platform/Collection, but the search
// field here filters the whole library (no platform/collection scope).
// Fetches the first paginated batch on mount (matches v1) so users land
// on results immediately.
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
import storeGalleryFilter from "@/stores/galleryFilter";
import storeHeartbeat from "@/stores/heartbeat";
import storeRoms from "@/stores/roms";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import GameGrid from "@/v2/components/Gallery/GameGrid.vue";
import GameList from "@/v2/components/Gallery/GameList.vue";
import LetterGroupedGrid from "@/v2/components/Gallery/LetterGroupedGrid.vue";
import LoadMore from "@/v2/components/Gallery/LoadMore.vue";
import EmptyState from "@/v2/components/shared/EmptyState.vue";
import PageHeader from "@/v2/components/shared/PageHeader.vue";
import { useGalleryMode } from "@/v2/composables/useGalleryMode";
import { useLetterGroups } from "@/v2/composables/useLetterGroups";

const romsStore = storeRoms();
const galleryFilterStore = storeGalleryFilter();
const heartbeatStore = storeHeartbeat();

const {
  _allRoms: allRoms,
  fetchingRoms,
  fetchTotalRoms,
  initialSearch,
  characterIndex,
  romIdIndex,
} = storeToRefs(romsStore);
const { searchTerm } = storeToRefs(galleryFilterStore);
const { groupBy, layout, toolbarPosition } = useGalleryMode();

// Local mirror of the debounced input so typing stays fluid while the store
// only updates on pause.
const searchInput = ref(searchTerm.value ?? "");
let searchDebounce: ReturnType<typeof setTimeout> | null = null;

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

watch(allRoms, () => onGridScroll(), { deep: false });

onMounted(async () => {
  // Global search — drop any platform/collection scoping from previous views.
  romsStore.setCurrentPlatform(null);
  romsStore.setCurrentCollection(null);
  // Land on the first paginated batch (matches v1).
  if (allRoms.value.length === 0) {
    romsStore.resetPagination();
    await romsStore.fetchRoms();
  }
  romsStore.initialSearch = true;
  await nextTick();
  onGridScroll();
});

onBeforeUnmount(() => {
  if (searchDebounce) clearTimeout(searchDebounce);
});
</script>

<template>
  <section class="r-v2-search">
    <div
      :ref="(el) => (scrollEl = el as HTMLElement | null)"
      class="r-v2-search__scroll r-v2-scroll-hidden"
      @scroll="onGridScroll"
    >
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

      <GalleryToolbar
        v-if="toolbarPosition === 'header'"
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

      <!-- Grid + grouped by letter -->
      <LetterGroupedGrid
        v-if="layout === 'grid' && groupBy === 'letter'"
        :groups="letterGroups"
        :fetching="fetchingRoms"
        :has-more="hasMore"
        :remaining="remaining"
        :webp="supportsWebp"
        empty-label="No games match your search."
        :skeleton-count="18"
        :set-letter-ref="setLetterRef"
        @load-more="loadMore"
      />

      <!-- Grid + flat -->
      <template v-else-if="layout === 'grid'">
        <GameGrid
          :roms="allRoms"
          :loading="fetchingRoms"
          :webp="supportsWebp"
          :show-platform="true"
        />
        <LoadMore
          v-if="hasMore"
          :loading="fetchingRoms"
          :remaining="remaining"
          @load="loadMore"
        />
      </template>

      <!-- List -->
      <GameList
        v-else
        :roms="allRoms"
        :total-roms="fetchTotalRoms"
        :loading="fetchingRoms"
        :webp="supportsWebp"
        @update:options="onListSort"
      />

      <!-- Empty state (after results resolve) -->
      <EmptyState
        v-if="!fetchingRoms && allRoms.length === 0 && searchTerm"
        variant="boxed"
        icon="mdi-emoticon-confused-outline"
        :message="`No games match &quot;${searchTerm}&quot;.`"
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
.r-v2-search {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: calc(100vh - var(--r-nav-h));
  position: relative;
}

.r-v2-search__scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 32px var(--r-row-pad) 60px;
}

@media (max-width: 768px) {
  .r-v2-search__scroll {
    padding: 16px 14px 80px;
  }
}
</style>
