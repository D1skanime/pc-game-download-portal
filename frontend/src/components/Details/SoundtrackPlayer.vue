<script setup lang="ts">
// jsmediatags's package.json `browser` field points to a missing file; import the
// shipped browser bundle directly. Types come from the standard package.
// @ts-expect-error: no declaration file for the dist sub-path.
import jsmediatags from "jsmediatags/dist/jsmediatags.min.js";
import type { PictureType, TagType, jsmediatagsError } from "jsmediatags/types";
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  watch,
} from "vue";
import { useI18n } from "vue-i18n";
import type { DetailedRom } from "@/stores/roms";
import { formatBytes } from "@/utils";

const props = defineProps<{ rom: DetailedRom }>();
const emit = defineEmits<{
  (e: "upload-tracks"): void;
  (e: "delete-track", fileId: number): void;
}>();
const { t } = useI18n();

const AUDIO_EXTS = new Set([
  "mp3",
  "ogg",
  "oga",
  "opus",
  "m4a",
  "aac",
  "wav",
  "flac",
]);
const COVER_EXTS = new Set(["png", "jpg", "jpeg", "webp", "gif"]);

interface TrackMeta {
  title?: string;
  artist?: string;
  album?: string;
  year?: string;
  genre?: string;
  track?: string;
  disc?: string;
  pictureUrl?: string;
}

function getExt(name: string): string {
  return name.split(".").pop()?.toLowerCase() ?? "";
}

function fileUrl(fileId: number, fileName: string): string {
  return `/api/roms/${fileId}/files/content/${encodeURIComponent(fileName)}`;
}

const tracks = computed(() =>
  props.rom.files
    .filter(
      (f) => f.category === "soundtrack" && AUDIO_EXTS.has(getExt(f.file_name)),
    )
    .slice()
    .sort((a, b) => a.file_name.localeCompare(b.file_name)),
);

const folderCoverUrl = computed(() => {
  const cover = props.rom.files
    .filter(
      (f) => f.category === "soundtrack" && COVER_EXTS.has(getExt(f.file_name)),
    )
    .sort((a, b) => a.file_name.localeCompare(b.file_name))[0];
  return cover ? fileUrl(cover.id, cover.file_name) : null;
});

const tracksMeta = shallowRef(new Map<number, TrackMeta>());
const objectUrls: string[] = [];
const activeTrackId = ref<number | null>(null);
const audioEl = ref<HTMLAudioElement | null>(null);
const isPlaying = ref(false);

const activeTrack = computed(() =>
  tracks.value.find((t) => t.id === activeTrackId.value),
);

const activeTrackUrl = computed(() =>
  activeTrack.value
    ? fileUrl(activeTrack.value.id, activeTrack.value.file_name)
    : "",
);

const activeMeta = computed<TrackMeta | undefined>(() =>
  activeTrackId.value != null
    ? tracksMeta.value.get(activeTrackId.value)
    : undefined,
);

const activeArtUrl = computed(
  () => activeMeta.value?.pictureUrl ?? folderCoverUrl.value,
);

const activeTitle = computed(
  () =>
    activeMeta.value?.title ??
    (activeTrack.value
      ? activeTrack.value.file_name.replace(/\.[^.]+$/, "")
      : ""),
);

function trackTitleFor(fileId: number, fallback: string): string {
  return (
    tracksMeta.value.get(fileId)?.title ?? fallback.replace(/\.[^.]+$/, "")
  );
}

function trackArtistFor(fileId: number): string | undefined {
  return tracksMeta.value.get(fileId)?.artist;
}

function thumbForTrack(fileId: number): string | null {
  return (
    tracksMeta.value.get(fileId)?.pictureUrl ?? folderCoverUrl.value ?? null
  );
}

function pictureToObjectUrl(picture: PictureType): string {
  const bytes = new Uint8Array(picture.data);
  const blob = new Blob([bytes], { type: picture.format });
  const url = URL.createObjectURL(blob);
  objectUrls.push(url);
  return url;
}

async function readMeta(url: string): Promise<TrackMeta> {
  let blob: Blob;
  try {
    const resp = await fetch(url, { credentials: "same-origin" });
    if (!resp.ok) return {};
    blob = await resp.blob();
  } catch {
    return {};
  }

  return await new Promise((resolve) => {
    jsmediatags.read(blob, {
      onSuccess: ({ tags }: TagType) => {
        const tpos = (tags as Record<string, { data?: string } | undefined>)
          ?.TPOS?.data;
        const meta: TrackMeta = {
          title: tags.title,
          artist: tags.artist,
          album: tags.album,
          year: tags.year,
          genre: tags.genre,
          track: tags.track,
          disc: tpos,
        };
        if (tags.picture) {
          meta.pictureUrl = pictureToObjectUrl(tags.picture);
        }
        resolve(meta);
      },
      onError: (err: jsmediatagsError) => {
        console.warn("[SoundtrackPlayer] tag read failed:", err);
        resolve({});
      },
    });
  });
}

async function loadAllMetadata() {
  const next = new Map<number, TrackMeta>();
  await Promise.all(
    tracks.value.map(async (track) => {
      const meta = await readMeta(fileUrl(track.id, track.file_name));
      next.set(track.id, meta);
    }),
  );
  tracksMeta.value = next;
}

onMounted(() => {
  void loadAllMetadata();
});

