<script setup lang="ts">
// The Media tab presents three screenshot sections:
//
//   * ROM        is the read-only shared library view.
//   * Mine       is per-user storage under the user's asset folder.
//                  Private by default, with a per-item public/private toggle.
//   * Community  contains other users' public screenshots and is read-only.
//
// Only the RomM-owned personal asset section accepts uploads or deletes.
import { RBtn, RDropzone } from "@v2/lib";
import axios from "axios";
import { storeToRefs } from "pinia";
import { computed, defineAsyncComponent, ref } from "vue";
import { useI18n } from "vue-i18n";
import romApi from "@/services/api/rom";
import screenshotApi from "@/services/api/screenshot";
import storeAuth from "@/stores/auth";
import storeRoms, { type DetailedRom } from "@/stores/roms";
import storeUpload from "@/stores/upload";
import type { ScreenshotItem } from "@/v2/components/GameDetails/ScreenshotsTab.vue";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useSnackbar } from "@/v2/composables/useSnackbar";

const ScreenshotsTab = defineAsyncComponent(
  () => import("@/v2/components/GameDetails/ScreenshotsTab.vue"),
);

// Previewable image extensions for the per-ROM (RomFile) gallery. Mirrors the
// canonical "Web Images" set.
const IMAGE_EXTENSIONS = new Set([
  "png",
  "jpg",
  "jpeg",
  "webp",
  "gif",
  "bmp",
  "avif",
]);

function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string" && detail) return detail;
    return err.message;
  }
  return err instanceof Error ? err.message : String(err);
}

const props = defineProps<{ rom: DetailedRom }>();

const { t } = useI18n();
const snackbar = useSnackbar();
const confirm = useConfirm();
const romsStore = storeRoms();
const uploadStore = storeUpload();
const authStore = storeAuth();
const { user } = storeToRefs(authStore);

