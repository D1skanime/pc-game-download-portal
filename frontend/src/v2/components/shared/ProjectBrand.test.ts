import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ProjectBrand from "@/v2/components/shared/ProjectBrand.vue";

describe("ProjectBrand", () => {
  it.each(["auth", "navigation", "about"] as const)(
    "renders truthful semantic %s identity without artwork or extra focus stops",
    (variant) => {
      const wrapper = mount(ProjectBrand, { props: { variant } });
      expect(wrapper.text()).toContain(
        variant === "auth" ? "ZockArchive" : "ZA",
      );
      expect(
        wrapper.find("img, svg, a, button, [tabindex], [role]").exists(),
      ).toBe(false);
      expect(wrapper.attributes("aria-label")).toBeUndefined();
      expect(wrapper.text()).not.toMatch(/PGDP|RomM/);
    },
  );

  it("keeps both navigation words while allowing the expanded word alone to hide", () => {
    const wrapper = mount(ProjectBrand, { props: { variant: "navigation" } });
    expect(wrapper.get(".project-brand__short").text()).toBe("ZA");
    expect(wrapper.get(".project-brand__word").text()).toBe("ZockArchive");
  });

  it("allows the home link owner to suppress redundant announcements", () => {
    const wrapper = mount(ProjectBrand, {
      props: { variant: "navigation" },
      attrs: { "aria-hidden": "true" },
    });
    expect(wrapper.attributes("aria-hidden")).toBe("true");
  });
});
