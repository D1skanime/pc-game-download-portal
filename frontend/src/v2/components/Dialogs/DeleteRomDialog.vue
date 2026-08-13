<script setup lang="ts">
// Catalog-only removal keeps original files unchanged. Optional exclusions
// prevent successfully removed entries from returning in later scans.
import { RBtn, RCheckbox, RDialog, RIcon } from "@v2/lib";
import type { Emitter } from "mitt";
import { inject, onBeforeUnmount, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter, useRoute } from "vue-router";
import { ROUTES } from "@/plugins/router";
import configApi from "@/services/api/config";
import romApi from "@/services/api/rom";
import storeConfig from "@/stores/config";
import storeRoms, { type SimpleRom } from "@/stores/roms";
import type { Events } from "@/types/emitter";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import storeGalleryRoms from "@/v2/stores/galleryRoms";
import storeGallerySelection from "@/v2/stores/gallerySelection";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const show = ref(false);
const romsStore = storeRoms();
const galleryRomsStore = storeGalleryRoms();
const gallerySelectionStore = storeGallerySelection();
const roms = ref<SimpleRom[]>([]);
const excludeOnDelete = ref(false);
const platformId = ref<number>(0);
const deleting = ref(false);
const emitter = inject<Emitter<Events>>("emitter");
const snackbar = useSnackbar();
const configStore = storeConfig();

const openHandler = (romsToDelete: SimpleRom[]) => {
  roms.value = romsToDelete;
  platformId.value = romsToDelete[0]?.platform_id ?? 0;
  show.value = true;
};
emitter?.on("showDeleteRomDialog", openHandler);
onBeforeUnmount(() => emitter?.off("showDeleteRomDialog", openHandler));

function coverFor(rom: SimpleRom): string | null {
  return rom.path_cover_small ?? rom.url_cover ?? null;
}

async function deleteRoms() {
  if (deleting.value) return;
  deleting.value = true;

  // Snapshot the dialog state up front: the dialog is a singleton, so a
  // fresh `showDeleteRomDialog` event could replace these refs while the
  // request is in flight. Acting on the snapshot keeps the response tied
  // to the ROMs it actually processed.
  const targetRoms = roms.value;
  const targetPlatformId = platformId.value;
  const exclude = excludeOnDelete.value;

  try {
    const response = await romApi.deleteRoms({ roms: targetRoms });
    // The backend removes each catalog entry independently. Only prune the
    // ROMs it actually removed so a failed subset stays visible and
    // selected for the user to retry.
    const failedIds = new Set(response.data.failed_ids);
    const deletedRoms = targetRoms.filter((rom) => !failedIds.has(rom.id));
    snackbar.success(
      t("rom.removed-from-catalog", {
        count: response.data.successful_items,
      }),
      { icon: "mdi-check-bold" },
    );
    if (exclude) {
      for (const rom of deletedRoms) {
        const type = rom.has_simple_single_file
          ? "EXCLUDED_SINGLE_FILES"
          : "EXCLUDED_MULTI_FILES";
        configApi.addExclusion({
          exclusionValue: rom.fs_name,
          exclusionType: type,
        });
        configStore.addExclusion(type, rom.fs_name);
      }
    }
    romsStore.resetSelection();
    // Drop the deleted ROMs from the gallery selection
    gallerySelectionStore.removeIds(deletedRoms.map((rom) => rom.id));
    romsStore.remove(deletedRoms);
    galleryRomsStore.remove(deletedRoms);
    romsStore.setRecentRoms(
      romsStore.recentRoms.filter(
        (r) => !deletedRoms.some((rom) => rom.id === r.id),
      ),
    );
    romsStore.setContinuePlayingRoms(
      romsStore.continuePlayingRoms.filter(
        (r) => !deletedRoms.some((rom) => rom.id === r.id),
      ),
    );
    emitter?.emit("refreshDrawer", null);
    closeDialog();
    // Only leave the single-ROM route when that ROM was actually deleted.
    if (route.name === "rom" && deletedRoms.length > 0) {
      router.push({
        name: ROUTES.PLATFORM,
        params: { platform: targetPlatformId },
      });
    }
  } catch (error: unknown) {
    console.error(error);
    const axiosErr = error as { response?: { data?: { detail?: string } } };
    snackbar.error(
      axiosErr.response?.data?.detail ?? t("rom.delete-roms-failed"),
      {
        icon: "mdi-close-circle",
      },
    );
  } finally {
    deleting.value = false;
  }
}

