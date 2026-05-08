<script setup lang="ts">
// MetadataSources — v2-native rewrite. Provider tiles match the mock's
// settings-provider-card pattern: header (logo + name + status text)
// stacked above an action row separated by a hairline border-top. The
// action row has two circular icon buttons:
//   • API-key — links to the provider's API-keys / docs page so users
//     know where to grab a key when one is missing. Color reflects
//     whether the key is currently set on the server.
//   • Website — opens the provider's main website in a new tab.
// Heartbeat pings are fetched in parallel on mount; status text + the
// API-key button color both update as each one resolves.
import { RIcon, RTooltip } from "@v2/lib";
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import storeConfig from "@/stores/config";
import storeHeartbeat from "@/stores/heartbeat";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";

defineOptions({ inheritAttrs: false });

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

interface Source {
  name: string;
  value: string;
  logo: string;
  website: string;
  docsUrl: string;
  disabled: boolean;
  heartbeat?: boolean;
}

const sources = computed<Source[]>(() => [
  {
    name: "IGDB",
    value: "igdb",
    logo: "/assets/scrappers/igdb.png",
    website: "https://www.igdb.com",
    docsUrl: "https://api-docs.igdb.com/#account-creation",
    disabled: !heartbeat.value.METADATA_SOURCES?.IGDB_API_ENABLED,
    heartbeat: heartbeatStatus.value.igdb,
  },
  {
    name: "MobyGames",
    value: "moby",
    logo: "/assets/scrappers/moby.png",
    website: "https://www.mobygames.com",
    docsUrl: "https://www.mobygames.com/info/api/",
    disabled: !heartbeat.value.METADATA_SOURCES?.MOBY_API_ENABLED,
    heartbeat: heartbeatStatus.value.moby,
  },
  {
    name: "ScreenScraper",
    value: "ss",
    logo: "/assets/scrappers/ss.png",
    website: "https://www.screenscraper.fr",
    docsUrl: "https://www.screenscraper.fr/membreinscription.php",
    disabled: !heartbeat.value.METADATA_SOURCES?.SS_API_ENABLED,
    heartbeat: heartbeatStatus.value.ss,
  },
  {
    name: "RetroAchievements",
    value: "ra",
    logo: "/assets/scrappers/ra.png",
    website: "https://retroachievements.org",
    docsUrl: "https://retroachievements.org/APIDemo.php",
    disabled: !heartbeat.value.METADATA_SOURCES?.RA_API_ENABLED,
    heartbeat: heartbeatStatus.value.ra,
  },
  {
    name: "Hasheous",
    value: "hasheous",
    logo: "/assets/scrappers/hasheous.png",
    website: "https://hasheous.org",
    docsUrl: "https://hasheous.org/index.html?page=apidocs",
    disabled: !heartbeat.value.METADATA_SOURCES?.HASHEOUS_API_ENABLED,
    heartbeat: heartbeatStatus.value.hasheous,
  },
  {
    name: "LaunchBox",
    value: "launchbox",
    logo: "/assets/scrappers/launchbox.png",
    website: "https://www.launchbox-app.com",
    docsUrl: "https://gamesdb.launchbox-app.com",
    disabled: !heartbeat.value.METADATA_SOURCES?.LAUNCHBOX_API_ENABLED,
    heartbeat: heartbeatStatus.value.launchbox,
  },
  {
    name: "Flashpoint Archive",
    value: "flashpoint",
    logo: "/assets/scrappers/flashpoint.png",
    website: "https://flashpointarchive.org",
    docsUrl: "https://flashpointarchive.org/datahub/Flashpoint_API",
    disabled: !heartbeat.value.METADATA_SOURCES?.FLASHPOINT_API_ENABLED,
    heartbeat: heartbeatStatus.value.flashpoint,
  },
  {
    name: "HowLongToBeat",
    value: "hltb",
    logo: "/assets/scrappers/hltb.png",
    website: "https://howlongtobeat.com",
    docsUrl: "https://howlongtobeat.com",
    disabled: !heartbeat.value.METADATA_SOURCES?.HLTB_API_ENABLED,
    heartbeat: heartbeatStatus.value.hltb,
  },
  {
    name: "SteamGridDB",
    value: "sgdb",
    logo: "/assets/scrappers/sgdb.png",
    website: "https://www.steamgriddb.com",
    docsUrl: "https://www.steamgriddb.com/profile/preferences/api",
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
  await Promise.all(
    sources.value
      .filter((source) => !source.disabled)
      .map(async (source) => {
        const result = await heartbeat.fetchMetadataHeartbeat(source.value);
        heartbeatStatus.value[source.value] = result;
      }),
  );
}

onMounted(() => {
  configStore.fetchConfig();
  void fetchAllHeartbeats();
});
</script>

<template>
  <SettingsShell bare>
    <h1 class="r-v2-settings__page-title">
      {{ t("scan.metadata-sources") }}
    </h1>

    <div class="r-v2-meta__grid">
      <article
        v-for="source in sources"
        :key="source.value"
        class="r-v2-meta__card"
        :class="`r-v2-meta__card--${statusOf(source)}`"
      >
        <header class="r-v2-meta__header">
          <div class="r-v2-meta__logo">
            <img :src="source.logo" :alt="source.name" />
          </div>
          <div class="r-v2-meta__head-text">
            <span class="r-v2-meta__name">{{ source.name }}</span>
            <span
              class="r-v2-meta__status"
              :class="`r-v2-meta__status--${statusOf(source)}`"
            >
              {{ statusLabel(source) }}
            </span>
          </div>
        </header>

        <div class="r-v2-meta__actions">
          <RTooltip>
            <template #activator="{ props: tipProps }">
              <a
                v-bind="tipProps"
                :href="source.docsUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="r-v2-meta__action-btn"
                :class="`r-v2-meta__action-btn--${statusOf(source) === 'ok' ? 'ok' : statusOf(source) === 'failed' ? 'fail' : 'muted'}`"
                :aria-label="t('scan.api-key-set')"
              >
                <RIcon icon="mdi-key-variant" size="16" />
              </a>
            </template>
            <span>{{ t("scan.api-key-set") }} ({{ source.name }})</span>
          </RTooltip>
          <RTooltip>
            <template #activator="{ props: tipProps }">
              <a
                v-bind="tipProps"
                :href="source.website"
                target="_blank"
                rel="noopener noreferrer"
                class="r-v2-meta__action-btn r-v2-meta__action-btn--info"
                :aria-label="`Visit ${source.name}`"
              >
                <RIcon icon="mdi-web" size="16" />
              </a>
            </template>
            <span>Visit {{ source.name }}</span>
          </RTooltip>
        </div>
      </article>
    </div>
  </SettingsShell>
</template>

<style scoped>
.r-v2-settings__page-title {
  margin: 0 0 20px;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--r-color-fg);
}

/* Mock-faithful 3-col provider grid; collapses gracefully on narrow
   viewports. */
.r-v2-meta__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 1100px) {
  .r-v2-meta__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .r-v2-meta__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* Card chrome — subtle bg + 12px radius + overflow hidden so the inner
   border-top reaches the rounded corners cleanly. */
.r-v2-meta__card {
  border-radius: 12px;
  border: 1px solid var(--r-color-border);
  background: var(--r-color-bg-elevated);
  overflow: hidden;
  transition: border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-meta__card--disabled {
  opacity: 0.6;
}

.r-v2-meta__header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 16px 12px;
}

.r-v2-meta__logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  background: var(--r-color-surface);
  padding: 4px;
}
.r-v2-meta__logo img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.r-v2-meta__head-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.r-v2-meta__name {
  font-size: 14px;
  font-weight: var(--r-font-weight-bold);
  color: var(--r-color-fg);
}

.r-v2-meta__status {
  font-size: 11px;
  color: var(--r-color-fg-muted);
}
.r-v2-meta__status--ok {
  color: var(--r-color-success);
}
.r-v2-meta__status--failed,
.r-v2-meta__status--disabled {
  color: var(--r-color-danger);
}
.r-v2-meta__status--pending {
  color: var(--r-color-warning);
}

.r-v2-meta__actions {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--r-color-border);
}

/* Round 36×36 action buttons (rendered as <a>; behave as colored
   targets that hint at status). */
.r-v2-meta__action-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  text-decoration: none;
  color: var(--r-color-overlay-emphasis-fg);
  transition:
    filter var(--r-motion-fast) var(--r-motion-ease-out),
    background var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-meta__action-btn:hover {
  filter: brightness(1.18);
}
.r-v2-meta__action-btn--ok {
  background: var(--r-color-success);
}
.r-v2-meta__action-btn--fail {
  background: var(--r-color-danger);
}
.r-v2-meta__action-btn--muted {
  background: var(--r-color-fg-faint);
}
.r-v2-meta__action-btn--info {
  background: var(--r-color-info);
}
</style>
