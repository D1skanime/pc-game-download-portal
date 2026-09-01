import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { IGDBRelatedGame } from "@/__generated__";
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
  it("opens a locally matched DLC in the current game's filtered Files tab", async () => {
    const open = vi.spyOn(window, "open");
    const wrapper = mount(RelatedGameCard, {
      props: { game, localComponentId: 7, isDlc: true },
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
      path: "/rom/1",
      query: { tab: "files", component: "7" },
    });
    expect(open).not.toHaveBeenCalled();
    expect(getRomByMetadataProvider).not.toHaveBeenCalled();
  });
});
