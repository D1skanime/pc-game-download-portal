<script setup lang="ts">
// ExcludedSection — v2-native rebuild of v1
// `Settings/LibraryManagement/Config/Excluded.vue`. Lets the user view and
// manage scan exclusions (file names, extensions, platforms). Defaults
// from `DEFAULT_EXCLUDED_*` are listed read-only at the bottom.
//
// Visuals follow the mock's settings table pattern (subtle borders,
// uppercase column heads, hairline-divided rows). The "Add" flow opens
// a local RDialog that walks the user through type selection + value
// entry.
import { RBtn, REmptyState, RIcon, RTextField } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import configApi from "@/services/api/config";
import storeAuth from "@/stores/auth";
import storeConfig from "@/stores/config";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import RDialog from "@/v2/lib/overlays/RDialog/RDialog.vue";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const configStore = storeConfig();
const { config } = storeToRefs(configStore);
const authStore = storeAuth();
const snackbar = useSnackbar();

const search = ref("");
const dialogOpen = ref(false);
const newType = ref<string | null>(null);
const newValue = ref("");
const submitting = ref(false);

type ExclusionDef = {
  key:
    | "EXCLUDED_PLATFORMS"
    | "EXCLUDED_SINGLE_FILES"
    | "EXCLUDED_SINGLE_EXT"
    | "EXCLUDED_MULTI_FILES"
    | "EXCLUDED_MULTI_PARTS_FILES"
    | "EXCLUDED_MULTI_PARTS_EXT";
  title: string;
  description: string;
  icon: string;
};

const exclusionDefs = computed<ExclusionDef[]>(() => [
  {
    key: "EXCLUDED_PLATFORMS",
    title: t("common.platform"),
    description: t("settings.exclusions-platforms-desc"),
    icon: "mdi-gamepad-variant-outline",
  },
  {
    key: "EXCLUDED_SINGLE_FILES",
    title: t("settings.excluded-single-rom-files"),
    description: t("settings.exclusions-single-files-desc"),
    icon: "mdi-file-remove-outline",
  },
  {
    key: "EXCLUDED_SINGLE_EXT",
    title: t("settings.excluded-single-rom-extensions"),
    description: t("settings.exclusions-single-ext-desc"),
    icon: "mdi-file-code-outline",
  },
  {
    key: "EXCLUDED_MULTI_FILES",
    title: t("settings.excluded-multi-rom-files"),
    description: t("settings.exclusions-multi-files-desc"),
    icon: "mdi-file-multiple-outline",
  },
  {
    key: "EXCLUDED_MULTI_PARTS_FILES",
    title: t("settings.excluded-multi-rom-parts-files"),
    description: t("settings.exclusions-multi-parts-files-desc"),
    icon: "mdi-folder-multiple-outline",
  },
  {
    key: "EXCLUDED_MULTI_PARTS_EXT",
    title: t("settings.excluded-multi-rom-parts-extensions"),
    description: t("settings.exclusions-multi-parts-ext-desc"),
    icon: "mdi-file-cog-outline",
  },
]);

const DEFAULT_LIST_MAP: Record<
  ExclusionDef["key"],
  | "DEFAULT_EXCLUDED_DIRS"
  | "DEFAULT_EXCLUDED_FILES"
  | "DEFAULT_EXCLUDED_EXTENSIONS"
> = {
  EXCLUDED_PLATFORMS: "DEFAULT_EXCLUDED_DIRS",
  EXCLUDED_SINGLE_FILES: "DEFAULT_EXCLUDED_FILES",
  EXCLUDED_SINGLE_EXT: "DEFAULT_EXCLUDED_EXTENSIONS",
  EXCLUDED_MULTI_FILES: "DEFAULT_EXCLUDED_DIRS",
  EXCLUDED_MULTI_PARTS_FILES: "DEFAULT_EXCLUDED_FILES",
  EXCLUDED_MULTI_PARTS_EXT: "DEFAULT_EXCLUDED_EXTENSIONS",
};

function isDefault(key: ExclusionDef["key"], value: string): boolean {
  const defaults = config.value[DEFAULT_LIST_MAP[key]] || [];
  return defaults.includes(value);
}

type Row = {
  type: ExclusionDef["key"];
  title: string;
  icon: string;
  value: string;
};

const exclusions = computed<Row[]>(() => {
  const rows: Row[] = [];
  for (const def of exclusionDefs.value) {
    const set = config.value[def.key] || [];
    for (const v of set) {
      if (!isDefault(def.key, v)) {
        rows.push({
          type: def.key,
          title: def.title,
          icon: def.icon,
          value: v,
        });
      }
    }
  }
  rows.sort(
    (a, b) => a.title.localeCompare(b.title) || a.value.localeCompare(b.value),
  );
  return rows;
});

const filteredExclusions = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return exclusions.value;
  return exclusions.value.filter(
    (r) =>
      r.value.toLowerCase().includes(q) || r.title.toLowerCase().includes(q),
  );
});

