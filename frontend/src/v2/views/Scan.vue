<script setup lang="ts">
// Scan — library scan control + live log. The socket listeners that push
// platforms/ROMs/firmware into `storeScanning` live in the shared
// `ScanBtn` navigation component (mounted app-wide), so this view is pure
// UI: read store state, render the log, emit scan/stop actions.
//
// The ScanPlatform expansion body is the v1 primitive — it's feature-scoped
// and fine to reuse inside a v2 panel until we rebuild it natively.
import { RAlert, RBtn, RIcon, RPlatformIcon, RSelect } from "@v2/lib";
import { useLocalStorage } from "@vueuse/core";
import { storeToRefs } from "pinia";
import {
  computed,
  nextTick,
  onBeforeUnmount,
  ref,
  useTemplateRef,
  watch,
} from "vue";
import { useI18n } from "vue-i18n";
import { useDisplay } from "vuetify";
import ScanPlatform from "@/components/Scan/ScanPlatform.vue";
import { ROUTES } from "@/plugins/router";
import socket from "@/services/socket";
import storeConfig from "@/stores/config";
import storeHeartbeat, { type MetadataOption } from "@/stores/heartbeat";
import storePlatforms from "@/stores/platforms";
import storeScanning from "@/stores/scanning";
import { platformCategoryToIcon } from "@/utils";
import MissingFSBadge from "@/v2/components/shared/MissingFSBadge.vue";
import { useBackgroundArt } from "@/v2/composables/useBackgroundArt";

const LOCAL_STORAGE_METADATA_SOURCES_KEY = "scan.metadataSources";
const LOCAL_STORAGE_LAUNCHBOX_REMOTE_ENABLED_KEY =
  "scan.launchboxRemoteEnabled";
const { t } = useI18n();
const { xs } = useDisplay();
const scanningStore = storeScanning();
const { scanning, scanningPlatforms, scanStats } = storeToRefs(scanningStore);
const platformsStore = storePlatforms();
const { filteredPlatforms } = storeToRefs(platformsStore);
const configStore = storeConfig();
const { config } = storeToRefs(configStore);
const heartbeat = storeHeartbeat();
const platformsToScan = ref<number[]>([]);
const panels = ref<number[]>([]);
const scanLog = useTemplateRef<HTMLDivElement>("scan-log");

const setBgArt = useBackgroundArt();
setBgArt(null);

const sortedPlatforms = computed(() =>
  [...filteredPlatforms.value].sort((a, b) =>
    a.display_name.localeCompare(b.display_name),
  ),
);

const calculateHashes = computed(
  () => !config.value.SKIP_HASH_CALCULATION || false,
);

const metadataOptions = computed(() =>
  heartbeat.getMetadataOptionsByPriority().map((option) => {
    const requiresHashes = option.value === "hasheous" || option.value === "ra";
    const hashingDisabled = !calculateHashes.value;
    let disabled = option.disabled;
    if (hashingDisabled && requiresHashes) {
      if (option.value === "hasheous") {
        disabled = t("scan.hasheous-requires-hashes");
      } else if (option.value === "ra") {
        disabled = t("scan.retroachievements-requires-hashes");
      }
    }
    return { ...option, disabled };
  }),
);

const storedMetadataSources = useLocalStorage(
  LOCAL_STORAGE_METADATA_SOURCES_KEY,
  [] as string[],
);
const launchboxRemoteEnabled = useLocalStorage(
  LOCAL_STORAGE_LAUNCHBOX_REMOTE_ENABLED_KEY,
  true,
);
const metadataSources = ref<MetadataOption[]>(
  metadataOptions.value.filter(
    (m) => storedMetadataSources.value.includes(m.value) && !m.disabled,
  ) || heartbeat.getEnabledMetadataOptions(),
);

const isLaunchboxSelected = computed(() =>
  metadataSources.value.some((s) => s.value === "launchbox"),
);

watch(metadataOptions, (newOptions) => {
  metadataSources.value = metadataSources.value.filter((s) =>
    newOptions.some((opt) => opt.value === s.value && !opt.disabled),
  );
});

// Auto-expand panels when a platform first reports roms or firmware.
const platformsWithRomsKey = computed(() =>
  scanningPlatforms.value
    .map((p) => (p.roms.length > 0 || p.firmware_count > 0 ? 1 : 0))
    .join(""),
);
watch(platformsWithRomsKey, () => {
  panels.value = scanningPlatforms.value
    .map((p, index) => (p.roms.length > 0 || p.firmware_count > 0 ? index : -1))
    .filter((index) => index !== -1);
});

