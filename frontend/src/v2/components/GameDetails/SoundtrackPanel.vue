<script setup lang="ts">
import { RBtn, RDropzone, REmptyState, RSlider } from "@v2/lib";
import axios from "axios";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { RomOwnedMediaSchema } from "@/__generated__";
import romApi from "@/services/api/rom";
import storeRoms, { type DetailedRom } from "@/stores/roms";
import useSoundtrackPlayer, {
  type PlayerMeta,
  type PlayerTrack,
} from "@/stores/soundtrackPlayer";
import VolumeControl from "@/v2/components/Soundtrack/VolumeControl.vue";
import { useCan } from "@/v2/composables/useCan";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useSnackbar } from "@/v2/composables/useSnackbar";

const props = defineProps<{ rom: DetailedRom }>();
const { t } = useI18n();
const snackbar = useSnackbar();
const confirm = useConfirm();
const romsStore = storeRoms();
const player = useSoundtrackPlayer();
const {
  track: activeStoreTrack,
  isPlaying,
  currentTime,
  duration,
  hasPrevious,
  hasNext,
} = storeToRefs(player);
const scope = { kind: "rom", id: props.rom.id } as const;
const canManage = useCan("rom.edit", scope);
const canDelete = useCan("rom.delete", scope);
const uploading = ref(false);
const localBackgroundAudioUpdating = ref(false);
const ownedBackgroundAudioUpdating = ref(false);
const movingId = ref<number | null>(null);
const deletingId = ref<number | null>(null);
const uploadFailures = ref<string[]>([]);
const dropzone = ref<InstanceType<typeof RDropzone> | null>(null);
const acceptedAudioTypes = [
  "audio/mpeg",
  "audio/aac",
  "audio/flac",
  "audio/ogg",
  "audio/opus",
  "audio/mp4",
  "audio/wav",
];
const acceptedAudioExtensions = ".mp3,.aac,.flac,.ogg,.opus,.m4a,.wav";

const ownedTracks = computed(() =>
  (props.rom.owned_media ?? []).filter(
    (item) => item.role === "soundtrack" && item.state === "active",
  ),
);
function soundtrackPlacement(item: RomOwnedMediaSchema) {
  return item.placements?.find(
    (placement) => placement.surface === "soundtrack",
  );
}
const includedTracks = computed(() =>
  ownedTracks.value
    .filter((item) => soundtrackPlacement(item))
    .slice()
    .sort(
      (left, right) =>
        (soundtrackPlacement(left)?.position ?? 0) -
        (soundtrackPlacement(right)?.position ?? 0),
    ),
);
const availableTracks = computed(() =>
  ownedTracks.value.filter((item) => !soundtrackPlacement(item)),
);
const localTracks = computed(() =>
  props.rom.files.filter((file) => file.category === "soundtrack"),
);
const selectedLocalTrackIds = computed(
  () => new Set(props.rom.local_background_audio_file_ids ?? []),
);
const selectedOwnedTrackIds = computed(
  () => new Set(props.rom.owned_background_audio_media_ids ?? []),
);
const activeTrackId = computed(() =>
  activeStoreTrack.value?.romId === props.rom.id
    ? activeStoreTrack.value.mediaId
    : null,
);
const activeTrack = computed(() =>
  includedTracks.value.find((item) => item.id === activeTrackId.value),
);

