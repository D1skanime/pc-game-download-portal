import { flushPromises, mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import { reactive } from "vue";
import type { DetailedRom } from "@/v2/data/adapters/legacy/stores/roms";
import MediaTab from "./MediaTab.vue";

vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
const replace = vi.fn();
const route = reactive({
  path: "/rom/1",
  query: { tab: "media", subtab: "screenshots", retained: "value" } as Record<
    string,
    string
  >,
});
vi.mock("vue-router", () => ({
  useRoute: () => route,
  useRouter: () => ({ replace }),
}));
vi.mock("@v2/lib", () => ({
  RIcon: { template: "<span />" },
  REmptyState: { template: "<div />" },
}));
vi.mock("@/v2/components/GameDetails/ScreenshotsSubtab.vue", () => ({
  __esModule: true,
  default: { template: "<div data-screenshots />" },
}));
vi.mock("@/v2/components/GameDetails/ManualSubtab.vue", () => ({
  __esModule: true,
  default: { template: "<div data-manual />" },
}));
vi.mock("@/v2/components/GameDetails/ArtworkSubtab.vue", () => ({
  __esModule: true,
  default: { template: "<div data-artwork />" },
}));
vi.mock("@/v2/components/GameDetails/SoundtrackPanel.vue", () => ({
  __esModule: true,
  default: { template: "<div data-soundtrack />" },
}));

const source = readFileSync(
  "src/v2/components/GameDetails/MediaTab.vue",
  "utf8",
);
describe("MediaTab soundtrack access", () => {
  it("keeps the soundtrack panel available so an empty game can receive uploads", () => {
    expect(source).toContain('<SoundtrackPanel :rom="rom"');
    expect(source).not.toContain("!rom.has_soundtrack");
  });
  it("defaults the parent media tab to screenshots", () => {
    expect(source).toContain(': "screenshots",');
  });
  it("keeps all media owners mounted and preserves query state across screenshot/manual navigation", async () => {
    const wrapper = mount(MediaTab, {
      props: { rom: { id: 1 } as DetailedRom },
    });
    await flushPromises();
    const screenshot = wrapper.get("[data-screenshots]").element;
    const manual = wrapper.get("[data-manual]").element;
    const soundtrack = wrapper.get("[data-soundtrack]").element;
    const tabs = wrapper.findAll('[role="tab"]');
    await tabs[0].trigger("click");
    expect(replace).toHaveBeenLastCalledWith({
      path: "/rom/1",
      query: { tab: "media", subtab: "manual", retained: "value" },
    });
    expect(wrapper.get("[data-screenshots]").element).toBe(screenshot);
    expect(wrapper.get("[data-manual]").element).toBe(manual);
    expect(wrapper.get("[data-soundtrack]").element).toBe(soundtrack);
    expect(
      wrapper.get("#media-panel-screenshots").attributes("style"),
    ).toContain("display: none");
    await tabs[1].trigger("click");
    expect(
      wrapper.get("#media-panel-screenshots").attributes("style") ?? "",
    ).not.toContain("display: none");
    route.query.subtab = "artwork";
    await flushPromises();
    expect(
      wrapper.get("#media-panel-artwork").attributes("style") ?? "",
    ).not.toContain("display: none");
    route.query.tab = "overview";
    await flushPromises();
    expect(replace).toHaveBeenLastCalledWith({
      path: "/rom/1",
      query: { tab: "overview", retained: "value" },
    });
    wrapper.unmount();
  });
});