const defaultExclusions = computed(() => {
  const seen = new Map<string, Row>();
  for (const def of exclusionDefs.value) {
    const set = config.value[def.key] || [];
    for (const v of set) {
      if (isDefault(def.key, v) && !seen.has(v)) {
        seen.set(v, {
          type: def.key,
          title: def.title,
          icon: def.icon,
          value: v,
        });
      }
    }
  }
  return [...seen.values()].sort((a, b) => a.value.localeCompare(b.value));
});

const canEdit = computed(
  () =>
    authStore.scopes.includes("platforms.write") &&
    config.value.CONFIG_FILE_WRITABLE,
);

function openCreate() {
  newType.value = null;
  newValue.value = "";
  dialogOpen.value = true;
}

function closeCreate() {
  dialogOpen.value = false;
  newType.value = null;
  newValue.value = "";
}

const selectedDef = computed(() =>
  exclusionDefs.value.find((d) => d.key === newType.value),
);

async function submitExclusion() {
  if (!newType.value || !newValue.value.trim()) return;
  submitting.value = true;
  try {
    await configApi.addExclusion({
      exclusionValue: newValue.value.trim(),
      exclusionType: newType.value,
    });
    if (configStore.isExclusionType(newType.value)) {
      configStore.addExclusion(newType.value, newValue.value.trim());
    }
    snackbar.success("Exclusion added");
    closeCreate();
  } catch (err) {
    snackbar.error(`Could not add exclusion: ${(err as Error).message}`);
  } finally {
    submitting.value = false;
  }
}

async function removeRow(row: Row) {
  try {
    await configApi.deleteExclusion({
      exclusionValue: row.value,
      exclusionType: row.type,
    });
    if (configStore.isExclusionType(row.type)) {
      configStore.removeExclusion(row.value, row.type);
    }
  } catch (err) {
    snackbar.error(`Could not remove exclusion: ${(err as Error).message}`);
  }
}
</script>

<template>
  <div class="r-v2-excluded">
    <!-- Toolbar: search + add -->
    <div class="r-v2-excluded__toolbar">
      <div class="r-v2-search">
        <RIcon icon="mdi-magnify" size="15" />
        <input
          v-model="search"
          type="text"
          :placeholder="t('common.search')"
          aria-label="Search exclusions"
        />
      </div>
      <RBtn
        v-if="canEdit"
        variant="flat"
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreate"
      >
        {{ t("common.add") }}
      </RBtn>
    </div>

    <!-- Active exclusions table or empty state -->
    <div v-if="exclusions.length === 0" class="r-v2-excluded__empty">
      <REmptyState
        icon="mdi-format-list-bulleted"
        :message="t('settings.exclusions-none')"
      />
      <RBtn
        v-if="canEdit"
        variant="flat"
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreate"
      >
        {{ t("common.add") }}
      </RBtn>
    </div>
    <div v-else class="r-v2-table-wrap">
      <table class="r-v2-table">
        <thead>
          <tr>
            <th>{{ t("common.name") }}</th>
            <th>{{ t("common.type") }}</th>
            <th class="r-v2-table__col-actions" />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in filteredExclusions"
            :key="`${row.type}:${row.value}`"
          >
            <td class="r-v2-excluded__value">{{ row.value }}</td>
            <td>
              <span class="r-v2-excluded__type">
                <RIcon :icon="row.icon" size="14" />
                {{ row.title }}
              </span>
            </td>
            <td class="r-v2-table__col-actions">
              <button
                v-if="canEdit"
                type="button"
                class="r-v2-icon-btn r-v2-icon-btn--danger"
                :aria-label="t('common.delete')"
                :title="t('common.delete')"
                @click="removeRow(row)"
              >
                <RIcon icon="mdi-trash-can-outline" size="14" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Defaults (read-only) -->
    <div v-if="defaultExclusions.length > 0" class="r-v2-excluded__defaults">
      <div class="r-v2-excluded__defaults-label">
        {{ t("settings.exclusions-defaults") }}
      </div>
      <ul class="r-v2-excluded__defaults-list">
        <li
          v-for="d in defaultExclusions"
          :key="d.value"
          class="r-v2-excluded__defaults-item"
        >
          <RIcon :icon="d.icon" size="14" />
          <span class="r-v2-excluded__defaults-value">{{ d.value }}</span>
          <span class="r-v2-excluded__defaults-type">{{ d.title }}</span>
        </li>
      </ul>
    </div>

    <!-- Add exclusion dialog -->
    <RDialog
      v-model="dialogOpen"
      icon="mdi-cancel"
      :width="540"
      @close="closeCreate"
    >
      <template #header>
        <span class="r-v2-excluded__dialog-title">
          {{ t("common.add") }}
        </span>
      </template>
      <template #content>
        <div class="r-v2-excluded__dialog-body">
          <p class="r-v2-excluded__dialog-help">
            {{ t("settings.select-exclusion-type") }}
          </p>
          <div class="r-v2-excluded__type-grid">
            <button
              v-for="def in exclusionDefs"
              :key="def.key"
              type="button"
              class="r-v2-excluded__type-card"
              :class="{
                'r-v2-excluded__type-card--active': newType === def.key,
              }"
              :aria-pressed="newType === def.key"
              @click="newType = def.key"
            >
              <RIcon :icon="def.icon" size="22" />
              <span class="r-v2-excluded__type-card-title">{{
                def.title
              }}</span>
              <span class="r-v2-excluded__type-card-desc">
                {{ def.description }}
              </span>
            </button>
          </div>
          <RTextField
            v-model="newValue"
            variant="outlined"
            :label="t('settings.exclusion-value')"
            :placeholder="t('settings.exclusion-placeholder')"
            :prepend-inner-icon="selectedDef?.icon"
            :disabled="!newType"
            hide-details
            @keyup.enter="submitExclusion"
          />
        </div>
      </template>
      <template #footer>
        <div class="r-v2-excluded__dialog-actions">
          <RBtn variant="text" @click="closeCreate">
            {{ t("common.cancel") }}
          </RBtn>
          <RBtn
            variant="flat"
            color="primary"
            :loading="submitting"
            :disabled="!newType || !newValue.trim()"
            @click="submitExclusion"
          >
            {{ t("common.confirm") }}
          </RBtn>
        </div>
      </template>
    </RDialog>
  </div>
