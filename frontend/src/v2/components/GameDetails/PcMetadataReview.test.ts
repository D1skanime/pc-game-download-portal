import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import PcMetadataReview from "./PcMetadataReview.vue";

const { getCandidates, selectCandidate } = vi.hoisted(() => ({
  getCandidates: vi.fn(),
  selectCandidate: vi.fn(),
}));

vi.mock("@/services/api/rom", () => ({
  default: {
    getPcMetadataCandidates: getCandidates,
    selectPcMetadataCandidate: selectCandidate,
  },
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string) =>
      ({
        "rom.pc-find-metadata": "Find metadata",
        "rom.pc-no-metadata-matches": "No metadata matches found",
        "rom.pc-metadata-source-unavailable":
          "This metadata source is unavailable. Try again or choose another source.",
        "rom.pc-apply-selected-metadata": "Apply selected metadata",
      })[key] ?? key,
  }),
}));

vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ error: vi.fn() }),
}));

describe("PcMetadataReview", () => {
  it("requires a candidate selection before applying metadata", async () => {
    getCandidates.mockResolvedValue({
      data: {
        expected_version: "2026-09-01T10:00:00Z",
        providers: {
          launchbox: {
            provider: "launchbox",
            available: true,
            candidates: [
              {
                id: "launchbox:1",
                provider: "launchbox",
                title: "Example PC Game",
                provider_ids: { launchbox_id: 1 },
                description_available: true,
                media: [],
              },
            ],
          },
        },
      },
    });

    const wrapper = mount(PcMetadataReview, {
      props: { romId: 1 },
      global: {
        stubs: { RDialog: { template: "<div><slot name='content' /></div>" } },
      },
    });
    await wrapper.get("[data-testid='find-pc-metadata']").trigger("click");
    await vi.waitFor(() =>
      expect(getCandidates).toHaveBeenCalledWith({ romId: 1 }),
    );

    const apply = wrapper.get("[data-testid='apply-pc-metadata']");
    expect(apply.attributes("disabled")).toBeDefined();
    expect(selectCandidate).not.toHaveBeenCalled();

    await wrapper
      .get("[data-testid='pc-candidate-launchbox:1']")
      .trigger("click");
    expect(apply.attributes("disabled")).toBeUndefined();

    await apply.trigger("click");
    expect(selectCandidate).toHaveBeenCalledWith({
      romId: 1,
      selection: {
        candidate_id: "launchbox:1",
        expected_version: "2026-09-01T10:00:00Z",
      },
    });
  });

  it("closes the review after successfully applying a candidate", async () => {
    getCandidates.mockResolvedValue({
      data: {
        expected_version: "2026-09-01T10:00:00Z",
        providers: {
          igdb: {
            provider: "igdb",
            available: true,
            candidates: [
              {
                id: "igdb:1877",
                provider: "igdb",
                title: "Cyberpunk 2077",
                provider_ids: { igdb_id: 1877 },
                description_available: true,
                media: [],
              },
            ],
          },
        },
      },
    });
    selectCandidate.mockResolvedValue({ data: {} });

    const wrapper = mount(PcMetadataReview, {
      props: { romId: 1 },
      global: {
        stubs: {
          RDialog: {
            props: ["modelValue"],
            template: "<div v-if='modelValue'><slot name='content' /></div>",
          },
        },
      },
    });
    await wrapper.get("[data-testid='find-pc-metadata']").trigger("click");
    await vi.waitFor(() => expect(getCandidates).toHaveBeenCalled());
    await wrapper
      .get("[data-testid='pc-candidate-igdb:1877']")
      .trigger("click");

    await wrapper.get("[data-testid='apply-pc-metadata']").trigger("click");
    await vi.waitFor(() => expect(selectCandidate).toHaveBeenCalled());

    expect(wrapper.emitted("applied")).toHaveLength(1);
    expect(wrapper.find("[data-testid='apply-pc-metadata']").exists()).toBe(
      false,
    );
  });

  it("shows the approved empty and provider-error copy", async () => {
    getCandidates.mockResolvedValue({
      data: {
        expected_version: "2026-09-01T10:00:00Z",
        providers: {
          launchbox: {
            provider: "launchbox",
            available: false,
            candidates: [],
            reason: "offline",
          },
        },
      },
    });

    const wrapper = mount(PcMetadataReview, {
      props: { romId: 1 },
      global: {
        stubs: { RDialog: { template: "<div><slot name='content' /></div>" } },
      },
    });
    await wrapper.get("[data-testid='find-pc-metadata']").trigger("click");
    await vi.waitFor(() => expect(getCandidates).toHaveBeenCalled());

    expect(wrapper.text()).toContain("No metadata matches found");
    expect(wrapper.text()).toContain(
      "This metadata source is unavailable. Try again or choose another source.",
    );
  });
});
