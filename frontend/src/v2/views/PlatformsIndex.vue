<script setup lang="ts">
// PlatformsIndex — full grid of every platform. Fills with PlatformTile
// in its "grid" variant so the tile matches the Home row visually but
// fills the auto-fit cell.
import { RSkeletonBlock } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";
import storePlatforms from "@/stores/platforms";
import PlatformTile from "@/v2/components/Platforms/PlatformTile.vue";
import EmptyState from "@/v2/components/shared/EmptyState.vue";
import PageHeader from "@/v2/components/shared/PageHeader.vue";

const platformsStore = storePlatforms();
const { filledPlatforms, fetchingPlatforms } = storeToRefs(platformsStore);

onMounted(() => {
  if (platformsStore.allPlatforms.length === 0) {
    platformsStore.fetchPlatforms();
  }
});

const count = computed(() => filledPlatforms.value.length);
</script>

<template>
  <section class="r-v2-pidx">
    <PageHeader title="Platforms" :count="count" />

    <div v-if="fetchingPlatforms && !count" class="r-v2-pidx__grid">
      <RSkeletonBlock
        v-for="n in 16"
        :key="`sk-${n}`"
        width="100%"
        height="140px"
        rounded="card"
      />
    </div>

    <EmptyState
      v-else-if="!count"
      message="No platforms found. Run a scan to populate your library."
    />

    <div v-else class="r-v2-pidx__grid">
      <PlatformTile
        v-for="p in filledPlatforms"
        :key="p.id"
        :id="p.id"
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

.r-v2-pidx__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
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
