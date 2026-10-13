import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import InfoGrid from "./InfoGrid.vue";

describe("InfoGrid", () => {
  it("uses stable facet IDs and preserves the current platform in chip links", () => {
    const wrapper = mount(InfoGrid, {
      props: {
        platformId: 4,
        sections: [
          {
            label: "Themes",
            filter: "themes",
            items: [{ id: "igdb:1", label: "Fantasy (translated)" }],
          },
        ],
      },
      global: {
        stubs: {
          RIcon: true,
          RouterLink: {
            props: ["to"],
            template: `<a :href="JSON.stringify(to)"><slot /></a>`,
          },
        },
      },
    });

    const link = wrapper.get("a");
    expect(link.text()).toBe("Fantasy (translated)");
    expect(link.attributes("href")).toContain('"themes":"igdb:1"');
    expect(link.attributes("href")).toContain('"platforms":"4"');
    expect(link.attributes("href")).not.toContain("Fantasy (translated)");
  });

  it("does not invent a link for role sections without a filter", () => {
    const wrapper = mount(InfoGrid, {
      props: {
        sections: [
          { label: "Developer", items: [{ id: "7", label: "Studio" }] },
        ],
      },
      global: { stubs: { RIcon: true } },
    });

    expect(wrapper.find("a").exists()).toBe(false);
    expect(wrapper.text()).toContain("Studio");
  });
});
