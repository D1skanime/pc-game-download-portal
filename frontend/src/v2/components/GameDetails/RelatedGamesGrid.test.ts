import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type { IGDBRelatedGame } from "@/__generated__";
import RelatedGamesGrid from "./RelatedGamesGrid.vue";

const game = {
  id: 123,
  name: "Phantom Liberty",
  slug: "cyberpunk-2077-phantom-liberty",
  type: "dlc",
  cover_url: "",
} satisfies IGDBRelatedGame;

describe("RelatedGamesGrid", () => {
  it("merges matching local DLCs and appends local-only candidates", () => {
    const wrapper = mount(RelatedGamesGrid, {
      props: {
        items: [game],
        isDlc: true,
        parentRomId: 42,
        localCandidates: [
          {
            igdbId: 123,
            componentId: 7,
            name: "Local Phantom Liberty",
            coverUrl: "/assets/romm/resources/roms/42/components/7/cover.webp",
          },
          {
            igdbId: 456,
            componentId: 8,
            name: "Blood and Wine",
            coverUrl: "/assets/romm/resources/roms/42/components/8/cover.webp",
          },
        ],
      },
      global: {
        stubs: {
          RelatedGameCard: {
            props: ["parentRomId", "localComponentId", "localCoverUrl", "game"],
            template:
              "<div :data-parent-rom-id='parentRomId' :data-component-id='localComponentId' :data-cover='localCoverUrl'>{{ game.name }}</div>",
          },
        },
      },
    });

    const cards = wrapper.findAll("[data-parent-rom-id]");
    expect(cards).toHaveLength(2);
    expect(cards[0].text()).toBe("Phantom Liberty");
    expect(cards[0].attributes("data-parent-rom-id")).toBe("42");
    expect(cards[0].attributes("data-component-id")).toBe("7");
    expect(cards[0].attributes("data-cover")).toContain(
      "components/7/cover.webp",
    );
    expect(cards[1].text()).toBe("Blood and Wine");
    expect(cards[1].attributes("data-component-id")).toBe("8");
  });
});
