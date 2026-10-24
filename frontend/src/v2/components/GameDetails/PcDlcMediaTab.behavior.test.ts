import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, ref } from "vue";
import type { PcComponentSchema } from "@/__generated__";
import PcDlcMediaTab from "./PcDlcMediaTab.vue";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
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
const component = {
  id: 20,
  updated_at: "2026-10-24T10:00:00Z",
} as PcComponentSchema;
const media = {
  id: 7,
  role: "screenshot",
  origin: "provider",
  provider: "steam",
  placements: [{ media_id: 7, position: 0 }],
};
function render() {
  return mount(PcDlcMediaTab, { props: { romId: 24, component } });
}
beforeEach(() => {
  vi.clearAllMocks();
  mocks.editable = true;
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
    expect(wrapper.get(".za-shot__badge").text()).toBe(
      "rom.screenshots-overview-position:1",
    );
    expect(wrapper.findAll(".za-shot__actions button")).toHaveLength(2);
    await button.trigger("click");
    await flushPromises();
    expect(mocks.delete).toHaveBeenCalledExactlyOnceWith(
      `${endpoint}/7/placement`,
      { params: { expected_version: component.updated_at } },
    );
    expect(wrapper.emitted("refresh")).toHaveLength(1);
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
    expect(wrapper.emitted("refresh")).toHaveLength(1);
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

  it("keeps the existing card mounted during media reconciliation", async () => {
    const wrapper = render();
    await flushPromises();
    const card = wrapper.get(".za-shot").element;
    let release!: (value: { data: (typeof media)[] }) => void;
    mocks.get.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          release = resolve;
        }),
    );
    await wrapper
      .get('[aria-label="rom.remove-from-overview"]')
      .trigger("click");
    await flushPromises();
    expect(wrapper.get(".za-shot").element).toBe(card);
    release({ data: [media] });
    await flushPromises();
    expect(wrapper.get(".za-shot").element).toBe(card);
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
