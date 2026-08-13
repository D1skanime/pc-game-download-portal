import { flushPromises, mount } from "@vue/test-utils";
import mitt from "mitt";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import type { SimpleRom } from "@/stores/roms";
import type { Events } from "@/types/emitter";
import DeleteRomDialog from "./DeleteRomDialog.vue";

const mocks = vi.hoisted(() => ({
  addExclusion: vi.fn(),
  apiPost: vi.fn(),
  configAddExclusion: vi.fn(),
  galleryRemove: vi.fn(),
  push: vi.fn(),
  remove: vi.fn(),
  removeIds: vi.fn(),
  resetSelection: vi.fn(),
  setContinuePlayingRoms: vi.fn(),
  setRecentRoms: vi.fn(),
  snackbarError: vi.fn(),
  snackbarSuccess: vi.fn(),
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string, params?: unknown) =>
      params === undefined ? key : `${key}:${JSON.stringify(params)}`,
  }),
}));

vi.mock("@/plugins/router", () => ({
  ROUTES: { PLATFORM: "platform" },
}));

vi.mock("vue-router", () => ({
  useRoute: () => ({ name: "platform" }),
  useRouter: () => ({ push: mocks.push }),
}));

vi.mock("@/services/api/config", () => ({
  default: { addExclusion: mocks.configAddExclusion },
}));

vi.mock("@/services/api", () => ({
  default: { post: mocks.apiPost },
}));

vi.mock("@/stores/config", () => ({
  default: () => ({ addExclusion: mocks.addExclusion }),
}));

vi.mock("@/stores/roms", () => ({
  default: () => ({
    continuePlayingRoms: [],
    recentRoms: [],
    remove: mocks.remove,
    resetSelection: mocks.resetSelection,
    setContinuePlayingRoms: mocks.setContinuePlayingRoms,
    setRecentRoms: mocks.setRecentRoms,
  }),
}));

vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({
    error: mocks.snackbarError,
    success: mocks.snackbarSuccess,
  }),
}));

vi.mock("@/v2/stores/galleryRoms", () => ({
  default: () => ({ remove: mocks.galleryRemove }),
}));

vi.mock("@/v2/stores/gallerySelection", () => ({
  default: () => ({ removeIds: mocks.removeIds }),
}));

const RDialog = {
  props: ["modelValue"],
  template: `
    <section v-if="modelValue" role="dialog">
      <header><slot name="header" /></header>
      <div><slot name="toolbar" /></div>
      <main><slot name="content" /></main>
      <div><slot name="append" /></div>
      <footer><slot name="footer" /></footer>
    </section>
  `,
};

const RBtn = {
  props: ["disabled", "loading"],
  emits: ["click"],
  template:
    '<button type="button" :disabled="disabled" :data-loading="loading" @click="$emit(\'click\')"><slot /></button>',
};

const RCheckbox = {
  props: ["modelValue", "label"],
  emits: ["update:modelValue"],
  template: `
    <label>
      <input
        class="future-scan-exclusion"
        type="checkbox"
        :checked="modelValue"
        @change="$emit('update:modelValue', !modelValue)"
      />
      {{ label }}
    </label>
  `,
};

const RIcon = {
  props: ["icon"],
  template: '<i :data-icon="icon" />',
};

function rom(id: number, name: string): SimpleRom {
  return {
    id,
    platform_id: 7,
    fs_name: `${name}.rom`,
    has_simple_single_file: true,
    name,
    path_cover_small: null,
    url_cover: null,
  } as SimpleRom;
}

function mountDialog() {
  const emitter = mitt<Events>();
  const wrapper = mount(DeleteRomDialog, {
    global: {
      plugins: [createPinia()],
      provide: { emitter },
      stubs: { RBtn, RCheckbox, RDialog, RIcon },
    },
  });
  return { emitter, wrapper };
}

async function openDialog(roms: SimpleRom[]) {
  const mounted = mountDialog();
  mounted.emitter.emit("showDeleteRomDialog", roms);
  await nextTick();
  return mounted.wrapper;
}

