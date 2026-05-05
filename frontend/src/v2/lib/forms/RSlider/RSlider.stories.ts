import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import RSlider from "./RSlider.vue";

const meta: Meta<typeof RSlider> = {
  title: "Forms/RSlider",
  component: RSlider,
  argTypes: {
    min: { control: "number" },
    max: { control: "number" },
    step: { control: "number" },
    color: { control: "text" },
    size: { control: "text" },
    density: {
      control: "select",
      options: ["default", "comfortable", "compact"],
    },
    disabled: { control: "boolean" },
    readonly: { control: "boolean" },
    thumbLabel: { control: "boolean" },
  },
  render: (args) => ({
    components: { RSlider },
    setup: () => {
      const value = ref(args.modelValue ?? 50);
      return { args, value };
    },
    template: `<div style="padding: 24px; min-width: 320px;">
      <RSlider v-model="value" v-bind="args" />
      <div style="margin-top: 8px; font-size: 12px; color: var(--r-color-fg-muted);">
        value: {{ value }}
      </div>
    </div>`,
  }),
};

export default meta;
type Story = StoryObj<typeof RSlider>;

export const Default: Story = { args: { modelValue: 50 } };
export const WithThumbLabel: Story = {
  args: { modelValue: 30, thumbLabel: true },
};
export const Stepped: Story = {
  args: { modelValue: 4, min: 0, max: 10, step: 1, thumbLabel: "always" },
};
export const Disabled: Story = {
  args: { modelValue: 60, disabled: true },
};
