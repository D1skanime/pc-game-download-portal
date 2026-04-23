<script setup lang="ts">
// Platform gallery — data/orchestration only. All visuals delegated:
//   * InfoPanel + RPlatformIcon — hero card with stats
//   * LetterGroupedGrid         — the A-Z grid (shared with Collection.vue)
//   * AlphaStrip                — letter jump sidebar
//   * useLetterGroups           — grouping + scroll-spy logic
import { RChip, RPlatformIcon } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { onBeforeRouteUpdate, useRoute } from "vue-router";
import storeHeartbeat from "@/stores/heartbeat";
import storePlatforms, { type Platform } from "@/stores/platforms";
import storeRoms from "@/stores/roms";
import { formatBytes } from "@/utils";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import InfoPanel from "@/v2/components/Gallery/InfoPanel.vue";
import LetterGroupedGrid from "@/v2/components/Gallery/LetterGroupedGrid.vue";
import BackBtn from "@/v2/components/shared/BackBtn.vue";
import Stat from "@/v2/components/shared/Stat.vue";
import { useLetterGroups } from "@/v2/composables/useLetterGroups";

const route = useRoute();
const platformsStore = storePlatforms();
const romsStore = storeRoms();
const heartbeatStore = storeHeartbeat();

const {
  _allRoms: allRoms,
  currentPlatform,
  fetchingRoms,
  fetchTotalRoms,
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

const tags = computed<string[]>(() => {
  const p = currentPlatform.value as
    | (Platform & {
        category?: string | null;
        family_name?: string | null;
        generation?: number | null;
      })
    | null;
  if (!p) return [];
  const out: string[] = [];
  if (p.category) out.push(p.category);
  if (p.family_name) out.push(p.family_name);
  if (p.generation) out.push(`Generation ${p.generation}`);
  return out;
});

type StatRow = { label: string; value: string };
const platformStats = computed<StatRow[]>(() => {
  const p = currentPlatform.value as
    | (Platform & {
        fs_size_bytes?: number | null;
        firmware_count?: number | null;
      })
    | null;
  if (!p) return [];
  const rows: StatRow[] = [
    { label: "In Library", value: String(p.rom_count ?? allRoms.value.length) },
  ];
  if (p.fs_size_bytes) {
    rows.push({ label: "On Disk", value: formatBytes(p.fs_size_bytes) });
  }
  if (p.firmware_count) {
    rows.push({ label: "Firmware", value: String(p.firmware_count) });
  }
  return rows;
});

const {
  scrollEl,
  letterGroups,
  availableLetters,
  currentLetter,
  setLetterRef,
  scrollToLetter,
  onGridScroll,
} = useLetterGroups(allRoms);

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
  await nextTick();
  onGridScroll();
}

onMounted(() => {
  loadForId(Number(route.params.platform));
});

onBeforeRouteUpdate((to) => {
  if (to.name === "platform") loadForId(Number(to.params.platform));
});

watch(
  () => route.params.platform,
  (next) => {
    if (next != null) loadForId(Number(next));
  },
);

watch(allRoms, () => onGridScroll(), { deep: false });

const hasMore = computed(() => allRoms.value.length < fetchTotalRoms.value);
const remaining = computed(() => fetchTotalRoms.value - allRoms.value.length);
function loadMore() {
  if (fetchingRoms.value || !hasMore.value) return;
  romsStore.fetchRoms();
}
</script>

<template>
  <section class="r-v2-plat">
    <header class="r-v2-plat__header">
      <BackBtn to="/platforms" label="Platforms" />
    </header>

    <div
      :ref="(el) => (scrollEl = el as HTMLElement | null)"
      class="r-v2-plat__scroll r-v2-scroll-hidden"
      @scroll="onGridScroll"
    >
      <InfoPanel v-if="currentPlatform" :title="currentPlatform.display_name">
        <template #cover>
          <div class="r-v2-plat__panel-icon">
            <RPlatformIcon
              :name="currentPlatform.name"
              :alt="currentPlatform.display_name"
              :size="148"
            />
          </div>
        </template>
        <template v-if="tags.length" #tags>
          <RChip
            v-for="t in tags"
            :key="t"
            size="small"
            variant="tonal"
            :rounded="20"
          >
            {{ t }}
          </RChip>
        </template>
        <template v-if="platformStats.length" #stats>
          <Stat
            v-for="s in platformStats"
            :key="s.label"
            :value="s.value"
            :label="s.label"
          />
        </template>
      </InfoPanel>

      <div v-if="notFound" class="r-v2-plat__empty">Platform not found.</div>

      <LetterGroupedGrid
        v-else
        :groups="letterGroups"
        :fetching="fetchingRoms"
        :has-more="hasMore"
        :remaining="remaining"
        :webp="supportsWebp"
        :show-platform-badge="false"
        empty-label="No games in this platform yet."
        :skeleton-count="18"
        :set-letter-ref="setLetterRef"
        @load-more="loadMore"
      />
    </div>

    <AlphaStrip
      v-if="letterGroups.length"
      :available="availableLetters"
      :current="currentLetter"
      @pick="scrollToLetter"
    />
  </section>
</template>

<style scoped>
.r-v2-plat {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: calc(100vh - var(--r-nav-h));
  position: relative;
}

.r-v2-plat__header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2;
  padding: 20px var(--r-row-pad) 0;
  display: flex;
  align-items: center;
  gap: 14px;
  pointer-events: none;
}

.r-v2-plat__header > * {
  pointer-events: auto;
}

.r-v2-plat__scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 56px var(--r-row-pad) 60px;
}

.r-v2-plat__panel-icon {
  width: 200px;
  height: 148px;
  display: grid;
  place-items: center;
}

.r-v2-plat__empty {
  padding: 80px 0;
  color: rgba(255, 255, 255, 0.25);
  font-size: 13.5px;
  text-align: center;
}

@media (max-width: 768px) {
  .r-v2-plat__scroll {
    padding: 48px 14px 80px;
  }
  .r-v2-plat__panel-icon {
    width: 80px;
    height: 60px;
  }
}
</style>
