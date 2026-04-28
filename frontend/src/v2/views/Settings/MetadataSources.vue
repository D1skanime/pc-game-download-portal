<script setup lang="ts">
// MetadataSources — v2-native rewrite. Tiles show API key + connection
// status for every metadata provider. Heartbeat pings are fetched in
// parallel on mount; cards reactively update as each one resolves.
import { RIcon } from "@v2/lib";
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import storeConfig from "@/stores/config";
import storeHeartbeat from "@/stores/heartbeat";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";

const { t } = useI18n();
const heartbeat = storeHeartbeat();
const configStore = storeConfig();

const heartbeatStatus = ref<Record<string, boolean | undefined>>({
  igdb: undefined,
  moby: undefined,
  ss: undefined,
  ra: undefined,
  hasheous: undefined,
  launchbox: undefined,
  flashpoint: undefined,
  hltb: undefined,
  sgdb: undefined,
});

type SourceStatus = "disabled" | "ok" | "failed" | "pending";

type Source = {
  name: string;
  value: string;
  logo: string;
  disabled: boolean;
  heartbeat?: boolean;
};

const sources = computed<Source[]>(() => [
  {
    name: "IGDB",
    value: "igdb",
    logo: "/assets/scrappers/igdb.png",
    disabled: !heartbeat.value.METADATA_SOURCES?.IGDB_API_ENABLED,
    heartbeat: heartbeatStatus.value.igdb,
  },
  {
    name: "MobyGames",
    value: "moby",
    logo: "/assets/scrappers/moby.png",
    disabled: !heartbeat.value.METADATA_SOURCES?.MOBY_API_ENABLED,
    heartbeat: heartbeatStatus.value.moby,
  },
  {
    name: "ScreenScraper",
    value: "ss",
    logo: "/assets/scrappers/ss.png",
    disabled: !heartbeat.value.METADATA_SOURCES?.SS_API_ENABLED,
    heartbeat: heartbeatStatus.value.ss,
  },
  {
    name: "RetroAchievements",
    value: "ra",
    logo: "/assets/scrappers/ra.png",
    disabled: !heartbeat.value.METADATA_SOURCES?.RA_API_ENABLED,
    heartbeat: heartbeatStatus.value.ra,
  },
  {
    name: "Hasheous",
    value: "hasheous",
    logo: "/assets/scrappers/hasheous.png",
    disabled: !heartbeat.value.METADATA_SOURCES?.HASHEOUS_API_ENABLED,
    heartbeat: heartbeatStatus.value.hasheous,
  },
  {
    name: "LaunchBox",
    value: "launchbox",
    logo: "/assets/scrappers/launchbox.png",
    disabled: !heartbeat.value.METADATA_SOURCES?.LAUNCHBOX_API_ENABLED,
    heartbeat: heartbeatStatus.value.launchbox,
  },
  {
    name: "Flashpoint Archive",
    value: "flashpoint",
    logo: "/assets/scrappers/flashpoint.png",
    disabled: !heartbeat.value.METADATA_SOURCES?.FLASHPOINT_API_ENABLED,
    heartbeat: heartbeatStatus.value.flashpoint,
  },
  {
    name: "HowLongToBeat",
    value: "hltb",
    logo: "/assets/scrappers/hltb.png",
    disabled: !heartbeat.value.METADATA_SOURCES?.HLTB_API_ENABLED,
    heartbeat: heartbeatStatus.value.hltb,
  },
  {
    name: "SteamGridDB",
    value: "sgdb",
    logo: "/assets/scrappers/sgdb.png",
    disabled: !heartbeat.value.METADATA_SOURCES?.STEAMGRIDDB_API_ENABLED,
    heartbeat: heartbeatStatus.value.sgdb,
  },
]);

function statusOf(source: Source): SourceStatus {
  if (source.disabled) return "disabled";
  if (source.heartbeat === true) return "ok";
  if (source.heartbeat === false) return "failed";
  return "pending";
}

function statusLabel(source: Source) {
  const s = statusOf(source);
  if (s === "disabled") return t("scan.api-key-missing-short");
  if (s === "ok") return t("scan.api-key-valid");
  if (s === "failed") return t("scan.api-key-invalid");
  return t("scan.connection-in-progress");
}

