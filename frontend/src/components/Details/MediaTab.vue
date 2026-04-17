<script setup lang="ts">
import type { Emitter } from "mitt";
import { computed, inject, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import { useDisplay } from "vuetify";
import PdfViewer from "@/components/Details/PDFViewer.vue";
import SoundtrackPlayer from "@/components/Details/SoundtrackPlayer.vue";
import romApi from "@/services/api/rom";
import storeRoms, { type DetailedRom } from "@/stores/roms";
import storeUpload from "@/stores/upload";
import type { Events } from "@/types/emitter";
import { FRONTEND_RESOURCES_PATH } from "@/utils";

const props = defineProps<{ rom: DetailedRom }>();
const { t } = useI18n();
const { mdAndDown } = useDisplay();
const route = useRoute();
const router = useRouter();
const emitter = inject<Emitter<Events>>("emitter");
const romsStore = storeRoms();
const uploadStore = storeUpload();

const validSubtabs = ["manual", "soundtrack"] as const;
type Subtab = (typeof validSubtabs)[number];

const subTab = ref<Subtab>(
  validSubtabs.includes(route.query.subtab as Subtab)
    ? (route.query.subtab as Subtab)
    : "manual",
);

watch(subTab, (newSubtab) => {
  if (route.query.subtab !== newSubtab) {
    router.replace({
      path: route.path,
      query: { ...route.query, subtab: newSubtab },
    });
  }
});

watch(
  () => route.query.subtab,
  (newSubtab) => {
    if (newSubtab && validSubtabs.includes(newSubtab as Subtab)) {
      subTab.value = newSubtab as Subtab;
    }
  },
  { immediate: true },
);

watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab !== "media" && route.query.subtab) {
      const rest = { ...route.query };
      delete rest.subtab;
      router.replace({ path: route.path, query: rest });
    }
  },
);

type ManualEntry = {
  id: string;
  label: string;
  url: string;
  isPrimary: boolean;
};

const manualEntries = computed<ManualEntry[]>(() => {
  const entries: ManualEntry[] = [];
  if (props.rom.has_manual && props.rom.path_manual) {
    entries.push({
      id: "primary",
      label: t("rom.scraped-manual"),
      url: `${FRONTEND_RESOURCES_PATH}/${props.rom.path_manual}`,
      isPrimary: true,
    });
  }
  for (const file of props.rom.files) {
    if (file.category === "manual") {
      entries.push({
        id: `file-${file.id}`,
        label: file.file_name.replace(/\.[^.]+$/, ""),
        url: `/api/roms/${file.id}/files/content/${encodeURIComponent(file.file_name)}`,
        isPrimary: false,
      });
    }
  }
  return entries;
});

const selectedManualId = ref<string>("");

watch(
  manualEntries,
  (entries) => {
    if (entries.length === 0) {
      selectedManualId.value = "";
    } else if (!entries.some((e) => e.id === selectedManualId.value)) {
      selectedManualId.value = entries[0].id;
    }
  },
  { immediate: true },
);

const selectedManual = computed(() =>
  manualEntries.value.find((e) => e.id === selectedManualId.value),
);

const soundtrackSupported = computed(() => !props.rom.has_simple_single_file);

const manualUploadInput = ref<HTMLInputElement | null>(null);
const soundtrackUploadInput = ref<HTMLInputElement | null>(null);
const showConfirmDeleteManual = ref(false);
const redownloadingManual = ref(false);
const showUploadTargetDialog = ref(false);
const pendingManualFiles = ref<File[]>([]);

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

  if (props.rom.has_simple_single_file) {
    void uploadManualsToResources(files);
    return;
  }

  pendingManualFiles.value = files;
  showUploadTargetDialog.value = true;
}

async function handleManualUploadResult(
  responses: PromiseSettledResult<unknown>[],
  successKey: string,
  skippedKey: string,
) {
  const successful = responses.filter((r) => r.status === "fulfilled").length;
  const failed = responses.length - successful;

  if (failed === 0) {
    uploadStore.reset();
  }

  if (successful > 0) {
    emitter?.emit("snackbarShow", {
      msg: t(successKey, { count: successful, failed }),
      icon: "mdi-check-bold",
      color: "green",
      timeout: 3000,
    });
    await refreshRom();
  } else {
    emitter?.emit("snackbarShow", {
      msg: t(skippedKey),
      icon: "mdi-close-circle",
      color: "orange",
      timeout: 5000,
    });
  }
}

async function uploadManualsToResources(files: File[]) {
  const responses = await romApi.uploadManuals({
    romId: props.rom.id,
    filesToUpload: files,
  });
  await handleManualUploadResult(
    responses,
    "rom.manuals-upload-success",
    "rom.manuals-upload-skipped",
  );
}

async function uploadManualsToFolder(files: File[]) {
  const responses = await romApi.uploadManualFiles({
    romId: props.rom.id,
    filesToUpload: files,
  });
  await handleManualUploadResult(
    responses,
    "rom.manual-files-upload-success",
    "rom.manual-files-upload-skipped",
  );
}

