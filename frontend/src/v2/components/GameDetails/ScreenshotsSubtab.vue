<script setup lang="ts">
import {
  RBtn,
  RCarousel,
  RDropzone,
  REmptyState,
  RSkeletonBlock,
  RTooltip,
} from "@v2/lib";
import axios from "axios";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import type {
  RomOwnedMediaSchema,
  RomOwnedMediaSurface,
} from "@/__generated__";
import romApi from "@/services/api/rom";
import screenshotApi from "@/services/api/screenshot";
import storeAuth from "@/stores/auth";
import storeRoms, { type DetailedRom } from "@/stores/roms";
import storeUpload from "@/stores/upload";
import ScreenshotsTab, {
  type ScreenshotItem,
} from "@/v2/components/GameDetails/ScreenshotsTab.vue";
import { useCan } from "@/v2/composables/useCan";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useSnackbar } from "@/v2/composables/useSnackbar";

const props = defineProps<{ rom: DetailedRom }>();
const { t } = useI18n();
const snackbar = useSnackbar();
const confirm = useConfirm();
const romsStore = storeRoms();
const uploadStore = storeUpload();
const { user } = storeToRefs(storeAuth());
const scope = { kind: "rom", id: props.rom.id } as const;
const canManage = useCan("rom.edit", scope);
const canRefresh = useCan("rom.refresh", scope);
const canDelete = useCan("rom.delete", scope);
const providerScreenshots = computed(() =>
  (props.rom.owned_media ?? []).filter(
    (item) =>
      item.origin === "provider" &&
      item.role === "screenshot" &&
      item.state === "active",
  ),
);
const providerUrls = computed(() =>
  providerScreenshots.value.map((item) => mediaContentUrl(item.id)),
);
const providerLightboxOpen = ref(false);
const providerLightboxIndex = ref(0);
const refreshing = ref(false);
const mutatingId = ref<number | null>(null);
const allUserScreenshots = computed(() => props.rom.all_user_screenshots ?? []);
const myScreenshots = computed<ScreenshotItem[]>(() =>
  allUserScreenshots.value
    .filter((item) => user.value?.id != null && item.user_id === user.value.id)
    .map((item) => ({
      id: item.id,
      url: item.download_path,
      isOwn: true,
      isPublic: Boolean(item.is_public),
    })),
);
const communityScreenshots = computed<ScreenshotItem[]>(() =>
  allUserScreenshots.value
    .filter((item) => user.value?.id == null || item.user_id !== user.value.id)
    .map((item) => ({
      id: item.id,
      url: item.download_path,
      isOwn: false,
      isPublic: true,
      username: item.username,
      userId: item.user_id,
      userAvatarPath: item.user_avatar_path,
      userUpdatedAt: item.user_updated_at,
    })),
);
const myDz = ref<InstanceType<typeof RDropzone> | null>(null);
const togglingId = ref<number | null>(null);

