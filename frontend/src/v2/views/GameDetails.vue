<script setup lang="ts">
// GameDetails — artist-mockup layout.
//
// Two-column body: fixed cover column on the left, everything else (header,
// tabs, tab panel) stacked in a flex-1 column on the right. Thin
// orchestrator — data + tab state live here, every visual piece is a
// sub-component under components/GameDetails/.
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { IGDBRelatedGame, RomUserStatus } from "@/__generated__";
import storeHeartbeat from "@/stores/heartbeat";
import storeRoms from "@/stores/roms";
import { formatBytes, getDownloadPath, romStatusMap } from "@/utils";
import AchievementsTab from "@/v2/components/GameDetails/AchievementsTab.vue";
import CoverColumn from "@/v2/components/GameDetails/CoverColumn.vue";
import DetailsTabs from "@/v2/components/GameDetails/DetailsTabs.vue";
import type { FileRowEntry } from "@/v2/components/GameDetails/FilesTab.vue";
import FilesTab from "@/v2/components/GameDetails/FilesTab.vue";
import GameHeader from "@/v2/components/GameDetails/GameHeader.vue";
import type { InfoGridSection } from "@/v2/components/GameDetails/InfoGrid.vue";
import MediaTab from "@/v2/components/GameDetails/MediaTab.vue";
import NotesTab from "@/v2/components/GameDetails/NotesTab.vue";
import OverviewTab from "@/v2/components/GameDetails/OverviewTab.vue";
import PersonalTab from "@/v2/components/GameDetails/PersonalTab.vue";
import RelatedGamesGrid from "@/v2/components/GameDetails/RelatedGamesGrid.vue";
import BackBtn from "@/v2/components/shared/BackBtn.vue";
import { useBackgroundArt } from "@/v2/composables/useBackgroundArt";

const route = useRoute();
const router = useRouter();
const romsStore = storeRoms();
const heartbeatStore = storeHeartbeat();
const { currentRom } = storeToRefs(romsStore);

const setBgArt = useBackgroundArt();

const tab = ref<string>((route.query.tab as string) || "overview");
watch(tab, (value) => {
  if (route.query.tab !== value) {
    router.replace({
      path: route.path,
      query: { ...route.query, tab: value },
    });
  }
});
watch(
  () => route.query.tab,
  (value) => {
    if (typeof value === "string" && value !== tab.value) {
      tab.value = value;
    }
  },
);

const supportsWebp = computed<boolean>(() =>
  Boolean(
    (
      heartbeatStore.value as unknown as {
        FRONTEND?: { IMAGES_WEBP?: boolean };
      }
    )?.FRONTEND?.IMAGES_WEBP,
  ),
);

const title = computed(() => {
  const r = currentRom.value;
  if (!r) return "";
  return r.name || r.fs_name_no_ext;
});

const platformLabel = computed(() => {
  const r = currentRom.value;
  if (!r) return "";
  return r.platform_custom_name || r.platform_display_name;
});

const releaseYear = computed(() => {
  const ts = currentRom.value?.metadatum?.first_release_date;
  if (!ts) return null;
  return new Date(ts * 1000).getFullYear();
});

const fileSize = computed(() => {
  const bytes = currentRom.value?.fs_size_bytes;
  return bytes != null ? formatBytes(bytes) : null;
});

const playerCount = computed(
  () => currentRom.value?.metadatum?.player_count ?? null,
);

const ageRatings = computed(
  () => currentRom.value?.metadatum?.age_ratings ?? [],
);
const genres = computed(() => currentRom.value?.metadatum?.genres ?? []);
const franchises = computed(
  () => currentRom.value?.metadatum?.franchises ?? [],
);
const companies = computed(() => currentRom.value?.metadatum?.companies ?? []);
const collections = computed(
  () => currentRom.value?.metadatum?.collections ?? [],
);

const regions = computed(() => currentRom.value?.regions ?? []);
const languages = computed(() => currentRom.value?.languages ?? []);

const verified = computed(() => Boolean(currentRom.value?.crc_hash));

const coverPath = computed(() => {
  const r = currentRom.value;
  if (!r) return null;
  const path = r.path_cover_large ?? r.path_cover_small ?? null;
  if (!path) return null;
  return supportsWebp.value
    ? path.replace(/\.(png|jpg|jpeg)$/i, ".webp")
    : path;
});

const coverFallback = computed(() => currentRom.value?.url_cover ?? null);
const resolvedCover = computed(() => coverPath.value ?? coverFallback.value);

watch(
  resolvedCover,
  (url) => {
    if (url) setBgArt(url);
  },
  { immediate: true },
);

const downloadHref = computed(() =>
  currentRom.value ? getDownloadPath({ rom: currentRom.value }) : undefined,
);

const canPlayEJS = computed(() => {
  const emu = heartbeatStore.value?.EMULATION;
  return Boolean(emu && !emu.DISABLE_EMULATOR_JS);
});

const romUser = computed(() => currentRom.value?.rom_user ?? null);

type StatusKey = RomUserStatus | "now_playing" | "backlogged";
const statusKey = computed<StatusKey | null>(() => {
  const ru = romUser.value;
  if (!ru) return null;
  if (ru.now_playing) return "now_playing";
  if (ru.backlogged) return "backlogged";
  return ru.status ?? null;
});
const statusDisplay = computed(() => {
  const k = statusKey.value;
  if (!k) return null;
  return romStatusMap[k as keyof typeof romStatusMap] ?? null;
});
const lastPlayed = computed(() => {
  const ts = romUser.value?.last_played;
  if (!ts) return null;
  return new Date(ts).toLocaleString();
});

