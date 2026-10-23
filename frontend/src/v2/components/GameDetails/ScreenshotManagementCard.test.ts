import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { RomOwnedMediaSchema } from "@/__generated__";
import ScreenshotManagementCard from "./ScreenshotManagementCard.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string, args?: Record<string, unknown>) =>
      args ? key + ":" + args.position : key,
  }),
}));
vi.mock("@v2/lib", () => ({
  RBtn: {
    props: ["icon", "disabled"],
    template: '<button :disabled="disabled"><slot /></button>',
  },
  RTooltip: { template: "<span />" },
  RAvatar: { template: "<span />" },
  RIcon: {
    props: ["icon"],
    template: '<span aria-hidden="true" :data-icon="icon" />',
  },
}));
const media = {
  id: 7,
  provider: "IGDB",
  display_label: "<script>unsafe</script>",
  placements: [
    { surface: "overview", position: 0 },
    { surface: "background", position: 3 },
  ],
} as RomOwnedMediaSchema;
describe("ScreenshotManagementCard source capabilities", () => {
  it("shows both stored positions including zero and emits separate provider actions", async () => {
    const item = {
      source: "provider" as const,
      key: "provider:7" as const,
      media,
      url: "/provider",
    };
    const wrapper = mount(ScreenshotManagementCard, {
      props: { item, canManage: true },
    });
    expect(wrapper.text()).toContain("rom.screenshots-action-overview");
    expect(wrapper.text()).toContain("rom.screenshots-action-background");
    expect(wrapper.text()).toContain("common.delete");
    expect(wrapper.text()).toContain("rom.screenshots-overview-position:1");
    expect(wrapper.text()).toContain("rom.screenshots-background-position:4");
    expect(
      wrapper
        .get('[aria-label="rom.remove-from-overview"]')
        .attributes("aria-pressed"),
    ).toBe("true");
    expect(
      wrapper
        .get('[aria-label="rom.remove-as-background"]')
        .attributes("aria-pressed"),
    ).toBe("true");
    await wrapper.get("[data-preview]").trigger("click");
    await wrapper
      .get('[aria-label="rom.remove-from-overview"]')
      .trigger("click");
    await wrapper
      .get('[aria-label="rom.remove-as-background"]')
      .trigger("click");
    await wrapper
      .get('[aria-label="rom.provider-screenshot-remove-title"]')
      .trigger("click");
    expect(wrapper.emitted("action")?.map(([action]) => action)).toEqual([
      { type: "preview", item },
      { type: "placement", item, surface: "overview" },
      { type: "placement", item, surface: "background" },
      { type: "remove-provider", item },
    ]);
    const overview = wrapper.get('[aria-label="rom.remove-from-overview"]');
    expect(overview.attributes("variant")).toBe("flat");
    expect(overview.find('[data-icon="mdi-check-circle"]').exists()).toBe(true);
    await wrapper.setProps({
      item: { ...item, media: { ...media, placements: [] } },
    });
    const unselected = wrapper.get('[aria-label="rom.add-to-overview"]');
    expect(unselected.attributes("variant")).toBe("translucent");
    expect(unselected.find('[data-icon="mdi-check-circle"]').exists()).toBe(
      false,
    );
    expect(wrapper.find("script").exists()).toBe(false);
    expect(wrapper.get("[data-preview]").find("button").exists()).toBe(false);
  });
  it("keeps provider read-only without management permission", () => {
    const wrapper = mount(ScreenshotManagementCard, {
      props: {
        item: {
          source: "provider",
          key: "provider:7",
          media,
          url: "/provider",
        },
      },
    });
    expect(wrapper.findAll("button")).toHaveLength(1);
  });
  it("allows personal actions without provider permission and preserves visibility", async () => {
    const item = {
      source: "mine" as const,
      key: "user:7" as const,
      shot: { id: 7, url: "/mine", isOwn: true, isPublic: true },
    };
    const wrapper = mount(ScreenshotManagementCard, { props: { item } });
    expect(wrapper.text()).toContain("rom.screenshot-public");
    await wrapper
      .get('[aria-label="rom.screenshot-make-private"]')
      .trigger("click");
    await wrapper.get('[aria-label="common.delete"]').trigger("click");
    expect(wrapper.emitted("action")?.map(([action]) => action)).toEqual([
      { type: "visibility", item, isPublic: false },
      { type: "delete-mine", item },
    ]);
  });
  it("keeps community preview-only despite equal IDs, admin capability or misleading own flag", async () => {
    const item = {
      source: "community" as const,
      key: "user:7" as const,
      shot: { id: 7, url: "/community", isOwn: true, username: "<b>Alice</b>" },
    };
    const wrapper = mount(ScreenshotManagementCard, {
      props: { item, canManage: true },
    });
    expect(wrapper.findAll("button")).toHaveLength(1);
    expect(wrapper.find("b").exists()).toBe(false);
    expect(wrapper.text()).toContain("<b>Alice</b>");
    await wrapper.get("img").trigger("error");
    expect(wrapper.text()).toContain("rom.screenshots-preview-unavailable");
    await wrapper.get("[data-preview]").trigger("click");
    expect(wrapper.emitted("action")).toEqual([[{ type: "preview", item }]]);
  });
});
