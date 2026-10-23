import axios from "axios";
import { storeToRefs } from "pinia";
import { computed, onScopeDispose, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type {
  RomOwnedMediaSchema,
  RomOwnedMediaSurface,
} from "@/__generated__";
import type { ScreenshotItem } from "@/v2/components/GameDetails/ScreenshotsTab.vue";
import { useCan } from "@/v2/composables/useCan";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import romApi from "@/v2/data/adapters/legacy/services/api/rom";
import screenshotApi from "@/v2/data/adapters/legacy/services/api/screenshot";
import storeAuth from "@/v2/data/adapters/legacy/stores/auth";
import storeRoms, {
  type DetailedRom,
} from "@/v2/data/adapters/legacy/stores/roms";
import storeUpload from "@/v2/data/adapters/legacy/stores/upload";

/** Owns screenshot mutations; provider media and personal gallery IDs are separate domains. */
export function useScreenshotManagement(rom: () => DetailedRom) {
  const { t } = useI18n();
  const snackbar = useSnackbar();
  const confirm = useConfirm();
  const romsStore = storeRoms();
  const uploadStore = storeUpload();
  const { user } = storeToRefs(storeAuth());
  const scope = {
    kind: "rom" as const,
    get id() {
      return rom().id;
    },
  };
  const canManage = useCan("rom.edit", scope);
  const canRefresh = useCan("rom.refresh", scope);
  const canUpload = computed(() => user.value?.id != null);
  const providerScreenshots = computed(() =>
    (rom().owned_media ?? []).filter(
      (item) =>
        item.origin === "provider" &&
        item.role === "screenshot" &&
        item.state === "active",
    ),
  );
  const allUserScreenshots = computed(() => rom().all_user_screenshots ?? []);
  const myScreenshots = computed<ScreenshotItem[]>(() =>
    allUserScreenshots.value
      .filter(
        (item) => user.value?.id != null && item.user_id === user.value.id,
      )
      .map((item) => ({
        id: item.id,
        url: item.download_path,
        isOwn: true,
        isPublic: Boolean(item.is_public),
      })),
  );
  const communityScreenshots = computed<ScreenshotItem[]>(() =>
    allUserScreenshots.value
      .filter(
        (item) => user.value?.id == null || item.user_id !== user.value.id,
      )
      .map((item) => ({
        id: item.id,
        url: item.download_path,
        isOwn: false,
        isPublic: true,
        username: item.username,
        userId: item.user_id,
        userAvatarPath: item.user_avatar_path,
        userUpdatedAt: item.user_updated_at,
      })),
  );
  const providerUrls = computed(() =>
    providerScreenshots.value.map((item) => mediaContentUrl(item.id)),
  );
  const refreshing = ref(false);
  const mutatingId = ref<number | null>(null);
  const togglingId = ref<number | null>(null);
  const deletingId = ref<number | null>(null);
  const uploading = ref(false);
  const newlyUploadedIds = ref<number[]>([]);
  let generation = 0;
  let active = true;
  let fetchSequence = 0;
  let providerLane: symbol | null = null;
  let personalLane: symbol | null = null;
  watch(
    [() => rom().id, () => user.value?.id],
    () => {
      generation++;
      providerLane = personalLane = null;
      refreshing.value = false;
      mutatingId.value = togglingId.value = deletingId.value = null;
      newlyUploadedIds.value = [];
    },
    { flush: "sync" },
  );
  onScopeDispose(() => {
    active = false;
    generation++;
  });
  function capture() {
    return { romId: rom().id, expectedVersion: rom().updated_at, generation };
  }
  type Context = ReturnType<typeof capture>;
  function current(context: Context) {
    return (
      active && generation === context.generation && rom().id === context.romId
    );
  }
  function mediaContentUrl(mediaId: number) {
    return `/api/roms/${rom().id}/media/${mediaId}/content`;
  }
  function hasPlacement(
    item: RomOwnedMediaSchema,
    surface: RomOwnedMediaSurface,
  ) {
    return (
      item.placements?.some((placement) => placement.surface === surface) ??
      false
    );
  }
  function placementPosition(
    item: RomOwnedMediaSchema,
    surface: RomOwnedMediaSurface,
  ) {
    return item.placements?.find((placement) => placement.surface === surface)
      ?.position;
  }
  function owned(id: number) {
    return myScreenshots.value.some((item) => item.id === id);
  }
  function provider(item: RomOwnedMediaSchema) {
    return item.origin === "provider" &&
      item.role === "screenshot" &&
      item.state === "active"
      ? providerScreenshots.value.find((candidate) => candidate.id === item.id)
      : undefined;
  }
  function errorMessage(error: unknown) {
    if (axios.isAxiosError(error))
      return typeof error.response?.data?.detail === "string"
        ? error.response.data.detail
        : error.message;
    return error instanceof Error ? error.message : String(error);
  }
  // A generation survives canonical object replacement, but never route or identity changes.
  async function refreshCanonical(context = capture()) {
    if (!current(context)) return;
    const sequence = ++fetchSequence;
    const { data } = await romApi.getRom({ romId: context.romId });
    if (
      !current(context) ||
      sequence !== fetchSequence ||
      data.id !== context.romId ||
      (romsStore.currentRom && romsStore.currentRom.id !== context.romId)
    )
      return;
    romsStore.setCurrentRom(data);
    romsStore.update(data);
    return data;
  }
  async function recoverFromConflict(error: unknown, context: Context) {
    if (axios.isAxiosError(error) && error.response?.status === 409) {
      await refreshCanonical(context);
      if (current(context)) snackbar.warning(t("common.error"));
      return true;
    }
    return false;
  }
  async function runProvider(
    itemId: number | null,
    permitted: () => boolean,
    operation: (context: Context) => Promise<unknown>,
    confirmation?: () => Promise<boolean>,
    successKey?: string,
  ) {
    if (!active || providerLane || !permitted()) return;
    const context = capture();
    const token = Symbol();
    providerLane = token;
    mutatingId.value = itemId;
    refreshing.value = itemId === null;
    try {
      if (confirmation && !(await confirmation())) return;
      if (!current(context) || !permitted() || providerLane !== token) return;
      await operation(context);
      const canonical = await refreshCanonical(context);
      if (canonical && current(context) && successKey)
        snackbar.success(t(successKey));
    } catch (error) {
      if (!current(context)) return;
      try {
        if (!(await recoverFromConflict(error, context)) && current(context))
          snackbar.error(errorMessage(error));
      } catch (refreshError) {
        if (current(context)) snackbar.error(errorMessage(refreshError));
      }
    } finally {
      if (providerLane === token) {
        providerLane = null;
        mutatingId.value = null;
        refreshing.value = false;
      }
    }
  }
  async function togglePlacement(
    item: RomOwnedMediaSchema,
    surface: RomOwnedMediaSurface,
  ) {
    const candidate = provider(item);
    if (!candidate || !["overview", "background"].includes(surface)) return;
    return runProvider(
      item.id,
      () => canManage.value && Boolean(provider(item)),
      async (context) => {
        const args = {
          romId: context.romId,
          mediaId: item.id,
          surface,
          expectedVersion: context.expectedVersion,
        };
        return hasPlacement(candidate, surface)
          ? romApi.removeOwnedMediaPlacement(args)
          : romApi.setOwnedMediaPlacement(args);
      },
    );
  }
  async function refreshProviderScreenshots() {
    return runProvider(
      null,
      () => canRefresh.value,
      (context) =>
        romApi.refreshOwnedMedia({
          romId: context.romId,
          expectedVersion: context.expectedVersion,
        }),
      undefined,
      "common.refresh",
    );
  }
  async function deleteProviderScreenshot(item: RomOwnedMediaSchema) {
    if (!provider(item)) return;
    return runProvider(
      item.id,
      () => canManage.value && Boolean(provider(item)),
      (context) =>
        romApi.deleteOwnedMedia({
          romId: context.romId,
          mediaId: item.id,
          expectedVersion: context.expectedVersion,
        }),
      () =>
        confirm({
          title: t("rom.provider-screenshot-remove-title"),
          body: t("rom.provider-screenshot-remove-body"),
          confirmText: t("rom.provider-screenshot-remove-confirm"),
          tone: "danger",
        }),
      "rom.owned-media-deleted",
    );
  }
  async function runPersonal(id: number, visibility?: boolean) {
    if (!active || personalLane || !owned(id)) return;
    const context = capture();
    const token = Symbol();
    personalLane = token;
    if (visibility === undefined) deletingId.value = id;
    else togglingId.value = id;
    try {
      if (
        visibility === undefined &&
        !(await confirm({
          title: t("rom.delete-screenshot-title"),
          body: t("rom.delete-screenshot-body"),
          confirmText: t("common.delete"),
          tone: "danger",
        }))
      )
        return;
      if (!current(context) || !owned(id) || personalLane !== token) return;
      if (visibility === undefined)
        await screenshotApi.deleteScreenshot({ id });
      else
        await screenshotApi.setScreenshotVisibility({
          id,
          isPublic: visibility,
        });
      const canonical = await refreshCanonical(context);
      if (canonical && current(context) && visibility === undefined)
        snackbar.success(t("rom.screenshot-removed"));
    } catch (error) {
      if (current(context)) snackbar.error(errorMessage(error));
    } finally {
      if (personalLane === token) {
        personalLane = null;
        togglingId.value = deletingId.value = null;
      }
    }
  }
  function deleteMyScreenshot(id: number) {
    return runPersonal(id);
  }
  function toggleVisibility(id: number, isPublic: boolean) {
    return runPersonal(id, isPublic);
  }
  function reportUpload(responses: PromiseSettledResult<unknown>[]) {
    const successful = responses.filter(
      (item) => item.status === "fulfilled",
    ).length;
    if (successful === responses.length) uploadStore.reset();
    successful
      ? snackbar.success(
          t("rom.screenshots-uploaded-n", successful, {
            named: { n: successful },
          }),
        )
      : snackbar.warning(t("rom.no-screenshots-uploaded"));
  }
  async function handleMyFiles(files: File[]) {
    if (!files.length) return;
    const responses = await screenshotApi.uploadGalleryScreenshots({
      romId: rom().id,
      filesToUpload: files,
    });
    reportUpload(responses);
    if (responses.some((item) => item.status === "fulfilled")) {
      try {
        await refreshCanonical();
      } catch (error) {
        snackbar.error(errorMessage(error));
      }
    }
  }
  return {
    providerScreenshots,
    providerUrls,
    myScreenshots,
    communityScreenshots,
    canManage,
    canRefresh,
    canUpload,
    refreshing,
    mutatingId,
    togglingId,
    deletingId,
    uploading,
    newlyUploadedIds,
    mediaContentUrl,
    hasPlacement,
    placementPosition,
    refreshCanonical,
    togglePlacement,
    refreshProviderScreenshots,
    deleteProviderScreenshot,
    deleteMyScreenshot,
    toggleVisibility,
    handleMyFiles,
  };
}