function mediaContentUrl(mediaId: number) {
  return `/api/roms/${props.rom.id}/media/${mediaId}/content`;
}
function hasPlacement(
  item: RomOwnedMediaSchema,
  surface: RomOwnedMediaSurface,
) {
  return (
    item.placements?.some((placement) => placement.surface === surface) ?? false
  );
}
function placementPosition(
  item: RomOwnedMediaSchema,
  surface: RomOwnedMediaSurface,
) {
  return item.placements?.find((placement) => placement.surface === surface)
    ?.position;
}
function errorMessage(error: unknown) {
  if (axios.isAxiosError(error))
    return typeof error.response?.data?.detail === "string"
      ? error.response.data.detail
      : error.message;
  return error instanceof Error ? error.message : String(error);
}
async function refreshCanonical() {
  await romsStore.refreshRom(props.rom.id);
}
async function recoverFromConflict(error: unknown) {
  if (axios.isAxiosError(error) && error.response?.status === 409) {
    await refreshCanonical();
    snackbar.warning(t("common.error"));
    return true;
  }
  return false;
}
async function togglePlacement(
  item: RomOwnedMediaSchema,
  surface: RomOwnedMediaSurface,
) {
  if (mutatingId.value !== null) return;
  mutatingId.value = item.id;
  try {
    if (hasPlacement(item, surface))
      await romApi.removeOwnedMediaPlacement({
        romId: props.rom.id,
        mediaId: item.id,
        surface,
        expectedVersion: props.rom.updated_at,
      });
    else
      await romApi.setOwnedMediaPlacement({
        romId: props.rom.id,
        mediaId: item.id,
        surface,
        expectedVersion: props.rom.updated_at,
      });
    await refreshCanonical();
  } catch (error) {
    if (!(await recoverFromConflict(error)))
      snackbar.error(errorMessage(error));
  } finally {
    mutatingId.value = null;
  }
}
async function refreshProviderScreenshots() {
  if (refreshing.value) return;
  refreshing.value = true;
  try {
    await romApi.refreshOwnedMedia({
      romId: props.rom.id,
      expectedVersion: props.rom.updated_at,
    });
    await refreshCanonical();
    snackbar.success(t("common.refresh"));
  } catch (error) {
    if (!(await recoverFromConflict(error)))
      snackbar.error(errorMessage(error));
  } finally {
    refreshing.value = false;
  }
}
async function deleteProviderScreenshot(item: RomOwnedMediaSchema) {
  if (
    !(await confirm({
      title: t("rom.delete-screenshot-title"),
      body: item.display_label,
      confirmText: t("common.delete"),
      tone: "danger",
    }))
  )
    return;
  mutatingId.value = item.id;
  try {
    await romApi.deleteOwnedMedia({
      romId: props.rom.id,
      mediaId: item.id,
      expectedVersion: props.rom.updated_at,
    });
    await refreshCanonical();
    snackbar.success(t("rom.screenshot-removed"));
  } catch (error) {
    if (!(await recoverFromConflict(error)))
      snackbar.error(errorMessage(error));
  } finally {
    mutatingId.value = null;
  }
}
async function refreshRom() {
  try {
    await refreshCanonical();
  } catch (error) {
    console.error(error);
  }
}
function reportUpload(responses: PromiseSettledResult<unknown>[]) {
  const successful = responses.filter(
    (item) => item.status === "fulfilled",
  ).length;
  if (successful === responses.length) uploadStore.reset();
  successful
    ? snackbar.success(
        t("rom.screenshots-uploaded-n", successful, {
          named: { n: successful },
        }),
      )
    : snackbar.warning(t("rom.no-screenshots-uploaded"));
}
async function handleMyFiles(files: File[]) {
  if (!files.length) return;
  const responses = await screenshotApi.uploadGalleryScreenshots({
    romId: props.rom.id,
    filesToUpload: files,
  });
  reportUpload(responses);
  if (responses.some((item) => item.status === "fulfilled")) await refreshRom();
}
async function deleteMyScreenshot(id: number) {
  if (
    !(await confirm({
      title: t("rom.delete-screenshot-title"),
      body: t("rom.delete-screenshot-body"),
      confirmText: t("common.delete"),
      tone: "danger",
    }))
  )
    return;
  try {
    await screenshotApi.deleteScreenshot({ id });
    await refreshRom();
    snackbar.success(t("rom.screenshot-removed"));
  } catch (error) {
    snackbar.error(errorMessage(error));
  }
}
async function toggleVisibility(id: number, isPublic: boolean) {
  if (togglingId.value !== null) return;
  togglingId.value = id;
  try {
    await screenshotApi.setScreenshotVisibility({ id, isPublic });
    await refreshRom();
  } catch (error) {
    snackbar.error(errorMessage(error));
  } finally {
    togglingId.value = null;
  }
}
</script>

