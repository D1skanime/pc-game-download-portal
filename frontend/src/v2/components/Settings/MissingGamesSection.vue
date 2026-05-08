<script setup lang="ts">
// MissingGamesSection — v2-native rebuild of v1
// `Settings/LibraryManagement/Config/MissingGames.vue`. Lists ROMs whose
// files are missing from the filesystem, with a per-platform filter and
// a "cleanup all" action that purges them server-side.
//
// Uses the shared `storeRoms` paginator with `setFilterMissing(true)`
// so the listing reuses the same backend search; pagination is a manual
// "Load more" button (no infinite scroll on a settings table).
import { RBtn, RIcon, RSelect, RSpinner } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import MissingFromFSIcon from "@/components/common/MissingFromFSIcon.vue";
import PlatformIcon from "@/components/common/Platform/PlatformIcon.vue";
import taskApi from "@/services/api/task";
import storeGalleryFilter from "@/stores/galleryFilter";
import storePlatforms from "@/stores/platforms";
import storeRoms from "@/stores/roms";
import { formatBytes } from "@/utils";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const romsStore = storeRoms();
const { fetchingRoms, fetchTotalRoms, filteredRoms } = storeToRefs(romsStore);
const galleryFilterStore = storeGalleryFilter();
const { selectedPlatform } = storeToRefs(galleryFilterStore);
const platformsStore = storePlatforms();
const snackbar = useSnackbar();
const confirm = useConfirm();

const cleaningUp = ref(false);
const initialLoading = ref(false);