// Auto-scroll to bottom as new platforms arrive, unless the user scrolled up.
let userScrolledUp = false;
watch(
  () => scanningPlatforms.value.length,
  async () => {
    if (userScrolledUp) return;
    await nextTick();
    scanLog.value?.scrollTo({ top: scanLog.value.scrollHeight });
  },
);

function onScroll(e: Event) {
  const el = e.target as HTMLDivElement;
  userScrolledUp = el.scrollTop + el.clientHeight + 1 < el.scrollHeight;
}

type ScanType =
  | "new_platforms"
  | "quick"
  | "unmatched"
  | "update"
  | "hashes"
  | "complete";

const scanOptions: { title: string; subtitle: string; value: ScanType }[] = [
  {
    title: t("scan.new-platforms"),
    subtitle: t("scan.new-platforms-desc"),
    value: "new_platforms",
  },
  {
    title: t("scan.quick-scan"),
    subtitle: t("scan.quick-scan-desc"),
    value: "quick",
  },
  {
    title: t("scan.unmatched-games"),
    subtitle: t("scan.unmatched-games-desc"),
    value: "unmatched",
  },
  {
    title: t("scan.update-metadata"),
    subtitle: t("scan.update-metadata-desc"),
    value: "update",
  },
  {
    title: t("scan.hashes"),
    subtitle: t("scan.hashes-desc"),
    value: "hashes",
  },
  {
    title: t("scan.complete-rescan"),
    subtitle: t("scan.complete-rescan-desc"),
    value: "complete",
  },
];
const scanType = ref<ScanType>("quick");

function scan() {
  scanningStore.setScanning(true);
  scanningPlatforms.value = [];

  if (!socket.connected) socket.connect();

  storedMetadataSources.value = metadataSources.value.map((s) => s.value);

  socket.emit("scan", {
    platforms: platformsToScan.value,
    type: scanType.value,
    apis: metadataSources.value.map((s) => s.value),
    launchbox_remote_enabled: launchboxRemoteEnabled.value,
  });
}

type ScanStatsPayload = typeof scanStats.value;
function onScanDone(stats: ScanStatsPayload) {
  scanStats.value = stats;
}
socket.on("scan:done", onScanDone);
onBeforeUnmount(() => {
  socket.off("scan:done", onScanDone);
});

function stopScan() {
  socket.emit("scan:stop");
}
</script>