function closeDialog() {
  roms.value = [];
  excludeOnDelete.value = false;
  show.value = false;
}
</script>

<template>
  <RDialog
    v-model="show"
    icon="mdi-delete-outline"
    scroll-content
    width="560"
    @close="closeDialog"
  >
    <template #header>
      <span>{{ t("rom.remove-from-catalog-title", roms.length) }}</span>
    </template>
    <template #toolbar>
      <div class="r-v2-del-rom__toolbar">
        <p class="r-v2-del-rom__summary">
          {{ t("rom.remove-from-catalog-body", roms.length) }}
        </p>
        <p class="r-v2-del-rom__assurance">
          {{ t("rom.remove-from-catalog-source-unchanged") }}
        </p>
        <p class="r-v2-del-rom__assurance">
          {{ t("rom.remove-from-catalog-retained-value") }}
        </p>
      </div>
    </template>
    <template #content>
      <ul class="r-v2-del-rom__list">
        <li v-for="rom in roms" :key="rom.id" class="r-v2-del-rom__row">
          <div class="r-v2-del-rom__cover">
            <img
              v-if="coverFor(rom)"
              :src="coverFor(rom)!"
              :alt="rom.name ?? ''"
            />
            <div v-else class="r-v2-del-rom__cover-placeholder">
              <RIcon icon="mdi-disc" size="18" />
            </div>
          </div>
          <div class="r-v2-del-rom__meta">
            <p class="r-v2-del-rom__name" :title="rom.name ?? undefined">
              {{ rom.name || rom.fs_name }}
            </p>
            <p class="r-v2-del-rom__file" :title="rom.fs_name">
              {{ rom.fs_name }}
            </p>
          </div>
        </li>
      </ul>
    </template>
    <template #append>
      <div class="r-v2-del-rom__append">
        <RCheckbox
          v-model="excludeOnDelete"
          hide-details
          :label="t('rom.remove-from-catalog-future-scan-exclusion')"
        />
      </div>
    </template>
    <template #footer>
      <RBtn variant="text" :disabled="deleting" @click="closeDialog">
        {{ t("common.cancel") }}
      </RBtn>
      <div style="flex: 1" />
      <RBtn
        variant="translucent"
        color="error"
        prepend-icon="mdi-delete"
        :loading="deleting"
        :disabled="deleting || roms.length === 0"
        @click="deleteRoms"
      >
        {{ t("rom.remove-from-catalog-confirm") }}
      </RBtn>
    </template>
  </RDialog>
</template>

<style scoped>
.r-v2-del-rom__toolbar {
  display: flex;
  align-items: flex-start;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  font-size: 12px;
  color: var(--r-color-fg-muted);
}
.r-v2-del-rom__summary,
.r-v2-del-rom__assurance {
  margin: 0;
  line-height: 1.4;
}
.r-v2-del-rom__summary {
  color: var(--r-color-fg-secondary);
}
.r-v2-del-rom__assurance {
  color: var(--r-color-fg-muted);
}

.r-v2-del-rom__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 360px;
  overflow-y: auto;
}

.r-v2-del-rom__row {
  display: grid;
  grid-template-columns: 36px 1fr;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: var(--r-color-bg-elevated);
  border: 1px solid var(--r-color-border);
  border-radius: var(--r-radius-md);
}

.r-v2-del-rom__cover {
  width: 36px;
  aspect-ratio: 3 / 4;
  border-radius: var(--r-radius-sm);
  overflow: hidden;
  background: var(--r-color-cover-placeholder);
  display: grid;
  place-items: center;
}
.r-v2-del-rom__cover img {
  width: 100%;
  height: 100%;
  /* Show the whole cover at its natural aspect (no crop); the slot stays a
     uniform width so the delete list's rows keep their alignment. */
  object-fit: contain;
  display: block;
}
.r-v2-del-rom__cover-placeholder {
  color: var(--r-color-fg-faint);
}

.r-v2-del-rom__meta {
  min-width: 0;
}
.r-v2-del-rom__name {
  margin: 0;
  font-size: 13px;
  font-weight: var(--r-font-weight-medium);
  color: var(--r-color-fg);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.r-v2-del-rom__file {
  margin: 2px 0 0;
  font-size: 11px;
  font-family: var(--r-font-family-mono, monospace);
  color: var(--r-color-fg-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.r-v2-del-rom__append {
  padding: 10px 14px 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
