import { flushPromises, shallowMount } from "@vue/test-utils";
import mitt from "mitt";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, nextTick } from "vue";
import type { Events } from "@/types/emitter";
import ManualSubtab from "@/v2/components/GameDetails/ManualSubtab.vue";

const mocks = vi.hoisted(() => ({
  canEdit: true,
  emitterEvents: vi.fn(),
  romApi: {
    getRom: vi.fn(),
    redownloadManual: vi.fn(),
    uploadManual: vi.fn(),
  },
  romsStore: {
    currentRom: null as Record<string, unknown> | null,
    update: vi.fn(),
  },
  snackbar: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));
vi.mock("@/services/api/rom", () => ({ default: mocks.romApi }));
vi.mock("@/stores/roms", () => ({ default: () => mocks.romsStore }));
vi.mock("@/v2/composables/useCan", () => ({
  useCan: () => computed(() => mocks.canEdit),
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => mocks.snackbar,
}));
vi.mock("@/utils", () => ({ FRONTEND_RESOURCES_PATH: "/resources" }));

const RBtnStub = defineComponent({
  inheritAttrs: false,
  props: {
    disabled: Boolean,
    loading: Boolean,
  },
  emits: ["click"],
  template: `
    <button
      v-bind="$attrs"
      :disabled="disabled"
      :data-loading="loading ? 'true' : 'false'"
      @click="$emit('click')"
    ><slot /></button>
  `,
});

const RDropzoneStub = defineComponent({
  inheritAttrs: false,
  props: {
    accept: String,
    disabled: Boolean,
    hint: String,
    inputLabel: String,
    multiple: Boolean,
    overlay: Boolean,
    title: String,
  },
  emits: ["files"],
  setup(_props, { expose }) {
    const open = vi.fn();
    expose({ open });
    return { open };
  },
  template: `
    <section
      v-bind="$attrs"
      data-dropzone
      :data-disabled="disabled ? 'true' : 'false'"
      :data-multiple="multiple ? 'true' : 'false'"
      :data-overlay="overlay ? 'true' : 'false'"
      :data-accept="accept"
      :data-input-label="inputLabel"
    >
      <span data-dropzone-title>{{ title }}</span>
      <span data-dropzone-hint>{{ hint }}</span>
      <slot />
      <slot name="actions" />
    </section>
  `,
});

const ViewerStub = defineComponent({
  props: {
    deletable: Boolean,
    mutationDisabled: Boolean,
    pdfUrl: String,
    redownloadable: Boolean,
    url: String,
  },
  emits: ["delete", "redownload"],
  template: `
    <article
      data-manual-viewer
      :data-deletable="deletable ? 'true' : 'false'"
      :data-mutation-disabled="mutationDisabled ? 'true' : 'false'"
      :data-redownloadable="redownloadable ? 'true' : 'false'"
      :data-url="pdfUrl || url"
    />
  `,
});

const stubs = {
  MarkdownViewer: ViewerStub,
  PdfViewer: ViewerStub,
  RBtn: RBtnStub,
  RDropzone: RDropzoneStub,
  REmptyState: {
    props: ["title"],
    template: "<section data-empty-state><span>{{ title }}</span></section>",
  },
  RSelect: { template: "<select />" },
};

const baseRom = {
  id: 7,
  name: "Example",
  platform_id: 2,
  updated_at: "2026-08-20T00:00:00Z",
  has_manual: true,
  path_manual: "manuals/7/original.pdf",
  url_manual: "https://example.invalid/manual.pdf",
};

const emptyRom = {
  ...baseRom,
  has_manual: false,
  path_manual: "",
  url_manual: "",
};

const refreshedRom = {
  ...baseRom,
  updated_at: "2026-08-21T00:00:00Z",
  path_manual: "manuals/7/replacement.pdf",
};

function deferred<T>() {
  let resolvePromise!: (value: T | PromiseLike<T>) => void;
  let rejectPromise!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });
  return { promise, reject: rejectPromise, resolve: resolvePromise };
}