// ---------- ROM (shared) screenshots — RomFile-backed ----------
const romScreenshots = computed<ScreenshotItem[]>(() => {
  const cacheBust = encodeURIComponent(props.rom.updated_at);
  const out: ScreenshotItem[] = [];
  for (const file of props.rom.files ?? []) {
    const rel = file.full_path
      .replace(props.rom.full_path, "")
      .replace(/^\//, "");
    const firstSegment = rel.split("/")[0]?.toLowerCase();
    if (firstSegment !== "screenshots" && firstSegment !== "screenshot") {
      continue;
    }
    const ext = file.file_name.split(".").pop()?.toLowerCase() ?? "";
    if (!IMAGE_EXTENSIONS.has(ext)) continue;
    out.push({
      id: file.id,
      url: `/api/roms/${file.id}/files/content/${encodeURIComponent(
        file.file_name,
      )}?v=${cacheBust}`,
    });
  }
  return out;
});

// ---------- Per-user screenshots — asset-backed ----------
const allUserScreenshots = computed(() => props.rom.all_user_screenshots ?? []);

const myScreenshots = computed<ScreenshotItem[]>(() =>
  allUserScreenshots.value
    .filter((s) => user.value?.id != null && s.user_id === user.value.id)
    .map((s) => ({
      id: s.id,
      url: s.download_path,
      isOwn: true,
      isPublic: Boolean(s.is_public),
    })),
);

const communityScreenshots = computed<ScreenshotItem[]>(() =>
  allUserScreenshots.value
    .filter((s) => user.value?.id == null || s.user_id !== user.value.id)
    .map((s) => ({
      id: s.id,
      url: s.download_path,
      isOwn: false,
      isPublic: true,
      username: s.username,
      userId: s.user_id,
      userAvatarPath: s.user_avatar_path,
      userUpdatedAt: s.user_updated_at,
    })),
);

async function refreshRom() {
  try {
    const { data } = await romApi.getRom({ romId: props.rom.id });
    romsStore.currentRom = data;
    romsStore.update(data);
  } catch (error) {
    console.error(error);
  }
}

// ---------- Upload result toast (shared by both upload paths) ----------
function reportUpload(responses: PromiseSettledResult<unknown>[]) {
  const successful = responses.filter((r) => r.status === "fulfilled").length;
  const failed = responses.length - successful;
  if (failed === 0) uploadStore.reset();
  if (successful > 0) {
    snackbar.success(
      failed
        ? t("rom.screenshots-uploaded-with-failed", successful, {
            named: { n: successful, failed },
          })
        : t("rom.screenshots-uploaded-n", successful, {
            named: { n: successful },
          }),
      { icon: "mdi-check-bold", timeout: 3000 },
    );
  } else {
    snackbar.warning(t("rom.no-screenshots-uploaded"), {
      icon: "mdi-close-circle",
      timeout: 5000,
    });
  }
}

// ---------- Personal asset upload ----------
const myDz = ref<InstanceType<typeof RDropzone> | null>(null);

async function handleMyFiles(files: File[]) {
  if (files.length === 0) return;
  const responses = await screenshotApi.uploadGalleryScreenshots({
    romId: props.rom.id,
    filesToUpload: files,
  });
  reportUpload(responses);
  if (responses.some((r) => r.status === "fulfilled")) await refreshRom();
}

// ---------- Personal asset delete ----------
async function deleteMyScreenshot(id: number) {
  const ok = await confirm({
    title: t("rom.delete-screenshot-title"),
    body: t("rom.delete-screenshot-body"),
    confirmText: t("common.delete"),
    tone: "danger",
  });
  if (!ok) return;
  try {
    await screenshotApi.deleteScreenshot({ id });
    await refreshRom();
    snackbar.success(t("rom.screenshot-removed"), { icon: "mdi-check-bold" });
  } catch (error: unknown) {
    snackbar.error(
      t("rom.screenshot-remove-failed", { error: errorMessage(error) }),
      { icon: "mdi-close-circle" },
    );
  }
}

// ---------- Visibility toggle ----------
const togglingId = ref<number | null>(null);
async function toggleVisibility(id: number, isPublic: boolean) {
  if (togglingId.value != null) return;
  togglingId.value = id;
  try {
    await screenshotApi.setScreenshotVisibility({ id, isPublic });
    await refreshRom();
  } catch (error: unknown) {
    snackbar.error(
      t("rom.screenshot-visibility-failed", { error: errorMessage(error) }),
      { icon: "mdi-close-circle" },
    );
  } finally {
    togglingId.value = null;
  }
}
</script>

<template>
  <div class="r-v2-shots">
    <!-- RomM presents shared screenshots read-only. -->
    <section v-if="romScreenshots.length > 0" class="r-v2-shots__section">
      <header class="r-v2-shots__head">
        <div class="r-v2-shots__head-text">
          <h3 class="r-v2-shots__title">
            {{ t("rom.screenshots-section-rom") }}
          </h3>
          <p class="r-v2-shots__subtitle">
            {{ t("rom.screenshots-section-rom-desc") }}
          </p>
        </div>
      </header>

      <ScreenshotsTab :screenshots="romScreenshots" />
    </section>

    <!-- My (per-user) screenshots -->
    <section class="r-v2-shots__section">
      <header class="r-v2-shots__head">
        <div class="r-v2-shots__head-text">
          <h3 class="r-v2-shots__title">
            {{ t("rom.screenshots-section-mine") }}
          </h3>
        </div>
        <RBtn
          v-if="myScreenshots.length > 0"
          variant="outlined"
          size="small"
          prepend-icon="mdi-cloud-upload-outline"
          @click="myDz?.open()"
        >
          {{ t("common.upload") }}
        </RBtn>
      </header>

      <RDropzone
        v-if="myScreenshots.length === 0"
        :title="t('rom.screenshots-empty')"
        :hint="t('common.dropzone-hint')"
        :active-title="t('common.dropzone-drag-over')"
        :input-label="t('rom.upload-screenshots')"
        accept="image/*"
        multiple
        @files="handleMyFiles"
      />
      <RDropzone
        v-else
        ref="myDz"
        overlay
        :release-label="t('common.dropzone-drag-over')"
        :input-label="t('rom.upload-screenshots')"
        accept="image/*"
        multiple
        @files="handleMyFiles"
      >
        <ScreenshotsTab
          :screenshots="myScreenshots"
          deletable
          togglable
          :toggling-id="togglingId"
          @delete="deleteMyScreenshot"
          @toggle-visibility="toggleVisibility"
        />
      </RDropzone>
    </section>

    <!-- Community (others' public) screenshots -->
    <section v-if="communityScreenshots.length > 0" class="r-v2-shots__section">
      <header class="r-v2-shots__head">
        <div class="r-v2-shots__head-text">
          <h3 class="r-v2-shots__title">
            {{ t("rom.screenshots-section-community") }}
          </h3>
        </div>
      </header>
      <ScreenshotsTab :screenshots="communityScreenshots" />
    </section>
  </div>
</template>

<style scoped>
.r-v2-shots {
  display: flex;
  flex-direction: column;
  gap: 24px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--r-color-border-strong) transparent;
  padding-right: 4px;
}

.r-v2-shots__section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.r-v2-shots__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.r-v2-shots__title {
  margin: 0;
  font-size: 14px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg);
}
.r-v2-shots__subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--r-color-fg-muted);
}
</style>
