<script setup lang="ts">
import {
  RAlert,
  RBtn,
  RCard,
  RDivider,
  REmptyState,
  RList,
  RListItem,
  RSkeletonBlock,
  RSteps,
} from "@v2/lib";
import axios from "axios";
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import { ROUTES } from "@/plugins/router";
import storageApi from "@/services/api/storage";
import storePlatforms from "@/stores/platforms";
import { useCan } from "@/v2/composables/useCan";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useSnackbar } from "@/v2/composables/useSnackbar";

interface Draft {
  rootId: number | null;
  relativePath: string;
  testedKey: string | null;
}

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const platformsStore = storePlatforms();
const snackbar = useSnackbar();
const confirm = useConfirm();
const canAdmin = useCan("app.admin");

const roots = ref<Awaited<ReturnType<typeof storageApi.getRoots>>["data"]>([]);
const mapping = ref<
  Awaited<ReturnType<typeof storageApi.getMapping>>["data"] | null
>(null);
const preview = ref<
  Awaited<ReturnType<typeof storageApi.getPreview>>["data"] | null
>(null);
const stalePreview = ref<
  Awaited<ReturnType<typeof storageApi.getPreview>>["data"] | null
>(null);
const entries = ref<
  Awaited<ReturnType<typeof storageApi.browseRoot>>["data"]["entries"]
>([]);
const loading = ref(true);
const browsing = ref(false);
const saving = ref(false);
const testing = ref(false);
const refreshingPreview = ref(false);
const removing = ref(false);
const errorState = ref<"forbidden" | "unreachable" | "generic" | null>(null);
const editing = ref(false);
const step = ref(1);
const currentPath = ref("");
const draft = ref<Draft>({ rootId: null, relativePath: "", testedKey: null });

const platformId = computed(() => Number(route.params.platformId));
const platform = computed(() =>
  platformsStore.allPlatforms.find(
    (candidate) => candidate.id === platformId.value,
  ),
);
const selectedRoot = computed(() =>
  roots.value.find((root) => root.id === draft.value.rootId),
);
const testKey = computed(() =>
  draft.value.rootId === null
    ? null
    : `${draft.value.rootId}:${draft.value.relativePath}`,
);
const tested = computed(() => draft.value.testedKey === testKey.value);
const breadcrumbs = computed(() =>
  currentPath.value ? currentPath.value.split("/").filter(Boolean) : [],
);
const previewLabel = computed(() => {
  if (!preview.value)
    return t("storage.preview-missing", "No preview has been started.");
  if (preview.value.stale)
    return t(
      "storage.preview-stale",
      "Preview is stale. Start a current preview.",
    );
  if (preview.value.state === "pending")
    return t(
      "storage.preview-pending",
      "Preview is queued. Mapping remains active.",
    );
  const observed =
    preview.value.observed_files + preview.value.observed_directories;
  if (preview.value.state === "partial") {
    return t(
      "storage.preview-partial",
      `At least ${observed} entries were observed.`,
    );
  }
  return t("storage.preview-complete", `${observed} entries were observed.`);
});

function safeMessage(error: unknown, fallback: string) {
  if (!axios.isAxiosError(error)) return fallback;
  if (error.response?.status === 403)
    return t(
      "storage.forbidden",
      "Storage administration requires administrator access.",
    );
  const detail = error.response?.data?.detail;
  if (typeof detail === "object" && detail && "message" in detail) {
    return String(detail.message);
  }
  return fallback;
}

function isMissingMappingError(error: unknown) {
  if (!axios.isAxiosError(error)) return false;
  return (
    error.response?.status === 409 &&
    error.response?.data?.detail?.code === "platform_mapping_missing"
  );
}

async function ensurePlatforms() {
  if (platformsStore.allPlatforms.length === 0)
    await platformsStore.fetchPlatforms();
}

