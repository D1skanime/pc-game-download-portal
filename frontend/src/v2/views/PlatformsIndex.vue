<script setup lang="ts">
// PlatformsIndex — full grid of every platform. Fills with PlatformTile
// in its "grid" variant so the tile matches the Home row visually but
// fills the auto-fit cell.
import { RSkeletonBlock } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";
import storePlatforms from "@/stores/platforms";
import PlatformTile from "@/v2/components/Platforms/PlatformTile.vue";

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
    <header class="r-v2-pidx__head">
      <h1 class="r-v2-pidx__title">Platforms</h1>
      <span class="r-v2-pidx__count">{{ count }}</span>
    </header>

    <div v-if="fetchingPlatforms && !count" class="r-v2-pidx__grid">
      <RSkeletonBlock
        v-for="n in 16"
        :key="`sk-${n}`"
        width="100%"
        height="140px"
        rounded="card"
      />
    </div>

    <div v-else-if="!count" class="r-v2-pidx__empty">
      No platforms found. Run a scan to populate your library.
    </div>

    <div v-else class="r-v2-pidx__grid">
      <PlatformTile
        v-for="p in filledPlatforms"
        :key="p.id"
        :id="p.id"
        :slug="p.name"
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

.r-v2-pidx__head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 24px;
}

.r-v2-pidx__title {
  font-size: var(--r-font-size-3xl);
  font-weight: var(--r-font-weight-extrabold);
  letter-spacing: -0.025em;
  color: #fff;
  margin: 0;
}

.r-v2.r-v2-light .r-v2-pidx__title {
  color: var(--r-color-fg);
}

.r-v2-pidx__count {
  font-size: var(--r-font-size-md);
  color: rgba(255, 255, 255, 0.4);
}

.r-v2-pidx__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
}

.r-v2-pidx__empty {
  padding: 80px 0;
  color: rgba(255, 255, 255, 0.25);
  font-size: 13.5px;
  text-align: center;
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
