<script setup lang="ts">
// Search — global ROM search. Thin orchestrator: clears any prior
// gallery scope, kicks the initial fetch, and provides a PageHeader
// hero. Everything else lives in `GalleryShell`.
import { RChip } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, ref } from "vue";
import storeGalleryFilter from "@/stores/galleryFilter";
import GalleryShell from "@/v2/components/Gallery/GalleryShell.vue";
import EmptyState from "@/v2/components/shared/EmptyState.vue";
import PageHeader from "@/v2/components/shared/PageHeader.vue";
import storeGalleryRoms from "@/v2/stores/galleryRoms";

const galleryRoms = storeGalleryRoms();
const galleryFilterStore = storeGalleryFilter();
const { searchTerm } = storeToRefs(galleryFilterStore);
const { total, initialFetching } = storeToRefs(galleryRoms);

const initialSearch = ref(false);
const shellRef = ref<InstanceType<typeof GalleryShell> | null>(null);

const showStandaloneEmpty = computed(
  () => !initialFetching.value && total.value === 0 && !!searchTerm.value,
);

const emptyMessage = computed(() =>
  searchTerm.value
    ? `No games match "${searchTerm.value}".`
    : "No games match your search.",
);

onMounted(async () => {
  // Global search — drop ALL gallery scoping from previous views.
  galleryRoms.resetGallery();
  await galleryRoms.fetchWindowAt(0);
  initialSearch.value = true;
  await nextTick();
  shellRef.value?.applyRestoredScroll();
});
</script>

<template>
  <GalleryShell
    ref="shellRef"
    :has-hero="true"
    :hero-height="86"
    search-placeholder="Search by name, filename, hash…"
    :empty-message="emptyMessage"
    :skeleton-row-count="4"
  >
    <template #hero>
      <PageHeader title="Search" bottom-border>
        <template #count>
          <RChip
            v-if="initialSearch && !initialFetching"
            size="small"
            variant="tonal"
          >
            {{ total }} results
          </RChip>
        </template>
      </PageHeader>
    </template>

    <!-- Boxed empty state shown when a search resolves with no hits.
         Falls back to the shell's plain text message when there's no
         active query (e.g., before the user types anything). -->
    <template #empty="{ message }">
      <EmptyState
        v-if="showStandaloneEmpty"
        variant="boxed"
        icon="mdi-emoticon-confused-outline"
        :message="message"
      />
      <span v-else>{{ message }}</span>
    </template>
  </GalleryShell>
</template>