<template>
  <div class="r-v2-shots">
    <section
      class="r-v2-shots__section"
      aria-labelledby="provider-screenshots-heading"
    >
      <header class="r-v2-shots__head">
        <div>
          <h3 id="provider-screenshots-heading" class="r-v2-shots__title">
            {{ t("rom.screenshots") }}
          </h3>
          <p class="r-v2-shots__subtitle">
            {{ t("rom.screenshots-section-rom-desc") }}
          </p>
        </div>
        <RTooltip :text="t('common.refresh')"
          ><RBtn
            v-if="canRefresh"
            icon="mdi-refresh"
            :loading="refreshing"
            :aria-label="t('common.refresh')"
            @click="refreshProviderScreenshots"
        /></RTooltip>
      </header>
      <div
        v-if="refreshing && providerScreenshots.length === 0"
        class="r-v2-shots__grid"
      >
        <RSkeletonBlock v-for="index in 3" :key="index" height="180" />
      </div>
      <REmptyState
        v-else-if="providerScreenshots.length === 0"
        :title="t('rom.screenshots-empty')"
      />
      <ul v-else class="r-v2-shots__grid">
        <li
          v-for="(item, index) in providerScreenshots"
          :key="item.id"
          class="r-v2-shots__candidate"
        >
          <button
            type="button"
            class="r-v2-shots__preview"
            :aria-label="item.display_label"
            @click="
              providerLightboxIndex = index;
              providerLightboxOpen = true;
            "
          >
            <img :src="mediaContentUrl(item.id)" :alt="item.display_label" />
          </button>
          <p class="r-v2-shots__origin">
            {{ item.provider ?? t("rom.screenshots") }}
          </p>
          <p v-if="hasPlacement(item, 'overview')" class="r-v2-shots__ordinal">
            {{ placementPosition(item, "overview") }}
          </p>
          <div v-if="canManage" class="r-v2-shots__actions">
            <RBtn
              size="small"
              :loading="mutatingId === item.id"
              :aria-label="
                hasPlacement(item, 'overview')
                  ? t('common.remove')
                  : t('common.add')
              "
              @click.stop="togglePlacement(item, 'overview')"
              >{{
                hasPlacement(item, "overview")
                  ? t("common.remove")
                  : t("common.add")
              }}</RBtn
            ><RBtn
              size="small"
              variant="outlined"
              :loading="mutatingId === item.id"
              :aria-label="
                hasPlacement(item, 'background')
                  ? t('common.remove')
                  : t('common.add')
              "
              @click.stop="togglePlacement(item, 'background')"
              >{{
                hasPlacement(item, "background")
                  ? t("common.remove")
                  : t("common.add")
              }}</RBtn
            ><RTooltip :text="t('common.delete')"
              ><RBtn
                v-if="canDelete"
                icon="mdi-delete-outline"
                :loading="mutatingId === item.id"
                :aria-label="t('common.delete')"
                @click.stop="deleteProviderScreenshot(item)"
            /></RTooltip>
          </div>
        </li>
      </ul>
    </section>
    <section class="r-v2-shots__section">
      <header class="r-v2-shots__head">
        <h3 class="r-v2-shots__title">
          {{ t("rom.screenshots-section-mine") }}
        </h3>
        <RBtn
          v-if="myScreenshots.length"
          variant="outlined"
          size="small"
          @click="myDz?.open()"
          >{{ t("common.upload") }}</RBtn
        >
      </header>
      <RDropzone
        v-if="!myScreenshots.length"
        :title="t('rom.screenshots-empty')"
        :hint="t('common.dropzone-hint')"
        :active-title="t('common.dropzone-drag-over')"
        :input-label="t('rom.upload-screenshots')"
        accept="image/*"
        multiple
        @files="handleMyFiles"
      /><RDropzone
        v-else
        ref="myDz"
        overlay
        :input-label="t('rom.upload-screenshots')"
        accept="image/*"
        multiple
        @files="handleMyFiles"
        ><ScreenshotsTab
          :screenshots="myScreenshots"
          deletable
          togglable
          :toggling-id="togglingId"
          @delete="deleteMyScreenshot"
          @toggle-visibility="toggleVisibility"
      /></RDropzone>
    </section>
    <section v-if="communityScreenshots.length" class="r-v2-shots__section">
      <h3 class="r-v2-shots__title">
        {{ t("rom.screenshots-section-community") }}
      </h3>
      <ScreenshotsTab :screenshots="communityScreenshots" />
    </section>
  </div>
  <RCarousel
    v-if="providerLightboxOpen"
    v-model="providerLightboxIndex"
    :items="providerUrls"
    fullscreen
    show-thumbnails
    :aria-label="t('rom.screenshots')"
    @close="providerLightboxOpen = false"
    ><template #default="{ item, index }"
      ><img
        :src="item"
        :alt="providerScreenshots[index]?.display_label" /></template
    ><template #thumbnail="{ item, index }"
      ><img
        :src="item"
        :alt="providerScreenshots[index]?.display_label" /></template
  ></RCarousel>
</template>

<style scoped>
.r-v2-shots {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--r-space-6);
  min-height: 0;
  overflow-y: auto;
}
.r-v2-shots__section {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}
.r-v2-shots__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--r-space-4);
}
.r-v2-shots__title {
  margin: 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-lg);
  font-weight: var(--r-font-weight-semibold);
}
.r-v2-shots__subtitle,
.r-v2-shots__origin,
.r-v2-shots__ordinal {
  margin: 0;
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-sm);
}
.r-v2-shots__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--r-space-4);
  margin: 0;
  padding: 0;
  list-style: none;
}
.r-v2-shots__candidate {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  padding: var(--r-space-4);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  background: var(--r-color-bg-elevated);
}
.r-v2-shots__preview {
  width: 100%;
  padding: 0;
  overflow: hidden;
  border: 0;
  border-radius: var(--r-radius-md);
  background: transparent;
  cursor: pointer;
}
.r-v2-shots__preview img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: var(--r-color-cover-placeholder);
}
.r-v2-shots__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--r-space-2);
}
</style>