async function fetchAllHeartbeats() {
  sources.value
    .filter((source) => !source.disabled)
    .map(async (source) => {
      const result = await heartbeat.fetchMetadataHeartbeat(source.value);
      heartbeatStatus.value[source.value] = result;
    });
}

onMounted(() => {
  configStore.fetchConfig();
  fetchAllHeartbeats();
});
</script>

<template>
  <SettingsShell
    :title="t('scan.metadata-sources')"
    subtitle="Configured providers and live connection status."
    icon="mdi-database-cog"
    bare
  >
    <div class="r-v2-meta">
      <div
        v-for="source in sources"
        :key="source.value"
        class="r-v2-meta__tile"
        :class="[`r-v2-meta__tile--${statusOf(source)}`]"
      >
        <div class="r-v2-meta__head">
          <div class="r-v2-meta__logo">
            <img :src="source.logo" :alt="source.name" />
          </div>
          <div class="r-v2-meta__text">
            <p class="r-v2-meta__name">
              {{ source.name }}
            </p>
            <p class="r-v2-meta__status">
              {{ statusLabel(source) }}
            </p>
          </div>
        </div>

        <div class="r-v2-meta__indicators">
          <div
            class="r-v2-meta__indicator"
            :class="[
              source.disabled
                ? 'r-v2-meta__indicator--off'
                : 'r-v2-meta__indicator--on',
            ]"
            :title="
              source.disabled
                ? t('scan.api-key-missing-or-disabled')
                : t('scan.api-key-set')
            "
          >
            <RIcon
              :icon="source.disabled ? 'mdi-key-alert' : 'mdi-key'"
              size="16"
            />
            <span>API key</span>
          </div>
          <div
            class="r-v2-meta__indicator"
            :class="{
              'r-v2-meta__indicator--on': source.heartbeat === true,
              'r-v2-meta__indicator--off': source.heartbeat === false,
              'r-v2-meta__indicator--muted': source.disabled,
              'r-v2-meta__indicator--pending':
                !source.disabled && source.heartbeat === undefined,
            }"
            :title="
              source.disabled
                ? t('scan.api-key-missing-or-disabled')
                : source.heartbeat === true
                  ? t('scan.connection-successful')
                  : source.heartbeat === false
                    ? t('scan.connection-failed')
                    : t('scan.connection-in-progress')
            "
          >
            <RIcon
              :icon="
                source.heartbeat === true
                  ? 'mdi-web-check'
                  : source.heartbeat === false
                    ? 'mdi-web-remove'
                    : source.disabled
                      ? 'mdi-web-off'
                      : 'mdi-web-refresh'
              "
              size="16"
            />
            <span>Connection</span>
          </div>
        </div>
      </div>
    </div>
  </SettingsShell>
</template>

<style scoped>
.r-v2-meta {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.r-v2-meta__tile {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  transition: border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-meta__tile--ok {
  border-color: rgba(34, 197, 94, 0.3);
}
.r-v2-meta__tile--failed {
  border-color: rgba(239, 68, 68, 0.35);
}
.r-v2-meta__tile--disabled {
  opacity: 0.6;
}

.r-v2-meta__head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.r-v2-meta__logo {
  width: 40px;
  height: 40px;
  border-radius: var(--r-radius-sm);
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  display: grid;
  place-items: center;
  padding: 4px;
  flex-shrink: 0;
}
.r-v2-meta__logo img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.r-v2-meta__text {
  min-width: 0;
}

.r-v2-meta__name {
  margin: 0;
  font-size: 14px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg);
}
.r-v2-meta__status {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--r-color-fg-secondary);
}

.r-v2-meta__indicators {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.r-v2-meta__indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: var(--r-radius-pill);
  font-size: 11px;
  font-weight: var(--r-font-weight-medium);
  background: var(--r-color-bg-elevated);
  color: var(--r-color-fg-secondary);
  border: 1px solid var(--r-color-border);
}
.r-v2-meta__indicator--on {
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(34, 197, 94, 0.3);
  color: #4ade80;
}
.r-v2-meta__indicator--off {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.3);
  color: #f87171;
}
.r-v2-meta__indicator--pending {
  background: rgba(234, 179, 8, 0.12);
  border-color: rgba(234, 179, 8, 0.3);
  color: #facc15;
}
.r-v2-meta__indicator--muted {
  background: var(--r-color-bg-elevated);
  color: var(--r-color-fg-muted);
}
</style>
