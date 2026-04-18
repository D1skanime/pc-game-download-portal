<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, onBeforeUnmount, ref, watch } from "vue";
import { useRoute } from "vue-router";
import VolumeControl from "@/components/common/VolumeControl.vue";
import useSoundtrackPlayer from "@/stores/soundtrackPlayer";

const route = useRoute();
const store = useSoundtrackPlayer();
const {
  track,
  meta,
  isPlaying,
  isBuffering,
  currentTime,
  duration,
  hasPrevious,
  hasNext,
} = storeToRefs(store);

const audioEl = ref<HTMLAudioElement | null>(null);

const onSoundtrackSubtab = computed(
  () =>
    route.name === "rom" &&
    route.query.tab === "media" &&
    route.query.subtab === "soundtrack",
);

const showMiniPlayer = computed(
  () => track.value !== null && !onSoundtrackSubtab.value,
);

const coverUrl = computed(
  () => meta.value.coverUrl ?? meta.value.folderCoverUrl ?? null,
);

onMounted(() => {
  store.setAudioRef(audioEl.value);
});

onBeforeUnmount(() => {
  store.setAudioRef(null);
});

watch(track, async (t) => {
  const el = audioEl.value;
  if (!el) return;
  if (t) {
    el.src = t.url;
    try {
      await el.play();
    } catch {
      // autoplay may be blocked; user can click play in the UI
    }
  } else {
    el.pause();
    el.removeAttribute("src");
    try {
      el.load();
    } catch {
      // ignore
    }
  }
});

function onPlay() {
  isPlaying.value = true;
  isBuffering.value = false;
}
function onPause() {
  isPlaying.value = false;
}
function onEnded() {
  isPlaying.value = false;
  if (hasNext.value) store.next();
}
function onTimeUpdate() {
  if (audioEl.value) store.reportCurrentTime(audioEl.value.currentTime || 0);
}
function onLoadedMetadata() {
  if (audioEl.value) duration.value = audioEl.value.duration || 0;
}
function onWaiting() {
  isBuffering.value = true;
}
function onCanPlay() {
  isBuffering.value = false;
}

function fmt(s: number) {
  if (!Number.isFinite(s) || s < 0) return "0:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${sec}`;
}
</script>

<template>
  <!-- Persistent (always-mounted) audio element, hidden visually -->
  <!-- eslint-disable-next-line vuejs-accessibility/media-has-caption -->
  <audio
    ref="audioEl"
    class="d-none"
    preload="metadata"
    @play="onPlay"
    @pause="onPause"
    @ended="onEnded"
    @timeupdate="onTimeUpdate"
    @loadedmetadata="onLoadedMetadata"
    @waiting="onWaiting"
    @canplay="onCanPlay"
  />

  <Transition name="mini-player">
    <v-card
      v-if="showMiniPlayer && track"
      class="mini-player position-fixed elevation-12"
    >
      <div class="d-flex align-stretch pt-4 px-4 ga-3">
        <div
          class="mini-disc rounded-circle overflow-hidden d-flex align-center justify-center flex-shrink-0 align-self-center position-relative"
          :class="{ spinning: isPlaying }"
        >
          <img v-if="coverUrl" :src="coverUrl" class="w-100 h-100" alt="" />
          <v-icon v-else size="40">mdi-music-note</v-icon>
          <div
            v-if="isBuffering"
            class="buffering-overlay position-absolute d-flex align-center justify-center"
          >
            <v-progress-circular
              indeterminate
              size="24"
              width="2"
              color="white"
            />
          </div>
        </div>
        <div class="d-flex flex-column flex-grow-1" style="min-width: 0">
          <div class="d-flex align-center ga-2">
            <div class="flex-grow-1" style="min-width: 0">
              <div class="text-body-2 text-truncate">
                {{ meta.title || track.fileName }}
              </div>
              <div
                v-if="meta.artist"
                class="text-subtitle-2 text-medium-emphasis text-truncate"
              >
                {{ meta.artist }}
              </div>
            </div>
            <v-btn
              icon="mdi-close"
              variant="text"
              size="small"
              @click="store.stop()"
            />
          </div>
          <div class="d-flex align-center ga-1 mt-auto">
            <v-btn
              icon="mdi-skip-previous"
              variant="text"
              size="small"
              :disabled="!hasPrevious"
              @click="store.previous()"
            />
            <v-btn
              :icon="isPlaying ? 'mdi-pause-circle' : 'mdi-play-circle'"
              variant="text"
              size="default"
              @click="store.togglePlayPause()"
            />
            <v-btn
              icon="mdi-skip-next"
              variant="text"
              size="small"
              :disabled="!hasNext"
              @click="store.next()"
            />
            <v-divider vertical class="mx-1 my-2" />
            <VolumeControl btn-size="small" />
          </div>
        </div>
      </div>
      <div class="d-flex align-center px-4 pb-2 ga-2">
        <span class="text-caption text-medium-emphasis">
          {{ fmt(currentTime) }}
        </span>
        <v-slider
          :model-value="currentTime"
          :max="duration || 0"
          :step="0.1"
          density="compact"
          hide-details
          color="primary"
          thumb-size="12"
          track-size="2"
          class="flex-grow-1"
          @update:model-value="(v: number) => store.seek(v)"
        />
        <span class="text-caption text-medium-emphasis">
          {{ fmt(duration) }}
        </span>
      </div>
    </v-card>
  </Transition>
</template>

<style scoped>
.mini-player {
  bottom: 16px;
  right: 16px;
  width: 360px;
  max-width: calc(100vw - 32px);
  z-index: 2000;
  border-radius: 12px;
  background: rgba(var(--v-theme-toplayer), 0.98);
  backdrop-filter: blur(8px);
}

.mini-disc {
  width: 88px;
  height: 88px;
  background: rgba(0, 0, 0, 0.25);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.6);
}
.mini-disc img {
  object-fit: cover;
  animation: spin 12s linear infinite;
  animation-play-state: paused;
}
.mini-disc.spinning img {
  animation-play-state: running;
}
.buffering-overlay {
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
}
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.mini-player-enter-from,
.mini-player-leave-to {
  transform: translate(20%, 120%);
  opacity: 0;
}
.mini-player-enter-active,
.mini-player-leave-active {
  transition:
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.25s ease;
}
</style>