<template>
  <section class="r-v2-scan">
    <header class="r-v2-scan__head">
      <div>
        <span class="r-v2-scan__eyebrow">
          <RIcon icon="mdi-magnify-scan" size="13" />
          Library
        </span>
        <h1 class="r-v2-scan__title">
          {{ t("scan.scan") }}
        </h1>
      </div>
      <RBtn
        variant="text"
        size="small"
        prepend-icon="mdi-table-cog"
        :to="{ name: ROUTES.LIBRARY_MANAGEMENT }"
      >
        {{ t("scan.manage-library") }}
      </RBtn>
    </header>

    <!-- Config panel -->
    <div class="r-v2-scan__config">
      <div class="r-v2-scan__fields">
        <RSelect
          v-model="platformsToScan"
          :items="sortedPlatforms"
          :menu-props="{ maxHeight: 650 }"
          :label="t('common.platforms')"
          item-title="display_name"
          item-value="id"
          prepend-inner-icon="mdi-controller"
          variant="outlined"
          density="comfortable"
          multiple
          clearable
          hide-details
          chips
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps" class="py-3">
              <template #prepend>
                <RPlatformIcon
                  :key="item.raw.slug"
                  :size="32"
                  :slug="item.raw.slug"
                  :name="item.raw.name"
                  :fs-slug="item.raw.fs_slug"
                />
              </template>
              <div class="r-v2-scan__plat-item">
                <v-icon
                  :icon="platformCategoryToIcon(item.raw.category || '')"
                  class="text-caption text-grey"
                  :title="item.raw.category"
                />
                <span
                  v-if="item.raw.family_name"
                  class="text-caption text-grey"
                >
                  {{ item.raw.family_name }}
                </span>
              </div>
              <template #append>
                <MissingFSBadge
                  v-if="item.raw.missing_from_fs"
                  text="Missing platform from filesystem"
                  class="ml-2"
                />
                <v-chip class="ml-1" size="small" label>
                  {{ item.raw.rom_count }}
                </v-chip>
              </template>
            </v-list-item>
          </template>
          <template #chip="{ item }">
            <v-chip>
              <RPlatformIcon
                :key="item.raw.slug"
                :slug="item.raw.slug"
                :name="item.raw.name"
                :fs-slug="item.raw.fs_slug"
                :size="18"
              />
              <span class="ml-2">{{ item.raw.display_name }}</span>
            </v-chip>
          </template>
        </RSelect>

        <RSelect
          v-model="metadataSources"
          :items="metadataOptions"
          :label="t('scan.metadata-sources')"
          item-title="name"
          prepend-inner-icon="mdi-database-search"
          variant="outlined"
          density="comfortable"
          multiple
          return-object
          clearable
          hide-details
          chips
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item
              v-bind="itemProps"
              :title="item.raw.name"
              :subtitle="item.raw.disabled"
              :disabled="Boolean(item.raw.disabled)"
            >
              <template #prepend>
                <v-avatar size="22" rounded="1">
                  <v-img :src="item.raw.logo_path" />
                </v-avatar>
              </template>

              <template v-if="item.raw.value === 'launchbox'" #append>
                <div class="r-v2-scan__lb-toggle">
                  <span
                    class="text-caption"
                    :class="{
                      'r-v2-scan__lb-inactive': launchboxRemoteEnabled,
                    }"
                  >
                    Local
                  </span>
                  <v-switch
                    v-model="launchboxRemoteEnabled"
                    color="primary"
                    density="compact"
                    hide-details
                    :disabled="!isLaunchboxSelected"
                    @click.stop
                    @mousedown.stop
                  />
                  <span
                    class="text-caption"
                    :class="{
                      'r-v2-scan__lb-inactive': !launchboxRemoteEnabled,
                    }"
                  >
                    Cloud
                  </span>
                </div>
              </template>
            </v-list-item>
          </template>
          <template #chip="{ item }">
            <v-chip>
              <v-avatar class="mr-1" size="18" rounded="1">
                <v-img :src="item.raw.logo_path" />
              </v-avatar>
              <span>{{ item.raw.name }}</span>
            </v-chip>
          </template>
        </RSelect>

        <RSelect
          v-model="scanType"
          :items="scanOptions"
          :label="t('scan.scan-options')"
          prepend-inner-icon="mdi-magnify-scan"
          hide-details
          density="comfortable"
          variant="outlined"
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps" :subtitle="item.raw.subtitle" />
          </template>
        </RSelect>
      </div>

      <div class="r-v2-scan__actions">
        <RBtn
          size="large"
          variant="flat"
          color="primary"
          prepend-icon="mdi-magnify-scan"
          :loading="scanning"
          :disabled="scanning"
          @click="scan"
        >
          {{ t("scan.scan") }}
        </RBtn>
        <RBtn
          size="large"
          variant="outlined"
          color="error"
          prepend-icon="mdi-alert-octagon"
          :disabled="!scanning"
          @click="stopScan"
        >
          {{ t("scan.abort") }}
        </RBtn>
      </div>

      <div
        v-if="metadataSources.length === 0 || !calculateHashes"
        class="r-v2-scan__alerts"
      >
        <RAlert
          v-if="metadataSources.length === 0"
          type="warning"
          density="compact"
          :icon="false"
        >
          {{ t("scan.select-one-source") }}
        </RAlert>
        <RAlert
          v-if="!calculateHashes"
          type="warning"
          density="compact"
          :icon="false"
        >
          {{ t("scan.hash-calculation-disabled") }}
        </RAlert>
      </div>
    </div>

    <!-- Scan log -->
    <div ref="scan-log" class="r-v2-scan__log" @scroll="onScroll">
      <div v-if="scanningPlatforms.length === 0" class="r-v2-scan__empty">
        <RIcon icon="mdi-magnify-scan" size="48" />
        <p>
          {{
            scanning
              ? t("scan.scanning-library")
              : "Pick a scan configuration and hit Scan to begin."
          }}
        </p>
      </div>
      <v-expansion-panels
        v-else
        v-model="panels"
        multiple
        flat
        variant="accordion"
      >
        <v-expansion-panel
          v-for="platform in scanningPlatforms"
          :key="platform.id"
          class="r-v2-scan__panel"
        >
          <ScanPlatform :platform="platform" />
        </v-expansion-panel>
      </v-expansion-panels>
    </div>

    <!-- Sticky stats bar -->
    <div v-if="scanningPlatforms.length > 0" class="r-v2-scan__stats">
      <div class="r-v2-scan__stat">
        <RIcon icon="mdi-controller" size="14" />
        <span v-if="xs">
          {{ t("scan.platforms-scanned-n", scanStats.scanned_platforms) }}
        </span>
        <span v-else>
          {{
            t("scan.platforms-scanned-with-details", {
              n_scanned_platforms: scanStats.scanned_platforms,
              n_total_platforms: scanStats.total_platforms,
              n_new_platforms: scanStats.new_platforms,
              n_identified_platforms: Math.min(
                scanStats.identified_platforms,
                scanStats.scanned_platforms,
              ),
            })
          }}
        </span>
      </div>
      <div class="r-v2-scan__stat">
        <RIcon icon="mdi-disc" size="14" />
        <span v-if="xs">
          {{ t("scan.roms-scanned-n", scanStats.scanned_roms) }}
        </span>
        <span v-else>
          {{
            t("scan.roms-scanned-with-details", {
              n_scanned_roms: scanStats.scanned_roms,
              n_total_roms: scanStats.total_roms,
              n_new_roms: scanStats.new_roms,
              n_identified_roms: Math.min(
                scanStats.identified_roms,
                scanStats.scanned_roms,
              ),
            })
          }}
        </span>
      </div>
      <div class="r-v2-scan__stat r-v2-scan__stat--alt">
        <RIcon icon="mdi-memory" size="14" />
        <span v-if="xs">
          {{ t("scan.firmware-scanned-n", scanStats.scanned_firmware) }}
        </span>
        <span v-else>
          {{
            t("scan.firmware-scanned-with-details", {
              n_scanned_firmware: scanStats.scanned_firmware,
              n_new_firmware: scanStats.new_firmware,
            })
          }}
        </span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.r-v2-scan {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px var(--r-row-pad) 48px;
  min-height: calc(100vh - var(--r-nav-h));
  max-width: 1240px;
  margin: 0 auto;
  width: 100%;
}

