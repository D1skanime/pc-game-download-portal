import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import StorageRootsSection from "./StorageRootsSection.vue";

const bootstrapLegacy = vi.hoisted(() => vi.fn());
vi.mock("@/services/api/storage", () => ({
  default: {
    getRoots: vi.fn().mockResolvedValue({ data: [] }),
    bootstrapLegacy,
  },
}));
vi.mock("@/services/api/platform", () => ({
  default: {
    getPlatforms: vi.fn().mockResolvedValue({ data: [] }),
    getSupportedPlatforms: vi.fn().mockResolvedValue({ data: [] }),
  },
}));
vi.mock("@/v2/composables/useCan", () => ({ useCan: () => true }));
vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/v2/data/adapters/legacy/stores/platforms", () => ({
  default: () => ({ allPlatforms: [], set: vi.fn() }),
}));

describe("StorageRootsSection", () => {
  it("does not expose or invoke the legacy bootstrap mutation", async () => {
    const wrapper = mount(StorageRootsSection, {
      global: {
        stubs: {
          RAlert: {
            template:
              "<div><slot /><slot name='title' /><slot name='append' /></div>",
          },
          RBtn: { template: "<button><slot /></button>" },
          RCard: { template: "<div><slot /></div>" },
          RList: { template: "<div><slot /></div>" },
          RListItem: true,
          RSkeletonBlock: true,
          PlatformSelect: true,
        },
      },
    });
    expect(wrapper.text()).not.toContain("storage.reconcile-legacy");
    expect(wrapper.text()).not.toContain("storage.import-legacy");
    expect(bootstrapLegacy).not.toHaveBeenCalled();
  });
});
