import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent } from "vue";
import PlatformStorageMapping from "./PlatformStorageMapping.vue";

const mocks = vi.hoisted(() => ({
  route: { params: { platformId: "1" } },
  routerPush: vi.fn(),
  fetchPlatforms: vi.fn(),
  getRoots: vi.fn(),
  getMapping: vi.fn(),
  getPreview: vi.fn(),
  browseRoot: vi.fn(),
  testMapping: vi.fn(),
  createMapping: vi.fn(),
  updateMapping: vi.fn(),
  refreshPreview: vi.fn(),
  removalConsequences: vi.fn(),
  removeMapping: vi.fn(),
  snackbar: { error: vi.fn(), success: vi.fn() },
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (_key: string, fallback?: string) => fallback ?? _key }),
}));

vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.routerPush }),
}));

vi.mock("@/stores/platforms", () => ({
  default: () => ({
    allPlatforms: [{ id: 1, display_name: "Arcade", name: "Arcade" }],
    fetchPlatforms: mocks.fetchPlatforms,
  }),
}));

vi.mock("@/v2/composables/useCan", () => ({
  useCan: () => computed(() => true),
}));

vi.mock("@/v2/composables/useConfirm", () => ({
  useConfirm: () => vi.fn().mockResolvedValue(false),
}));

vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => mocks.snackbar,
}));

vi.mock("@/services/api/storage", () => ({
  default: {
    getRoots: mocks.getRoots,
    getMapping: mocks.getMapping,
    getPreview: mocks.getPreview,
    browseRoot: mocks.browseRoot,
    testMapping: mocks.testMapping,
    createMapping: mocks.createMapping,
    updateMapping: mocks.updateMapping,
    refreshPreview: mocks.refreshPreview,
    removalConsequences: mocks.removalConsequences,
    removeMapping: mocks.removeMapping,
  },
}));

vi.mock("@v2/lib", () => ({
  RAlert: defineComponent({
    template: "<div><slot /><slot name='title' /><slot name='append' /></div>",
  }),
  RBtn: defineComponent({
    emits: ["click"],
    template: "<button @click=\"$emit('click')\"><slot /></button>",
  }),
  RCard: defineComponent({ template: "<section><slot /></section>" }),
  RDivider: defineComponent({ template: "<hr />" }),
  REmptyState: defineComponent({ template: "<div><slot /></div>" }),
  RList: defineComponent({ template: "<div><slot /></div>" }),
  RListItem: defineComponent({ template: "<div><slot /></div>" }),
  RSkeletonBlock: defineComponent({ template: "<div />" }),
  RSteps: defineComponent({ template: "<div><slot /></div>" }),
}));

describe("PlatformStorageMapping", () => {
  beforeEach(() => {
    mocks.fetchPlatforms.mockReset();
    mocks.getRoots.mockReset();
    mocks.getMapping.mockReset();
    mocks.getPreview.mockReset();
    mocks.browseRoot.mockReset();
    mocks.testMapping.mockReset();
    mocks.createMapping.mockReset();
    mocks.updateMapping.mockReset();
    mocks.refreshPreview.mockReset();
    mocks.removalConsequences.mockReset();
    mocks.removeMapping.mockReset();
    mocks.routerPush.mockReset();
    mocks.snackbar.error.mockReset();
    mocks.snackbar.success.mockReset();

    mocks.getRoots.mockResolvedValue({
      data: [{ id: 7, name: "Library", active: true }],
    });
  });

  it("treats platform_mapping_missing as an unmapped state instead of a generic error", async () => {
    mocks.getMapping.mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 409,
        data: { detail: { code: "platform_mapping_missing" } },
      },
    });

    const wrapper = mount(PlatformStorageMapping);
    await flushPromises();

    expect(wrapper.text()).toContain("Storage administration");
    expect(wrapper.text()).toContain("No storage folder mapped");
    expect(wrapper.text()).toContain("Map storage");
    expect(wrapper.text()).not.toContain("Something went wrong");
  });
});
