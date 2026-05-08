<script setup lang="ts">
// FolderMappingsSection — v2-native rebuild of v1
// `Settings/LibraryManagement/Config/FolderMappings.vue`. Lists every
// filesystem folder the scanner sees and lets admins map each one to a
// RomM platform (alias) or to a parent platform's metadata (variant).
// Auto-detected mappings are read-only.
//
// Visual mirrors the mock's settings table pattern: subtle borders,
// uppercase column heads, hairline-divided rows, hover tint. Editable
// platform / type cells open RMenu pickers.
import { RBtn, RIcon, RMenu, RMenuItem, RMenuPanel, RTooltip } from "@v2/lib";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import PlatformIcon from "@/components/common/Platform/PlatformIcon.vue";
import configApi from "@/services/api/config";
import platformApi from "@/services/api/platform";
import storeAuth from "@/stores/auth";
import storeConfig from "@/stores/config";
import storeHeartbeat from "@/stores/heartbeat";
import type { Platform } from "@/stores/platforms";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const authStore = storeAuth();
const configStore = storeConfig();
const { config } = storeToRefs(configStore);
const heartbeat = storeHeartbeat();
const snackbar = useSnackbar();

const supportedPlatforms = ref<Platform[]>([]);
const search = ref("");
const loading = ref(false);

type RowType = "alias" | "variant" | "auto" | null;

interface Row {
  fsSlug: string;
  slug?: string;
  displayName?: string;
  type: RowType;
}

const mappings = computed<Row[]>(() => {
  const rows: Row[] = [];
  const folders = heartbeat.value?.FILESYSTEM?.FS_PLATFORMS || [];
  const bindings = config.value.PLATFORMS_BINDING || {};
  const versions = config.value.PLATFORMS_VERSIONS || {};
  const autoSlug: Record<string, string | undefined> = {};

  for (const p of supportedPlatforms.value) autoSlug[p.slug] = p.slug;

  for (const folder of folders) {
    if (bindings[folder]) {
      const slug = bindings[folder];
      const platform = supportedPlatforms.value.find((p) => p.slug === slug);
      rows.push({
        fsSlug: folder,
        slug,
        displayName: platform?.display_name || platform?.name || slug,
        type: "alias",
      });
      continue;
    }
    if (versions[folder]) {
      const slug = versions[folder];
      const platform = supportedPlatforms.value.find((p) => p.slug === slug);
      rows.push({
        fsSlug: folder,
        slug,
        displayName: platform?.display_name || platform?.name || slug,
        type: "variant",
      });
      continue;
    }
    const auto = autoSlug[folder];
    if (auto) {
      const platform = supportedPlatforms.value.find((p) => p.slug === auto);
      rows.push({
        fsSlug: folder,
        slug: auto,
        displayName: platform?.display_name || platform?.name || auto,
        type: "auto",
      });
    } else {
      rows.push({
        fsSlug: folder,
        slug: undefined,
        displayName: undefined,
        type: null,
      });
    }
  }

  return rows.sort((a, b) => a.fsSlug.localeCompare(b.fsSlug));
});

const filteredMappings = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return mappings.value;
  return mappings.value.filter(
    (r) =>
      r.fsSlug.toLowerCase().includes(q) ||
      (r.displayName ?? "").toLowerCase().includes(q),
  );
});

const canEdit = computed(
  () =>
    authStore.scopes.includes("platforms.write") &&
    config.value.CONFIG_FILE_WRITABLE,
);

async function setPlatform(row: Row, slug: string | undefined) {
  loading.value = true;
  try {
    if (!slug) {
      // Delete the mapping.
      if (row.type === "alias") {
        await configApi.deletePlatformBindConfig({ fsSlug: row.fsSlug });
      } else if (row.type === "variant") {
        await configApi.deletePlatformVersionConfig({ fsSlug: row.fsSlug });
      }
      await configStore.fetchConfig();
      snackbar.success(t("settings.platform-mapping-deleted"));
      return;
    }
    if (row.type === null) {
      await configApi.addPlatformBindConfig({ fsSlug: row.fsSlug, slug });
      await configStore.fetchConfig();
      snackbar.success(t("settings.platform-mapping-created"));
      return;
    }
    if (row.type === "auto") {
      await configApi.addPlatformBindConfig({ fsSlug: row.fsSlug, slug });
      await configStore.fetchConfig();
      snackbar.success(t("settings.platform-mapping-updated"));
      return;
    }
    if (row.type === "alias") {
      await configApi.deletePlatformBindConfig({ fsSlug: row.fsSlug });
      await configApi.addPlatformBindConfig({ fsSlug: row.fsSlug, slug });
      await configStore.fetchConfig();
      snackbar.success(t("settings.platform-mapping-updated"));
      return;
    }
    if (row.type === "variant") {
      await configApi.deletePlatformVersionConfig({ fsSlug: row.fsSlug });
      await configApi.addPlatformVersionConfig({ fsSlug: row.fsSlug, slug });
      await configStore.fetchConfig();
      snackbar.success(t("settings.platform-mapping-updated"));
    }
  } catch (err) {
    const e = err as {
      response?: { data?: { detail?: string }; statusText?: string };
      message?: string;
    };
    const detail =
      e?.response?.data?.detail || e?.response?.statusText || e?.message;
    snackbar.error(t("settings.unable-to-update-platform-mapping", { detail }));
  } finally {
    loading.value = false;
  }
}