async function loadPreview(mappingId: number) {
  try {
    preview.value = (await storageApi.getPreview(mappingId)).data;
  } catch (error) {
    if (!axios.isAxiosError(error) || error.response?.status !== 404) {
      snackbar.error(
        safeMessage(
          error,
          t("storage.preview-error", "Could not load preview."),
        ),
      );
    }
  }
}

async function loadMapping() {
  mapping.value = null;
  preview.value = null;
  try {
    mapping.value = (await storageApi.getMapping(platformId.value)).data;
    await loadPreview(mapping.value.id);
  } catch (error) {
    if (
      (axios.isAxiosError(error) && error.response?.status === 404) ||
      isMissingMappingError(error)
    )
      return;
    if (axios.isAxiosError(error) && error.response?.status === 403)
      errorState.value = "forbidden";
    else errorState.value = "generic";
  }
}

async function loadRoots() {
  try {
    roots.value = (await storageApi.getRoots()).data;
  } catch (error) {
    errorState.value =
      axios.isAxiosError(error) && error.response?.status === 403
        ? "forbidden"
        : "unreachable";
  }
}

async function reload() {
  loading.value = true;
  errorState.value = null;
  await Promise.all([ensurePlatforms(), loadRoots(), loadMapping()]);
  loading.value = false;
}

async function browse(path = "") {
  if (draft.value.rootId === null) return;
  browsing.value = true;
  try {
    const { data } = await storageApi.browseRoot(draft.value.rootId, path);
    currentPath.value = path;
    entries.value = data.entries;
  } catch (error) {
    errorState.value = "unreachable";
    snackbar.error(
      safeMessage(
        error,
        t("storage.browse-error", "This folder could not be opened."),
      ),
    );
  } finally {
    browsing.value = false;
  }
}

function beginEdit() {
  draft.value = {
    rootId:
      mapping.value?.storage_root_id ??
      roots.value.find((root) => root.active)?.id ??
      null,
    relativePath: mapping.value?.relative_path ?? "",
    testedKey: null,
  };
  currentPath.value = draft.value.relativePath;
  editing.value = true;
  step.value = 1;
  if (draft.value.rootId !== null) void browse(currentPath.value);
}

function chooseRoot(rootId: number) {
  draft.value.rootId = rootId;
  draft.value.relativePath = "";
  draft.value.testedKey = null;
  currentPath.value = "";
  step.value = 2;
  void browse();
}

function selectCurrentFolder() {
  draft.value.relativePath = currentPath.value;
  draft.value.testedKey = null;
  step.value = 3;
}

async function testDraft() {
  if (draft.value.rootId === null) return;
  testing.value = true;
  try {
    await storageApi.testMapping({
      platform_id: platformId.value,
      storage_root_id: draft.value.rootId,
      relative_path: draft.value.relativePath,
    });
    draft.value.testedKey = testKey.value;
    step.value = 4;
    snackbar.success(
      t("storage.test-success", "Storage selection passed the safety test."),
    );
  } catch (error) {
    snackbar.error(
      safeMessage(
        error,
        t(
          "storage.test-failed",
          "The selected folder did not pass the safety test.",
        ),
      ),
    );
  } finally {
    testing.value = false;
  }
}

async function saveDraft() {
  if (draft.value.rootId === null || !tested.value || saving.value) return;
  saving.value = true;
  try {
    const saved = mapping.value
      ? await storageApi.updateMapping(mapping.value.id, {
          storage_root_id: draft.value.rootId,
          relative_path: draft.value.relativePath,
          expected_version: mapping.value.version,
        })
      : await storageApi.createMapping({
          platform_id: platformId.value,
          storage_root_id: draft.value.rootId,
          relative_path: draft.value.relativePath,
        });
    mapping.value = saved.data;
    stalePreview.value = preview.value;
    editing.value = false;
    await refreshPreview();
    snackbar.success(t("storage.saved", "Storage mapping saved."));
  } catch (error) {
    snackbar.error(
      safeMessage(
        error,
        t(
          "storage.save-failed",
          "The mapping changed or could not be saved. Review and retry.",
        ),
      ),
    );
  } finally {
    saving.value = false;
  }
}

