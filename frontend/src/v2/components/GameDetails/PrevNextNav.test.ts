import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import PrevNextNav from "./PrevNextNav.vue";

const mocks = vi.hoisted(() => ({
  enteredFromGallery: { value: false },
  getRomAt: vi.fn(),
  getRoms: vi.fn(),
  push: vi.fn(),
  romIdIndex: [] as number[],
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));
vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRoute: () => ({ query: { tab: "overview" } }),
  useRouter: () => ({ push: mocks.push }),
}));
vi.mock("@/services/api/rom", () => ({ default: { getRoms: mocks.getRoms } }));
vi.mock("@/v2/composables/useGalleryProvenance", () => ({
  useGalleryProvenance: () => ({
    enteredFromGallery: mocks.enteredFromGallery,
  }),
}));
vi.mock("@/v2/stores/galleryRoms", () => ({
  default: () => ({
    getRomAt: mocks.getRomAt,
    romIdIndex: mocks.romIdIndex,
  }),
}));

describe("PrevNextNav", () => {
  it("loads alphabetical platform neighbours for a directly opened game", async () => {
    mocks.enteredFromGallery.value = false;
    mocks.romIdIndex = [];
    mocks.getRoms.mockResolvedValueOnce({
      data: { rom_id_index: [31, 32, 33] },
    });

    const wrapper = mount(PrevNextNav, {
      props: { romId: 32, platformId: 9 },
      global: { stubs: { RBtn: false } },
    });
    await flushPromises();

    expect(mocks.getRoms).toHaveBeenCalledWith({
      groupByMetaId: true,
      limit: 1,
      orderBy: "name",
      orderDir: "asc",
      platformIds: [9],
      withCharIndex: false,
      withFilterValues: false,
      withTotal: false,
    });
    expect(wrapper.findAll("button")).toHaveLength(2);

    await wrapper.findAll("button")[1].trigger("click");
    expect(mocks.push).toHaveBeenCalledWith({
      name: "rom",
      params: { rom: 33 },
      query: { tab: "overview" },
    });
  });
});
