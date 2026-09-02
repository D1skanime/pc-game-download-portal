import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent } from "vue";
import type { DetailedRom } from "@/stores/roms";
import AgeRatingBadges from "./AgeRatingBadges.vue";

const TooltipStub = defineComponent({
  template: "<span><slot name='activator' :props='{}' /></span>",
});

function rom(): DetailedRom {
  return {
    metadatum: {
      age_ratings: ["R 18+", "18", "18", "Z", "18", "19+", "M"],
    },
    igdb_metadata: {
      age_ratings: [
        { rating: "R 18+", category: "ACB", rating_cover_url: "/acb.png" },
        { rating: "18", category: "PEGI", rating_cover_url: "/pegi.png" },
        {
          rating: "18",
          category: "CLASS_IND",
          rating_cover_url: "/class-ind.png",
        },
        { rating: "Z", category: "CERO", rating_cover_url: "/cero.png" },
        { rating: "18", category: "USK", rating_cover_url: "/usk.png" },
        { rating: "19+", category: "GRAC", rating_cover_url: "/grac.png" },
        { rating: "M", category: "ESRB", rating_cover_url: "/esrb.png" },
      ],
    },
  } as DetailedRom;
}

describe("AgeRatingBadges", () => {
  it("shows one preferred badge when several providers report the same rating", () => {
    const wrapper = mount(AgeRatingBadges, {
      props: { rom: rom() },
      global: { stubs: { RIcon: true, RTooltip: TooltipStub } },
    });

    const badges = wrapper.findAll("img");
    expect(badges).toHaveLength(5);
    expect(
      badges.filter((badge) => badge.attributes("alt") === "USK: 18"),
    ).toHaveLength(1);
    expect(badges.map((badge) => badge.attributes("alt"))).toEqual([
      "ACB: R 18+",
      "USK: 18",
      "CERO: Z",
      "GRAC: 19+",
      "ESRB: M",
    ]);
  });
});