async function refreshPreview() {
  if (!mapping.value || refreshingPreview.value) return;
  refreshingPreview.value = true;
  try {
    stalePreview.value = preview.value;
    preview.value = (await storageApi.refreshPreview(mapping.value.id)).data;
  } catch (error) {
    snackbar.error(
      safeMessage(
        error,
        t(
          "storage.preview-error",
          "The mapping was saved, but its preview could not be started.",
        ),
      ),
    );
  } finally {
    refreshingPreview.value = false;
  }
}

async function removeCurrentMapping() {
  if (!mapping.value || removing.value) return;
  try {
    const consequences = await storageApi.removalConsequences(
      mapping.value.id,
      mapping.value.version,
    );
    const accepted = await confirm({
      title: t("storage.remove-title", "Remove storage mapping"),
      body: t(
        "storage.remove-body",
        "This removes only RomM's mapping. Original files remain unchanged.",
      ),
      confirmText: t("storage.remove", "Remove mapping"),
      tone: "danger",
    });
    if (!accepted) return;
    removing.value = true;
    await storageApi.removeMapping(
      mapping.value.id,
      mapping.value.version,
      consequences.data.retained_visible_unreachable_catalog_count,
    );
    mapping.value = null;
    preview.value = null;
    snackbar.success(
      t(
        "storage.removed",
        "Storage mapping removed. Original files were not changed.",
      ),
    );
  } catch (error) {
    snackbar.error(
      safeMessage(
        error,
        t(
          "storage.remove-failed",
          "The mapping could not be removed. Reload and review it.",
        ),
      ),
    );
  } finally {
    removing.value = false;
  }
}

function cancelEdit() {
  editing.value = false;
  draft.value = { rootId: null, relativePath: "", testedKey: null };
}

function goBack() {
  router.push({
    name: ROUTES.PLATFORM,
    params: { platform: platformId.value },
  });
}

watch(platformId, () => void reload());
onMounted(() => void reload());
</script>