function mountManual(rom = baseRom) {
  const emitter = mitt<Events>();
  emitter.on("showManualUploadTargetDialog", mocks.emitterEvents);
  emitter.on("showDeleteManualDialog", mocks.emitterEvents);
  return shallowMount(ManualSubtab, {
    props: { rom: rom as never },
    global: {
      provide: { emitter },
      stubs,
    },
  });
}

function findDropzone(
  wrapper: ReturnType<typeof mountManual>,
  overlay: boolean,
) {
  const found = wrapper
    .findAllComponents(RDropzoneStub)
    .find((candidate) => candidate.props("overlay") === overlay);
  if (!found) throw new Error(`Expected overlay=${overlay} dropzone`);
  return found;
}

function source(path: string) {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

beforeEach(() => {
  mocks.canEdit = true;
  mocks.emitterEvents.mockReset();
  mocks.romApi.getRom.mockReset();
  mocks.romApi.redownloadManual.mockReset();
  mocks.romApi.uploadManual.mockReset();
  mocks.romsStore.currentRom = { ...baseRom };
  mocks.romsStore.update.mockReset();
  mocks.snackbar.error.mockReset();
  mocks.snackbar.success.mockReset();
  mocks.snackbar.warning.mockReset();
});

describe("ManualSubtab", () => {
  it("redownload_blocks_every_competing_manual_gesture", async () => {
    const redownload = deferred<unknown>();
    const refresh = deferred<{ data: typeof refreshedRom }>();
    mocks.romApi.redownloadManual.mockReturnValueOnce(redownload.promise);
    mocks.romApi.getRom.mockReturnValueOnce(refresh.promise);

    const wrapper = mountManual();
    await flushPromises();
    const overlay = findDropzone(wrapper, true);
    const viewer = wrapper.getComponent(ViewerStub);
    const replaceButton = wrapper
      .findAll("button")
      .find((button) => button.text() === "rom.replace-manual");
    const file = new File(["replacement"], "replacement.pdf", {
      type: "application/pdf",
    });
    const originalUrl = viewer.attributes("data-url");

    viewer.vm.$emit("redownload");
    await nextTick();

    expect(mocks.romApi.redownloadManual).toHaveBeenCalledTimes(1);
    expect(wrapper.get(".r-v2-manual").attributes("aria-busy")).toBe("true");
    expect(overlay.attributes("data-disabled")).toBe("true");
    expect(replaceButton?.attributes().disabled).toBeDefined();
    expect(viewer.attributes("data-mutation-disabled")).toBe("true");
    expect(viewer.attributes("data-url")).toBe(originalUrl);

    overlay.vm.$emit("files", [file]);
    viewer.vm.$emit("delete");
    viewer.vm.$emit("redownload");
    await replaceButton?.trigger("click");
    await nextTick();

    expect(mocks.romApi.uploadManual).not.toHaveBeenCalled();
    expect(mocks.romApi.redownloadManual).toHaveBeenCalledTimes(1);
    expect(mocks.emitterEvents).not.toHaveBeenCalled();
    expect(
      (overlay.vm as { open: ReturnType<typeof vi.fn> }).open,
    ).not.toHaveBeenCalled();

    redownload.resolve({});
    await flushPromises();
    expect(mocks.romApi.getRom).toHaveBeenCalledWith({ romId: baseRom.id });
    expect(mocks.snackbar.success).not.toHaveBeenCalled();
    expect(viewer.attributes("data-url")).toBe(originalUrl);

    refresh.resolve({ data: refreshedRom });
    await flushPromises();
    expect(mocks.romsStore.currentRom).toBe(refreshedRom);
    expect(mocks.snackbar.success).toHaveBeenCalledWith(
      "rom.manual-redownloaded",
      { icon: "mdi-check-bold" },
    );

    mocks.romApi.redownloadManual.mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 409 },
    });
    const conflict = mountManual();
    await flushPromises();
    const conflictViewer = conflict.getComponent(ViewerStub);
    const conflictUrl = conflictViewer.attributes("data-url");
    conflictViewer.vm.$emit("redownload");
    await flushPromises();

    expect(conflict.get(".r-v2-manual").attributes("aria-busy")).toBe("false");
    expect(conflictViewer.attributes("data-url")).toBe(conflictUrl);
    expect(mocks.snackbar.error).toHaveBeenCalled();

    mocks.romApi.redownloadManual.mockResolvedValueOnce({});
    mocks.romApi.getRom.mockResolvedValueOnce({ data: refreshedRom });
    conflictViewer.vm.$emit("redownload");
    await flushPromises();
    expect(mocks.romApi.redownloadManual).toHaveBeenCalledTimes(3);
  });

  it("one_manual_gesture_sends_one_post_and_preserves_viewer_while_pending", async () => {
    const violations: string[] = [];
    const check = (condition: unknown, message: string) => {
      if (!condition) violations.push(message);
    };
    const callsWith = (spy: ReturnType<typeof vi.fn>, expected: string) =>
      spy.mock.calls.some(([message]) => message === expected);

    const upload = deferred<unknown>();
    const refresh = deferred<{ data: typeof refreshedRom }>();
    mocks.romApi.uploadManual.mockReturnValueOnce(upload.promise);
    mocks.romApi.getRom.mockReturnValueOnce(refresh.promise);

    const wrapper = mountManual();
    await flushPromises();
    const overlay = findDropzone(wrapper, true);
    const file = new File(["replacement"], "replacement.pdf", {
      type: "application/pdf",
    });
    const originalUrl = wrapper
      .get("[data-manual-viewer]")
      .attributes("data-url");

    overlay.vm.$emit("files", [file]);
    await nextTick();

    check(
      mocks.romApi.uploadManual.mock.calls.length === 1,
      `expected one uploadManual request, received ${mocks.romApi.uploadManual.mock.calls.length}`,
    );
    check(
      mocks.emitterEvents.mock.calls.length === 0,
      "active v2 still emitted the plural manual coordinator event",
    );
    check(
      mocks.romApi.uploadManual.mock.calls[0]?.[0]?.romId === baseRom.id &&
        mocks.romApi.uploadManual.mock.calls[0]?.[0]?.file === file,
      "the request did not bind the initiating ROM and exact single File",
    );
    check(
      wrapper.get("[data-manual-viewer]").attributes("data-url") ===
        originalUrl,
      "the existing viewer changed before authoritative refresh",
    );
    check(
      wrapper.get(".r-v2-manual").attributes("aria-busy") === "true",
      "the manual region did not expose aria-busy while pending",
    );
    const liveStatus = wrapper.find('[role="status"][aria-live="polite"]');
    check(
      liveStatus.exists() && liveStatus.text() === "rom.manual-replacing",
      "the replacement pending transition was not announced once",
    );
    check(
      overlay.attributes("data-disabled") === "true" &&
        overlay.attributes("data-multiple") === "false",
      "the single-select drop boundary stayed interactive while pending",
    );
    check(
      wrapper
        .get("[data-manual-viewer]")
        .attributes("data-mutation-disabled") === "true",
      "viewer delete and re-download mutations stayed active",
    );
    const replaceButton = wrapper
      .findAll("button")
      .find((button) => button.text() === "rom.replace-manual");
    check(
      Boolean(replaceButton),
      "the existing-manual action label is not Replace manual",
    );
    check(
      replaceButton?.attributes("data-loading") === "true" &&
        replaceButton.attributes().disabled !== undefined,
      "the visible replace action did not use loading and disabled semantics",
    );

    overlay.vm.$emit("files", [file]);
    await nextTick();
    check(
      mocks.romApi.uploadManual.mock.calls.length === 1,
      "a second local gesture started another request",
    );

    upload.resolve({});
    await flushPromises();
    check(
      mocks.romApi.getRom.mock.calls.length === 1 &&
        mocks.romApi.getRom.mock.calls[0]?.[0]?.romId === baseRom.id,
      "API success did not refresh the initiating ROM exactly once",
    );
    check(
      mocks.snackbar.success.mock.calls.length === 0,
      "success was announced before same-ROM refresh completed",
    );
    check(
      wrapper.get(".r-v2-manual").attributes("aria-busy") === "true",
      "the region stopped being busy during authoritative refresh",
    );

    refresh.resolve({ data: refreshedRom });
    await flushPromises();
    check(
      mocks.romsStore.currentRom === refreshedRom &&
        mocks.romsStore.update.mock.calls[0]?.[0] === refreshedRom,
      "the refreshed matching ROM was not installed authoritatively",
    );
    check(
      callsWith(mocks.snackbar.success, "rom.manual-replace-success"),
      "replacement success was not announced after refresh",
    );
    check(
      wrapper.get(".r-v2-manual").attributes("aria-busy") === "false",
      "the region did not return to idle after refresh",
    );

    mocks.romApi.uploadManual.mockReset();
    mocks.romApi.uploadManual.mockRejectedValueOnce(
      new Error("write rejected"),
    );
    mocks.snackbar.error.mockReset();
    const replacementFailure = mountManual();
    await flushPromises();
    const failedUrl = replacementFailure
      .get("[data-manual-viewer]")
      .attributes("data-url");
    findDropzone(replacementFailure, true).vm.$emit("files", [file]);
    await flushPromises();
    check(
      replacementFailure.get("[data-manual-viewer]").attributes("data-url") ===
        failedUrl &&
        callsWith(mocks.snackbar.error, "rom.manual-replace-failed-safe"),
      "replacement failure did not preserve the viewer with safe copy",
    );

    mocks.romApi.uploadManual.mockResolvedValueOnce({});
    mocks.romApi.getRom.mockResolvedValueOnce({ data: refreshedRom });
    findDropzone(replacementFailure, true).vm.$emit("files", [file]);
    await flushPromises();
    check(
      mocks.romApi.uploadManual.mock.calls.length === 2,
      "retry was not available after a safe replacement failure",
    );

    mocks.romApi.uploadManual.mockReset();
    mocks.romApi.uploadManual.mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 409 },
    });
    mocks.snackbar.warning.mockReset();
    const conflict = mountManual();
    await flushPromises();
    findDropzone(conflict, true).vm.$emit("files", [file]);
    await flushPromises();
    check(
      callsWith(mocks.snackbar.warning, "rom.manual-upload-conflict"),
      "server conflict did not use the bounded conflict copy",
    );

    mocks.romApi.uploadManual.mockReset();
    mocks.romApi.getRom.mockReset();
    mocks.romApi.uploadManual.mockResolvedValueOnce({});
    mocks.romApi.getRom.mockRejectedValueOnce(new Error("refresh rejected"));
    mocks.snackbar.success.mockReset();
    mocks.snackbar.warning.mockReset();
    const refreshFailure = mountManual();
    await flushPromises();
    findDropzone(refreshFailure, true).vm.$emit("files", [file]);
    await flushPromises();
    check(
      callsWith(mocks.snackbar.warning, "rom.manual-refresh-warning") &&
        mocks.snackbar.success.mock.calls.length === 0,
      "post-save refresh failure did not use only the reload warning",
    );

    mocks.romApi.uploadManual.mockReset();
    mocks.romApi.getRom.mockReset();
    mocks.snackbar.error.mockReset();
    const emptyFailure = mountManual(emptyRom);
    await flushPromises();
    const emptyDropzone = findDropzone(emptyFailure, false);
    check(
      emptyDropzone.attributes("data-multiple") === "false" &&
        emptyDropzone.attributes("data-accept") === "application/pdf,.md" &&
        emptyDropzone.attributes("data-input-label") === "rom.upload-manual" &&
        emptyDropzone.find("[data-dropzone-hint]").text() ===
          "rom.manual-empty-upload-hint",
      "empty state did not expose the approved single-file ownership contract",
    );
    mocks.romApi.uploadManual.mockRejectedValueOnce(
      new Error("upload rejected"),
    );
    emptyDropzone.vm.$emit("files", [file]);
    await flushPromises();
    check(
      emptyFailure.find("[data-manual-viewer]").exists() === false &&
        callsWith(mocks.snackbar.error, "rom.manual-upload-failed-safe"),
      "empty upload failure created a phantom manual or used unsafe copy",
    );

    mocks.romApi.uploadManual.mockReset();
    mocks.snackbar.error.mockReset();
    const invalid = new File(["text"], "notes.txt", { type: "text/plain" });
    emptyDropzone.vm.$emit("files", [file, file]);
    emptyDropzone.vm.$emit("files", [invalid]);
    emptyDropzone.vm.$emit("files", []);
    await flushPromises();
    check(
      mocks.romApi.uploadManual.mock.calls.length === 0 &&
        callsWith(mocks.snackbar.error, "rom.manual-invalid-selection"),
      "multiple or invalid selections created a request or lacked recovery copy",
    );

    mocks.romApi.uploadManual.mockReset();
    mocks.romApi.getRom.mockReset();
    const navigationUpload = deferred<unknown>();
    const navigationRefresh = deferred<{ data: typeof refreshedRom }>();
    mocks.romApi.uploadManual.mockReturnValueOnce(navigationUpload.promise);
    mocks.romApi.getRom.mockReturnValueOnce(navigationRefresh.promise);
    mocks.romsStore.currentRom = { ...baseRom };
    const navigation = mountManual();
    await flushPromises();
    findDropzone(navigation, true).vm.$emit("files", [file]);
    navigationUpload.resolve({});
    await flushPromises();
    const otherRom = { ...baseRom, id: 99 };
    mocks.romsStore.currentRom = otherRom;
    navigationRefresh.resolve({ data: refreshedRom });
    await flushPromises();
    check(
      mocks.romsStore.currentRom === otherRom,
      "completion overwrote a different current ROM after navigation",
    );

    mocks.canEdit = false;
    const readOnly = mountManual();
    await flushPromises();
    check(
      readOnly
        .findAll("button")
        .every((button) => button.text() !== "rom.replace-manual") &&
        findDropzone(readOnly, true).attributes("data-disabled") === "true" &&
        readOnly.get("[data-manual-viewer]").attributes("data-deletable") ===
          "false",
      "a user without rom.edit retained a primary-manual mutation action",
    );

    const componentSource = source(
      "src/v2/components/GameDetails/ManualSubtab.vue",
    );
    const dialogsSource = source("src/v2/components/Dialogs/GlobalDialogs.vue");
    check(
      componentSource.includes("r-v2-manual__fill") &&
        componentSource.includes("height: 70dvh") &&
        componentSource.includes("min-height: 20rem") &&
        !componentSource.includes("@media") &&
        !componentSource.includes("useGridNav") &&
        !componentSource.includes("@keydown"),
      "native input order or the approved responsive viewer structure changed",
    );
    check(
      !dialogsSource.includes("ManualUploadTargetDialog") &&
        !existsSync(
          resolve(
            process.cwd(),
            "src/v2/components/Dialogs/ManualUploadTargetDialog.vue",
          ),
        ),
      "the active-v2 plural coordinator mount or file remains",
    );

    if (violations.length > 0) {
      const error = new Error(violations.join("\n"));
      error.stack = error.message;
      throw error;
    }
  });

  it("preserves frozen v1 upload service, emitter, and consumers", () => {
    const service = source("src/services/api/rom.ts");
    const emitter = source("src/types/emitter.d.ts");
    const layout = source("src/layouts/Main.vue");
    const media = source("src/components/Details/MediaTab.vue");
    const target = source(
      "src/components/common/Game/Dialog/ManualUploadTarget.vue",
    );
    const edit = source("src/components/common/Game/Dialog/EditRom.vue");

    expect(service).toMatch(/async function uploadManuals\s*\(/);
    expect(service).toMatch(/\buploadManuals,\s*\n/);
    expect(emitter).toContain("showManualUploadTargetDialog");
    expect(layout).toContain("ManualUploadTargetDialog");
    expect(media).toContain("showManualUploadTargetDialog");
    expect(target).toContain("romApi.uploadManuals");
    expect(edit).toMatch(/romApi\s*\.\s*uploadManuals/);
  });
});
