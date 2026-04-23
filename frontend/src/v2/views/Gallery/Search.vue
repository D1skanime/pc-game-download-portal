<script setup lang="ts">
import { RChip, RTextField } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import storeGalleryFilter from "@/stores/galleryFilter";
import storeHeartbeat from "@/stores/heartbeat";
import storeRoms from "@/stores/roms";
import GameGrid from "@/v2/components/Gallery/GameGrid.vue";
import LoadMore from "@/v2/components/Gallery/LoadMore.vue";
import EmptyState from "@/v2/components/shared/EmptyState.vue";
import PageHeader from "@/v2/components/shared/PageHeader.vue";

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
    <PageHeader title="Search" class="r-v2-search__head">
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

    <EmptyState
      v-if="!initialSearch && !searchTerm"
      variant="boxed"
      icon="mdi-magnify"
      message="Type to search across your whole library."
    />

    <template v-else>
      <GameGrid
        :roms="allRoms"
        :loading="fetchingRoms"
        :webp="supportsWebp"
        :show-platform="true"
      />

      <EmptyState
        v-if="!fetchingRoms && allRoms.length === 0 && searchTerm"
        variant="boxed"
        icon="mdi-emoticon-confused-outline"
        :message="`No games match &quot;${searchTerm}&quot;.`"
      />

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
  padding: 32px var(--r-row-pad) 60px;
}

.r-v2-search__input {
  max-width: 640px;
}

@media (max-width: 768px) {
  .r-v2-search {
    padding: 16px 14px 80px;
  }
}
</style>
