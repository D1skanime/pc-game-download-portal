<script setup lang="ts">
import {
  RBtn,
  RCarousel,
  RChip,
  RDropzone,
  REmptyState,
  RSkeletonBlock,
  RTooltip,
} from "@v2/lib";
import axios from "axios";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import type {
  RomOwnedMediaSchema,
  RomOwnedMediaSurface,
} from "@/__generated__";
import romApi from "@/services/api/rom";
import storeRoms, { type DetailedRom } from "@/stores/roms";
import { useCan } from "@/v2/composables/useCan";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useSnackbar } from "@/v2/composables/useSnackbar";

const props = defineProps<{ rom: DetailedRom }>();
const { t } = useI18n();
const snackbar = useSnackbar();
const confirm = useConfirm();
const romsStore = storeRoms();
const scope = { kind: "rom", id: props.rom.id } as const;
const canManage = useCan("rom.edit", scope);
const canRefresh = useCan("rom.refresh", scope);
const canDelete = useCan("rom.delete", scope);
const uploadDropzone = ref<InstanceType<typeof RDropzone> | null>(null);
const refreshing = ref(false);
const mutatingId = ref<number | null>(null);
const uploading = ref(false);
const uploadProgress = ref<Record<string, number>>({});
const lightboxIndex = ref(0);
const lightboxOpen = ref(false);

