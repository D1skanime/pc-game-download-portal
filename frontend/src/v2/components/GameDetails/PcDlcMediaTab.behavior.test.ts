import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, ref } from "vue";
import type { PcComponentSchema } from "@/__generated__";
import PcDlcMediaTab from "./PcDlcMediaTab.vue";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  refresh: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
  open: vi.fn(),
  confirm: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  editable: true,
}));
vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string, args?: Record<string, unknown>) =>
      args ? `${key}:${args.position}` : key,
  }),
}));
vi.mock("@/v2/composables/useCan", () => ({
  useCan: () => computed(() => mocks.editable),
}));
vi.mock("@/v2/composables/useConfirm", () => ({
  useConfirm: () => mocks.confirm,
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ success: mocks.success, error: mocks.error }),
}));
vi.mock("@/v2/composables/useResponsiveColumns", () => ({
  useResponsiveColumns: () => ({ columns: ref(3) }),
}));
vi.mock("@/v2/composables/useWrapGridNav", () => ({ useWrapGridNav: vi.fn() }));
vi.mock("@/v2/data/adapters/legacy/services/api/rom", () => ({
  romApi: mocks,
}));
vi.mock("@v2/lib", () => ({
  RBtn: {
    props: { disabled: Boolean },
    template:
      '<button :disabled="disabled"><slot name="prepend" /><slot /></button>',
  },
  RIcon: { props: ["icon"], template: '<span :data-icon="icon" />' },
  RSelect: { template: "<div />" },
  REmptyState: { template: "<div />" },
  RCarousel: {
    props: ["items", "modelValue"],
    template: "<div data-carousel />",
  },
  RDropzone: defineComponent({
    name: "RDropzone",
    props: { disabled: Boolean },
    emits: ["files"],
    setup(_, { slots, expose }) {
      expose({ open: mocks.open });
      return () => h("div", slots.default?.());
    },
  }),
}));
const endpoint = "/roms/24/pc-components/20/media";
const media = {
  id: 7,
  role: "screenshot" as const,
  origin: "provider" as const,
  provider: "steam",
  provider_media_id: "7",
  mime_type: "image/png",
  owned_path: "fixture/shot.png",
  created_at: "2026-10-24T10:00:00Z",
  updated_at: "2026-10-24T10:00:00Z",
  placements: [{ id: 1, media_id: 7, position: 0 }],
};
const component: PcComponentSchema = {
  id: 20,
  kind: "dlc",
  relative_path: "DLC/fixture",
  manifest_members: [],
  updated_at: "2026-10-24T10:00:00Z",
  owned_media: [media],
};
function render(refresh = mocks.refresh) {
  return mount(PcDlcMediaTab, { props: { romId: 24, component, refresh } });
}
beforeEach(() => {
  vi.clearAllMocks();
  mocks.editable = true;
  mocks.refresh.mockResolvedValue(true);
  mocks.get.mockResolvedValue({ data: [media] });
  mocks.post.mockResolvedValue({ data: {} });
  mocks.delete.mockResolvedValue({ data: {} });
  mocks.confirm.mockResolvedValue(true);
});
describe("DLC media presentation preserves component capabilities", () => {
  it("keeps the crown selected, displays position one and removes only the component placement", async () => {
    const wrapper = render();
    await flushPromises();
    const button = wrapper.get('[aria-label="rom.remove-from-overview"]');
    expect(button.attributes("aria-pressed")).toBe("true");
    expect(button.find('[data-icon="mdi-crown-outline"]').exists()).toBe(true);
    expect(button.find(".za-shot__check").exists()).toBe(true);
    expect(wrapper.find(".za-shot__badge").text()).toBe(
      "rom.screenshots-overview-position:1",
    );
    expect(wrapper.findAll(".za-shot__actions button")).toHaveLength(2);
    await button.trigger("click");
    await flushPromises();
    expect(mocks.delete).toHaveBeenCalledExactlyOnceWith(
      `${endpoint}/7/placement`,
      { params: { expected_version: component.updated_at } },
    );
    expect(mocks.refresh).toHaveBeenCalledTimes(1);
  });
  it("opens one existing picker and posts one file to the nested endpoint", async () => {
    const wrapper = render();
    await flushPromises();
    await wrapper.get('[aria-label="common.upload"]').trigger("click");
    expect(mocks.open).toHaveBeenCalledTimes(1);
    const file = new File(["one"], "one.png", { type: "image/png" });
    wrapper.findComponent({ name: "RDropzone" }).vm.$emit("files", [file]);
    await flushPromises();
    expect(mocks.post).toHaveBeenCalledTimes(1);
    const [path, body] = mocks.post.mock.calls[0];
    expect(path).toBe(endpoint);
    expect(body.get("media")).toBe(file);
    expect(body.get("role")).toBe("screenshot");
    expect(body.get("expected_version")).toBe(component.updated_at);
    expect(mocks.refresh).toHaveBeenCalledTimes(1);
  });
  it("keeps read-only media previewable without editing or upload actions", async () => {
    mocks.editable = false;
    const wrapper = render();
    await flushPromises();
    expect(wrapper.find('[aria-label="common.upload"]').exists()).toBe(false);
    expect(wrapper.find(".za-shot__actions").exists()).toBe(false);
    expect(wrapper.findComponent({ name: "RDropzone" }).props("disabled")).toBe(
      true,
    );
    wrapper
      .findComponent({ name: "RDropzone" })
      .vm.$emit("files", [new File(["no"], "no.png")]);
    await flushPromises();
    expect(mocks.post).not.toHaveBeenCalled();
    await wrapper.get(".za-shot__preview").trigger("click");
    expect(wrapper.find("[data-carousel]").exists()).toBe(true);
  });
  it("does not send a second placement while the current selection is saving", async () => {
    let release!: () => void;
    mocks.delete.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          release = resolve;
        }),
    );
    const wrapper = render();
    await flushPromises();
    const button = wrapper.get('[aria-label="rom.remove-from-overview"]');
    await button.trigger("click");
    await button.trigger("click");
    expect(mocks.delete).toHaveBeenCalledTimes(1);
    release();
    await flushPromises();
  });

  it("keeps the existing card mounted during canonical reconciliation", async () => {
    let release!: (ok: boolean) => void;
    const refresh = vi.fn(
      () =>
        new Promise<boolean>((resolve) => {
          release = resolve;
        }),
    );
    const wrapper = render(refresh);
    await flushPromises();
    const card = wrapper.get(".za-shot").element;
    await wrapper
      .get('[aria-label="rom.remove-from-overview"]')
      .trigger("click");
    await flushPromises();
    expect(wrapper.find(".za-shot").element).toBe(card);
    release(true);
    await flushPromises();
    expect(wrapper.find(".za-shot").element).toBe(card);
  });

  it("keeps edits blocked until the canonical parent version settles", async () => {
    let release!: (ok: boolean) => void;
    const refresh = vi.fn(
      () =>
        new Promise<boolean>((resolve) => {
          release = resolve;
        }),
    );
    const wrapper = render(refresh);
    await flushPromises();
    await wrapper
      .get('[aria-label="rom.remove-from-overview"]')
      .trigger("click");
    await flushPromises();
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(
      wrapper
        .get('[aria-label="rom.remove-from-overview"]')
        .attributes("disabled"),
    ).toBeDefined();
    expect(wrapper.findComponent({ name: "RDropzone" }).props("disabled")).toBe(
      true,
    );
    release(true);
    await flushPromises();
    expect(
      wrapper
        .get('[aria-label="rom.remove-from-overview"]')
        .attributes("disabled"),
    ).toBeUndefined();
  });

  it("retains a blocked editor and retries only reconciliation after a failed canonical read", async () => {
    mocks.refresh.mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    const wrapper = render();
    await flushPromises();
    await wrapper
      .get('[aria-label="rom.remove-from-overview"]')
      .trigger("click");
    await flushPromises();
    expect(wrapper.find('[aria-label="common.try-again"]').exists()).toBe(true);
    expect(
      wrapper
        .get('[aria-label="rom.remove-from-overview"]')
        .attributes("disabled"),
    ).toBeDefined();
    await wrapper.get('[aria-label="common.try-again"]').trigger("click");
    await flushPromises();
    expect(mocks.refresh).toHaveBeenCalledTimes(2);
    expect(mocks.delete).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[aria-label="common.try-again"]').exists()).toBe(
      false,
    );
  });

  it("preserves deletion confirmation and does not mutate after cancellation", async () => {
    mocks.confirm.mockResolvedValue(false);
    const wrapper = render();
    await flushPromises();
    await wrapper.get('[aria-label="common.delete"]').trigger("click");
    await flushPromises();
    expect(mocks.confirm).toHaveBeenCalledWith({
      title: "common.delete",
      tone: "danger",
    });
    expect(mocks.delete).not.toHaveBeenCalled();
  });
});
