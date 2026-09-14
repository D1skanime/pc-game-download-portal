<script setup lang="ts">
import { RBtn, RCarousel, RDropzone, REmptyState, RSelect } from "@v2/lib";
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import type {
  PcComponentOwnedMediaSchema,
  PcComponentSchema,
  RomComponentOwnedMediaRole,
} from "@/__generated__";
import { romApi as api } from "@/services/api/rom";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });

const props = defineProps<{ romId: number; component: PcComponentSchema }>();
const emit = defineEmits<{ (event: "refresh"): void }>();
const { t } = useI18n();
const snackbar = useSnackbar();
const confirm = useConfirm();
const media = ref<PcComponentOwnedMediaSchema[]>([]);
const loading = ref(true);
const uploading = ref(false);
const role = ref<RomComponentOwnedMediaRole>("artwork");
const roles: RomComponentOwnedMediaRole[] = [
  "cover",
  "background",
  "gallery",
  "screenshot",
  "artwork",
];
const componentVersion = computed(() => props.component.updated_at ?? null);
const mediaUrls = computed(() =>
  media.value.map((item) => mediaContentUrl(item.id)),
);
const lightboxIndex = ref(0);
const lightboxOpen = ref(false);

const endpoint = `/roms/${props.romId}/pc-components/${props.component.id}/media`;

function mediaContentUrl(mediaId: number) {
  return `${endpoint}/${mediaId}/content`;
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
  if (!file || !componentVersion.value) return;
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

async function remove(mediaId: number) {
  if (!componentVersion.value) return;
  if (!(await confirm({ title: t("common.delete"), tone: "danger" }))) return;
  try {
    await api.delete(`${endpoint}/${mediaId}`, {
      params: { expected_version: componentVersion.value },
    });
    await load();
    emit("refresh");
    snackbar.success(t("common.delete"));
  } catch (error) {
    console.error(error);
    snackbar.error(t("common.error"));
  }
}

onMounted(load);
</script>

<template>
  <section class="pc-dlc-media" aria-labelledby="pc-dlc-media-heading">
    <h2 id="pc-dlc-media-heading" class="pc-dlc-media__heading">
      {{ t("rom.media") }}
    </h2>
    <RSelect v-model="role" :items="roles" :label="t('rom.media')" />
    <RDropzone
      :disabled="uploading || !componentVersion"
      accept="image/jpeg,image/png,image/webp"
      :title="t('common.upload')"
      :hint="t('common.dropzone-hint')"
      :input-label="t('common.upload')"
      @files="upload"
    />
    <p v-if="loading">{{ t("common.loading") }}</p>
    <REmptyState
      v-else-if="media.length === 0"
      :title="t('rom.artwork-empty')"
    />
    <ul v-else class="pc-dlc-media__list">
      <li
        v-for="(item, index) in media"
        :key="item.id"
        class="pc-dlc-media__item"
      >
        <button
          type="button"
          class="pc-dlc-media__preview"
          :aria-label="`${item.role} ${index + 1}`"
          @click="openMedia(index)"
        >
          <img :src="mediaContentUrl(item.id)" :alt="item.role" />
        </button>
        <div class="pc-dlc-media__details">
          <strong>{{ item.role }}</strong>
          <span>{{ item.mime_type }}</span>
        </div>
        <RBtn
          icon="mdi-delete-outline"
          :aria-label="t('common.delete')"
          @click="remove(item.id)"
        />
      </li>
    </ul>
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
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}
.pc-dlc-media__heading {
  margin: 0;
  color: var(--r-color-fg);
  font-size: var(--r-font-size-2xl);
}
.pc-dlc-media__list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--r-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.pc-dlc-media__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--r-space-3);
  padding: var(--r-space-3);
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}
.pc-dlc-media__preview {
  width: 100%;
  padding: 0;
  overflow: hidden;
  background: transparent;
  border: 0;
  border-radius: var(--r-radius-md);
  cursor: pointer;
}
.pc-dlc-media__preview img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: var(--r-color-cover-placeholder);
}
.pc-dlc-media__details {
  align-self: stretch;
  min-width: 0;
}
.pc-dlc-media__details strong,
.pc-dlc-media__details span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pc-dlc-media__details span {
  color: var(--r-color-fg-muted);
  font-size: var(--r-font-size-sm);
}
</style>
