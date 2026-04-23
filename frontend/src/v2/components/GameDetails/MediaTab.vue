<script setup lang="ts">
// Combined Manual + Soundtrack tab for GameDetails.
//
// Behaviour mirrors the v1 MediaTab:
//   * Both subtabs always visible; empty states drive the upload CTAs
//   * Hidden file inputs handle upload — manual upload routes through the
//     `showManualUploadTargetDialog` emitter (dialog mounted in AppLayout)
//   * Soundtrack upload goes straight through `romApi.uploadSoundtracks`
//   * Re-download primary manual + delete manual both handled here
//
// The actual PDF viewer and soundtrack player are reused from v1 for now
// (visual polish after all waves will replace them with v2-branded
// equivalents).
import { RBtn, RIcon, RSelect } from "@v2/lib";
import axios from "axios";
import type { Emitter } from "mitt";
import { computed, defineAsyncComponent, inject, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import romApi from "@/services/api/rom";
import storeRoms, { type DetailedRom } from "@/stores/roms";
import storeUpload from "@/stores/upload";
import type { Events } from "@/types/emitter";
import { FRONTEND_RESOURCES_PATH } from "@/utils";

const PdfViewer = defineAsyncComponent(
  () => import("@/components/Details/PDFViewer.vue"),
);
const SoundtrackPanel = defineAsyncComponent(
  () => import("@/v2/components/GameDetails/SoundtrackPanel.vue"),
);
const ScreenshotsTab = defineAsyncComponent(
  () => import("@/v2/components/GameDetails/ScreenshotsTab.vue"),
);

function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string" && detail) return detail;
    return err.message;
  }
  return err instanceof Error ? err.message : String(err);
}

const props = defineProps<{ rom: DetailedRom }>();
const emitter = inject<Emitter<Events>>("emitter");
const romsStore = storeRoms();
const uploadStore = storeUpload();

// ---------- Subtab state ----------
// Mirrored to `?subtab=` so the SoundtrackMiniPlayer can detect when the full
// player is visible here and hide itself to avoid duplication.
const validSubtabs = ["manual", "soundtrack", "screenshots"] as const;
type Subtab = (typeof validSubtabs)[number];

const route = useRoute();
const router = useRouter();

const subTab = ref<Subtab>(
  validSubtabs.includes(route.query.subtab as Subtab)
    ? (route.query.subtab as Subtab)
    : "manual",
);

watch(subTab, (value) => {
  if (route.query.subtab !== value) {
    router.replace({
      path: route.path,
      query: { ...route.query, subtab: value },
    });
  }
});

watch(
  () => route.query.subtab,
  (value) => {
    if (typeof value === "string" && validSubtabs.includes(value as Subtab)) {
      subTab.value = value as Subtab;
    }
  },
);

// When the user navigates away from the Media tab, drop the subtab query
// param so stale state doesn't leak onto other tabs.
watch(
  () => route.query.tab,
  (value) => {
    if (value !== "media" && route.query.subtab) {
      const rest = { ...route.query };
      delete rest.subtab;
      router.replace({ path: route.path, query: rest });
    }
  },
);

// ---------- Manual entries ----------
type ManualEntry = {
  id: string;
  label: string;
  url: string;
  isPrimary: boolean;
};

const manualEntries = computed<ManualEntry[]>(() => {
  const entries: ManualEntry[] = [];
  const cacheBust = encodeURIComponent(props.rom.updated_at);
  if (props.rom.has_manual && props.rom.path_manual) {
    entries.push({
      id: "primary",
      label: "Scraped manual",
      url: `${FRONTEND_RESOURCES_PATH}/${props.rom.path_manual}?v=${cacheBust}`,
      isPrimary: true,
    });
  }
  for (const file of props.rom.files ?? []) {
    if (file.category === "manual") {
      entries.push({
        id: `file-${file.id}`,
        label: file.file_name.replace(/\.[^.]+$/, ""),
        url: `/api/roms/${file.id}/files/content/${encodeURIComponent(
          file.file_name,
        )}?v=${cacheBust}`,
        isPrimary: false,
      });
    }
  }
  return entries;
});

const selectedManualId = ref<string>("");
let previousManualIds = new Set<string>();

