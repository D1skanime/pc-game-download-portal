import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, h, nextTick, ref } from "vue";
import type { RomOwnedMediaSchema } from "@/__generated__";
import type { ScreenshotItem } from "@/v2/components/GameDetails/ScreenshotsTab.vue";
import type { DetailedRom } from "@/v2/data/adapters/legacy/stores/roms";
import ScreenshotsSubtab from "./ScreenshotsSubtab.vue";

const actions = vi.hoisted(() => ({
  togglePlacement: vi.fn(),
  deleteProviderScreenshot: vi.fn(),
  refreshProviderScreenshots: vi.fn(),
  handleMyFiles: vi.fn(),
  deleteMyScreenshot: vi.fn(),
  toggleVisibility: vi.fn(),
  open: vi.fn(),
}));
vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string, args?: Record<string, unknown>) =>
      args?.position !== undefined ? key + ":" + args.position : key,
  }),
}));
vi.mock("@/v2/composables/useWrapGridNav", () => ({ useWrapGridNav: vi.fn() }));
vi.mock("@v2/lib", () => ({
  RBtn: {
    name: "RBtn",
    props: ["disabled"],
    template: '<button :disabled="disabled"><slot /></button>',
  },
  RIcon: { template: "<span />" },
  RTooltip: { template: "<span />" },
  RAvatar: { template: "<span />" },
  REmptyState: { props: ["title"], template: "<p>{{ title }}</p>" },
  RSkeletonBlock: { template: "<span />" },
  RCarousel: {
    name: "RCarousel",
    props: ["items", "modelValue"],
    emits: ["close", "update:modelValue"],
    template: "<div data-carousel />",
  },
  RDropzone: defineComponent({
    name: "RDropzone",
    props: { disabled: Boolean },
    emits: ["files"],
    setup(props, { slots, emit, expose }) {
      expose({ open: actions.open });
      return () =>
        h("div", [
          h("input", {
            type: "file",
            multiple: true,
            disabled: props.disabled,
            onChange: (event: Event) =>
              emit(
                "files",
                Array.from((event.target as HTMLInputElement).files ?? []),
              ),
          }),
          slots.default?.(),
        ]);
    },
  }),
}));
vi.mock("@/v2/composables/useScreenshotManagement", () => ({
  useScreenshotManagement: () => state,
}));
function provider(id: number, positions = true) {
  return {
    id,
    provider: "IGDB",
    display_label: "Provider " + id,
    placements: positions
      ? [
          { surface: "overview", position: 0 },
          { surface: "background", position: 2 },
        ]
      : [],
  } as RomOwnedMediaSchema;
}
function createState() {
  const providers = ref([provider(7), provider(8)]);
  return {
    ...actions,
    canManage: ref(true),
    canRefresh: ref(true),
    canUpload: ref(true),
    refreshing: ref(false),
    uploading: ref(false),
    mutatingId: ref<number | null>(null),
    togglingId: ref<number | null>(null),
    deletingId: ref<number | null>(null),
    newlyUploadedIds: ref<number[]>([]),
    providerScreenshots: providers,
    providerUrls: computed(() =>
      providers.value.map((item) => "/provider/" + item.id),
    ),
    myScreenshots: ref<ScreenshotItem[]>([
      { id: 10, url: "/mine/10", isOwn: true, isPublic: true },
      { id: 11, url: "/mine/11", isOwn: true, isPublic: false },
    ]),
    communityScreenshots: ref<ScreenshotItem[]>([
      { id: 7, url: "/community/7", username: "Alice", isOwn: false },
    ]),
    mediaContentUrl: (id: number) => "/provider/" + id,
    hasPlacement: (item: RomOwnedMediaSchema, surface: string) =>
      item.placements?.some((p) => p.surface === surface),
    placementPosition: (item: RomOwnedMediaSchema, surface: string) =>
      item.placements?.find((p) => p.surface === surface)?.position,
  };
}
let state = createState();
function render() {
  return mount(ScreenshotsSubtab, {
    attachTo: document.body,
    props: { rom: { id: 1 } as DetailedRom },
  });
}
beforeEach(() => {
  vi.clearAllMocks();
  state = createState();
  actions.handleMyFiles.mockResolvedValue(undefined);
});
describe("ScreenshotsSubtab single gallery owner", () => {
  it("keeps one input/dropzone through empty-to-populated and opens the top picker once", async () => {
    state.myScreenshots.value = [];
    const wrapper = render();
    const input = wrapper.get('input[type="file"]').element;
    const zone = wrapper.getComponent({ name: "RDropzone" }).vm;
    await wrapper.get('[aria-label="rom.upload-screenshots"]').trigger("click");
    expect(actions.open).toHaveBeenCalledTimes(1);
    state.myScreenshots.value = [{ id: 10, url: "/mine/10", isOwn: true }];
    await nextTick();
    expect(wrapper.get('input[type="file"]').element).toBe(input);
    expect(wrapper.getComponent({ name: "RDropzone" }).vm).toBe(zone);
    expect(wrapper.findAll('input[type="file"]')).toHaveLength(1);
    const files = [new File(["a"], "a.png"), new File(["b"], "b.png")];
    wrapper.getComponent({ name: "RDropzone" }).vm.$emit("files", files);
    await flushPromises();
    expect(actions.handleMyFiles).toHaveBeenCalledTimes(1);
    expect(actions.handleMyFiles).toHaveBeenCalledWith(files);
    state.uploading.value = true;
    await nextTick();
    expect(
      wrapper
        .get('[aria-label="rom.upload-screenshots"]')
        .attributes("disabled"),
    ).toBeDefined();
    expect(wrapper.getComponent({ name: "RDropzone" }).props("disabled")).toBe(
      true,
    );
    wrapper.unmount();
  });
  it("retains source order, both stored placements, named actions and permission boundaries", async () => {
    const wrapper = render();
    expect(
      wrapper
        .findAll("[data-shot-key]")
        .map((card) => card.attributes("data-shot-key")),
    ).toEqual(["provider:7", "provider:8", "user:10", "user:11", "user:7"]);
    const first = wrapper.get('[data-shot-key="provider:7"]');
    expect(first.text()).toContain("rom.screenshots-overview-position:0");
    expect(first.text()).toContain("rom.screenshots-background-position:2");
    await first.get('[aria-label="rom.remove-from-overview"]').trigger("click");
    await first.get('[aria-label="rom.remove-as-background"]').trigger("click");
    await first
      .get('[aria-label="rom.provider-screenshot-remove-title"]')
      .trigger("click");
    expect(
      actions.togglePlacement.mock.calls.map((args) => [args[0].id, args[1]]),
    ).toEqual([
      [7, "overview"],
      [7, "background"],
    ]);
    expect(actions.deleteProviderScreenshot).toHaveBeenCalledWith(
      state.providerScreenshots.value[0],
    );
    state.providerScreenshots.value = [provider(7, false), provider(8)];
    await nextTick();
    await first.get('[aria-label="rom.add-to-overview"]').trigger("click");
    await first.get('[aria-label="rom.add-as-background"]').trigger("click");
    await wrapper
      .get(
        '[data-shot-key="user:10"] [aria-label="rom.screenshot-make-private"]',
      )
      .trigger("click");
    await wrapper
      .get('[data-shot-key="user:10"] [aria-label="common.delete"]')
      .trigger("click");
    expect(actions.toggleVisibility).toHaveBeenCalledWith(10, false);
    expect(actions.deleteMyScreenshot).toHaveBeenCalledWith(10);
    expect(
      wrapper.get('[data-shot-key="user:7"]').findAll("button"),
    ).toHaveLength(1);
    state.canManage.value = false;
    state.canRefresh.value = false;
    await nextTick();
    expect(first.findAll("button")).toHaveLength(1);
    expect(wrapper.find('[aria-label="common.refresh"]').exists()).toBe(false);
    expect(
      wrapper.get('[data-shot-key="user:10"]').findAll("button"),
    ).toHaveLength(3);
    wrapper.unmount();
  });
  it("delegates provider refresh and keeps initial skeleton distinct from empty", async () => {
    state.providerScreenshots.value = [];
    state.refreshing.value = true;
    const wrapper = render();
    expect(
      wrapper.findAllComponents({ name: "RSkeletonBlock" }).length,
    ).toBeGreaterThan(0);
    state.refreshing.value = false;
    await nextTick();
    await wrapper.get('[aria-label="common.refresh"]').trigger("click");
    expect(actions.refreshProviderScreenshots).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("rom.screenshots-empty");
    wrapper.unmount();
  });
  it.each([
    ["provider:8", ["/provider/7", "/provider/8"], 1],
    ["user:11", ["/mine/10", "/mine/11"], 1],
    ["user:7", ["/community/7"], 0],
  ] as const)(
    "opens exact source sequence for %s and restores invoking focus",
    async (key, urls, index) => {
      const wrapper = render();
      const preview = wrapper.get(
        '[data-shot-key="' + key + '"] [data-preview]',
      );
      (preview.element as HTMLElement).focus();
      await preview.trigger("click");
      const carousel = wrapper.getComponent({ name: "RCarousel" });
      expect(carousel.props("items")).toEqual(urls);
      expect(carousel.props("modelValue")).toBe(index);
      carousel.vm.$emit("update:modelValue", 0);
      await nextTick();
      expect(carousel.props("modelValue")).toBe(0);
      carousel.vm.$emit("close");
      await nextTick();
      expect(wrapper.find("[data-carousel]").exists()).toBe(false);
      expect(document.activeElement).toBe(preview.element);
      wrapper.unmount();
    },
  );
  it("closes when active source disappears and safely falls back after entity change", async () => {
    const wrapper = render();
    await wrapper
      .get('[data-shot-key="provider:7"] [data-preview]')
      .trigger("click");
    state.providerScreenshots.value = [provider(8)];
    await flushPromises();
    expect(wrapper.find("[data-carousel]").exists()).toBe(false);
    expect(document.activeElement).toBe(
      wrapper.get('[aria-label="rom.upload-screenshots"]').element,
    );
    await wrapper
      .get('[data-shot-key="provider:8"] [data-preview]')
      .trigger("click");
    await wrapper.setProps({ rom: { id: 2 } as DetailedRom });
    await flushPromises();
    expect(wrapper.find("[data-carousel]").exists()).toBe(false);
    wrapper.unmount();
  });
  it("marks confirmed uploads and compensates only visible anchor displacement without stealing focus", async () => {
    const wrapper = render();
    const owner = wrapper.get("[data-shot-scroll]").element as HTMLElement;
    Object.defineProperty(owner, "clientHeight", { value: 500 });
    owner.scrollTop = 200;
    const card = wrapper.get('[data-shot-key="user:10"]')
      .element as HTMLElement;
    let top = 100;
    vi.spyOn(owner, "getBoundingClientRect").mockReturnValue({
      top: 0,
      bottom: 500,
    } as DOMRect);
    wrapper.findAll("[data-shot-key]").forEach((node) => {
      vi.spyOn(node.element, "getBoundingClientRect").mockImplementation(
        () =>
          ({
            top: node.element === card ? top : -100,
            bottom: node.element === card ? top + 100 : -1,
          }) as DOMRect,
      );
    });
    const preview = wrapper.get('[data-shot-key="user:10"] [data-preview]')
      .element as HTMLElement;
    preview.focus();
    actions.handleMyFiles.mockImplementationOnce(async () => {
      state.myScreenshots.value = [
        { id: 12, url: "/mine/12", isOwn: true },
        ...state.myScreenshots.value,
      ];
      state.newlyUploadedIds.value = [12];
      top = 240;
    });
    wrapper
      .getComponent({ name: "RDropzone" })
      .vm.$emit("files", [new File(["x"], "x.png")]);
    await flushPromises();
    expect(owner.scrollTop).toBe(340);
    expect(document.activeElement).toBe(preview);
    expect(wrapper.get('[data-shot-key="user:12"]').text()).toContain(
      "common.uploaded-n",
    );
    expect(
      wrapper
        .findAll("[data-shot-key]")
        .map((node) => node.attributes("data-shot-key")),
    ).toEqual([
      "provider:7",
      "provider:8",
      "user:12",
      "user:10",
      "user:11",
      "user:7",
    ]);
    wrapper.unmount();
  });
});