async function chooseUploadTarget(target: "resources" | "folder") {
  const files = pendingManualFiles.value;
  pendingManualFiles.value = [];
  showUploadTargetDialog.value = false;
  if (files.length === 0) return;
  if (target === "resources") {
    await uploadManualsToResources(files);
  } else {
    await uploadManualsToFolder(files);
  }
}

function cancelUploadTarget() {
  pendingManualFiles.value = [];
  showUploadTargetDialog.value = false;
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

  if (failed === 0) {
    uploadStore.reset();
  }

  if (successful > 0) {
    emitter?.emit("snackbarShow", {
      msg: t("rom.soundtracks-upload-success", { count: successful, failed }),
      icon: "mdi-check-bold",
      color: "green",
      timeout: 3000,
    });
    await refreshRom();
  } else {
    emitter?.emit("snackbarShow", {
      msg: t("rom.soundtracks-upload-skipped"),
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
      msg: t("rom.manual-redownloaded"),
      icon: "mdi-check-bold",
      color: "green",
    });
  } catch (error: any) {
    emitter?.emit("snackbarShow", {
      msg: t("rom.manual-redownload-failed", {
        error: error.response?.data?.detail || error.message,
      }),
      icon: "mdi-close-circle",
      color: "red",
    });
  } finally {
    redownloadingManual.value = false;
  }
}

async function deleteManual() {
  showConfirmDeleteManual.value = false;
  const entry = selectedManual.value;
  if (!entry) return;
  try {
    if (entry.isPrimary) {
      await romApi.removeManual({ romId: props.rom.id });
    } else {
      const fileId = Number(entry.id.replace(/^file-/, ""));
      await romApi.deleteManualFile({ romId: props.rom.id, fileId });
    }
    await refreshRom();
    emitter?.emit("snackbarShow", {
      msg: t(
        entry.isPrimary ? "rom.manual-removed" : "rom.manual-file-removed",
      ),
      icon: "mdi-check-bold",
      color: "green",
    });
  } catch (error: any) {
    emitter?.emit("snackbarShow", {
      msg: t(
        entry.isPrimary
          ? "rom.manual-remove-failed"
          : "rom.manual-file-remove-failed",
        { error: error.response?.data?.detail || error.message },
      ),
      icon: "mdi-close-circle",
      color: "red",
    });
  }
}

async function deleteSoundtrack(fileId: number) {
  try {
    await romApi.removeSoundtrack({ romId: props.rom.id, fileId });
    await refreshRom();
    emitter?.emit("snackbarShow", {
      msg: t("rom.soundtrack-removed"),
      icon: "mdi-check-bold",
      color: "green",
    });
  } catch (error: any) {
    emitter?.emit("snackbarShow", {
      msg: t("rom.soundtrack-remove-failed", {
        error: error.response?.data?.detail || error.message,
      }),
      icon: "mdi-close-circle",
      color: "red",
    });
  }
}
</script>