const ownedArtwork = computed(() =>
  (props.rom.owned_media ?? []).filter(
    (item) => item.role === "artwork" && item.state === "active",
  ),
);
const backgroundPlacements = computed(() =>
  (props.rom.owned_media_placements ?? [])
    .filter((placement) => placement.surface === "background")
    .toSorted((a, b) => a.position - b.position),
);
const backgrounds = computed(() =>
  backgroundPlacements.value.flatMap((placement) => {
    const candidate = props.rom.owned_media?.find(
      (item) => item.id === placement.media_id && item.state === "active",
    );
    return candidate ? [{ candidate, placement }] : [];
  }),
);
const artworkUrls = computed(() =>
  ownedArtwork.value.map((item) => mediaContentUrl(item.id)),
);

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
function backgroundPosition(item: RomOwnedMediaSchema) {
  return item.placements?.find(
    (placement) => placement.surface === "background",
  )?.position;
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
    snackbar.warning(t("rom.owned-media-order-conflict"));
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
async function moveBackground(index: number, direction: -1 | 1) {
  const nextIndex = index + direction;
  if (nextIndex < 0 || nextIndex >= backgrounds.value.length) return;
  const ids = backgrounds.value.map(({ candidate }) => candidate.id);
  [ids[index], ids[nextIndex]] = [ids[nextIndex], ids[index]];
  mutatingId.value = backgrounds.value[index].candidate.id;
  try {
    await romApi.replaceOwnedMediaPlacements({
      romId: props.rom.id,
      surface: "background",
      mediaIds: ids,
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
async function refreshProviderArtwork() {
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
async function uploadArtwork(files: File[]) {
  if (uploading.value || files.length === 0) return;
  uploading.value = true;
  uploadProgress.value = Object.fromEntries(
    files.map((file) => [file.name, 0]),
  );
  const results = await Promise.allSettled(
    files.map((file) =>
      romApi.uploadOwnedMedia({
        romId: props.rom.id,
        role: "artwork",
        file,
        expectedVersion: props.rom.updated_at,
        onUploadProgress: (event) => {
          uploadProgress.value[file.name] = event.total
            ? Math.round((event.loaded / event.total) * 100)
            : 0;
        },
      }),
    ),
  );
  try {
    if (results.some((result) => result.status === "fulfilled")) {
      await refreshCanonical();
      snackbar.success(t("common.uploaded-n", results.length));
    }
    if (results.some((result) => result.status === "rejected"))
      snackbar.error(t("rom.owned-media-upload-failed"));
  } finally {
    uploading.value = false;
    uploadProgress.value = {};
  }
}
async function deleteArtwork(item: RomOwnedMediaSchema) {
  if (
    !(await confirm({
      title: t("rom.delete-artwork-title"),
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
    snackbar.success(t("common.delete"));
  } catch (error) {
    if (!(await recoverFromConflict(error)))
      snackbar.error(errorMessage(error));
  } finally {
    mutatingId.value = null;
  }
}
</script>

<template>
  <div class="r-v2-art">
    <section class="r-v2-art__section" aria-labelledby="artwork-heading">
      <header class="r-v2-art__head">
        <div>
          <h3 id="artwork-heading" class="r-v2-art__title">
            {{ t("rom.artwork-and-backgrounds") }}
          </h3>
          <p class="r-v2-art__subtitle">{{ t("rom.owned-media-hint") }}</p>
        </div>
        <div v-if="canManage || canRefresh" class="r-v2-art__header-actions">
          <RTooltip :text="t('common.refresh')"
            ><RBtn
              v-if="canRefresh"
              icon="mdi-refresh"
              :loading="refreshing"
              :disabled="uploading"
              :aria-label="t('common.refresh')"
              @click="refreshProviderArtwork"
          /></RTooltip>
          <RBtn
            v-if="canManage"
            prepend-icon="mdi-upload"
            :loading="uploading"
            @click="uploadDropzone?.open()"
            >{{ t("rom.upload-artwork") }}</RBtn
          >
        </div>
      </header>
      <RDropzone
        ref="uploadDropzone"
        class="r-v2-art__upload"
        :title="t('rom.upload-artwork')"
        :hint="t('rom.owned-media-image-hint')"
        :input-label="t('rom.upload-artwork')"
        accept="image/*"
        multiple
        :disabled="uploading || !canManage"
        @files="uploadArtwork"
      />
      <p
        v-for="(progress, name) in uploadProgress"
        :key="name"
        class="r-v2-art__progress"
      >
        {{ name }} {{ progress }}%
      </p>
    </section>
    <section class="r-v2-art__section" aria-labelledby="backgrounds-heading">
      <h3 id="backgrounds-heading" class="r-v2-art__title">
        {{ t("rom.backgrounds") }}
      </h3>
      <div v-if="refreshing && backgrounds.length === 0" class="r-v2-art__rows">
        <RSkeletonBlock v-for="index in 2" :key="index" height="64" />
      </div>
      <REmptyState
        v-else-if="backgrounds.length === 0"
        icon="mdi-image-off-outline"
        :title="t('rom.backgrounds-empty')"
      />
      <ol v-else class="r-v2-art__rows">
        <li
          v-for="({ candidate }, index) in backgrounds"
          :key="candidate.id"
          class="r-v2-art__row"
        >
          <img
            class="r-v2-art__row-preview"
            :src="mediaContentUrl(candidate.id)"
            :alt="candidate.display_label"
          /><span class="r-v2-art__ordinal">{{ index + 1 }}</span
          ><span class="r-v2-art__row-label">{{ candidate.display_label }}</span
          ><span class="r-v2-art__origin">{{ candidate.origin }}</span>
          <RTooltip
            :text="
              index === 0
                ? t('rom.background-move-unavailable')
                : t('common.move-up')
            "
            ><RBtn
              icon="mdi-arrow-up"
              :disabled="index === 0 || mutatingId !== null"
              :aria-label="t('common.move-up')"
              @click="moveBackground(index, -1)"
          /></RTooltip>
          <RTooltip
            :text="
              index === backgrounds.length - 1
                ? t('rom.background-move-unavailable')
                : t('common.move-down')
            "
            ><RBtn
              icon="mdi-arrow-down"
              :disabled="
                index === backgrounds.length - 1 || mutatingId !== null
              "
              :aria-label="t('common.move-down')"
              @click="moveBackground(index, 1)"
          /></RTooltip>
        </li>
      </ol>
    </section>
    <section
      class="r-v2-art__section"
      aria-labelledby="artwork-candidates-heading"
    >
      <h3 id="artwork-candidates-heading" class="r-v2-art__title">
        {{ t("rom.artwork") }}
      </h3>
      <REmptyState
        v-if="ownedArtwork.length === 0"
        icon="mdi-image-off-outline"
        :title="t('rom.artwork-empty')"
      />
      <ul v-else class="r-v2-art__grid">
        <li
          v-for="(item, index) in ownedArtwork"
          :key="item.id"
          class="r-v2-art__cell"
        >
          <button
            type="button"
            class="r-v2-art__preview"
            :aria-label="t('rom.artwork-open', { name: item.display_label })"
            @click="
              lightboxIndex = index;
              lightboxOpen = true;
            "
          >
            <img
              class="r-v2-art__media"
              :src="mediaContentUrl(item.id)"
              :alt="item.display_label"
              loading="lazy"
            />
          </button>
          <p class="r-v2-art__origin">{{ item.origin }}</p>
          <RChip v-if="backgroundPosition(item) != null" size="small">
            {{ t("rom.backgrounds") }} #{{ backgroundPosition(item)! + 1 }}
          </RChip>
          <div v-if="canManage" class="r-v2-art__actions">
            <RBtn
              size="small"
              :loading="mutatingId === item.id"
              :aria-label="
                hasPlacement(item, 'overview')
                  ? t('rom.remove-from-overview')
                  : t('rom.add-to-overview')
              "
              @click="togglePlacement(item, 'overview')"
              >{{
                hasPlacement(item, "overview")
                  ? t("rom.remove-from-overview")
                  : t("rom.add-to-overview")
              }}</RBtn
            ><RBtn
              size="small"
              :loading="mutatingId === item.id"
              :aria-label="
                hasPlacement(item, 'background')
                  ? t('rom.remove-as-background')
                  : t('rom.add-as-background')
              "
              @click="togglePlacement(item, 'background')"
              >{{
                hasPlacement(item, "background")
                  ? t("rom.remove-as-background")
                  : t("rom.add-as-background")
              }}</RBtn
            ><RTooltip
              v-if="item.origin === 'upload' && canDelete"
              :text="t('common.delete')"
              ><RBtn
                icon="mdi-delete-outline"
                :loading="mutatingId === item.id"
                :aria-label="t('common.delete')"
                @click="deleteArtwork(item)"
            /></RTooltip>
          </div>
        </li>
      </ul>
    </section>
  </div>
  <RCarousel
    v-if="lightboxOpen"
    v-model="lightboxIndex"
    :items="artworkUrls"
    fullscreen
    show-thumbnails
    :aria-label="t('rom.artwork')"
    @close="lightboxOpen = false"
    ><template #default="{ item, index }"
      ><img :src="item" :alt="ownedArtwork[index]?.display_label" /></template
    ><template #thumbnail="{ item, index }"
      ><img :src="item" :alt="ownedArtwork[index]?.display_label" /></template
  ></RCarousel>
</template>

<style scoped>
.r-v2-art {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}
.r-v2-art__section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.r-v2-art__head,
.r-v2-art__header-actions,
.r-v2-art__actions,
.r-v2-art__row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.r-v2-art__head {
  justify-content: space-between;
}
.r-v2-art__header-actions {
  flex-wrap: wrap;
}
.r-v2-art__title {
  margin: 0;
  color: var(--r-color-fg);
  font-size: 18px;
}
.r-v2-art__subtitle,
.r-v2-art__origin,
.r-v2-art__progress {
  margin: 0;
  color: var(--r-color-fg-muted);
  font-size: 13px;
}
.r-v2-art__upload {
  min-height: 96px;
}
.r-v2-art__rows,
.r-v2-art__grid {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.r-v2-art__row {
  min-height: 64px;
  padding: 8px;
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  background: var(--r-color-bg-elevated);
}
.r-v2-art__row-preview {
  width: 56px;
  height: 48px;
  object-fit: contain;
  border-radius: var(--r-radius-sm);
  background: var(--r-color-cover-placeholder);
}
.r-v2-art__ordinal {
  margin: 0;
  color: var(--r-color-fg-muted);
  font-variant-numeric: tabular-nums;
}
.r-v2-art__row-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.r-v2-art__grid {
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}
.r-v2-art__cell {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.r-v2-art__preview {
  padding: 0;
  border: 0;
  border-radius: var(--r-radius-md);
  background: transparent;
  cursor: pointer;
}
.r-v2-art__media {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  background: var(--r-color-cover-placeholder);
  object-fit: contain;
}
@media (max-width: 599px) {
  .r-v2-art__head {
    align-items: flex-start;
    flex-direction: column;
  }
  .r-v2-art__row {
    flex-wrap: wrap;
  }
  .r-v2-art__row-label {
    min-width: calc(100% - 72px);
  }
}
</style>