function mediaContentUrl(mediaId: number) {
  return `/api/roms/${props.rom.id}/media/${mediaId}/content`;
}
function playerTracks(): PlayerTrack[] {
  return includedTracks.value.map((item) => ({
    romId: props.rom.id,
    mediaId: item.id,
    fileName: item.display_label,
    url: mediaContentUrl(item.id),
  }));
}
function playerMetas(): Record<number, PlayerMeta> {
  return Object.fromEntries(
    includedTracks.value.map((item) => [
      item.id,
      { title: item.display_label },
    ]),
  );
}
function syncPlaylist() {
  player.loadPlaylistForRom(props.rom.id, playerTracks(), playerMetas());
}
watch(includedTracks, () => {
  if (player.activePlaylistRomId === props.rom.id) syncPlaylist();
});
async function refreshCanonical() {
  await romsStore.refreshRom(props.rom.id);
}
function errorMessage(error: unknown) {
  return axios.isAxiosError(error) &&
    typeof error.response?.data?.detail === "string"
    ? error.response.data.detail
    : t("common.error");
}
async function handleConflict(error: unknown) {
  if (axios.isAxiosError(error) && error.response?.status === 409) {
    await refreshCanonical();
    snackbar.warning(t("rom.media-order-conflict"));
    return true;
  }
  return false;
}

async function uploadTracks(files: File[]) {
  if (!files.length || uploading.value) return;
  uploading.value = true;
  uploadFailures.value = [];
  try {
    let expectedVersion = props.rom.updated_at;
    let successful = 0;
    for (const file of files) {
      try {
        const response = await romApi.uploadOwnedMedia({
          romId: props.rom.id,
          role: "soundtrack",
          file,
          expectedVersion,
        });
        expectedVersion = response.data.updated_at;
        successful += 1;
      } catch {
        uploadFailures.value.push(file.name);
      }
    }
    if (successful) {
      await refreshCanonical();
      snackbar.success(t("rom.soundtrack-uploaded"));
    }
    if (uploadFailures.value.length)
      snackbar.error(t("rom.soundtrack-upload-error"));
  } finally {
    uploading.value = false;
  }
}
async function toggleIncluded(item: RomOwnedMediaSchema) {
  if (movingId.value !== null) return;
  movingId.value = item.id;
  try {
    if (soundtrackPlacement(item))
      await romApi.removeOwnedMediaPlacement({
        romId: props.rom.id,
        mediaId: item.id,
        surface: "soundtrack",
        expectedVersion: props.rom.updated_at,
      });
    else
      await romApi.setOwnedMediaPlacement({
        romId: props.rom.id,
        mediaId: item.id,
        surface: "soundtrack",
        expectedVersion: props.rom.updated_at,
      });
    await refreshCanonical();
  } catch (error) {
    if (!(await handleConflict(error))) snackbar.error(errorMessage(error));
  } finally {
    movingId.value = null;
  }
}
async function toggleLocalBackgroundAudio(fileId: number) {
  if (localBackgroundAudioUpdating.value) return;
  localBackgroundAudioUpdating.value = true;
  const nextFileIds = new Set(selectedLocalTrackIds.value);
  if (nextFileIds.has(fileId)) nextFileIds.delete(fileId);
  else nextFileIds.add(fileId);
  try {
    await romApi.replaceLocalBackgroundAudio({
      romId: props.rom.id,
      fileIds: [...nextFileIds],
      expectedVersion: props.rom.updated_at,
    });
    await refreshCanonical();
  } catch (error) {
    if (!(await handleConflict(error))) snackbar.error(errorMessage(error));
  } finally {
    localBackgroundAudioUpdating.value = false;
  }
}
async function toggleOwnedBackgroundAudio(mediaId: number) {
  if (ownedBackgroundAudioUpdating.value) return;
  ownedBackgroundAudioUpdating.value = true;
  const nextMediaIds = new Set(selectedOwnedTrackIds.value);
  if (nextMediaIds.has(mediaId)) nextMediaIds.delete(mediaId);
  else nextMediaIds.add(mediaId);
  try {
    await romApi.replaceOwnedBackgroundAudio({
      romId: props.rom.id,
      mediaIds: [...nextMediaIds],
      expectedVersion: props.rom.updated_at,
    });
    await refreshCanonical();
  } catch (error) {
    if (!(await handleConflict(error))) snackbar.error(errorMessage(error));
  } finally {
    ownedBackgroundAudioUpdating.value = false;
  }
}
async function moveTrack(index: number, direction: -1 | 1) {
  const nextIndex = index + direction;
  if (nextIndex < 0 || nextIndex >= includedTracks.value.length) return;
  const reordered = includedTracks.value.map((item) => item.id);
  [reordered[index], reordered[nextIndex]] = [
    reordered[nextIndex],
    reordered[index],
  ];
  movingId.value = includedTracks.value[index].id;
  try {
    await romApi.replaceOwnedMediaPlacements({
      romId: props.rom.id,
      surface: "soundtrack",
      mediaIds: reordered,
      expectedVersion: props.rom.updated_at,
    });
    await refreshCanonical();
  } catch (error) {
    if (!(await handleConflict(error))) snackbar.error(errorMessage(error));
  } finally {
    movingId.value = null;
  }
}
function selectTrack(item: RomOwnedMediaSchema) {
  syncPlaylist();
  const selected = playerTracks().find((track) => track.mediaId === item.id);
  if (selected) player.play(selected, playerMetas()[item.id] ?? {});
}
function retryActiveTrack() {
  if (activeTrack.value) selectTrack(activeTrack.value);
}
async function deleteTrack(item: RomOwnedMediaSchema) {
  if (activeTrackId.value === item.id) player.stop();
  if (
    !(await confirm({
      title: t("rom.delete-soundtrack-title"),
      body: item.display_label,
      confirmText: t("common.delete"),
      tone: "danger",
    }))
  )
    return;
  deletingId.value = item.id;
  try {
    await romApi.deleteOwnedMedia({
      romId: props.rom.id,
      mediaId: item.id,
      expectedVersion: props.rom.updated_at,
    });
    await refreshCanonical();
    snackbar.success(t("rom.soundtrack-deleted"));
  } catch (error) {
    if (!(await handleConflict(error))) snackbar.error(errorMessage(error));
  } finally {
    deletingId.value = null;
  }
}
function downloadTrack(item: RomOwnedMediaSchema) {
  const anchor = document.createElement("a");
  anchor.href = mediaContentUrl(item.id);
  anchor.download = item.display_label;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
}
function fmt(seconds: number) {
  const safe = Number.isFinite(seconds) && seconds >= 0 ? seconds : 0;
  return `${Math.floor(safe / 60)}:${Math.floor(safe % 60)
    .toString()
    .padStart(2, "0")}`;
}
</script>

