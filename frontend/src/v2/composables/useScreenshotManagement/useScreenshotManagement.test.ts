import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, ref } from "vue";
import type { RomOwnedMediaSchema } from "@/__generated__";
import uploadStore from "@/stores/upload";
import storeAuth from "@/v2/data/adapters/legacy/stores/auth";
import storePermissions from "@/v2/data/adapters/legacy/stores/permissions";
import type { DetailedRom } from "@/v2/data/adapters/legacy/stores/roms";
import { useScreenshotManagement } from "./index";

const m = vi.hoisted(() => ({
  translate: vi.fn((key: string) => key),
  getRom: vi.fn(),
  setOwnedMediaPlacement: vi.fn(),
  removeOwnedMediaPlacement: vi.fn(),
  deleteOwnedMedia: vi.fn(),
  refreshOwnedMedia: vi.fn(),
  deleteScreenshot: vi.fn(),
  setScreenshotVisibility: vi.fn(),
  uploadGalleryScreenshots: vi.fn(),
  confirm: vi.fn(),
  success: vi.fn(),
  warning: vi.fn(),
  error: vi.fn(),
  setCurrentRom: vi.fn(),
  update: vi.fn(),
  reset: vi.fn(),
}));
vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: m.translate }) }));
vi.mock("@/v2/composables/useConfirm", () => ({ useConfirm: () => m.confirm }));
vi.mock("@/v2/composables/useSnackbar", () => ({ useSnackbar: () => m }));
vi.mock("@/v2/data/adapters/legacy/services/api/rom", () => ({ default: m }));
vi.mock("@/v2/data/adapters/legacy/services/api/screenshot", () => ({
  default: m,
}));
vi.mock("@/v2/data/adapters/legacy/stores/roms", () => ({ default: () => m }));
vi.mock("@/v2/data/adapters/legacy/stores/upload", () => ({
  default: () => m,
}));