describe("DeleteRomDialog catalog-only removal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the source-safe catalog contract without filesystem controls", async () => {
    const wrapper = await openDialog([rom(1, "Alpha")]);

    expect(wrapper.text()).toContain("rom.remove-from-catalog-title");
    expect(wrapper.text()).toContain("rom.remove-from-catalog-body");
    expect(wrapper.text()).toContain(
      "rom.remove-from-catalog-source-unchanged",
    );
    expect(wrapper.text()).toContain("rom.remove-from-catalog-retained-value");
    expect(wrapper.text()).toContain(
      "rom.remove-from-catalog-future-scan-exclusion",
    );
    expect(wrapper.text()).toContain("rom.remove-from-catalog-confirm");

    for (const forbidden of [
      "delete-file",
      "delete-from-disk-aria",
      "select-all-disk",
      "delete-filesystem-warning",
      "deleted-from-filesystem",
      "mdi-harddisk-remove",
    ]) {
      expect(wrapper.html()).not.toContain(forbidden);
    }

    const controls = wrapper.findAll("input, button");
    expect(controls.map((control) => control.text())).toEqual([
      "",
      "common.cancel",
      "rom.remove-from-catalog-confirm",
    ]);
    expect(controls[0].attributes("type")).toBe("checkbox");
    expect(controls[1].attributes("type")).toBe("button");
    expect(controls[2].attributes("type")).toBe("button");
  });

  it("sends ROM identities only and reconciles a partial result", async () => {
    const alpha = rom(1, "Alpha");
    const beta = rom(2, "Beta");
    mocks.apiPost.mockResolvedValueOnce({
      data: {
        errors: [
          { code: "catalog_removal_failed", message: "Failed", rom_id: 2 },
        ],
        failed_ids: [2],
        items: [
          {
            cleanup_pending: 0,
            retained_catalog_id: 10,
            retained_play_sessions: 1,
            retained_saves: 1,
            retained_states: 1,
            rom_id: 1,
          },
        ],
        retained_user_data: true,
        source_files_preserved: true,
        successful_items: 1,
      },
    });
    const wrapper = await openDialog([alpha, beta]);

    await wrapper.get(".future-scan-exclusion").trigger("change");
    await wrapper
      .findAll("button")
      .find((button) =>
        button.text().includes("rom.remove-from-catalog-confirm"),
      )!
      .trigger("click");
    await flushPromises();

    expect(mocks.apiPost).toHaveBeenCalledWith("/roms/remove-from-catalog", {
      rom_ids: [1, 2],
    });
    expect(mocks.apiPost.mock.calls[0][1]).toEqual({ rom_ids: [1, 2] });
    expect(Object.keys(mocks.apiPost.mock.calls[0][1])).toEqual(["rom_ids"]);
    expect(mocks.remove).toHaveBeenCalledWith([alpha]);
    expect(mocks.galleryRemove).toHaveBeenCalledWith([alpha]);
    expect(mocks.removeIds).toHaveBeenCalledWith([1]);
    expect(mocks.remove).not.toHaveBeenCalledWith(
      expect.arrayContaining([beta]),
    );
    expect(mocks.configAddExclusion).toHaveBeenCalledTimes(1);
    expect(mocks.configAddExclusion).toHaveBeenCalledWith({
      exclusionType: "EXCLUDED_SINGLE_FILES",
      exclusionValue: "Alpha.rom",
    });
    expect(mocks.snackbarSuccess).toHaveBeenCalledWith(
      expect.stringContaining("rom.removed-from-catalog"),
      { icon: "mdi-check-bold" },
    );
  });

  it("keeps the dialog and selection intact when removal fails", async () => {
    const alpha = rom(1, "Alpha");
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    mocks.apiPost.mockRejectedValueOnce({
      response: { data: { detail: "Catalog removal unavailable" } },
    });
    const wrapper = await openDialog([alpha]);

    await wrapper
      .findAll("button")
      .find((button) =>
        button.text().includes("rom.remove-from-catalog-confirm"),
      )!
      .trigger("click");
    await flushPromises();

    expect(wrapper.find('[role="dialog"]').exists()).toBe(true);
    expect(mocks.remove).not.toHaveBeenCalled();
    expect(mocks.removeIds).not.toHaveBeenCalled();
    expect(mocks.snackbarError).toHaveBeenCalledWith(
      "Catalog removal unavailable",
      { icon: "mdi-close-circle" },
    );
    expect(consoleError).toHaveBeenCalledOnce();
    consoleError.mockRestore();
  });
});
