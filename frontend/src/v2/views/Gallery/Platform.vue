<script setup lang="ts">
import {
  RBtn,
  RChip,
  RGameGrid,
  RIcon,
  RLoadMore,
  RPlatformIcon,
} from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import { onBeforeRouteUpdate, useRoute } from "vue-router";
import storeHeartbeat from "@/stores/heartbeat";
import storePlatforms from "@/stores/platforms";
import storeRoms from "@/stores/roms";

const route = useRoute();
const platformsStore = storePlatforms();
const romsStore = storeRoms();
const heartbeatStore = storeHeartbeat();

const {
  _allRoms: allRoms,
  currentPlatform,
  fetchingRoms,
  fetchTotalRoms,
  fetchOffset,
} = storeToRefs(romsStore);

const notFound = ref(false);

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

async function ensurePlatforms() {
  if (platformsStore.allPlatforms.length === 0) {
    await platformsStore.fetchPlatforms();
  }
}

async function loadForId(platformId: number) {
  await ensurePlatforms();
  const platform = platformsStore.allPlatforms.find((p) => p.id === platformId);
  if (!platform) {
    notFound.value = true;
    return;
  }
  notFound.value = false;

  if (currentPlatform.value?.id !== platform.id) {
    romsStore.resetPagination();
    romsStore._allRoms = [];
    romsStore.setCurrentPlatform(platform);
  }
  document.title = platform.display_name;
  await romsStore.fetchRoms();
}

function loadMore() {
  if (fetchingRoms.value || !hasMore.value) return;
  romsStore.fetchRoms();
}

onMounted(() => {
  loadForId(Number(route.params.platform));
});

onBeforeRouteUpdate((to) => {
  if (to.name === "platform") {
    loadForId(Number(to.params.platform));
  }
});

watch(
  () => route.params.platform,
  (next) => {
    if (next != null) loadForId(Number(next));
  },
);

// Unused but imported — referenced inline in the future
void fetchOffset;
</script>

<template>
  <section class="r-v2-gallery">
    <header v-if="currentPlatform" class="r-v2-gallery__head">
      <RPlatformIcon
        :name="currentPlatform.name"
        :alt="currentPlatform.display_name"
        :size="48"
        class="r-v2-gallery__platform-icon"
      />
      <div>
        <h1 class="r-v2-gallery__title">
          {{ currentPlatform.display_name }}
        </h1>
        <div class="r-v2-gallery__meta">
          <RChip size="small" variant="tonal">
            {{ currentPlatform.rom_count }} games
          </RChip>
        </div>
      </div>
    </header>

    <div v-if="notFound" class="r-v2-gallery__empty">
      <RIcon icon="mdi-alert-circle-outline" size="36" />
      <p>Platform not found.</p>
      <RBtn to="/" variant="outlined" prepend-icon="mdi-home">
        Back to home
      </RBtn>
    </div>

    <template v-else>
      <RGameGrid
        :roms="allRoms"
        :loading="fetchingRoms"
        :webp="supportsWebp"
        :show-platform="false"
      />

      <div
        v-if="!fetchingRoms && allRoms.length === 0 && !notFound"
        class="r-v2-gallery__empty"
      >
        <RIcon icon="mdi-nintendo-game-boy" size="36" />
        <p>No games in this platform yet.</p>
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

.r-v2-gallery__platform-icon {
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  padding: var(--r-space-2);
}

.r-v2-gallery__title {
  margin: 0;
  font-size: var(--r-font-size-3xl);
  font-weight: var(--r-font-weight-bold);
  line-height: var(--r-line-height-tight);
}

.r-v2-gallery__meta {
  display: flex;
  gap: var(--r-space-2);
  margin-top: var(--r-space-1);
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
