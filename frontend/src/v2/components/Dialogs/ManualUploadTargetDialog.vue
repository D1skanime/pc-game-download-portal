<script setup lang="ts">
import type { Emitter } from "mitt";
import { inject, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import romApi from "@/services/api/rom";
import storeRoms from "@/stores/roms";
import storeUpload from "@/stores/upload";
import type { Events } from "@/types/emitter";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const emitter = inject<Emitter<Events>>("emitter");
const snackbar = useSnackbar();
const romsStore = storeRoms();
const uploadStore = storeUpload();

const handleShow = (payload: Events["showManualUploadTargetDialog"]) => {
  void uploadToResources(payload.rom.id, payload.files);
};
emitter?.on("showManualUploadTargetDialog", handleShow);
onBeforeUnmount(() => emitter?.off("showManualUploadTargetDialog", handleShow));

async function refreshRom(romId: number) {
  try {
    const { data } = await romApi.getRom({ romId });
    romsStore.currentRom = data;
    romsStore.update(data);
  } catch (error) {
    console.error(error);
  }
}

async function handleUploadResult(
  responses: PromiseSettledResult<unknown>[],
  successKey: string,
  skippedKey: string,
) {
  const successful = responses.filter((r) => r.status === "fulfilled").length;
  const failed = responses.length - successful;

  if (failed === 0) uploadStore.reset();

  if (successful > 0) {
    snackbar.success(t(successKey, { count: successful, failed }), {
      icon: "mdi-check-bold",
      timeout: 3000,
    });
  } else {
    snackbar.warning(t(skippedKey), {
      icon: "mdi-close-circle",
      timeout: 5000,
    });
  }
}

async function uploadToResources(romId: number, files: File[]) {
  if (files.length === 0) return;
  const responses = await romApi.uploadManuals({ romId, filesToUpload: files });
  await handleUploadResult(
    responses,
    "rom.manuals-upload-success",
    "rom.manuals-upload-skipped",
  );
  if (responses.some((response) => response.status === "fulfilled")) {
    await refreshRom(romId);
  }
}
</script>