function provider(id = 7, placements: RomOwnedMediaSchema["placements"] = []) {
  return {
    id,
    origin: "provider",
    role: "screenshot",
    state: "active",
    display_label: "IGDB",
    placements,
  } as RomOwnedMediaSchema;
}
function rom(id = 1) {
  return {
    id,
    updated_at: "v1",
    owned_media: [provider()],
    all_user_screenshots: [
      { id: 10, user_id: 1, download_path: "/own", is_public: false },
      { id: 7, user_id: 2, download_path: "/community", is_public: true },
    ],
  } as DetailedRom;
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function setup() {
  const current = ref(rom());
  let actions!: ReturnType<typeof useScreenshotManagement>;
  const wrapper = mount(
    defineComponent({
      setup() {
        actions = useScreenshotManagement(() => current.value);
        return () => null;
      },
    }),
  );
  return { current, actions, wrapper };
}
beforeEach(() => {
  setActivePinia(createPinia());
  vi.resetAllMocks();
  storeAuth().$patch({ user: { id: 1 } });
  storePermissions().$patch({ isAdmin: true });
  m.translate.mockImplementation((key: string) => key);
  m.reset.mockImplementation(() => uploadStore().reset());
  m.confirm.mockResolvedValue(true);
  m.getRom.mockResolvedValue({ data: rom() });
});

describe("screenshot action ownership", () => {
  it("dispatches provider placement endpoints with captured version and position zero", async () => {
    const { actions, current } = setup();
    const item = provider(7, [
      { id: 1, media_id: 7, surface: "overview", position: 0 },
      { id: 2, media_id: 7, surface: "background", position: 3 },
    ]);
    current.value.owned_media = [
      item,
      provider(8, [{ id: 3, media_id: 8, surface: "overview", position: 4 }]),
    ];
    expect(actions.placementPosition(item, "overview")).toBe(0);
    await actions.togglePlacement(item, "overview");
    expect(m.removeOwnedMediaPlacement).toHaveBeenCalledWith({
      romId: 1,
      mediaId: 7,
      surface: "overview",
      expectedVersion: "v1",
    });
    await actions.togglePlacement(provider(8), "background");
    expect(m.setOwnedMediaPlacement).toHaveBeenCalledWith({
      romId: 1,
      mediaId: 8,
      surface: "background",
      expectedVersion: "v1",
    });
    expect(item.placements).toEqual([
      { id: 1, media_id: 7, surface: "overview", position: 0 },
      { id: 2, media_id: 7, surface: "background", position: 3 },
    ]);
    expect(m.setCurrentRom).toHaveBeenCalledWith(
      expect.objectContaining({ id: 1 }),
    );
    expect(m.update).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));
  });
  it("protects community and provider IDs from personal operations even for administrators", async () => {
    const { actions } = setup();
    await actions.deleteMyScreenshot(7);
    await actions.toggleVisibility(7, false);
    expect(m.confirm).not.toHaveBeenCalled();
    expect(m.deleteScreenshot).not.toHaveBeenCalled();
    expect(m.setScreenshotVisibility).not.toHaveBeenCalled();
    await actions.toggleVisibility(10, true);
    await actions.deleteMyScreenshot(10);
    expect(m.setScreenshotVisibility).toHaveBeenCalledWith({
      id: 10,
      isPublic: true,
    });
    expect(m.deleteScreenshot).toHaveBeenCalledWith({ id: 10 });
    expect(m.confirm).toHaveBeenCalledWith(
      expect.objectContaining({ tone: "danger" }),
    );
  });
  it("rejects forged provider items and permits viewer personal actions", async () => {
    storePermissions().$patch({ isAdmin: false, grants: [] });
    const { actions } = setup();
    await actions.togglePlacement(provider(), "overview");
    await actions.deleteProviderScreenshot(provider());
    await actions.refreshProviderScreenshots();
    await actions.toggleVisibility(10, true);
    expect(m.setOwnedMediaPlacement).not.toHaveBeenCalled();
    expect(m.deleteOwnedMedia).not.toHaveBeenCalled();
    expect(m.refreshOwnedMedia).not.toHaveBeenCalled();
    expect(m.setScreenshotVisibility).toHaveBeenCalled();
    storePermissions().$patch({ isAdmin: true });
    await actions.togglePlacement(
      { ...provider(), origin: "upload" } as RomOwnedMediaSchema,
      "overview",
    );
    expect(m.setOwnedMediaPlacement).not.toHaveBeenCalled();
  });
  it("updates resource-scoped capabilities on navigation", () => {
    storePermissions().$patch({
      isAdmin: false,
      grants: [
        { action: "rom.edit", scope: { kind: "rom", id: 1 } },
        { action: "rom.refresh", scope: { kind: "rom", id: 2 } },
      ],
    });
    const { actions, current } = setup();
    expect(actions.canManage.value).toBe(true);
    expect(actions.canRefresh.value).toBe(false);
    current.value = rom(2);
    expect(actions.canManage.value).toBe(false);
    expect(actions.canRefresh.value).toBe(true);
  });
  it("reserves provider lane before confirmation and rechecks permission", async () => {
    const confirmation = deferred<boolean>();
    m.confirm.mockReturnValue(confirmation.promise);
    const { actions } = setup();
    const deletion = actions.deleteProviderScreenshot(provider());
    await actions.togglePlacement(provider(), "overview");
    await actions.refreshProviderScreenshots();
    expect(m.setOwnedMediaPlacement).not.toHaveBeenCalled();
    expect(m.refreshOwnedMedia).not.toHaveBeenCalled();
    confirmation.resolve(false);
    await deletion;
    expect(m.deleteOwnedMedia).not.toHaveBeenCalled();
    m.confirm.mockImplementation(async () => {
      storePermissions().$patch({ isAdmin: false, grants: [] });
      return true;
    });
    await actions.deleteProviderScreenshot(provider());
    expect(m.deleteOwnedMedia).not.toHaveBeenCalled();
  });
  it("ignores late confirmation and old finally cannot clear successor lane", async () => {
    const confirmation = deferred<boolean>();
    m.confirm.mockReturnValue(confirmation.promise);
    const mutation = deferred<void>();
    m.setOwnedMediaPlacement.mockReturnValue(mutation.promise);
    const { actions, current } = setup();
    const old = actions.deleteProviderScreenshot(provider());
    current.value = rom(2);
    const next = actions.togglePlacement(provider(), "overview");
    confirmation.resolve(true);
    await old;
    expect(m.deleteOwnedMedia).not.toHaveBeenCalled();
    expect(actions.mutatingId.value).toBe(7);
    mutation.resolve();
    await next;
    expect(actions.mutatingId.value).toBe(null);
  });
  it("cannot resurrect A after A-B-A navigation or after unmount", async () => {
    const response = deferred<{ data: DetailedRom }>();
    m.getRom.mockReturnValue(response.promise);
    const { actions, current, wrapper } = setup();
    const pending = actions.refreshCanonical();
    current.value = rom(2);
    current.value = rom(1);
    response.resolve({ data: rom() });
    await pending;
    expect(m.setCurrentRom).not.toHaveBeenCalled();
    const afterUnmount = actions.refreshCanonical();
    wrapper.unmount();
    await afterUnmount;
    expect(m.update).not.toHaveBeenCalled();
  });
  it("reconciles 409 once without retrying destruction", async () => {
    m.deleteOwnedMedia.mockRejectedValue({
      isAxiosError: true,
      response: { status: 409, data: { detail: "stale" } },
    });
    const { actions } = setup();
    await actions.deleteProviderScreenshot(provider());
    expect(m.deleteOwnedMedia).toHaveBeenCalledTimes(1);
    expect(m.getRom).toHaveBeenCalledTimes(1);
    expect(m.warning).toHaveBeenCalledWith("common.error");
  });
  it("reports canonical refresh errors without success", async () => {
    m.getRom.mockRejectedValue(new Error("refresh unavailable"));
    const { actions } = setup();
    await actions.deleteMyScreenshot(10);
    expect(m.error).toHaveBeenCalledWith("refresh unavailable");
    expect(m.success).not.toHaveBeenCalled();
  });
});

