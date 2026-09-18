import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import DownloadModeSelector from "./DownloadModeSelector.vue";

const { supported } = vi.hoisted(() => ({ supported: vi.fn() }));
vi.mock("@/v2/composables/useBrowserDownloadQueue", () => ({
  isEnhancedDownloadSupported: supported,
}));
vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string) =>
      ({
        "rom.download-browser-mode": "Standard browser download",
        "rom.download-enhanced-mode": "Enhanced folder download",
        "rom.download-enhanced-description": "Choose a folder",
        "rom.download-enhanced-unavailable": "Standard remains available",
        "rom.download-standard-description": "Browser handles each file",
      })[key] ?? key,
  }),
}));

const checkbox = {
  props: ["modelValue", "label", "disabled"],
  emits: ["update:modelValue"],
  template:
    '<label><input type="radio" :checked="modelValue" :disabled="disabled" :aria-label="label" @change="$emit(\'update:modelValue\', true)" /><span>{{ label }}</span></label>',
};

describe("DownloadModeSelector", () => {
  it("offers enhanced mode only when the browser exposes folder access", () => {
    supported.mockReturnValue(true);
    const wrapper = mount(DownloadModeSelector, {
      props: { modelValue: "standard" },
      global: { stubs: { RCheckbox: checkbox } },
    });

    expect(wrapper.text()).toContain("Standard browser download");
    expect(wrapper.text()).toContain("Enhanced folder download");
    expect(wrapper.findAll("input")).toHaveLength(2);
  });

  it("emits an explicit enhanced mode selection", async () => {
    supported.mockReturnValue(true);
    const wrapper = mount(DownloadModeSelector, {
      props: { modelValue: "standard" },
      global: { stubs: { RCheckbox: checkbox } },
    });

    await wrapper.findAll("input")[1].trigger("change");
    expect(wrapper.emitted("update:modelValue")).toEqual([["enhanced"]]);
  });

  it("keeps standard mode available when enhanced folder access is absent", () => {
    supported.mockReturnValue(false);
    const wrapper = mount(DownloadModeSelector, {
      props: { modelValue: "standard" },
      global: { stubs: { RCheckbox: checkbox } },
    });

    expect(wrapper.findAll("input")).toHaveLength(1);
    expect(wrapper.text()).toContain("Standard remains available");
  });
});
