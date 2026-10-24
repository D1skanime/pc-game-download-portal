<script setup lang="ts">
import {
  RBtn,
  RCarousel,
  RDropzone,
  REmptyState,
  RIcon,
  RSelect,
} from "@v2/lib";
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import type {
  PcComponentOwnedMediaSchema,
  PcComponentSchema,
  RomComponentOwnedMediaRole,
} from "@/__generated__";
import { useCan } from "@/v2/composables/useCan";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useResponsiveColumns } from "@/v2/composables/useResponsiveColumns";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import { useWrapGridNav } from "@/v2/composables/useWrapGridNav";
import { romApi as api } from "@/v2/data/adapters/legacy/services/api/rom";

defineOptions({ inheritAttrs: false });

const props = defineProps<{ romId: number; component: PcComponentSchema }>();
const emit = defineEmits<{ (event: "refresh"): void }>();
const { t } = useI18n();
const snackbar = useSnackbar();
const confirm = useConfirm();
const canEdit = useCan("rom.edit", { kind: "rom", id: props.romId });
const media = ref<PcComponentOwnedMediaSchema[]>([]);
const loading = ref(true);
const uploading = ref(false);
const placing = ref(false);
const role = ref<RomComponentOwnedMediaRole>("screenshot");
const roles: RomComponentOwnedMediaRole[] = [
  "cover",
  "gallery",
  "screenshot",
  "artwork",
];
const roleItems = computed(() =>
  roles.map((value) => ({
    title: t(`rom.pc-media-role-${value}`),
    value,
  })),
);
const componentVersion = computed(() => props.component.updated_at ?? null);
const filteredMedia = computed(() =>
  media.value.filter((item) => item.role === role.value),
);
const mediaUrls = computed(() =>
  filteredMedia.value.map((item) => mediaContentUrl(item.id)),
);
const gallery = ref<HTMLElement | null>(null);
const root = ref<HTMLElement | null>(null);
const dropzone = ref<InstanceType<typeof RDropzone> | null>(null);
const { columns } = useResponsiveColumns(gallery, { cardWidth: 200, gap: 12 });
useWrapGridNav(root, { cellSelector: "button:not([disabled])" });
const lightboxIndex = ref(0);
const lightboxOpen = ref(false);

const endpoint = `/roms/${props.romId}/pc-components/${props.component.id}/media`;

function mediaContentUrl(mediaId: number) {
  return `/api${endpoint}/${mediaId}/content`;
}

function mediaRoleLabel(item: PcComponentOwnedMediaSchema) {
  return t(`rom.pc-media-role-${item.role}`);
}

function mediaSourceLabel(item: PcComponentOwnedMediaSchema) {
  if (item.origin === "provider" && item.provider) return item.provider;
  return item.origin === "provider"
    ? t("rom.pc-media-source-provider")
    : t("rom.pc-media-source-uploaded");
}

function openMedia(index: number) {
  lightboxIndex.value = index;
  lightboxOpen.value = true;
}

function closeLightbox() {
  lightboxOpen.value = false;
}

async function load() {
  loading.value = true;
  try {
    media.value = (await api.get<PcComponentOwnedMediaSchema[]>(endpoint)).data;
  } catch (error) {
    console.error(error);
    snackbar.error(t("common.error"));
  } finally {
    loading.value = false;
  }
}

async function upload(files: File[]) {
  const file = files[0];
  if (!file || !componentVersion.value || !canEdit.value || uploading.value)
    return;
  uploading.value = true;
  try {
    const body = new FormData();
    body.append("media", file);
    body.append("role", role.value);
    body.append("expected_version", componentVersion.value);
    await api.post(endpoint, body);
    await load();
    emit("refresh");
    snackbar.success(t("common.upload"));
  } catch (error) {
    console.error(error);
    snackbar.error(t("common.error"));
  } finally {
    uploading.value = false;
  }
}

function placementPosition(item: PcComponentOwnedMediaSchema) {
  const placement = (item.placements ?? []).find(
    (entry) => entry.position >= 0,
  );
  return placement ? placement.position + 1 : undefined;
}

function hasPlacement(item: PcComponentOwnedMediaSchema) {
  return (item.placements ?? []).some((placement) => placement.position >= 0);
}

async function togglePlacement(item: PcComponentOwnedMediaSchema) {
  if (!componentVersion.value || !canEdit.value || placing.value) return;
  placing.value = true;
  try {
    if (hasPlacement(item)) {
      await api.delete(`${endpoint}/${item.id}/placement`, {
        params: { expected_version: componentVersion.value },
      });
    } else {
      await api.post(`${endpoint}/${item.id}/placement`, {
        expected_version: componentVersion.value,
      });
    }
    await load();
    emit("refresh");
  } catch (error) {
    console.error(error);
    snackbar.error(t("common.error"));
  } finally {
    placing.value = false;
  }
}

async function remove(mediaId: number) {
  if (!componentVersion.value) return;
  if (!(await confirm({ title: t("common.delete"), tone: "danger" }))) return;
  try {
    await api.delete(`${endpoint}/${mediaId}`, {
      params: { expected_version: componentVersion.value },
    });
    await load();
    emit("refresh");
    snackbar.success(t("rom.pc-media-deleted"));
  } catch (error) {
    console.error(error);
    snackbar.error(t("common.error"));
  }
}

onMounted(load);
</script>