<template>
  <section class="r-v2-stp" aria-labelledby="soundtrack-heading">
    <header class="r-v2-stp__header">
      <div>
        <h3 id="soundtrack-heading">{{ t("rom.soundtrack") }}</h3>
        <p>{{ t("rom.soundtrack-owned-hint") }}</p>
      </div>
      <RBtn
        v-if="canManage"
        :loading="uploading"
        prepend-icon="mdi-upload"
        :aria-label="t('rom.upload-soundtrack')"
        @click="dropzone?.open()"
      >
        {{ t("rom.upload-soundtrack") }}
      </RBtn>
    </header>
    <RDropzone
      v-if="canManage"
      ref="dropzone"
      :disabled="uploading"
      :accept="acceptedAudioExtensions"
      :data-types="acceptedAudioTypes"
      multiple
      :title="t('rom.upload-soundtrack')"
      :hint="t('rom.soundtrack-upload-hint')"
      :input-label="t('rom.upload-soundtrack')"
      @files="uploadTracks"
    />
    <ul v-if="uploadFailures.length" class="r-v2-stp__failures">
      <li v-for="name in uploadFailures" :key="name">{{ name }}</li>
    </ul>
    <section
      v-if="localTracks.length"
      aria-labelledby="local-soundtrack-heading"
    >
      <h4 id="local-soundtrack-heading">{{ t("rom.soundtrack-local") }}</h4>
      <ul class="r-v2-stp__list">
        <li v-for="file in localTracks" :key="file.id">
          <span>{{ file.file_name }}</span>
          <div>
            <span v-if="selectedLocalTrackIds.has(file.id)">
              {{ t("rom.background-music") }}
            </span>
            <RBtn
              v-if="canManage"
              :loading="localBackgroundAudioUpdating"
              :disabled="localBackgroundAudioUpdating"
              :aria-label="`${selectedLocalTrackIds.has(file.id) ? t('rom.remove-as-background') : t('rom.add-as-background')}: ${file.file_name}`"
              @click="toggleLocalBackgroundAudio(file.id)"
            >
              {{
                selectedLocalTrackIds.has(file.id)
                  ? t("rom.remove-as-background")
                  : t("rom.add-as-background")
              }}
            </RBtn>
          </div>
        </li>
      </ul>
    </section>
    <div v-if="player.hasError" class="r-v2-stp__decode-error" role="alert">
      <span>{{ t("rom.soundtrack-playback-error") }}</span
      ><RBtn variant="text" size="small" @click="retryActiveTrack">{{
        t("common.retry")
      }}</RBtn>
    </div>
    <div class="r-v2-stp__transport" :aria-label="t('rom.soundtrack-player')">
      <RBtn
        icon="mdi-skip-previous"
        variant="text"
        :disabled="!hasPrevious"
        :aria-label="t('rom.soundtrack-previous')"
        @click="player.previous()"
      />
      <RBtn
        :icon="isPlaying ? 'mdi-pause-circle' : 'mdi-play-circle'"
        variant="text"
        :disabled="!activeTrack"
        :aria-label="
          isPlaying ? t('rom.soundtrack-pause') : t('rom.soundtrack-play')
        "
        @click="player.togglePlayPause()"
      />
      <RBtn
        icon="mdi-skip-next"
        variant="text"
        :disabled="!hasNext"
        :aria-label="t('rom.soundtrack-next')"
        @click="player.next()"
      />
      <span>{{ fmt(currentTime) }}</span
      ><RSlider
        :model-value="currentTime"
        :max="duration"
        :disabled="!activeTrack"
        :aria-label="t('rom.soundtrack-seek')"
        @update:model-value="(value: number) => player.seek(value)"
      /><span>{{ fmt(duration) }}</span
      ><VolumeControl size="small" />
    </div>
    <section aria-labelledby="included-soundtrack-heading">
      <h4 id="included-soundtrack-heading">
        {{ t("rom.included-soundtrack") }}
      </h4>
      <REmptyState
        v-if="includedTracks.length === 0"
        icon="mdi-music-note-off-outline"
        :title="t('rom.soundtrack-empty')"
      />
      <ol v-else class="r-v2-stp__list">
        <li v-for="(item, index) in includedTracks" :key="item.id">
          <span>{{ index + 1 }}. {{ item.display_label }}</span>
          <div>
            <span v-if="selectedOwnedTrackIds.has(item.id)">
              {{ t("rom.background-music") }}
            </span>
            <RBtn
              v-if="canManage"
              :loading="ownedBackgroundAudioUpdating"
              :disabled="ownedBackgroundAudioUpdating"
              :aria-label="`${selectedOwnedTrackIds.has(item.id) ? t('rom.remove-as-background') : t('rom.add-as-background')}: ${item.display_label}`"
              @click="toggleOwnedBackgroundAudio(item.id)"
            >
              {{
                selectedOwnedTrackIds.has(item.id)
                  ? t("rom.remove-as-background")
                  : t("rom.add-as-background")
              }}
            </RBtn>
            <RBtn
              icon="mdi-play"
              variant="text"
              :aria-label="t('rom.play-track', { title: item.display_label })"
              @click="selectTrack(item)"
            />
            <RBtn
              v-if="canManage"
              icon="mdi-arrow-up"
              variant="text"
              :disabled="index === 0 || movingId !== null"
              :aria-label="`${t('rom.move-up')}: ${item.display_label}`"
              :tooltip="t('rom.move-up')"
              @click="moveTrack(index, -1)"
            />
            <RBtn
              v-if="canManage"
              icon="mdi-arrow-down"
              variant="text"
              :disabled="
                index === includedTracks.length - 1 || movingId !== null
              "
              :aria-label="`${t('rom.move-down')}: ${item.display_label}`"
              :tooltip="t('rom.move-down')"
              @click="moveTrack(index, 1)"
            />
            <RBtn
              v-if="canManage"
              variant="text"
              :disabled="movingId !== null"
              :aria-label="`${t('rom.remove-from-soundtrack')}: ${item.display_label}`"
              @click="toggleIncluded(item)"
              >{{ t("rom.remove-from-soundtrack") }}</RBtn
            >
            <RBtn
              icon="mdi-download-outline"
              variant="text"
              :aria-label="`${t('common.download')}: ${item.display_label}`"
              @click="downloadTrack(item)"
            />
            <RBtn
              v-if="canDelete"
              icon="mdi-delete-outline"
              variant="text"
              :loading="deletingId === item.id"
              :disabled="deletingId !== null"
              :aria-label="`${t('common.delete')}: ${item.display_label}`"
              @click="deleteTrack(item)"
            />
          </div>
        </li>
      </ol>
    </section>
    <section aria-labelledby="available-uploads-heading">
      <h4 id="available-uploads-heading">{{ t("rom.available-uploads") }}</h4>
      <ul class="r-v2-stp__list">
        <li v-for="item in availableTracks" :key="item.id">
          <span>{{ item.display_label }}</span>
          <div>
            <span v-if="selectedOwnedTrackIds.has(item.id)">
              {{ t("rom.background-music") }}
            </span>
            <RBtn
              v-if="canManage"
              :loading="ownedBackgroundAudioUpdating"
              :disabled="ownedBackgroundAudioUpdating"
              :aria-label="`${selectedOwnedTrackIds.has(item.id) ? t('rom.remove-as-background') : t('rom.add-as-background')}: ${item.display_label}`"
              @click="toggleOwnedBackgroundAudio(item.id)"
            >
              {{
                selectedOwnedTrackIds.has(item.id)
                  ? t("rom.remove-as-background")
                  : t("rom.add-as-background")
              }}
            </RBtn>
            <RBtn
              v-if="canManage"
              :disabled="movingId !== null"
              :aria-label="`${t('rom.include-in-soundtrack')}: ${item.display_label}`"
              @click="toggleIncluded(item)"
              >{{ t("rom.include-in-soundtrack") }}</RBtn
            >
            <RBtn
              icon="mdi-download-outline"
              variant="text"
              :aria-label="`${t('common.download')}: ${item.display_label}`"
              @click="downloadTrack(item)"
            />
            <RBtn
              v-if="canDelete"
              icon="mdi-delete-outline"
              variant="text"
              :loading="deletingId === item.id"
              :disabled="deletingId !== null"
              :aria-label="`${t('common.delete')}: ${item.display_label}`"
              @click="deleteTrack(item)"
            />
          </div>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.r-v2-stp {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
  padding: var(--r-space-5);
}
.r-v2-stp__header,
.r-v2-stp__transport,
.r-v2-stp__list > li {
  display: flex;
  align-items: center;
  gap: var(--r-space-2);
}
.r-v2-stp__header,
.r-v2-stp__list > li {
  justify-content: space-between;
}
.r-v2-stp__header h3,
.r-v2-stp__header p,
.r-v2-stp h4 {
  margin: 0;
}
.r-v2-stp__header p {
  color: var(--r-color-fg-muted);
}
.r-v2-stp__transport,
.r-v2-stp__list > li,
.r-v2-stp__decode-error {
  padding: var(--r-space-2);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}
.r-v2-stp__transport > :nth-child(5) {
  flex: 1;
}
.r-v2-stp__list,
.r-v2-stp__failures {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.r-v2-stp__list > li > div {
  display: flex;
  gap: var(--r-space-1);
}
.r-v2-stp__decode-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--r-color-danger);
}
</style>