describe("settled screenshot uploads", () => {
  const files = [new File(["a"], "a.png"), new File(["b"], "b.png")];
  it("ignores empty batches and overlaps, then permits a later batch", async () => {
    const pending = deferred<PromiseSettledResult<unknown>[]>();
    m.uploadGalleryScreenshots
      .mockReturnValueOnce(pending.promise)
      .mockResolvedValue([]);
    const { actions } = setup();
    await actions.handleMyFiles([]);
    expect(m.uploadGalleryScreenshots).not.toHaveBeenCalled();
    const first = actions.handleMyFiles(files);
    expect(actions.uploading.value).toBe(true);
    await actions.handleMyFiles(files);
    expect(m.uploadGalleryScreenshots).toHaveBeenCalledTimes(1);
    pending.resolve([
      { status: "fulfilled", value: {} },
      { status: "fulfilled", value: {} },
    ]);
    await first;
    expect(actions.uploading.value).toBe(false);
    expect(m.getRom).toHaveBeenCalledTimes(1);
    expect(m.reset).toHaveBeenCalledTimes(1);
    await actions.handleMyFiles([files[0]]);
    expect(m.uploadGalleryScreenshots).toHaveBeenCalledTimes(2);
  });
  it("reports partial counts and retains failed progress with useful detail", async () => {
    const progress = uploadStore();
    progress.start("a.png");
    progress.start("b.png");
    progress.fail("b.png", "invalid image");
    m.uploadGalleryScreenshots.mockResolvedValue([
      { status: "fulfilled", value: {} },
      { status: "rejected", reason: new Error("invalid image") },
    ]);
    const { actions } = setup();
    await actions.handleMyFiles(files);
    expect(m.reset).not.toHaveBeenCalled();
    expect(
      progress.files.find((file) => file.filename === "b.png")?.failureReason,
    ).toBe("invalid image");
    expect(m.translate).toHaveBeenCalledWith("rom.screenshots-upload-partial", {
      uploaded: 1,
      failed: 1,
    });
    expect(m.warning).toHaveBeenCalledWith("rom.screenshots-upload-partial");
    expect(m.error).toHaveBeenCalledWith("invalid image");
    expect(m.success).not.toHaveBeenCalled();
    expect(m.getRom).toHaveBeenCalledTimes(1);
  });
  it("reports all failures and retains records without fetching", async () => {
    uploadStore().start("a.png");
    uploadStore().fail("a.png", "rejected");
    m.uploadGalleryScreenshots.mockResolvedValue([
      { status: "rejected", reason: new Error("rejected") },
    ]);
    const { actions } = setup();
    await actions.handleMyFiles([files[0]]);
    expect(m.warning).toHaveBeenCalledWith("rom.no-screenshots-uploaded");
    expect(m.getRom).not.toHaveBeenCalled();
    expect(m.reset).not.toHaveBeenCalled();
    expect(uploadStore().files[0].failed).toBe(true);
  });
  it("marks newly observed own IDs without reordering or mixing provider IDs", async () => {
    m.uploadGalleryScreenshots.mockResolvedValue([
      { status: "fulfilled", value: { id: 11 } },
    ]);
    const updated = rom();
    updated.all_user_screenshots = [
      ...updated.all_user_screenshots,
      { ...updated.all_user_screenshots[0], id: 11 },
      { ...updated.all_user_screenshots[1], id: 12 },
    ];
    m.getRom.mockResolvedValue({ data: updated });
    const { actions } = setup();
    await actions.handleMyFiles([files[0]]);
    expect(actions.newlyUploadedIds.value).toEqual([11]);
    expect(m.setCurrentRom).toHaveBeenCalledWith(updated);
    expect(updated.all_user_screenshots.map((item) => item.id)).toEqual([
      10, 7, 11, 12,
    ]);
  });
  it("does not claim canonical success when refresh fails", async () => {
    m.uploadGalleryScreenshots.mockResolvedValue([
      { status: "fulfilled", value: {} },
    ]);
    m.getRom.mockRejectedValue(new Error("network detail"));
    const { actions } = setup();
    await actions.handleMyFiles([files[0]]);
    expect(m.error).toHaveBeenCalledWith("rom.screenshots-update-error");
    expect(m.success).not.toHaveBeenCalled();
    expect(actions.newlyUploadedIds.value).toEqual([]);
  });
  it.each(["upload", "fetch"])(
    "suppresses stale %s completion, store writes and progress reset",
    async (stage) => {
      const settlement = deferred<PromiseSettledResult<unknown>[]>();
      const response = deferred<{ data: DetailedRom }>();
      m.uploadGalleryScreenshots.mockReturnValue(
        stage === "upload"
          ? settlement.promise
          : Promise.resolve([{ status: "fulfilled", value: {} }]),
      );
      m.getRom.mockReturnValue(response.promise);
      const { actions, current } = setup();
      const operation = actions.handleMyFiles([files[0]]);
      await Promise.resolve();
      current.value = rom(2);
      settlement.resolve([{ status: "fulfilled", value: {} }]);
      response.resolve({ data: rom() });
      await operation;
      expect(m.setCurrentRom).not.toHaveBeenCalled();
      expect(m.update).not.toHaveBeenCalled();
      expect(m.reset).not.toHaveBeenCalled();
      expect(m.success).not.toHaveBeenCalled();
      expect(m.warning).not.toHaveBeenCalled();
      expect(m.error).not.toHaveBeenCalled();
    },
  );
  it("releases the upload guard on unexpected API rejection", async () => {
    m.uploadGalleryScreenshots.mockRejectedValue(
      new Error("upload unavailable"),
    );
    const { actions } = setup();
    await actions.handleMyFiles([files[0]]);
    expect(actions.uploading.value).toBe(false);
    expect(m.error).toHaveBeenCalledWith("upload unavailable");
  });
  it("keeps the existing service one POST per file and inherited duplicate-name progress", async () => {
    const service = await import("@/services/api/screenshot");
    const post = vi
      .spyOn(service.screenshotApi, "post")
      .mockResolvedValue({ data: { id: 11 } });
    m.uploadGalleryScreenshots.mockImplementation(
      service.default.uploadGalleryScreenshots,
    );
    const { actions } = setup();
    await actions.handleMyFiles([files[0], new File(["other"], "a.png")]);
    expect(m.uploadGalleryScreenshots).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledTimes(2);
    expect(
      post.mock.calls.every(
        ([path, , config]) =>
          path === "/screenshots" && config?.params.rom_id === 1,
      ),
    ).toBe(true);
    expect(m.reset).toHaveBeenCalledTimes(1);
    const progress = uploadStore();
    progress.start("same.png");
    progress.start("same.png");
    progress.update("same.png", {
      loaded: 1,
      total: 1,
      bytes: 1,
      lengthComputable: true,
      progress: 1,
    });
    expect(progress.files.map((file) => file.finished)).toEqual([true, false]);
    post.mockRestore();
  });
});
