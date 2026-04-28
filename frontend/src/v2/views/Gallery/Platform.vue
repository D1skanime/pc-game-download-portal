<script setup lang="ts">
// Platform gallery — data/orchestration. Renders one of three gallery
// bodies based on `useGalleryMode`:
//   * grid + flat    → GameGrid
//   * grid + grouped → LetterGroupedGrid (+ AlphaStrip sidebar)
//   * list           → GameList (sortable columns; grouping ignored)
//
// GalleryToolbar exposes the toggles and can dock inline (header) or
// floating (top-right) based on the user's position preference.
import { RChip, RPlatformIcon } from "@v2/lib";
import { storeToRefs } from "pinia";
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { onBeforeRouteUpdate, useRoute } from "vue-router";
import storeGalleryFilter from "@/stores/galleryFilter";
import storeHeartbeat from "@/stores/heartbeat";
import storePlatforms, { type Platform } from "@/stores/platforms";
import storeRoms from "@/stores/roms";
import { formatBytes } from "@/utils";
import AlphaStrip from "@/v2/components/Gallery/AlphaStrip.vue";
import GalleryToolbar from "@/v2/components/Gallery/GalleryToolbar.vue";
import GameGrid from "@/v2/components/Gallery/GameGrid.vue";
import GameList from "@/v2/components/Gallery/GameList.vue";
import InfoPanel from "@/v2/components/Gallery/InfoPanel.vue";
import LetterGroupedGrid from "@/v2/components/Gallery/LetterGroupedGrid.vue";
import LoadMore from "@/v2/components/Gallery/LoadMore.vue";
import Stat from "@/v2/components/shared/Stat.vue";
import { useGalleryMode } from "@/v2/composables/useGalleryMode";
import { useLetterGroups } from "@/v2/composables/useLetterGroups";

const route = useRoute();
const platformsStore = storePlatforms();
const romsStore = storeRoms();
const heartbeatStore = storeHeartbeat();
const galleryFilterStore = storeGalleryFilter();
const { searchTerm } = storeToRefs(galleryFilterStore);

const {
  _allRoms: allRoms,
  currentPlatform,
  fetchingRoms,
  fetchTotalRoms,
  characterIndex,
  romIdIndex,
} = storeToRefs(romsStore);

const notFound = ref(false);
const { groupBy, layout, toolbarPosition } = useGalleryMode();

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
  visibleLetters,
  setLetterRef,
  scrollToLetter,
  onGridScroll,
} = useLetterGroups(allRoms, { characterIndex, romIdIndex });

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
  // Mirror v1's Platform.vue: a full reset() before switching context
  // clears every `current*` field (so a prior Collection's id doesn't
  // bleed into the next platform request), wipes _allRoms, resets
  // pagination, AND drops the `fetchingRoms` flag — otherwise the
  // re-entrancy guard in fetchRoms silently swallows the new call when
  // the user navigates between galleries mid-fetch and the new gallery
  // renders empty.
  if (currentPlatform.value?.id !== platform.id) {
    romsStore.reset();
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

// ── Search filter (debounced) ───────────────────────────────────────
const searchInput = ref(searchTerm.value ?? "");
let searchDebounce: ReturnType<typeof setTimeout> | null = null;
function setSearch(value: string) {
  searchInput.value = value;
  if (searchDebounce) clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    const normalized = value.trim();
    if (normalized === (searchTerm.value ?? "")) return;
    searchTerm.value = normalized || null;
    romsStore.resetPagination();
    romsStore._allRoms = [];
    // fetchRoms() supersedes any in-flight request via seq; no need to
    // wait for it to finish first.
    romsStore.fetchRoms();
  }, 300);
}
onBeforeUnmount(() => {
  if (searchDebounce) clearTimeout(searchDebounce);
  // Don't leak the term to the next gallery — clear on leave.
  searchTerm.value = null;
});

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
</script>

<template>
  <section class="r-v2-plat">
    <div
      :ref="(el) => (scrollEl = el as HTMLElement | null)"
      class="r-v2-plat__scroll r-v2-scroll-hidden"
      @scroll="onGridScroll"
    >
      <InfoPanel v-if="currentPlatform" :title="currentPlatform.display_name">
        <template #cover>
          <div
            class="r-v2-plat__panel-icon"
            :style="{
              viewTransitionName: `platform-icon-${currentPlatform.id}`,
            }"
          >
            <RPlatformIcon
              :slug="currentPlatform.slug"
              :fs-slug="currentPlatform.fs_slug"
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

      <!-- Inline toolbar (rendered here when the user chose the "header" dock). -->
      <GalleryToolbar
        v-if="toolbarPosition === 'header'"
        :group-by="groupBy"
        :layout="layout"
        :position="toolbarPosition"
        show-search
        :search="searchInput"
        search-placeholder="Filter this platform…"
        @update:group-by="groupBy = $event"
        @update:layout="layout = $event"
        @update:search="setSearch"
      />

      <div v-if="notFound" class="r-v2-plat__empty">Platform not found.</div>

      <!-- Grid + grouped by letter -->
      <LetterGroupedGrid
        v-else-if="layout === 'grid' && groupBy === 'letter'"
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

      <!-- Grid + flat -->
      <template v-else-if="layout === 'grid'">
        <GameGrid
          :roms="allRoms"
          :loading="fetchingRoms"
          :webp="supportsWebp"
          :show-platform="false"
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
    </div>

    <AlphaStrip
      v-if="letterGroups.length > 0"
      :available="availableLetters"
      :current="currentLetter"
      :visible="visibleLetters"
      @pick="scrollToLetter"
    />

    <!-- Floating toolbar — docked top-right of the gallery body. -->
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
.r-v2-plat {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: calc(100vh - var(--r-nav-h));
  position: relative;
}

.r-v2-plat__scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 32px var(--r-row-pad) 60px;
}

.r-v2-plat__panel-icon {
  width: 200px;
  height: 148px;
  display: grid;
  place-items: center;
}

.r-v2-plat__empty {
  padding: 80px 0;
  color: var(--r-color-fg-faint);
  font-size: 13.5px;
  text-align: center;
}

@media (max-width: 768px) {
  .r-v2-plat__scroll {
    padding: 16px 14px 80px;
  }
  .r-v2-plat__panel-icon {
    width: 80px;
    height: 60px;
  }
}
</style>
