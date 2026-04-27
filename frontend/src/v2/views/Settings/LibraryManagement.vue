<script setup lang="ts">
// LibraryManagement — v2 chrome around the v1 FolderMappings / Excluded /
// MissingGames sub-components. Tabs drive a ?tab= query param for
// deep-linking, same as v1. The config-file-unmounted / not-writable
// warnings are preserved verbatim.
import { RAlert, RSliderBtnGroup } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import Excluded from "@/components/Settings/LibraryManagement/Config/Excluded.vue";
import FolderMappings from "@/components/Settings/LibraryManagement/Config/FolderMappings.vue";
import MissingGames from "@/components/Settings/LibraryManagement/Config/MissingGames.vue";
import storeConfig from "@/stores/config";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";
import type { SliderBtnGroupItem } from "@/v2/lib/primitives/RSliderBtnGroup/types";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

type Tab = "mapping" | "excluded" | "missing";
const validTabs: Tab[] = ["mapping", "excluded", "missing"];

const tab = ref<Tab>(
  (validTabs as string[]).includes(route.query.tab as string)
    ? (route.query.tab as Tab)
    : "mapping",
);
const configStore = storeConfig();
const { config } = storeToRefs(configStore);

watch(tab, (newTab) => {
  router.replace({
    path: route.path,
    query: { ...route.query, tab: newTab },
  });
});

watch(
  () => route.query.tab,
  (newTab) => {
    if (
      newTab &&
      (validTabs as string[]).includes(newTab as string) &&
      tab.value !== newTab
    ) {
      tab.value = newTab as Tab;
    }
  },
  { immediate: true },
);

const tabs = computed<SliderBtnGroupItem<Tab>[]>(() => [
  {
    id: "mapping",
    label: t("settings.folder-mappings"),
    icon: "mdi-folder-cog",
  },
  { id: "excluded", label: t("settings.excluded"), icon: "mdi-cancel" },
  {
    id: "missing",
    label: t("settings.missing-games-tab"),
    icon: "mdi-folder-question",
  },
]);

function setTab(id: Tab) {
  tab.value = id;
}
</script>

<template>
  <SettingsShell
    :title="t('common.library-management')"
    subtitle="Folder mappings, excluded paths, and missing-from-disk games."
    icon="mdi-folder-cog"
    bare
  >
    <div class="r-v2-lib__tabs">
      <RSliderBtnGroup
        variant="tab"
        :model-value="tab"
        :items="tabs"
        aria-label="Library management section"
        @update:model-value="setTab"
      />
    </div>

    <RAlert v-if="!config.CONFIG_FILE_MOUNTED" type="error">
      <template #title>
        {{ t("settings.config-file-not-mounted-title") }}
      </template>
      {{ t("settings.config-file-not-mounted-desc") }}
    </RAlert>
    <RAlert v-else-if="!config.CONFIG_FILE_WRITABLE" type="warning">
      <template #title>
        {{ t("settings.config-file-not-writable-title") }}
      </template>
      {{ t("settings.config-file-not-writable-desc") }}
    </RAlert>

    <div class="r-v2-lib__body">
      <FolderMappings v-if="tab === 'mapping'" />
      <Excluded v-else-if="tab === 'excluded'" />
      <MissingGames v-else-if="tab === 'missing'" />
    </div>
  </SettingsShell>
</template>

<style scoped>
.r-v2-lib__tabs {
  display: flex;
  justify-content: flex-start;
}

.r-v2-lib__body {
  background: rgba(13, 17, 23, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: var(--r-radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  padding: 6px;
  min-height: 180px;
}
</style>
