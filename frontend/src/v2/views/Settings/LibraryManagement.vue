<script setup lang="ts">
// LibraryManagement — v2-native rewrite. Page title + mock-style
// underline tabs (`.settings-tabs`) + the three section composites
// (FolderMappings / Excluded / MissingGames). The `?tab=` query param
// is preserved so deep links keep working.
import { RAlert } from "@v2/lib";
import { storeToRefs } from "pinia";
import { ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import storeConfig from "@/stores/config";
import ExcludedSection from "@/v2/components/Settings/ExcludedSection.vue";
import FolderMappingsSection from "@/v2/components/Settings/FolderMappingsSection.vue";
import MissingGamesSection from "@/v2/components/Settings/MissingGamesSection.vue";
import SettingsShell from "@/v2/components/Settings/SettingsShell.vue";

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

interface TabDef {
  id: Tab;
  label: string;
}

const tabs: TabDef[] = [
  { id: "mapping", label: t("settings.folder-mappings") },
  { id: "excluded", label: t("settings.excluded") },
  { id: "missing", label: t("settings.missing-games-tab") },
];
</script>

<template>
  <SettingsShell bare>
    <h1 class="r-v2-settings__page-title">
      {{ t("common.library-management") }}
    </h1>

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

    <!-- Mock-faithful underline tabs. -->
    <nav class="r-v2-settings-tabs" role="tablist" aria-label="Library tabs">
      <button
        v-for="entry in tabs"
        :key="entry.id"
        type="button"
        role="tab"
        :aria-selected="tab === entry.id"
        :class="[
          'r-v2-settings-tabs__btn',
          { 'r-v2-settings-tabs__btn--active': tab === entry.id },
        ]"
        @click="tab = entry.id"
      >
        {{ entry.label }}
      </button>
    </nav>

    <FolderMappingsSection v-if="tab === 'mapping'" />
    <ExcludedSection v-else-if="tab === 'excluded'" />
    <MissingGamesSection v-else-if="tab === 'missing'" />
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

/* Mock-faithful underline tabs — bottom border on active, with the
   tab btn's bottom edge sitting on the strip's hairline. */
.r-v2-settings-tabs {
  display: flex;
  border-bottom: 1px solid var(--r-color-border);
  margin-bottom: 20px;
}
.r-v2-settings-tabs__btn {
  padding: 8px 18px;
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg-muted);
  cursor: pointer;
  border: none;
  background: transparent;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition:
    color var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-settings-tabs__btn:hover {
  color: var(--r-color-fg-secondary);
}
.r-v2-settings-tabs__btn--active {
  color: var(--r-color-fg);
  border-bottom-color: var(--r-color-fg);
}
</style>
