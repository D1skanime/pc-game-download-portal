import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { IGDBRelatedGame } from "@/__generated__";
import { ROUTES } from "@/plugins/router";
import RelatedGameCard from "./RelatedGameCard.vue";

const { push, getRomByMetadataProvider } = vi.hoisted(() => ({
  push: vi.fn(),
  getRomByMetadataProvider: vi.fn(),
}));

vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRouter: () => ({
    currentRoute: { value: { path: "/rom/1", query: { tab: "overview" } } },
    push,
  }),
}));

vi.mock("@/services/api/rom", () => ({
  default: { getRomByMetadataProvider },
}));

vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));

const game = {
  id: 123,
  name: "Phantom Liberty",
  slug: "cyberpunk-2077-phantom-liberty",
  type: "dlc",
  cover_url: "",
} satisfies IGDBRelatedGame;

describe("RelatedGameCard", () => {
  beforeEach(() => {
    push.mockReset();
    getRomByMetadataProvider.mockReset();
  });

  it("marks a locally matched DLC as available", () => {
    const wrapper = mount(RelatedGameCard, {
      props: { game, localComponentId: 7, isDlc: true },
      global: {
        stubs: { GameCard: { template: "<div><slot name='overlay' /></div>" } },
      },
    });

    expect(wrapper.get(".related-card__owned").text()).toBe("common.owned");
  });

  it("opens a locally matched DLC at its parent-owned detail route", async () => {
    const open = vi.spyOn(window, "open");
    const wrapper = mount(RelatedGameCard, {
      props: { game, localComponentId: 7, parentRomId: 1, isDlc: true },
      global: {
        stubs: {
          GameCard: {
            template:
              "<button @click='$emit(\"click\", $event)'><slot /></button>",
          },
        },
      },
    });

    await wrapper.get("button").trigger("click");

    expect(push).toHaveBeenCalledWith({
      name: ROUTES.PC_DLC,
      params: { rom: 1, component: 7 },
    });
    expect(open).not.toHaveBeenCalled();
    expect(getRomByMetadataProvider).not.toHaveBeenCalled();
  });

  it("does not navigate non-local DLC or external related games", async () => {
    const wrapper = mount(RelatedGameCard, {
      props: { game, isDlc: true },
      global: {
        stubs: {
          GameCard: {
            template:
              "<button @click='$emit(\"click\", $event)'><slot /></button>",
          },
        },
      },
    });

    await wrapper.get("button").trigger("click");

    expect(push).not.toHaveBeenCalled();
    expect(getRomByMetadataProvider).not.toHaveBeenCalled();
  });
});