</template>

<style scoped>
.r-v2-excluded {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.r-v2-excluded__toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}
.r-v2-excluded__toolbar > .r-v2-search {
  flex: 1;
}

/* Mock-faithful search input. */
.r-v2-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border);
  border-radius: 8px;
  color: var(--r-color-fg-muted);
  transition:
    border-color var(--r-motion-fast) var(--r-motion-ease-out),
    background var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-search:focus-within {
  border-color: color-mix(
    in srgb,
    var(--r-color-brand-primary) 50%,
    transparent
  );
  background: var(--r-color-surface-hover);
}
.r-v2-search input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  font: inherit;
  color: var(--r-color-fg);
  font-size: 13px;
}
.r-v2-search input::placeholder {
  color: var(--r-color-fg-faint);
}

/* Table chrome — mock-faithful (border-radius 10px outer, hairline rows). */
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
.r-v2-table__col-actions {
  width: 1%;
  text-align: right;
  white-space: nowrap;
}

.r-v2-excluded__value {
  font-weight: var(--r-font-weight-medium);
}
.r-v2-excluded__type {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--r-color-fg-muted);
}

/* Generic settings icon-button — also reused by FolderMappings. */
.r-v2-icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--r-color-fg-muted);
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-icon-btn:hover {
  background: var(--r-color-surface);
  color: var(--r-color-fg);
}
.r-v2-icon-btn--danger {
  color: color-mix(in srgb, var(--r-color-danger) 70%, transparent);
}
.r-v2-icon-btn--danger:hover {
  background: color-mix(in srgb, var(--r-color-danger) 12%, transparent);
  color: var(--r-color-danger);
}

/* Empty state with CTA below. */
.r-v2-excluded__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 24px 16px 32px;
}

/* Defaults list (read-only). */
.r-v2-excluded__defaults {
  border-top: 1px solid var(--r-color-border);
  padding-top: 16px;
}
.r-v2-excluded__defaults-label {
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--r-color-fg-muted);
  margin-bottom: 10px;
}
.r-v2-excluded__defaults-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
}
.r-v2-excluded__defaults-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  color: var(--r-color-fg-secondary);
  font-size: 12px;
}
.r-v2-excluded__defaults-value {
  font-weight: var(--r-font-weight-medium);
}
.r-v2-excluded__defaults-type {
  margin-left: auto;
  color: var(--r-color-fg-faint);
  font-size: 11px;
}

/* Add-exclusion dialog. */
.r-v2-excluded__dialog-title {
  font-weight: var(--r-font-weight-semibold);
}
.r-v2-excluded__dialog-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.r-v2-excluded__dialog-help {
  margin: 0;
  text-align: center;
  font-size: 13px;
  color: var(--r-color-fg-muted);
}
.r-v2-excluded__type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}
.r-v2-excluded__type-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 14px;
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border);
  border-radius: 8px;
  color: var(--r-color-fg-secondary);
  cursor: pointer;
  text-align: left;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-excluded__type-card:hover {
  background: var(--r-color-surface-hover);
  border-color: var(--r-color-border-strong);
  color: var(--r-color-fg);
}
.r-v2-excluded__type-card--active,
.r-v2-excluded__type-card--active:hover {
  background: color-mix(in srgb, var(--r-color-brand-primary) 14%, transparent);
  border-color: color-mix(
    in srgb,
    var(--r-color-brand-primary) 50%,
    transparent
  );
  color: var(--r-color-brand-primary);
}
.r-v2-excluded__type-card-title {
  font-size: 13px;
  font-weight: var(--r-font-weight-semibold);
}
.r-v2-excluded__type-card-desc {
  font-size: 11px;
  color: var(--r-color-fg-muted);
  line-height: 1.4;
}
.r-v2-excluded__dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 24px;
  border-top: 1px solid var(--r-color-border);
}
</style>