const allPlatforms = computed(() => {
  // De-dup platforms across the currently-loaded missing ROMs.
  const map = new Map<
    number,
    NonNullable<ReturnType<typeof platformsStore.get>>
  >();
  for (const rom of filteredRoms.value) {
    const p = platformsStore.get(rom.platform_id);
    if (p) map.set(p.id, p);
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
});

const platformItems = computed(() =>
  allPlatforms.value.map((p) => ({ title: p.name, value: p.id })),
);

const hasMore = computed(
  () => fetchTotalRoms.value > filteredRoms.value.length,
);

async function fetchPage(concat: boolean) {
  if (fetchingRoms.value) return;
  galleryFilterStore.setFilterMissing(true);
  try {
    await romsStore.fetchRoms(concat);
  } catch (err) {
    snackbar.error(
      t("settings.couldnt-fetch-missing-roms", { error: String(err) }),
    );
  } finally {
    galleryFilterStore.setFilterMissing(false);
  }
}

function onPlatformChange(value: unknown) {
  const id = typeof value === "number" ? value : null;
  selectedPlatform.value = id ? (platformsStore.get(id) ?? null) : null;
  romsStore.resetPagination();
  void fetchPage(false);
}

async function cleanupAll() {
  const platformLabel = selectedPlatform.value
    ? ` for ${selectedPlatform.value.name}`
    : "";
  const ok = await confirm({
    title: t("common.confirm-deletion"),
    body: t("settings.cleanup-all-confirm", { platform: platformLabel }),
    confirmText: t("settings.cleanup-all"),
    tone: "danger",
    requireTyped: "DELETE",
  });
  if (!ok) return;
  cleaningUp.value = true;
  try {
    const body = selectedPlatform.value?.id
      ? { platform_id: selectedPlatform.value.id }
      : {};
    await taskApi.runTask("cleanup_missing_roms", body);
    snackbar.success(
      "Cleanup task queued, missing ROMs will be deleted shortly.",
      { icon: "mdi-check-bold", timeout: 5000 },
    );
  } catch (err) {
    snackbar.error(`Couldn't queue cleanup task: ${String(err)}`, {
      icon: "mdi-close-circle",
    });
  } finally {
    cleaningUp.value = false;
  }
}

function reset() {
  romsStore.reset();
  galleryFilterStore.resetFilters();
}

onMounted(async () => {
  reset();
  initialLoading.value = true;
  try {
    await fetchPage(false);
  } finally {
    initialLoading.value = false;
  }
});

onBeforeUnmount(() => {
  reset();
});
</script>

<template>
  <div class="r-v2-missing">
    <div class="r-v2-missing__toolbar">
      <RSelect
        :model-value="selectedPlatform?.id ?? null"
        :items="platformItems"
        :label="t('common.platform')"
        :disabled="platformItems.length === 0"
        prepend-inner-icon="mdi-controller"
        variant="outlined"
        density="comfortable"
        clearable
        hide-details
        class="r-v2-missing__platform-select"
        @update:model-value="onPlatformChange"
      />
      <RBtn
        variant="flat"
        color="danger"
        prepend-icon="mdi-delete"
        :loading="cleaningUp"
        :disabled="filteredRoms.length === 0"
        @click="cleanupAll"
      >
        {{ t("settings.cleanup-all") }}
      </RBtn>
    </div>

    <div v-if="initialLoading" class="r-v2-missing__loading">
      <RSpinner :size="28" />
    </div>
    <div v-else-if="filteredRoms.length === 0" class="r-v2-missing__empty">
      <RIcon icon="mdi-folder-question" size="48" />
      <p>{{ t("settings.missing-games-none") }}</p>
    </div>
    <template v-else>
      <div class="r-v2-table-wrap">
        <table class="r-v2-table">
          <thead>
            <tr>
              <th>{{ t("common.name") }}</th>
              <th>{{ t("common.platform") }}</th>
              <th>{{ t("common.size-on-disk") }}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="rom in filteredRoms" :key="rom.id">
              <td class="r-v2-missing__name">
                <span class="r-v2-missing__title">
                  {{ rom.name ?? rom.fs_name_no_tags }}
                </span>
                <span class="r-v2-missing__subtitle">{{ rom.fs_name }}</span>
              </td>
              <td>
                <span class="r-v2-missing__platform">
                  <PlatformIcon
                    :slug="platformsStore.get(rom.platform_id)?.slug ?? ''"
                    :size="20"
                  />
                  {{ platformsStore.get(rom.platform_id)?.name ?? "—" }}
                </span>
              </td>
              <td>{{ formatBytes(rom.fs_size_bytes) }}</td>
              <td>
                <MissingFromFSIcon
                  :text="t('settings.missing-platform-from-fs')"
                  chip
                  chip-density="compact"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="hasMore" class="r-v2-missing__load-more">
        <RBtn variant="flat" :loading="fetchingRoms" @click="fetchPage(true)">
          {{ `Load more (${filteredRoms.length} / ${fetchTotalRoms})` }}
        </RBtn>
      </div>
    </template>
  </div>
</template>

<style scoped>
.r-v2-missing {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.r-v2-missing__toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}
.r-v2-missing__platform-select {
  flex: 1;
  min-width: 0;
}

.r-v2-missing__loading {
  padding: 40px;
  display: flex;
  justify-content: center;
}

.r-v2-missing__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 32px 16px;
  color: var(--r-color-fg-muted);
  text-align: center;
}
.r-v2-missing__empty p {
  margin: 0;
  font-size: 13px;
}

.r-v2-table-wrap {
  border: 1px solid var(--r-color-border);
  border-radius: 10px;
  overflow: hidden;
  background: var(--r-color-bg-elevated);
}
.r-v2-table {
  width: 100%;
  border-collapse: collapse;
}
.r-v2-table th {
  font-size: 10px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--r-color-fg-muted);
  text-align: left;
  padding: 10px 14px;
  border-bottom: 1px solid var(--r-color-border);
  background: var(--r-color-surface);
}
.r-v2-table td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--r-color-border);
  font-size: 13px;
  color: var(--r-color-fg);
  vertical-align: middle;
}
.r-v2-table tr:last-child td {
  border-bottom: none;
}
.r-v2-table tr:hover td {
  background: var(--r-color-surface);
}

.r-v2-missing__name {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.r-v2-missing__title {
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg);
}
.r-v2-missing__subtitle {
  font-size: 11px;
  color: var(--r-color-fg-muted);
  font-family: var(--r-font-family-mono, monospace);
}

.r-v2-missing__platform {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--r-color-fg);
}

.r-v2-missing__load-more {
  display: flex;
  justify-content: center;
}
</style>