watch(tracks, (newTracks, oldTracks) => {
  if (!oldTracks) return;
  const oldIds = new Set(oldTracks.map((t) => t.id));
  const newIds = new Set(newTracks.map((t) => t.id));
  const changed =
    oldIds.size !== newIds.size || [...newIds].some((id) => !oldIds.has(id));
  if (changed) void loadAllMetadata();
});

onBeforeUnmount(() => {
  for (const url of objectUrls) URL.revokeObjectURL(url);
});

function selectTrack(fileId: number) {
  activeTrackId.value = fileId;
}

function onDelete(fileId: number) {
  if (activeTrackId.value === fileId) {
    activeTrackId.value = null;
    isPlaying.value = false;
  }
  emit("delete-track", fileId);
}

function chips(meta: TrackMeta | undefined) {
  if (!meta) return [];
  const items: { icon: string; label: string }[] = [];
  if (meta.album) items.push({ icon: "mdi-album", label: meta.album });
  if (meta.artist)
    items.push({ icon: "mdi-account-music", label: meta.artist });
  if (meta.year) items.push({ icon: "mdi-calendar", label: meta.year });
  if (meta.genre)
    items.push({ icon: "mdi-music-clef-treble", label: meta.genre });
  if (meta.track) items.push({ icon: "mdi-numeric", label: `#${meta.track}` });
  if (meta.disc)
    items.push({ icon: "mdi-disc", label: `${t("rom.disc")} ${meta.disc}` });
  return items;
}
</script>

<template>
  <div class="pa-2">
    <div v-if="activeTrack" class="d-flex align-center mb-4 ga-4 flex-wrap">
      <div class="disc-wrapper" :class="{ spinning: isPlaying }">
        <img v-if="activeArtUrl" :src="activeArtUrl" class="disc" alt="" />
        <div v-else class="disc disc-placeholder">
          <v-icon size="64">mdi-music-note</v-icon>
        </div>
      </div>
      <div class="flex-grow-1" style="min-width: 200px">
        <div class="text-h6 text-truncate">{{ activeTitle }}</div>
        <div
          v-if="activeMeta?.artist"
          class="text-subtitle-2 text-medium-emphasis"
        >
          {{ activeMeta.artist }}
        </div>
        <div class="d-flex flex-wrap ga-2 mt-2">
          <v-chip
            v-for="(c, i) in chips(activeMeta)"
            :key="i"
            size="small"
            variant="tonal"
            :prepend-icon="c.icon"
          >
            {{ c.label }}
          </v-chip>
        </div>
      </div>
    </div>
    <!-- eslint-disable-next-line vuejs-accessibility/media-has-caption -->
    <audio
      v-if="activeTrackUrl"
      ref="audioEl"
      :src="activeTrackUrl"
      controls
      autoplay
      preload="metadata"
      class="w-100 mb-3"
      @play="isPlaying = true"
      @pause="isPlaying = false"
      @ended="isPlaying = false"
    />
    <v-list density="compact" class="bg-toplayer rounded">
      <v-list-item
        v-for="track in tracks"
        :key="track.id"
        :active="activeTrackId === track.id"
        @click="selectTrack(track.id)"
      >
        <template #prepend>
          <div class="track-thumb mr-3">
            <img
              v-if="thumbForTrack(track.id)"
              :src="thumbForTrack(track.id) ?? ''"
              alt=""
            />
            <v-icon v-else>
              {{
                activeTrackId === track.id
                  ? "mdi-volume-high"
                  : "mdi-music-note"
              }}
            </v-icon>
          </div>
        </template>
        <v-list-item-title>
          {{ trackTitleFor(track.id, track.file_name) }}
        </v-list-item-title>
        <v-list-item-subtitle v-if="trackArtistFor(track.id)">
          {{ trackArtistFor(track.id) }}
        </v-list-item-subtitle>
        <template #append>
          <span class="text-caption text-medium-emphasis mr-2">
            {{ formatBytes(track.file_size_bytes) }}
          </span>
          <v-btn
            icon="mdi-delete"
            variant="text"
            size="small"
            class="text-romm-red"
            @click.stop="onDelete(track.id)"
          />
        </template>
      </v-list-item>
    </v-list>
    <div class="d-flex justify-end mt-3">
      <v-btn
        prepend-icon="mdi-cloud-upload-outline"
        variant="tonal"
        size="small"
        @click="emit('upload-tracks')"
      >
        {{ t("rom.upload-tracks") }}
      </v-btn>
    </div>
  </div>
</template>

<style scoped>
.disc-wrapper {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  overflow: hidden;
  position: relative;
  flex-shrink: 0;
  box-shadow:
    0 0 0 6px rgba(0, 0, 0, 0.55),
    0 8px 24px rgba(0, 0, 0, 0.45);
  background: radial-gradient(
    circle at center,
    transparent 0,
    transparent 22px,
    rgba(0, 0, 0, 0.65) 22px,
    rgba(0, 0, 0, 0.65) 30px,
    transparent 31px
  );
}

.disc-wrapper::after {
  content: "";
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgba(var(--v-theme-surface), 1);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  box-shadow: inset 0 0 0 2px rgba(0, 0, 0, 0.6);
}

.disc {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
  display: block;
}

.disc-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(var(--v-theme-toplayer), 1);
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.spinning .disc {
  animation: spin 12s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.track-thumb {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.25);
  flex-shrink: 0;
}

.track-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
