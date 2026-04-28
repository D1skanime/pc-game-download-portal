<script setup lang="ts">
// MetadataProviderChips — third row of the header. One compact pill per
// provider that has a linked ID on this ROM (IGDB, MobyGames, RA, HLTB…).
// Clicking opens the provider's page for that ID in a new tab. Unlinked
// providers are hidden so the row only shows what's actually there.
import { computed } from "vue";
import type { DetailedRom } from "@/stores/roms";

defineOptions({ inheritAttrs: false });

const props = defineProps<{ rom: DetailedRom }>();

type Provider = {
  key: keyof DetailedRom;
  name: string;
  color: string;
  logo: string | null;
  url: ((id: string | number) => string) | null;
};

const PROVIDERS: Provider[] = [
  {
    key: "igdb_id",
    name: "IGDB",
    color: "#6366f1",
    logo: "https://www.igdb.com/favicon.ico",
    url: (id) => `https://www.igdb.com/search?type=1&q=${id}`,
  },
  {
    key: "moby_id",
    name: "MobyGames",
    color: "#f59e0b",
    logo: "https://www.mobygames.com/favicon.ico",
    url: (id) => `https://www.mobygames.com/game/${id}/`,
  },
  {
    key: "ss_id",
    name: "ScreenScraper",
    color: "#3b82f6",
    logo: "https://www.screenscraper.fr/favicon.ico",
    url: (id) => `https://www.screenscraper.fr/gameinfos.php?gameid=${id}`,
  },
  {
    key: "ra_id",
    name: "RetroAchievements",
    color: "#ef4444",
    logo: "https://static.retroachievements.org/favicon.ico",
    url: (id) => `https://retroachievements.org/game/${id}`,
  },
  {
    key: "sgdb_id",
    name: "SteamGridDB",
    color: "#0ea5e9",
    logo: "https://www.steamgriddb.com/favicon.ico",
    url: (id) => `https://www.steamgriddb.com/game/${id}`,
  },
  {
    key: "launchbox_id",
    name: "LaunchBox",
    color: "#8b5cf6",
    logo: "https://gamesdb.launchbox-app.com/favicon.ico",
    url: (id) => `https://gamesdb.launchbox-app.com/games/dbid/${id}`,
  },
  {
    key: "hasheous_id",
    name: "Hasheous",
    color: "#6b7280",
    logo: null,
    url: null,
  },
  {
    key: "flashpoint_id",
    name: "Flashpoint Archive",
    color: "#f97316",
    logo: "https://flashpointarchive.org/favicon.ico",
    url: null,
  },
  {
    key: "hltb_id",
    name: "HowLongToBeat",
    color: "#22c55e",
    logo: "https://howlongtobeat.com/favicon.ico",
    url: (id) => `https://howlongtobeat.com/game/${id}`,
  },
];

type Linked = { provider: Provider; id: string | number };
const linked = computed<Linked[]>(() =>
  PROVIDERS.flatMap<Linked>((p) => {
    const v = props.rom[p.key];
    if (v === null || v === undefined || v === "") return [];
    return [{ provider: p, id: v as string | number }];
  }),
);
</script>

<template>
  <div v-if="linked.length" class="r-v2-det-providers">
    <component
      :is="entry.provider.url ? 'a' : 'div'"
      v-for="entry in linked"
      :key="entry.provider.key"
      class="r-v2-det-providers__chip"
      :href="entry.provider.url ? entry.provider.url(entry.id) : undefined"
      :target="entry.provider.url ? '_blank' : undefined"
      :rel="entry.provider.url ? 'noopener' : undefined"
    >
      <span
        class="r-v2-det-providers__dot"
        :style="{ background: entry.provider.color }"
      />
      <img
        v-if="entry.provider.logo"
        :src="entry.provider.logo"
        :alt="entry.provider.name"
        loading="lazy"
        @error="($event.target as HTMLImageElement).style.display = 'none'"
      />
      <span class="r-v2-det-providers__name">{{ entry.provider.name }}</span>
      <span class="r-v2-det-providers__id">{{ entry.id }}</span>
    </component>
  </div>
</template>

<style scoped>
.r-v2-det-providers {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.r-v2-det-providers__chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--r-radius-chip);
  padding: 3px 9px 3px 6px;
  font-size: 11px;
  font-weight: var(--r-font-weight-medium);
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  transition:
    background var(--r-motion-fast),
    border-color var(--r-motion-fast);
}
.r-v2-det-providers__chip:hover {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(255, 255, 255, 0.18);
}

.r-v2-det-providers__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.r-v2-det-providers__chip img {
  width: 14px;
  height: 14px;
  object-fit: contain;
  border-radius: 2px;
}

.r-v2-det-providers__name {
  font-weight: var(--r-font-weight-semibold);
}

.r-v2-det-providers__id {
  opacity: 0.55;
  font-variant-numeric: tabular-nums;
}
</style>
