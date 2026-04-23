<script setup lang="ts">
import { RChip, RIcon, RTextField } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import storeGalleryFilter from "@/stores/galleryFilter";
import storeHeartbeat from "@/stores/heartbeat";
import storeRoms from "@/stores/roms";
import GameGrid from "@/v2/components/Gallery/GameGrid.vue";
import LoadMore from "@/v2/components/Gallery/LoadMore.vue";

const romsStore = storeRoms();
const galleryFilterStore = storeGalleryFilter();
const heartbeatStore = storeHeartbeat();

const {
  _allRoms: allRoms,
  fetchingRoms,
  fetchTotalRoms,
  initialSearch,
} = storeToRefs(romsStore);
const { searchTerm } = storeToRefs(galleryFilterStore);

// Local mirror of the debounced input so typing stays fluid while the store
// only updates on pause.
const input = ref(searchTerm.value ?? "");
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

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

function clearAndRefetch() {
  romsStore.resetPagination();
  romsStore._allRoms = [];
  romsStore.fetchRoms();
  romsStore.initialSearch = true;
}

function applyTerm(next: string) {
  const normalized = next.trim();
  if (normalized === (searchTerm.value ?? "")) return;
  searchTerm.value = normalized || null;
  clearAndRefetch();
}

watch(input, (value) => {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => applyTerm(value), 300);
});

function loadMore() {
  if (fetchingRoms.value || !hasMore.value) return;
  romsStore.fetchRoms();
}

onMounted(() => {
  // If we navigated in with an existing term, load it. Otherwise wait for
  // the user to type.
  if (searchTerm.value && allRoms.value.length === 0) {
    romsStore.fetchRoms();
  }
  // Always clear platform/collection scoping so this is truly a global search.
  romsStore.setCurrentPlatform(null);
  romsStore.setCurrentCollection(null);
});

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer);
});
</script>

<template>
  <section class="r-v2-search">
    <header class="r-v2-search__head">
      <div class="r-v2-search__title-wrap">
        <h1 class="r-v2-search__title">Search</h1>
        <RChip
          v-if="initialSearch && !fetchingRoms"
          size="small"
          variant="tonal"
        >
          {{ fetchTotalRoms }} results
        </RChip>
      </div>
      <RTextField
        v-model="input"
        variant="outlined"
        density="comfortable"
        placeholder="Search by name, filename, hash…"
        prepend-inner-icon="mdi-magnify"
        clearable
        hide-details
        class="r-v2-search__input"
      />
    </header>

    <template v-if="!initialSearch && !searchTerm">
      <div class="r-v2-search__empty">
        <RIcon icon="mdi-magnify" size="36" />
        <p>Type to search across your whole library.</p>
      </div>
    </template>

    <template v-else>
      <GameGrid
        :roms="allRoms"
        :loading="fetchingRoms"
        :webp="supportsWebp"
        :show-platform="true"
      />

      <div
        v-if="!fetchingRoms && allRoms.length === 0 && searchTerm"
        class="r-v2-search__empty"
      >
        <RIcon icon="mdi-emoticon-confused-outline" size="36" />
        <p>No games match "{{ searchTerm }}".</p>
      </div>

      <LoadMore
        v-if="hasMore"
        :loading="fetchingRoms"
        :remaining="remaining"
        @load="loadMore"
      />
    </template>
  </section>
</template>

<style scoped>
.r-v2-search {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-5);
}

.r-v2-search__head {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
}

.r-v2-search__title-wrap {
  display: flex;
  align-items: center;
  gap: var(--r-space-3);
}

.r-v2-search__title {
  margin: 0;
  font-size: var(--r-font-size-3xl);
  font-weight: var(--r-font-weight-bold);
  line-height: var(--r-line-height-tight);
}

.r-v2-search__input {
  max-width: 640px;
}

.r-v2-search__empty {
  padding: var(--r-space-10) var(--r-space-6);
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
