import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import SetupStepPlatforms from "./SetupStepPlatforms.vue";

vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));

const discovery = {
  root_label: "Games",
  folders: [
    {
      name: "Known",
      relative_path: "Known",
      association: "known" as const,
      suggested_platform: "windows",
    },
    {
      name: "Mystery",
      relative_path: "Mystery",
      association: "unknown" as const,
      suggested_platform: null,
    },
  ],
  platform_options: [
    { slug: "windows", display_name: "Windows" },
    { slug: "linux", display_name: "Linux" },
  ],
};

describe("SetupStepPlatforms", () => {
  it("renders direct folders and emits a typed draft update", async () => {
    const wrapper = mount(SetupStepPlatforms, {
      props: {
        discovery,
        draft: { Known: "windows", Mystery: null },
        disabled: false,
        submitting: false,
      },
      global: {
        stubs: {
          RSelect: {
            props: ["modelValue", "items"],
            emits: ["update:modelValue"],
            template:
              '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="item in items" :key="item.slug" :value="item.slug">{{ item.display_name }}</option></select>',
          },
        },
      },
    });

    expect(wrapper.text()).toContain("Known");
    expect(wrapper.text()).toContain("Mystery");
    expect(wrapper.text()).not.toContain("roms/{platform}");
    expect(wrapper.text()).not.toContain("Storage Administration");
    const selects = wrapper.findAll("select");
    expect(selects).toHaveLength(2);
    await selects[1].setValue("linux");
    expect(wrapper.emitted("update:draft")).toEqual([
      [{ Known: "windows", Mystery: "linux" }],
    ]);
  });
});