<template>
  <main class="r-storage" :aria-busy="loading">
    <header class="r-storage__head">
      <div>
        <p class="r-storage__eyebrow">
          {{ t("storage.administration", "Storage administration") }}
        </p>
        <h1>
          {{
            platform?.display_name ?? t("storage.platform", "Platform storage")
          }}
        </h1>
        <p>
          {{
            t(
              "storage.heading-hint",
              "Map a safe, read-only storage folder for this platform.",
            )
          }}
        </p>
      </div>
      <RBtn variant="text" prepend-icon="mdi-arrow-left" @click="goBack">
        {{ t("common.back", "Back") }}
      </RBtn>
    </header>

    <RAlert v-if="!canAdmin || errorState === 'forbidden'" type="error">
      <template #title>{{
        t("storage.forbidden-title", "Administrator access required")
      }}</template>
      {{
        t(
          "storage.forbidden",
          "Storage administration requires administrator access.",
        )
      }}
    </RAlert>

    <template v-else-if="loading">
      <RSkeletonBlock height="132" />
      <RSkeletonBlock height="260" class="r-storage__skeleton" />
    </template>

    <RAlert v-else-if="errorState === 'unreachable'" type="error">
      <template #title>{{
        t("storage.unreachable-title", "Storage root is unavailable")
      }}</template>
      {{
        t(
          "storage.unreachable",
          "The storage root could not be reached. Existing mappings remain unchanged.",
        )
      }}
      <template #append
        ><RBtn variant="outlined" @click="reload">{{
          t("storage.check-again", "Check again")
        }}</RBtn></template
      >
    </RAlert>

    <RAlert v-else-if="errorState === 'generic'" type="error">
      <template #title>{{
        t("common.error", "Something went wrong")
      }}</template>
      {{
        t(
          "storage.reload-hint",
          "Reload the mapping and review it before continuing.",
        )
      }}
      <template #append
        ><RBtn variant="outlined" @click="reload">{{
          t("common.reload", "Reload")
        }}</RBtn></template
      >
    </RAlert>

    <template v-else>
      <RCard class="r-storage__summary">
        <div class="r-storage__summary-title">
          <div>
            <p class="r-storage__label">
              {{ t("storage.active-mapping", "Active mapping") }}
            </p>
            <h2 v-if="mapping">
              {{
                roots.find((root) => root.id === mapping!.storage_root_id)
                  ?.name ?? t("storage.root", "Storage root")
              }}
            </h2>
            <h2 v-else>
              {{ t("storage.unmapped", "No storage folder mapped") }}
            </h2>
            <p v-if="mapping" class="r-storage__path">
              {{
                mapping.relative_path || t("storage.root-folder", "Root folder")
              }}
            </p>
          </div>
          <RBtn
            variant="flat"
            color="primary"
            :disabled="roots.length === 0"
            @click="beginEdit"
          >
            {{
              mapping
                ? t("storage.change", "Change mapping")
                : t("storage.map", "Map storage")
            }}
          </RBtn>
        </div>
        <RDivider class="r-storage__divider" />
        <div class="r-storage__preview">
          <p class="r-storage__label">{{ t("storage.preview", "Preview") }}</p>
          <p>{{ previewLabel }}</p>
          <p
            v-if="preview?.state === 'pending' && stalePreview"
            class="r-storage__muted"
          >
            {{
              t(
                "storage.preview-old",
                "The previous preview remains visible while a new one is running.",
              )
            }}
          </p>
          <RBtn
            v-if="mapping"
            variant="text"
            :loading="refreshingPreview"
            @click="refreshPreview"
            >{{ t("storage.refresh-preview", "Refresh preview") }}</RBtn
          >
        </div>
        <div v-if="mapping" class="r-storage__danger">
          <RBtn
            variant="text"
            color="danger"
            :loading="removing"
            @click="removeCurrentMapping"
            >{{ t("storage.remove", "Remove mapping") }}</RBtn
          >
          <span>{{
            t("storage.files-unchanged", "Original files remain unchanged.")
          }}</span>
        </div>
      </RCard>

      <RCard v-if="editing" class="r-storage__workspace">
        <RSteps
          :current="step"
          :steps="[
            { label: t('storage.root', 'Root') },
            { label: t('storage.folder', 'Folder') },
            { label: t('storage.test', 'Test') },
            { label: t('common.save', 'Save') },
          ]"
        />
        <section v-if="step === 1" class="r-storage__section">
          <h2>{{ t("storage.choose-root", "Choose a storage root") }}</h2>
          <RList>
            <RListItem
              v-for="root in roots"
              :key="root.id"
              :title="root.name"
              :subtitle="
                root.active
                  ? t('storage.root-active', 'Active')
                  : t('storage.root-inactive', 'Inactive')
              "
              :prepend-icon="
                root.health.reachable
                  ? 'mdi-folder-outline'
                  : 'mdi-folder-alert-outline'
              "
              :disabled="!root.active || !root.health.reachable"
              append-icon="mdi-chevron-right"
              @click="chooseRoot(root.id)"
            />
          </RList>
        </section>

        <section v-else-if="step === 2" class="r-storage__section">
          <div class="r-storage__section-head">
            <div>
              <h2>{{ t("storage.choose-folder", "Choose a folder") }}</h2>
              <p>
                {{ selectedRoot?.name }}
                <span v-for="crumb in breadcrumbs" :key="crumb">
                  / {{ crumb }}</span
                >
              </p>
            </div>
            <RBtn variant="outlined" @click="selectCurrentFolder">{{
              t("storage.select-folder", "Select this folder")
            }}</RBtn>
          </div>
          <RAlert type="info">{{
            t(
              "storage.recursive-scope",
              "The selected folder and all of its descendants are included. Sibling folders are excluded.",
            )
          }}</RAlert>
          <RSkeletonBlock v-if="browsing" height="180" />
          <REmptyState
            v-else-if="entries.length === 0"
            icon="mdi-folder-open-outline"
            :title="t('storage.empty-folder', 'No child folders here')"
            :description="
              t(
                'storage.empty-folder-hint',
                'This open folder can still be selected.',
              )
            "
          />
          <RList v-else>
            <RListItem
              v-for="entry in entries"
              :key="entry.relative_path"
              :title="entry.name"
              :prepend-icon="
                entry.navigable
                  ? 'mdi-folder-outline'
                  : 'mdi-folder-lock-outline'
              "
              :append-icon="entry.navigable ? 'mdi-chevron-right' : undefined"
              :disabled="!entry.navigable"
              @click="browse(entry.relative_path)"
            />
          </RList>
          <div class="r-storage__actions">
            <RBtn
              variant="text"
              :disabled="!currentPath"
              @click="browse(currentPath.split('/').slice(0, -1).join('/'))"
              >{{ t("storage.up", "Up one folder") }}</RBtn
            ><RBtn variant="text" @click="step = 1">{{
              t("storage.change-root", "Choose another root")
            }}</RBtn>
          </div>
        </section>

        <section v-else class="r-storage__section">
          <h2>{{ t("storage.review", "Review and test") }}</h2>
          <p>
            {{ selectedRoot?.name }} /
            {{ draft.relativePath || t("storage.root-folder", "Root folder") }}
          </p>
          <RAlert type="info">{{
            t(
              "storage.review-hint",
              "Run the safety test before saving. Changing the root or folder requires a new test.",
            )
          }}</RAlert>
          <div class="r-storage__actions">
            <RBtn variant="outlined" :loading="testing" @click="testDraft">{{
              t("storage.test", "Run safety test")
            }}</RBtn
            ><RBtn
              variant="flat"
              color="primary"
              :disabled="!tested"
              :loading="saving"
              @click="saveDraft"
              >{{ t("common.save", "Save mapping") }}</RBtn
            >
          </div>
        </section>
        <div class="r-storage__footer">
          <RBtn variant="text" @click="cancelEdit">{{
            t("common.cancel", "Cancel")
          }}</RBtn>
        </div>
      </RCard>
    </template>
  </main>