<template>
  <section
    ref="root"
    class="pc-dlc-media d-flex flex-column ga-4"
    aria-labelledby="pc-dlc-media-heading"
  >
    <h2 id="pc-dlc-media-heading" class="pc-dlc-media__heading">
      {{ t("rom.media") }}
    </h2>
    <RSelect
      v-model="role"
      :items="roleItems"
      item-title="title"
      item-value="value"
      :label="t('rom.media')"
    />
    <RDropzone
      ref="dropzone"
      overlay
      :disabled="uploading || !componentVersion || !canEdit"
      accept="image/jpeg,image/png,image/webp"
      :input-label="t('common.upload')"
      :release-label="t('common.dropzone-drag-over')"
      @files="upload"
    >
      <header class="za-media-upload d-flex flex-wrap align-center ga-3 pa-4">
        <RBtn
          v-if="canEdit"
          class="za-media-upload__button pa-1"
          variant="text"
          :loading="uploading"
          :disabled="uploading || placing || !componentVersion"
          :aria-label="t('common.upload')"
          @click="dropzone?.open()"
        >
          <template #prepend>
            <RIcon icon="mdi-cloud-upload-outline" size="30" color="primary" />
          </template>
          {{ t("common.upload") }}
        </RBtn>
        <p class="ma-0 za-media-upload__hint flex-1-1">
          {{ t("common.dropzone-hint") }}
        </p>
      </header>
      <p v-if="loading">{{ t("common.loading") }}</p>
      <REmptyState
        v-else-if="filteredMedia.length === 0"
        :title="t('rom.artwork-empty')"
      />
      <ul
        v-else
        ref="gallery"
        class="pc-dlc-media__list ga-3 ma-0 pa-0 pt-4"
        :style="{ '--za-shot-columns': columns }"
      >
        <li v-for="(item, index) in filteredMedia" :key="item.id">
          <article class="za-shot">
            <button
              type="button"
              class="za-shot__preview"
              :aria-label="`${mediaRoleLabel(item)} ${index + 1}`"
              @click="openMedia(index)"
            >
              <img
                :src="mediaContentUrl(item.id)"
                :alt="mediaRoleLabel(item)"
              />
            </button>
            <div class="za-shot__body d-flex flex-column">
              <span class="za-shot__source">{{ mediaRoleLabel(item) }}</span>
              <span class="za-shot__source" :title="mediaSourceLabel(item)">{{
                mediaSourceLabel(item)
              }}</span>
              <span
                v-if="hasPlacement(item)"
                class="za-shot__badge za-shot__badge--overview"
              >
                {{
                  t("rom.screenshots-overview-position", {
                    position: placementPosition(item),
                  })
                }}
              </span>
              <div
                v-if="canEdit"
                class="za-shot__actions d-flex flex-wrap ga-1"
              >
                <RBtn
                  size="small"
                  class="za-shot__action"
                  :class="{ 'za-shot__action--selected': hasPlacement(item) }"
                  variant="translucent"
                  border
                  color="var(--r-color-brand-primary)"
                  :disabled="!componentVersion || placing"
                  :loading="placing"
                  :aria-pressed="hasPlacement(item)"
                  :aria-label="
                    hasPlacement(item)
                      ? t('rom.remove-from-overview')
                      : t('rom.add-to-overview')
                  "
                  :tooltip="
                    hasPlacement(item)
                      ? t('rom.remove-from-overview')
                      : t('rom.add-to-overview')
                  "
                  @click="togglePlacement(item)"
                >
                  <span class="za-shot__action-content">
                    <span class="za-shot__identity">
                      <RIcon icon="mdi-crown-outline" size="18" />
                      <RIcon
                        v-if="hasPlacement(item)"
                        class="za-shot__check"
                        icon="mdi-check"
                        size="10"
                        aria-hidden="true"
                      />
                    </span>
                    <span>{{ t("rom.screenshots-action-overview") }}</span>
                  </span>
                </RBtn>
                <RBtn
                  size="small"
                  class="za-shot__action za-shot__action--danger"
                  variant="outlined"
                  color="var(--r-color-danger)"
                  :disabled="!componentVersion || placing"
                  :aria-label="t('common.delete')"
                  :tooltip="t('common.delete')"
                  @click="remove(item.id)"
                >
                  <span class="za-shot__action-content">
                    <RIcon icon="mdi-delete-outline" size="18" />
                    <span>{{ t("common.delete") }}</span>
                  </span>
                </RBtn>
              </div>
            </div>
          </article>
        </li>
      </ul>
    </RDropzone>
    <RCarousel
      v-if="lightboxOpen"
      v-model="lightboxIndex"
      :items="mediaUrls"
      fullscreen
      show-thumbnails
      :aria-label="t('rom.media')"
      @close="closeLightbox"
    >
      <template #default="{ item, index }">
        <img :src="item" :alt="`${t('rom.media')} ${index + 1}`" />
      </template>
      <template #thumbnail="{ item, index }">
        <img :src="item" :alt="`${t('rom.media')} ${index + 1}`" />
      </template>
    </RCarousel>
  </section>
</template>

<style scoped>
.pc-dlc-media {
  min-width: 0;
}
.pc-dlc-media__heading {
  margin: 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-2xl);
}
.pc-dlc-media__list {
  display: grid;
  grid-template-columns: repeat(var(--za-shot-columns, 1), minmax(0, 1fr));
  list-style: none;
}
.pc-dlc-media__list > li {
  min-width: 0;
}
</style>
<style scoped src="./mediaManagementCard.css" />
<style scoped src="./mediaManagementUpload.css" />