async function setType(row: Row, newType: "alias" | "variant") {
  if (!row.slug || row.type === newType) return;
  loading.value = true;
  try {
    if (row.type === "alias") {
      await configApi.deletePlatformBindConfig({ fsSlug: row.fsSlug });
    } else if (row.type === "variant") {
      await configApi.deletePlatformVersionConfig({ fsSlug: row.fsSlug });
    }
    if (newType === "alias") {
      await configApi.addPlatformBindConfig({
        fsSlug: row.fsSlug,
        slug: row.slug,
      });
    } else {
      await configApi.addPlatformVersionConfig({
        fsSlug: row.fsSlug,
        slug: row.slug,
      });
    }
    await configStore.fetchConfig();
    snackbar.success(t("settings.platform-mapping-updated"));
  } catch (err) {
    const e = err as {
      response?: { data?: { detail?: string }; statusText?: string };
      message?: string;
    };
    const detail =
      e?.response?.data?.detail || e?.response?.statusText || e?.message;
    snackbar.error(t("settings.unable-to-update-platform-mapping", { detail }));
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  loading.value = true;
  try {
    const { data } = await platformApi.getSupportedPlatforms();
    supportedPlatforms.value = data || [];
  } catch (err) {
    const e = err as {
      response?: { data?: { detail?: string }; statusText?: string };
      message?: string;
    };
    const detail =
      e?.response?.data?.detail || e?.response?.statusText || e?.message;
    snackbar.error(t("settings.unable-to-get-supported-platforms", { detail }));
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="r-v2-mappings">
    <div class="r-v2-mappings__toolbar">
      <div class="r-v2-search">
        <RIcon icon="mdi-magnify" size="15" />
        <input
          v-model="search"
          type="text"
          :placeholder="t('common.search')"
          aria-label="Search folder mappings"
        />
      </div>
      <RTooltip>
        <template #activator="{ props: tipProps }">
          <button
            type="button"
            class="r-v2-icon-btn"
            v-bind="tipProps"
            :aria-label="t('settings.exclusions-tooltip')"
          >
            <RIcon icon="mdi-information-outline" size="15" />
          </button>
        </template>
        <div class="r-v2-mappings__tip">
          <p>
            <strong>{{ t("settings.folder-alias") }}:</strong>
            {{ t("settings.folder-mappings-tooltip-aliases") }}
          </p>
          <p>
            <strong>{{ t("settings.platform-variant") }}:</strong>
            {{ t("settings.folder-mappings-tooltip-variants") }}
          </p>
          <p class="r-v2-mappings__tip-foot">
            {{ t("settings.folder-mappings-mutually-exclusive") }}
          </p>
        </div>
      </RTooltip>
    </div>

    <div class="r-v2-table-wrap">
      <table class="r-v2-table">
        <thead>
          <tr>
            <th>{{ t("settings.folder-name-header") }}</th>
            <th>{{ t("settings.romm-platform-header") }}</th>
            <th>{{ t("settings.type-header") }}</th>
            <th class="r-v2-table__col-actions" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredMappings" :key="row.fsSlug">
            <td class="r-v2-mappings__folder">{{ row.fsSlug }}</td>
            <td>
              <RMenu v-if="canEdit">
                <template #activator="{ props: menuProps }">
                  <button
                    v-bind="menuProps"
                    type="button"
                    class="r-v2-mappings__platform"
                  >
                    <PlatformIcon
                      v-if="row.slug"
                      :slug="row.slug"
                      :size="22"
                      class="r-v2-mappings__platform-icon"
                    />
                    <span v-if="row.slug">{{ row.displayName }}</span>
                    <span v-else class="r-v2-mappings__placeholder">—</span>
                    <RIcon icon="mdi-chevron-down" size="14" />
                  </button>
                </template>
                <RMenuPanel width="280px" max-height="320px">
                  <RMenuItem
                    v-for="platform in supportedPlatforms"
                    :key="platform.slug"
                    :label="platform.display_name"
                    @click="setPlatform(row, platform.slug)"
                  >
                    <template #icon>
                      <PlatformIcon :slug="platform.slug" :size="18" />
                    </template>
                  </RMenuItem>
                  <RMenuItem
                    v-if="row.slug && row.type !== 'auto'"
                    icon="mdi-delete"
                    variant="danger"
                    :label="t('common.delete')"
                    @click="setPlatform(row, undefined)"
                  />
                </RMenuPanel>
              </RMenu>
              <span v-else class="r-v2-mappings__platform">
                <PlatformIcon
                  v-if="row.slug"
                  :slug="row.slug"
                  :size="22"
                  class="r-v2-mappings__platform-icon"
                />
                <span v-if="row.slug">{{ row.displayName }}</span>
                <span v-else class="r-v2-mappings__placeholder">—</span>
              </span>
            </td>
            <td>
              <RMenu
                v-if="canEdit && row.slug && row.type !== null"
                location="bottom"
              >
                <template #activator="{ props: menuProps }">
                  <button
                    v-bind="menuProps"
                    type="button"
                    class="r-v2-mappings__type-pill"
                    :class="`r-v2-mappings__type-pill--${row.type}`"
                  >
                    <span>
                      {{
                        row.type === "auto"
                          ? t("settings.auto-detected")
                          : row.type === "alias"
                            ? t("settings.folder-alias")
                            : t("settings.platform-variant")
                      }}
                    </span>
                    <RIcon icon="mdi-chevron-down" size="12" />
                  </button>
                </template>
                <RMenuPanel width="200px">
                  <RMenuItem
                    :label="t('settings.folder-alias')"
                    icon="mdi-label-variant"
                    @click="setType(row, 'alias')"
                  />
                  <RMenuItem
                    :label="t('settings.platform-variant')"
                    icon="mdi-source-branch"
                    @click="setType(row, 'variant')"
                  />
                </RMenuPanel>
              </RMenu>
              <span
                v-else-if="row.type"
                class="r-v2-mappings__type-pill"
                :class="`r-v2-mappings__type-pill--${row.type}`"
              >
                {{
                  row.type === "auto"
                    ? t("settings.auto-detected")
                    : row.type === "alias"
                      ? t("settings.folder-alias")
                      : t("settings.platform-variant")
                }}
              </span>
            </td>
            <td class="r-v2-table__col-actions">
              <button
                v-if="canEdit && row.type !== 'auto' && row.slug"
                type="button"
                class="r-v2-icon-btn r-v2-icon-btn--danger"
                :aria-label="t('common.delete')"
                :title="t('common.delete')"
                @click="setPlatform(row, undefined)"
              >
                <RIcon icon="mdi-trash-can-outline" size="14" />
              </button>
            </td>
          </tr>
          <tr v-if="filteredMappings.length === 0">
            <td colspan="4" class="r-v2-mappings__empty">
              <RIcon icon="mdi-folder-search-outline" size="20" />
              <span>{{ t("common.search") }} — no folders found.</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <RBtn
      v-if="loading"
      variant="text"
      :loading="loading"
      class="r-v2-mappings__loading-row"
    >
      …
    </RBtn>
  </div>
</template>

<style scoped>
.r-v2-mappings {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.r-v2-mappings__toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.r-v2-mappings__toolbar > .r-v2-search {
  flex: 1;
}

.r-v2-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--r-color-surface);
  border: 1px solid var(--r-color-border);
  border-radius: 8px;
  color: var(--r-color-fg-muted);
}
.r-v2-search:focus-within {
  border-color: color-mix(
    in srgb,
    var(--r-color-brand-primary) 50%,
    transparent
  );
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
  padding: 10px 14px;
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

.r-v2-mappings__folder {
  font-weight: var(--r-font-weight-medium);
}

.r-v2-mappings__platform {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  color: var(--r-color-fg);
  font-size: 13px;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    border-color var(--r-motion-fast) var(--r-motion-ease-out);
}
.r-v2-mappings__platform:hover {
  background: var(--r-color-surface);
  border-color: var(--r-color-border);
}
.r-v2-mappings__platform-icon {
  flex-shrink: 0;
}
.r-v2-mappings__placeholder {
  color: var(--r-color-fg-faint);
}

.r-v2-mappings__type-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: var(--r-font-weight-semibold);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border: none;
  cursor: pointer;
}
button.r-v2-mappings__type-pill {
  cursor: pointer;
}
.r-v2-mappings__type-pill--alias {
  background: color-mix(in srgb, var(--r-color-brand-primary) 14%, transparent);
  color: var(--r-color-brand-primary);
}
.r-v2-mappings__type-pill--variant {
  background: color-mix(in srgb, var(--r-color-info) 14%, transparent);
  color: var(--r-color-info);
}
.r-v2-mappings__type-pill--auto {
  background: color-mix(
    in srgb,
    var(--r-color-status-base-success) 14%,
    transparent
  );
  color: var(--r-color-success);
}

.r-v2-mappings__empty {
  text-align: center;
  color: var(--r-color-fg-muted);
  padding: 24px 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.r-v2-mappings__tip {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  max-width: 320px;
}
.r-v2-mappings__tip-foot {
  margin: 0;
  color: var(--r-color-fg-muted);
}

.r-v2-mappings__loading-row {
  align-self: flex-start;
}
</style>
