<script setup lang="ts">
import { RSelect } from "@v2/lib";
import { computed } from "vue";
import { useI18n } from "vue-i18n";

export interface SetupFolder {
  name: string;
  relative_path: string;
  association: "known" | "unknown";
  suggested_platform: string | null;
}
export interface SetupPlatformOption {
  slug: string;
  display_name: string;
}
export interface SetupFolderDiscovery {
  root_label: string;
  folders: SetupFolder[];
  platform_options: SetupPlatformOption[];
}
export type SetupFolderDraft = Record<string, string | null>;
interface Props {
  discovery: SetupFolderDiscovery;
  draft: SetupFolderDraft;
  disabled: boolean;
  submitting: boolean;
}
const props = defineProps<Props>();
const emit = defineEmits<{
  (event: "update:draft", draft: SetupFolderDraft): void;
}>();
const { t } = useI18n();
const rows = computed(() =>
  [...props.discovery.folders].sort((a, b) => a.name.localeCompare(b.name)),
);
const options = computed(() =>
  [...props.discovery.platform_options].sort((a, b) =>
    a.display_name.localeCompare(b.display_name),
  ),
);
const updateFolder = (folder: SetupFolder, value: unknown) => {
  emit("update:draft", {
    ...props.draft,
    [folder.name]: typeof value === "string" ? value : null,
  });
};
</script>
<template>
  <section class="r-setup-platforms" aria-labelledby="setup-folders-title">
    <div class="r-setup-platforms__intro">
      <h3 id="setup-folders-title">{{ t("setup.folders-title") }}</h3>
      <p>
        {{ t("setup.folders-description", { root: discovery.root_label }) }}
      </p>
    </div>
    <div
      v-if="rows.length"
      class="r-setup-platforms__table-wrap"
      role="region"
      :aria-label="t('setup.folders-title')"
    >
      <table class="r-setup-platforms__table">
        <thead>
          <tr>
            <th scope="col">{{ t("setup.folder-column") }}</th>
            <th scope="col">{{ t("setup.platform-column") }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="folder in rows" :key="folder.relative_path">
            <th scope="row">
              <span>{{ folder.name }}</span
              ><small v-if="folder.association === 'unknown'">{{
                t("setup.folder-needs-assignment")
              }}</small>
            </th>
            <td>
              <RSelect
                :model-value="props.draft[folder.name]"
                :items="options"
                item-title="display_name"
                item-value="slug"
                :disabled="disabled || submitting"
                :label="t('setup.assign-folder', { folder: folder.name })"
                :placeholder="t('setup.choose-platform')"
                :search-placeholder="t('common.search')"
                hide-details
                @update:model-value="updateFolder(folder, $event)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else class="r-setup-platforms__empty">
      {{ t("setup.no-folders-found") }}
    </p>
  </section>
</template>
<style scoped>
.r-setup-platforms {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
  min-height: 0;
}
.r-setup-platforms__intro h3 {
  margin: 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-lg);
}
.r-setup-platforms__intro p {
  margin: var(--r-space-2) 0 0;
  color: var(--r-color-fg-secondary);
}
.r-setup-platforms__table-wrap {
  overflow-x: auto;
}
.r-setup-platforms__table {
  width: 100%;
  border-collapse: collapse;
  min-width: 320px;
}
.r-setup-platforms__table th,
.r-setup-platforms__table td {
  min-height: 44px;
  padding: var(--r-space-3);
  text-align: start;
  vertical-align: middle;
  border-bottom: 1px solid var(--r-color-border);
}
.r-setup-platforms__table thead th {
  color: var(--r-color-fg-secondary);
  font-size: var(--r-font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.r-setup-platforms__table tbody th {
  color: var(--r-color-fg);
  font-weight: var(--r-font-weight-medium);
}
.r-setup-platforms__table small {
  display: block;
  margin-top: var(--r-space-1);
  color: var(--r-color-status-base-warning);
  font-weight: var(--r-font-weight-normal);
}
.r-setup-platforms__empty {
  margin: 0;
  color: var(--r-color-fg-secondary);
}
html[data-bp~="xs"] .r-setup-platforms__table th,
html[data-bp~="xs"] .r-setup-platforms__table td {
  padding: var(--r-space-2);
}
</style>