const overviewSections = computed<InfoGridSection[]>(() => [
  { label: "Genres", items: genres.value },
  { label: "Developer", items: companies.value },
  { label: "Franchise", items: franchises.value },
  { label: "Collections", items: collections.value },
]);

const raMetadata = computed(() => currentRom.value?.merged_ra_metadata ?? null);
const hasAchievements = computed(
  () => (raMetadata.value?.achievements?.length ?? 0) > 0,
);

const igdb = computed(() => currentRom.value?.igdb_metadata ?? null);
const similarGames = computed<IGDBRelatedGame[]>(
  () => igdb.value?.similar_games ?? [],
);
const remakes = computed<IGDBRelatedGame[]>(() => igdb.value?.remakes ?? []);
const remasters = computed<IGDBRelatedGame[]>(
  () => igdb.value?.remasters ?? [],
);
const expansions = computed<IGDBRelatedGame[]>(
  () => igdb.value?.expansions ?? [],
);
const dlcs = computed<IGDBRelatedGame[]>(() => igdb.value?.dlcs ?? []);
const hasAdditional = computed(
  () => expansions.value.length + dlcs.value.length > 0,
);
const hasRelated = computed(
  () =>
    similarGames.value.length + remakes.value.length + remasters.value.length >
    0,
);

const detailsRows = computed<FileRowEntry[]>(() => {
  const r = currentRom.value;
  if (!r) return [];
  return [
    { label: "File name", value: r.fs_name },
    { label: "Extension", value: r.fs_extension || "—" },
    { label: "Size", value: fileSize.value ?? "—" },
    { label: "Path", value: r.fs_path, mono: true },
    { label: "Revision", value: r.revision ?? "—" },
    { label: "CRC", value: r.crc_hash ?? "—", mono: true },
    { label: "MD5", value: r.md5_hash ?? "—", mono: true },
    { label: "SHA1", value: r.sha1_hash ?? "—", mono: true },
  ];
});

const tabs = computed(() => [
  { id: "overview", label: "Overview", show: true },
  { id: "personal", label: "Personal", show: true },
  { id: "notes", label: "Notes", show: true },
  { id: "achievements", label: "Achievements", show: hasAchievements.value },
  { id: "media", label: "Media", show: true },
  { id: "additional", label: "Additional", show: hasAdditional.value },
  { id: "related", label: "Related", show: hasRelated.value },
  { id: "files", label: "Files", show: true },
]);

function back() {
  if (window.history.length > 1) router.back();
  else router.push(`/platform/${currentRom.value?.platform_id ?? ""}`);
}
</script>

<template>
  <section v-if="currentRom" class="r-v2-det">
    <header class="r-v2-det__topbar">
      <BackBtn label="Back" @click="back" />
    </header>

    <div class="r-v2-det__body">
      <CoverColumn :src="resolvedCover" :alt="title" />

      <div class="r-v2-det__info">
        <GameHeader
          :rom="currentRom"
          :title="title"
          :platform-label="platformLabel"
          :release-year="releaseYear"
          :player-count="playerCount"
          :age-ratings="ageRatings"
          :verified="verified"
          :genres="genres"
          :franchises="franchises"
          :regions="regions"
          :languages="languages"
          :can-play="canPlayEJS"
          :download-href="downloadHref"
        />

        <DetailsTabs v-model="tab" :tabs="tabs" />

        <div class="r-v2-det__panel">
          <OverviewTab
            v-if="tab === 'overview'"
            :summary="currentRom.summary ?? null"
            :status-display="statusDisplay"
            :sections="overviewSections"
            :hltb="currentRom.hltb_metadata"
          />
          <PersonalTab
            v-if="tab === 'personal'"
            :rom-user="romUser"
            :status-display="statusDisplay"
            :last-played="lastPlayed"
          />
          <NotesTab v-if="tab === 'notes'" :rom="currentRom" />
          <AchievementsTab
            v-if="tab === 'achievements'"
            :metadata="raMetadata"
          />
          <MediaTab v-if="tab === 'media'" :rom="currentRom" />
          <section v-if="tab === 'additional'">
            <RelatedGamesGrid title="Expansions" :items="expansions" />
            <RelatedGamesGrid title="DLC" :items="dlcs" />
          </section>
          <section v-if="tab === 'related'">
            <RelatedGamesGrid title="Remakes" :items="remakes" />
            <RelatedGamesGrid title="Remasters" :items="remasters" />
            <RelatedGamesGrid title="Similar games" :items="similarGames" />
          </section>
          <FilesTab v-if="tab === 'files'" :rows="detailsRows" />
        </div>
      </div>
    </div>
  </section>

  <section v-else class="r-v2-det__empty">
    <p>Loading ROM…</p>
  </section>
</template>

<style scoped>
.r-v2-det {
  position: relative;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.r-v2-det__topbar {
  position: relative;
  z-index: 2;
  padding: 20px var(--r-row-pad) 0;
}

.r-v2-det__body {
  position: relative;
  z-index: 2;
  flex: 1;
  display: flex;
  align-items: stretch;
  padding: 0 var(--r-row-pad) 32px;
  gap: 52px;
  min-height: 0;
}

.r-v2-det__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding-bottom: 32px;
}

.r-v2-det__panel {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.15) transparent;
  padding-right: 6px;
}
.r-v2-det__panel::-webkit-scrollbar {
  width: 4px;
}
.r-v2-det__panel::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
}

.r-v2-det__empty {
  flex: 1;
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
}

@media (max-width: 768px) {
  .r-v2-det__body {
    padding: 12px 14px 0;
    gap: 14px;
    align-items: flex-start;
  }
}
</style>
