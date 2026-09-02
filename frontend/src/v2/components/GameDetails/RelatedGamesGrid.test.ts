import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type { IGDBRelatedGame } from "@/__generated__";
import RelatedGamesGrid from "./RelatedGamesGrid.vue";

const game = {
  id: 123,
  name: "Phantom Liberty",
  slug: "cyberpunk-2077-phantom-liberty",
  type: "dlc",
  cover_url: null,
} satisfies IGDBRelatedGame;

describe("RelatedGamesGrid", () => {
  it("passes the parent ROM id and local component id to DLC cards", () => {
    const wrapper = mount(RelatedGamesGrid, {
      props: {
        items: [game],
        isDlc: true,
        parentRomId: 42,
        localComponentIds: { 123: 7 },
      },
      global: {
        stubs: {
          RelatedGameCard: {
            props: ["parentRomId", "localComponentId"],
            template:
              "<div :data-parent-rom-id='parentRomId' :data-component-id='localComponentId' />",
          },
        },
      },
    });

    const card = wrapper.get("[data-parent-rom-id]");
    expect(card.attributes("data-parent-rom-id")).toBe("42");
    expect(card.attributes("data-component-id")).toBe("7");
  });
});
