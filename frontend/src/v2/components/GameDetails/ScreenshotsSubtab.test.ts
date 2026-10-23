import { shallowMount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import type { DetailedRom } from "@/v2/data/adapters/legacy/stores/roms";
import ScreenshotsSubtab from "./ScreenshotsSubtab.vue";

const actions = vi.hoisted(() => ({
  togglePlacement: vi.fn(),
  deleteProviderScreenshot: vi.fn(),
  refreshProviderScreenshots: vi.fn(),
  handleMyFiles: vi.fn(),
  deleteMyScreenshot: vi.fn(),
  toggleVisibility: vi.fn(),
}));
vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("@v2/lib", () => ({
  RBtn: { name: "RBtn", template: "<button><slot /></button>" },
  RDropzone: { name: "RDropzone", template: "<div><slot /></div>" },
  RCarousel: { name: "RCarousel", template: "<div />" },
  REmptyState: { template: "<div />" },
  RSkeletonBlock: { template: "<div />" },
  RTooltip: { template: "<span><slot /></span>" },
}));
vi.mock("@/v2/components/GameDetails/ScreenshotsTab.vue", () => ({
  default: {
    name: "ScreenshotsTab",
    props: { screenshots: Array, deletable: Boolean, togglable: Boolean },
    template: "<div />",
  },
}));
vi.mock("@/v2/composables/useScreenshotManagement", async () => {
  const { computed, ref } = await import("vue");
  return {
    useScreenshotManagement: () => ({
      ...actions,
      canManage: ref(true),
      canRefresh: ref(true),
      refreshing: ref(false),
      mutatingId: ref(null),
      togglingId: ref(null),
      deletingId: ref(null),
      providerScreenshots: computed(() => [{ id: 7, display_label: "IGDB" }]),
      providerUrls: computed(() => ["/provider"]),
      myScreenshots: computed(() => [{ id: 10, isOwn: true }]),
      communityScreenshots: computed(() => [{ id: 7, isOwn: false }]),
      mediaContentUrl: () => "/provider",
      hasPlacement: () => false,
      placementPosition: () => undefined,
    }),
  };
});

const source = readFileSync(
  "src/v2/components/GameDetails/ScreenshotsSubtab.vue",
  "utf8",
);

const lifecycle = readFileSync(
  "src/v2/composables/useScreenshotManagement/index.ts",
  "utf8",
);
describe("ScreenshotsSubtab provider candidates", () => {
  it("keeps candidate existence separate from overview and background placement", () => {
    expect(source).toContain("providerScreenshots");
    expect(source).toContain("hasPlacement");
    expect(source).toContain('"overview"');
    expect(source).toContain('"background"');
    expect(lifecycle).toContain("setOwnedMediaPlacement");
    expect(lifecycle).toContain("removeOwnedMediaPlacement");
  });

  it("names each placement action by its destination", () => {
    expect(source).toContain('t("rom.add-to-overview")');
    expect(source).toContain('t("rom.remove-from-overview")');
    expect(source).toContain('t("rom.add-as-background")');
    expect(source).toContain('t("rom.remove-as-background")');
  });

  it("uses guarded owned-media mutations with conflict recovery", () => {
    expect(lifecycle).toContain("useCan");
    expect(lifecycle).toContain('const canManage = useCan("rom.edit", scope)');
    expect(source).not.toContain('useCan("rom.delete", scope)');
    expect(lifecycle).toContain('tone: "danger"');
    expect(lifecycle).toContain("deleteOwnedMedia");
    expect(lifecycle).toContain("refreshOwnedMedia");
    expect(lifecycle).toContain("response?.status === 409");
    expect(lifecycle).toContain("romApi.getRom");
    expect(lifecycle).toContain("romsStore.setCurrentRom(data)");
    expect(lifecycle).toContain("romsStore.update(data)");
  });

  it("keeps previews contained and action controls out of the lightbox trigger", () => {
    expect(source).toContain("RCarousel");
    expect(source).toContain("providerLightboxOpen");
    expect(source).toContain("@click.stop");
    expect(source).toContain("aria-label");
    expect(source).toContain("RSkeletonBlock");
  });

  it("renders migrated provider catalog entries without relying on legacy overview data", () => {
    expect(lifecycle).toContain("rom().owned_media ?? []");
    expect(lifecycle).toContain('item.role === "screenshot"');
    expect(lifecycle).toContain('item.origin === "provider"');
    expect(source).toContain('v-if="canManage" class="r-v2-shots__actions"');
    expect(source).toContain(
      'v-if="canManage"\n              icon="mdi-delete-outline"',
    );
    expect(source).toContain("providerScreenshots.length");
    expect(source).not.toContain("merged_screenshots");
  });

  it("keeps the provider delete button as the visible tooltip activator", () => {
    expect(source).toMatch(
      /<RBtn\s+v-if="canManage"\s+icon="mdi-delete-outline"\s+:loading="mutatingId === item\.id"\s+:aria-label="t\('common\.delete'\)"\s+@click\.stop="deleteProviderScreenshot\(item\)"\s+><RTooltip activator="parent" :text="t\('common\.delete'\)" \/>/,
    );
    expect(source).not.toContain(
      `<RTooltip :text="t('common.delete')"
              ><RBtn`,
    );
  });
});

describe("ScreenshotsSubtab delegates to its single lifecycle", () => {
  it("forwards provider clicks and files to the existing named handlers", async () => {
    const wrapper = shallowMount(ScreenshotsSubtab, {
      props: { rom: { id: 1 } as DetailedRom },
      global: {
        stubs: {
          RBtn: false,
          RTooltip: false,
          RDropzone: false,
          ScreenshotsTab: false,
        },
      },
    });
    await wrapper.get('[aria-label="rom.add-to-overview"]').trigger("click");
    expect(actions.togglePlacement).toHaveBeenCalledWith(
      expect.objectContaining({ id: 7 }),
      "overview",
    );
    await wrapper.get('[aria-label="rom.add-as-background"]').trigger("click");
    expect(actions.togglePlacement).toHaveBeenCalledWith(
      expect.objectContaining({ id: 7 }),
      "background",
    );
    await wrapper.get('[aria-label="common.delete"]').trigger("click");
    expect(actions.deleteProviderScreenshot).toHaveBeenCalledWith(
      expect.objectContaining({ id: 7 }),
    );
    const files = [new File(["a"], "a.png")];
    wrapper.findComponent({ name: "RDropzone" }).vm.$emit("files", files);
    expect(actions.handleMyFiles).toHaveBeenCalledWith(files);
    const galleries = wrapper.findAllComponents({ name: "ScreenshotsTab" });
    expect(galleries[0].props()).toMatchObject({
      deletable: true,
      togglable: true,
    });
    expect(galleries[1].props()).toMatchObject({
      deletable: false,
      togglable: false,
    });
    wrapper.unmount();
  });
});