<template>
  <input
    ref="manualUploadInput"
    type="file"
    accept="application/pdf"
    multiple
    class="d-none"
    :aria-label="t('rom.upload-manual')"
    @change="onManualUpload"
  />
  <input
    ref="soundtrackUploadInput"
    type="file"
    accept="audio/*,.flac,.opus"
    multiple
    class="d-none"
    :aria-label="t('rom.upload-soundtrack')"
    @change="onSoundtrackUpload"
  />
  <v-row no-gutters>
    <v-col cols="12" lg="auto">
      <v-tabs
        v-model="subTab"
        :direction="mdAndDown ? 'horizontal' : 'vertical'"
        :align-tabs="mdAndDown ? 'center' : 'start'"
        slider-color="secondary"
        class="mr-4 mt-2"
        selected-class="bg-toplayer"
      >
        <v-tab
          prepend-icon="mdi-book-open-page-variant-outline"
          class="rounded text-caption"
          value="manual"
        >
          {{ t("rom.manual") }}
        </v-tab>
        <v-tab
          prepend-icon="mdi-music"
          class="rounded text-caption"
          value="soundtrack"
        >
          {{ t("rom.soundtrack") }}
        </v-tab>
      </v-tabs>
    </v-col>
    <v-col>
      <v-tabs-window v-model="subTab">
        <v-tabs-window-item value="manual">
          <div v-if="manualEntries.length === 0" class="pa-6 text-center">
            <v-icon size="48" class="mb-2 text-medium-emphasis">
              mdi-book-open-page-variant-outline
            </v-icon>
            <div class="text-body-2 text-medium-emphasis mb-3">
              {{ t("rom.no-manual") }}
            </div>
            <div class="d-flex justify-center ga-2">
              <v-btn
                prepend-icon="mdi-cloud-upload-outline"
                variant="tonal"
                @click="triggerManualUpload"
              >
                {{ t("rom.upload-manual") }}
              </v-btn>
              <v-btn
                v-if="rom.url_manual"
                prepend-icon="mdi-cloud-download-outline"
                variant="tonal"
                :loading="redownloadingManual"
                :disabled="redownloadingManual"
                @click="redownloadManual"
              >
                {{ t("rom.redownload-manual") }}
              </v-btn>
            </div>
          </div>
          <div v-else>
            <div class="d-flex align-center mb-2 ga-2">
              <v-select
                v-if="manualEntries.length > 1"
                v-model="selectedManualId"
                :items="manualEntries"
                item-title="label"
                item-value="id"
                density="compact"
                hide-details
                variant="outlined"
                class="flex-grow-1"
              />
              <v-spacer v-else />
              <v-btn
                prepend-icon="mdi-cloud-upload-outline"
                variant="tonal"
                size="small"
                @click="triggerManualUpload"
              >
                {{ t("rom.upload-manual") }}
              </v-btn>
              <v-btn
                v-if="rom.url_manual"
                prepend-icon="mdi-cloud-download-outline"
                variant="tonal"
                size="small"
                :loading="redownloadingManual"
                :disabled="redownloadingManual"
                @click="redownloadManual"
              >
                {{ t("rom.redownload-manual") }}
              </v-btn>
              <v-btn
                v-if="selectedManual"
                prepend-icon="mdi-delete"
                variant="tonal"
                size="small"
                class="text-romm-red"
                @click="showConfirmDeleteManual = true"
              >
                {{ t("rom.delete") }}
              </v-btn>
            </div>
            <PdfViewer v-if="selectedManual" :pdf-url="selectedManual.url" />
          </div>
        </v-tabs-window-item>
        <v-tabs-window-item value="soundtrack">
          <div v-if="!soundtrackSupported" class="pa-6 text-center">
            <v-icon size="48" class="mb-2 text-medium-emphasis">
              mdi-music-off-outline
            </v-icon>
            <div class="text-body-2 text-medium-emphasis">
              {{ t("rom.soundtrack-folder-only") }}
            </div>
          </div>
          <div v-else-if="!rom.has_soundtrack" class="pa-6 text-center">
            <v-icon size="48" class="mb-2 text-medium-emphasis">
              mdi-music-note-outline
            </v-icon>
            <div class="text-body-2 text-medium-emphasis mb-3">
              {{ t("rom.no-soundtrack") }}
            </div>
            <v-btn
              prepend-icon="mdi-cloud-upload-outline"
              variant="tonal"
              @click="triggerSoundtrackUpload"
            >
              {{ t("rom.upload-soundtrack") }}
            </v-btn>
          </div>
          <SoundtrackPlayer
            v-else
            :rom="rom"
            @upload-tracks="triggerSoundtrackUpload"
            @delete-track="deleteSoundtrack"
          />
        </v-tabs-window-item>
      </v-tabs-window>
    </v-col>
  </v-row>

  <v-dialog v-model="showConfirmDeleteManual" max-width="420">
    <v-card>
      <v-card-text class="pa-4">
        <p class="text-body-1 mb-3">
          {{ t("rom.delete-manual-confirm-title") }}
        </p>
        <p class="text-body-2 text-medium-emphasis">
          {{ t("rom.delete-manual-confirm-body") }}
        </p>
      </v-card-text>
      <v-card-actions class="justify-center pb-4">
        <v-btn class="bg-toplayer" @click="showConfirmDeleteManual = false">
          {{ t("common.cancel") }}
        </v-btn>
        <v-btn class="text-romm-red bg-toplayer" @click="deleteManual">
          {{ t("rom.delete-manual-button") }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="showUploadTargetDialog" max-width="520" persistent>
    <v-card>
      <v-card-title class="text-h6 pt-4">
        {{ t("rom.manual-upload-target-title") }}
      </v-card-title>
      <v-card-text class="pt-2">
        <v-list class="bg-transparent" lines="two">
          <v-list-item
            class="bg-toplayer rounded mb-2"
            @click="chooseUploadTarget('resources')"
          >
            <template #prepend>
              <v-icon class="mr-2">mdi-database-edit-outline</v-icon>
            </template>
            <v-list-item-title>
              {{ t("rom.manual-upload-target-resources-title") }}
            </v-list-item-title>
            <v-list-item-subtitle class="text-wrap">
              {{ t("rom.manual-upload-target-resources-desc") }}
            </v-list-item-subtitle>
          </v-list-item>
          <v-list-item
            class="bg-toplayer rounded"
            @click="chooseUploadTarget('folder')"
          >
            <template #prepend>
              <v-icon class="mr-2">mdi-folder-plus-outline</v-icon>
            </template>
            <v-list-item-title>
              {{ t("rom.manual-upload-target-folder-title") }}
            </v-list-item-title>
            <v-list-item-subtitle class="text-wrap">
              {{ t("rom.manual-upload-target-folder-desc") }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card-text>
      <v-card-actions class="justify-end pb-4 px-4">
        <v-btn class="bg-toplayer" @click="cancelUploadTarget">
          {{ t("common.cancel") }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