watch(
  manualEntries,
  (entries) => {
    const currentIds = new Set(entries.map((e) => e.id));
    if (entries.length === 0) {
      selectedManualId.value = "";
    } else {
      // If a new entry appears after a prior snapshot, select it so the user
      // lands on the manual they just uploaded.
      const added = entries.filter((e) => !previousManualIds.has(e.id));
      if (added.length > 0 && previousManualIds.size > 0) {
        selectedManualId.value = added[added.length - 1].id;
      } else if (!entries.some((e) => e.id === selectedManualId.value)) {
        selectedManualId.value = entries[0].id;
      }
    }
    previousManualIds = currentIds;
  },
  { immediate: true },
);

const selectedManual = computed(() =>
  manualEntries.value.find((e) => e.id === selectedManualId.value),
);
const manualItems = computed(() =>
  manualEntries.value.map((e) => ({ title: e.label, value: e.id })),
);

// ---------- Soundtrack gating ----------
// Soundtracks live alongside the ROM folder, so single-file ROMs can't have
// one. Mirror the v1 gate.
const soundtrackSupported = computed(() => !props.rom.has_simple_single_file);

// ---------- Upload / refresh plumbing ----------
const manualUploadInput = ref<HTMLInputElement | null>(null);
const soundtrackUploadInput = ref<HTMLInputElement | null>(null);
const redownloadingManual = ref(false);

function triggerManualUpload() {
  manualUploadInput.value?.click();
}

function triggerSoundtrackUpload() {
  soundtrackUploadInput.value?.click();
}

async function refreshRom() {
  try {
    const { data } = await romApi.getRom({ romId: props.rom.id });
    romsStore.currentRom = data;
    romsStore.update(data);
  } catch (error) {
    console.error(error);
  }
}

function onManualUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = input.files ? Array.from(input.files) : [];
  input.value = "";
  if (files.length === 0) return;
  emitter?.emit("showManualUploadTargetDialog", { rom: props.rom, files });
}

async function onSoundtrackUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = input.files ? Array.from(input.files) : [];
  if (files.length === 0) return;

  const responses = await romApi.uploadSoundtracks({
    romId: props.rom.id,
    filesToUpload: files,
  });
  input.value = "";

  const successful = responses.filter((r) => r.status === "fulfilled").length;
  const failed = responses.length - successful;

  if (failed === 0) uploadStore.reset();

  if (successful > 0) {
    emitter?.emit("snackbarShow", {
      msg: `Uploaded ${successful} track${successful === 1 ? "" : "s"}${failed ? `, ${failed} failed` : ""}.`,
      icon: "mdi-check-bold",
      color: "green",
      timeout: 3000,
    });
    await refreshRom();
  } else {
    emitter?.emit("snackbarShow", {
      msg: "No tracks were uploaded.",
      icon: "mdi-close-circle",
      color: "orange",
      timeout: 5000,
    });
  }
}

async function redownloadManual() {
  if (redownloadingManual.value) return;
  redownloadingManual.value = true;
  try {
    await romApi.redownloadManual({ romId: props.rom.id });
    await refreshRom();
    emitter?.emit("snackbarShow", {
      msg: "Manual re-downloaded.",
      icon: "mdi-check-bold",
      color: "green",
    });
  } catch (error: unknown) {
    emitter?.emit("snackbarShow", {
      msg: `Manual re-download failed: ${errorMessage(error)}`,
      icon: "mdi-close-circle",
      color: "red",
    });
  } finally {
    redownloadingManual.value = false;
  }
}

function requestDeleteManual() {
  const entry = selectedManual.value;
  if (!entry) return;
  emitter?.emit("showDeleteManualDialog", {
    rom: props.rom,
    isPrimary: entry.isPrimary,
    fileId: entry.isPrimary
      ? undefined
      : Number(entry.id.replace(/^file-/, "")),
  });
}