</template>

<style scoped>
.r-storage {
  max-width: 1040px;
  margin: 0 auto;
  padding: 32px var(--r-row-pad) 72px;
  display: grid;
  gap: 20px;
}
.r-storage__head,
.r-storage__summary-title,
.r-storage__section-head,
.r-storage__actions,
.r-storage__danger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--r-space-3);
}
.r-storage__head {
  align-items: flex-start;
}
.r-storage__head h1,
.r-storage h2,
.r-storage p {
  margin: 0;
}
.r-storage__head h1 {
  font-size: var(--r-font-size-2xl);
}
.r-storage__head p,
.r-storage__muted,
.r-storage__path,
.r-storage__danger {
  color: var(--r-color-fg-muted);
}
.r-storage__eyebrow,
.r-storage__label {
  font-size: var(--r-font-size-xs);
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--r-color-fg-muted);
}
.r-storage__summary,
.r-storage__workspace {
  padding: 24px;
}
.r-storage__divider {
  margin: 20px 0;
}
.r-storage__preview,
.r-storage__section {
  display: grid;
  gap: 12px;
}
.r-storage__danger {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--r-color-border);
  justify-content: flex-start;
}
.r-storage__workspace {
  display: grid;
  gap: 24px;
}
.r-storage__footer {
  display: flex;
  justify-content: flex-end;
}
.r-storage__skeleton {
  margin-top: 20px;
}
html[data-bp~="xs"] .r-storage {
  padding-top: 20px;
}
html[data-bp~="xs"] .r-storage__head,
html[data-bp~="xs"] .r-storage__summary-title,
html[data-bp~="xs"] .r-storage__section-head {
  align-items: stretch;
  flex-direction: column;
}
</style>
