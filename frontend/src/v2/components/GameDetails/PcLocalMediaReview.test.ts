import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import PcLocalMediaReview from "./PcLocalMediaReview.vue";

const { getCandidates, selectMedia } = vi.hoisted(() => ({
  getCandidates: vi.fn(),
  selectMedia: vi.fn(),
}));

vi.mock("@/services/api/rom", () => ({
  default: {
    getPcLocalMediaCandidates: getCandidates,
    selectPcLocalMedia: selectMedia,
  },
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string) =>
      ({
        "rom.artwork": "Artwork",
        "rom.select-cover-image": "Use as cover",
        "rom.pc-extras": "Extras",
        "rom.pc-no-components": "No eligible local artwork",
        "common.apply": "Apply",
      })[key] ?? key,
  }),
}));

vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ error: vi.fn(), success: vi.fn() }),
}));

describe("PcLocalMediaReview", () => {
  it("requires an explicit candidate and role before applying local artwork", async () => {
    getCandidates.mockResolvedValue({
      data: {
        expected_version: "2026-09-01T10:00:00Z",
        candidates: [
          {
            component_id: 7,
            member_id: 11,
            relative_path: "Extras/poster.png",
            source_sha256: "a".repeat(64),
            image_type: "png",
            preview_url: "/api/roms/1/pc-local-media-preview/7/11",
          },
        ],
      },
    });

    const wrapper = mount(PcLocalMediaReview, {
      props: { romId: 1 },
      global: {
        stubs: { RDialog: { template: "<div><slot name='content' /></div>" } },
      },
    });

    await wrapper.get("[data-testid='select-local-artwork']").trigger("click");
    await vi.waitFor(() =>
      expect(getCandidates).toHaveBeenCalledWith({ romId: 1 }),
    );

    const apply = wrapper.get("[data-testid='apply-local-artwork']");
    expect(apply.attributes("disabled")).toBeDefined();

    await wrapper
      .get("[data-testid='local-art-candidate-7-11']")
      .trigger("click");
    expect(apply.attributes("disabled")).toBeDefined();

    await wrapper.get("[data-testid='local-art-role-cover']").trigger("click");
    expect(apply.attributes("disabled")).toBeUndefined();

    await apply.trigger("click");
    expect(selectMedia).toHaveBeenCalledWith({
      romId: 1,
      selection: {
        component_id: 7,
        member_id: 11,
        role: "cover",
        expected_version: "2026-09-01T10:00:00Z",
      },
    });
  });
});