async function deleteSoundtrack(fileId: number) {
  try {
    await romApi.removeSoundtrack({ romId: props.rom.id, fileId });
    await refreshRom();
    emitter?.emit("snackbarShow", {
      msg: "Track removed.",
      icon: "mdi-check-bold",
      color: "green",
    });
  } catch (error: unknown) {
    emitter?.emit("snackbarShow", {
      msg: `Couldn't remove track: ${errorMessage(error)}`,
      icon: "mdi-close-circle",
      color: "red",
    });
  }
}
</script>

<template>
  <!-- Hidden file inputs drive the upload buttons -->
  <input
    ref="manualUploadInput"
    type="file"
    accept="application/pdf"
    multiple
    class="r-v2-media__file-input"
    aria-label="Upload manual"
    @change="onManualUpload"
  />
  <input
    ref="soundtrackUploadInput"
    type="file"
    accept="audio/*,.flac,.opus"
    multiple
    class="r-v2-media__file-input"
    aria-label="Upload soundtrack"
    @change="onSoundtrackUpload"
  />

  <div class="r-v2-media">
    <!-- Subtabs -->
    <nav class="r-v2-media__subtabs" role="tablist">
      <button
        type="button"
        role="tab"
        class="r-v2-media__subtab"
        :class="{ 'r-v2-media__subtab--active': subTab === 'manual' }"
        :aria-selected="subTab === 'manual'"
        @click="subTab = 'manual'"
      >
        <RIcon icon="mdi-book-open-page-variant-outline" />
        Manual
      </button>
      <button
        type="button"
        role="tab"
        class="r-v2-media__subtab"
        :class="{ 'r-v2-media__subtab--active': subTab === 'soundtrack' }"
        :aria-selected="subTab === 'soundtrack'"
        @click="subTab = 'soundtrack'"
      >
        <RIcon icon="mdi-music" />
        Soundtrack
      </button>
      <button
        v-if="(rom.merged_screenshots?.length ?? 0) > 0"
        type="button"
        role="tab"
        class="r-v2-media__subtab"
        :class="{ 'r-v2-media__subtab--active': subTab === 'screenshots' }"
        :aria-selected="subTab === 'screenshots'"
        @click="subTab = 'screenshots'"
      >
        <RIcon icon="mdi-image-multiple-outline" />
        Screenshots
      </button>
    </nav>

    <!-- Manual subtab -->
    <section v-if="subTab === 'manual'" class="r-v2-media__panel">
      <template v-if="manualEntries.length === 0">
        <div class="r-v2-media__empty">
          <RIcon icon="mdi-book-open-page-variant-outline" size="48" />
          <div class="r-v2-media__empty-title">No manual yet</div>
          <div class="r-v2-media__empty-actions">
            <RBtn
              prepend-icon="mdi-cloud-upload-outline"
              @click="triggerManualUpload"
            >
              Upload manual
            </RBtn>
            <RBtn
              v-if="rom.url_manual"
              variant="outlined"
              prepend-icon="mdi-cloud-download-outline"
              :loading="redownloadingManual"
              :disabled="redownloadingManual"
              @click="redownloadManual"
            >
              Re-download
            </RBtn>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="r-v2-media__manual-toolbar">
          <RSelect
            v-if="manualEntries.length > 1"
            v-model="selectedManualId"
            :items="manualItems"
            density="compact"
            variant="outlined"
            hide-details
            class="r-v2-media__manual-select"
          />
          <div v-else class="r-v2-media__manual-spacer" />

          <RBtn
            size="small"
            variant="outlined"
            prepend-icon="mdi-cloud-upload-outline"
            @click="triggerManualUpload"
          >
            Upload
          </RBtn>
          <RBtn
            v-if="rom.url_manual"
            size="small"
            variant="outlined"
            prepend-icon="mdi-cloud-download-outline"
            :loading="redownloadingManual"
            :disabled="redownloadingManual"
            @click="redownloadManual"
          >
            Re-download
          </RBtn>
          <RBtn
            v-if="selectedManual"
            size="small"
            variant="outlined"
            color="romm-red"
            prepend-icon="mdi-delete"
            @click="requestDeleteManual"
          >
            Delete
          </RBtn>
        </div>

        <div class="r-v2-media__viewer">
          <PdfViewer
            v-if="selectedManual"
            :key="`${selectedManual.id}-${rom.updated_at}`"
            :pdf-url="selectedManual.url"
          />
        </div>
      </template>
    </section>

    <!-- Soundtrack subtab -->
    <section v-else class="r-v2-media__panel">
      <template v-if="!soundtrackSupported">
        <div class="r-v2-media__empty">
          <RIcon icon="mdi-music-off-outline" size="48" />
          <div class="r-v2-media__empty-title">
            Soundtrack needs a folder-based ROM
          </div>
          <div class="r-v2-media__empty-hint">
            Single-file ROMs can't have accompanying tracks. Re-organise this
            ROM as a folder and the upload option will appear here.
          </div>
        </div>
      </template>

      <template v-else-if="!rom.has_soundtrack">
        <div class="r-v2-media__empty">
          <RIcon icon="mdi-music-note-outline" size="48" />
          <div class="r-v2-media__empty-title">No soundtrack yet</div>
          <div class="r-v2-media__empty-actions">
            <RBtn
              prepend-icon="mdi-cloud-upload-outline"
              @click="triggerSoundtrackUpload"
            >
              Upload soundtrack
            </RBtn>
          </div>
        </div>
      </template>

      <SoundtrackPanel
        v-else
        :rom="rom"
        class="r-v2-media__soundtrack"
        @upload-tracks="triggerSoundtrackUpload"
        @delete-track="deleteSoundtrack"
      />
    </section>

    <!-- Screenshots subtab -->
    <section v-if="subTab === 'screenshots'" class="r-v2-media__panel">
      <ScreenshotsTab :urls="rom.merged_screenshots ?? []" />
    </section>
  </div>