.r-v2-scan__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.r-v2-scan__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 10px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-brand-primary);
  margin-bottom: 2px;
}

.r-v2-scan__title {
  margin: 0;
  font-size: var(--r-font-size-xl);
  font-weight: var(--r-font-weight-bold);
}

.r-v2-scan__config {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  background: rgba(13, 17, 23, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.r-v2-scan__fields {
  display: grid;
  grid-template-columns: 1.6fr 1.4fr 1fr;
  gap: 12px;
}

.r-v2-scan__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.r-v2-scan__alerts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.r-v2-scan__plat-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.r-v2-scan__lb-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.r-v2-scan__lb-inactive {
  color: rgba(255, 255, 255, 0.35);
}

/* Scan log. Pins the chrome above and the stats bar below, with a
   scrollable middle that holds the platform expansion panels. */
.r-v2-scan__log {
  flex: 1;
  min-height: 240px;
  overflow-y: auto;
  scroll-behavior: smooth;
  background: rgba(13, 17, 23, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  padding: 6px;
}

.r-v2-scan__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 16px;
  color: rgba(255, 255, 255, 0.4);
  text-align: center;
}
.r-v2-scan__empty p {
  margin: 0;
  font-size: 13px;
  max-width: 360px;
}

.r-v2-scan__panel {
  background: transparent !important;
}

/* Sticky stats row. */
.r-v2-scan__stats {
  position: sticky;
  bottom: 16px;
  align-self: center;
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(13, 17, 23, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: var(--r-radius-pill);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.45);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.88);
}

.r-v2-scan__stat {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(139, 116, 232, 0.18);
  border-radius: var(--r-radius-pill);
  color: var(--r-color-brand-primary);
}
.r-v2-scan__stat--alt {
  background: rgba(34, 197, 94, 0.18);
  color: #4ade80;
}

@media (max-width: 960px) {
  .r-v2-scan__fields {
    grid-template-columns: 1fr;
  }
}
</style>
