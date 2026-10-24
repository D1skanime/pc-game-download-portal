import { mount } from "@vue/test-utils";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import AppNav from "@/v2/components/AppShell/AppNav.vue";
import AboutDialog from "@/v2/components/Dialogs/AboutDialog.vue";
import AuthCard from "@/v2/components/shared/AuthCard.vue";
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

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));
vi.mock("@/v2/composables/useNavDestinations", () => ({
  useNavDestinations: () => ({ destinations: [], activeId: "home" }),
}));
vi.mock("@/v2/data/adapters/legacy/stores/heartbeat", () => ({
  default: () => ({ value: { SYSTEM: { VERSION: "v1.2.3" } } }),
}));

describe("brand consumers", () => {
  it("renders auth identity while preserving form slot and frame", () => {
    const wrapper = shallowMount(AuthCard, {
      slots: { default: '<input aria-label="Username" />' },
      global: {
        stubs: {
          ProjectBrand: false,
          RCard: { template: "<div><slot /></div>" },
        },
      },
    });
    expect(wrapper.text()).toBe("ZockArchive");
    expect(wrapper.find("input").exists()).toBe(true);
    expect(wrapper.find("r-img-stub").exists()).toBe(false);
  });

  it("retains one localized home link with decorative navigation text", () => {
    const wrapper = shallowMount(AppNav, {
      global: {
        stubs: {
          ProjectBrand: false,
          RouterLink: { props: ["to"], template: '<a :href="to"><slot /></a>' },
        },
      },
    });
    const home = wrapper.get("a");
    expect(home.attributes("href")).toBe("/");
    expect(home.attributes("aria-label")).toBe("common.home");
    expect(home.get(".project-brand").attributes("aria-hidden")).toBe("true");
    expect(home.text()).toContain("ZockArchive");
    expect(wrapper.find("r-img-stub").exists()).toBe(false);
  });

  it("uses project docs and explicitly attributes upstream community", () => {
    const wrapper = shallowMount(AboutDialog, {
      global: {
        stubs: {
          ProjectBrand: false,
          RDialog: {
            template:
              "<section><slot name='header' /><slot name='content' /></section>",
          },
        },
      },
    });
    const links = wrapper.findAll("a");
    expect(
      links.some(
        (link) =>
          link.attributes("href") ===
          "https://github.com/D1skanime/zockarchive/tree/main/docs",
      ),
    ).toBe(true);
    expect(
      links
        .find((link) =>
          link.attributes("href")?.startsWith("https://discord.com"),
        )
        ?.text(),
    ).toContain("RomM (upstream)");
    expect(wrapper.find("r-img-stub").exists()).toBe(false);
    wrapper.unmount();
  });
});