</template>

<style scoped>
.r-v2-media {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.r-v2-media__file-input {
  display: none;
}

/* Sub-tabs */
.r-v2-media__subtabs {
  display: inline-flex;
  gap: var(--r-space-1);
  padding: 4px;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-full);
  align-self: flex-start;
}

.r-v2-media__subtab {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--r-color-fg-muted);
  padding: var(--r-space-2) var(--r-space-4);
  border-radius: var(--r-radius-full);
  display: inline-flex;
  align-items: center;
  gap: var(--r-space-2);
  font-size: var(--r-font-size-sm);
  font-weight: var(--r-font-weight-medium);
  cursor: pointer;
  transition:
    background var(--r-motion-fast) var(--r-motion-ease-out),
    color var(--r-motion-fast) var(--r-motion-ease-out);
}

.r-v2-media__subtab:hover {
  color: var(--r-color-fg);
}

.r-v2-media__subtab--active {
  background: var(--r-color-brand-primary);
  color: #fff;
}

/* Panels */
.r-v2-media__panel {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-3);
  min-height: 320px;
}

/* Manual */
.r-v2-media__manual-toolbar {
  display: flex;
  align-items: center;
  gap: var(--r-space-2);
  flex-wrap: wrap;
}

.r-v2-media__manual-select {
  flex: 1;
  max-width: 420px;
}

.r-v2-media__manual-spacer {
  flex: 1;
}

.r-v2-media__viewer {
  min-height: 480px;
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  overflow: hidden;
  background: var(--r-color-bg-elevated);
}

/* Soundtrack — the v1 player has its own internal styling; wrap in an
   elevated container so it blends with v2 tokens. */
.r-v2-media__soundtrack {
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
  background: var(--r-color-bg-elevated);
}

/* Empty state */
.r-v2-media__empty {
  padding: var(--r-space-10) var(--r-space-6);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--r-space-3);
  background: var(--r-color-bg-elevated);
  border: 1px dashed var(--r-color-border);
  border-radius: var(--r-radius-md);
  text-align: center;
  color: var(--r-color-fg-muted);
}

.r-v2-media__empty-title {
  color: var(--r-color-fg);
  font-size: var(--r-font-size-lg);
  font-weight: var(--r-font-weight-semibold);
}

.r-v2-media__empty-hint {
  max-width: 440px;
  font-size: var(--r-font-size-sm);
  line-height: var(--r-line-height-relaxed);
}

.r-v2-media__empty-actions {
  display: flex;
  gap: var(--r-space-2);
  flex-wrap: wrap;
  justify-content: center;
  margin-top: var(--r-space-2);
}
</style>
