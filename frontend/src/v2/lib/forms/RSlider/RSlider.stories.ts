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
    valuePosition: {
      control: "select",
      options: ["none", "left", "right", "thumb"],
    },
    valueSuffix: { control: "text" },
    showTicks: { control: "boolean" },
    disabled: { control: "boolean" },
    readonly: { control: "boolean" },
  },
  render: (args) => ({
    components: { RSlider },
    setup: () => {
      const value = ref(args.modelValue ?? 50);
      return { args, value };
    },
    template: `<div style="padding: 32px; min-width: 360px;">
      <RSlider v-model="value" v-bind="args" />
      <div style="margin-top: 12px; font-size: 12px; color: var(--r-color-fg-muted);">
        value: {{ value }}
      </div>
    </div>`,
  }),
};

export default meta;
type Story = StoryObj<typeof RSlider>;

export const Default: Story = { args: { modelValue: 50 } };

export const ValueRight: Story = {
  args: { modelValue: 42, valuePosition: "right", valueSuffix: "%" },
};

export const ValueLeft: Story = {
  args: { modelValue: 42, valuePosition: "left", valueSuffix: "%" },
};

export const ValueThumb: Story = {
  args: { modelValue: 30, valuePosition: "thumb", valueSuffix: "%" },
};

export const Stepped: Story = {
  args: {
    modelValue: 4,
    min: 0,
    max: 10,
    step: 1,
    valuePosition: "thumb",
    showTicks: true,
  },
};

export const CustomValueSlot: Story = {
  args: { modelValue: 70, valuePosition: "right" },
  render: (args) => ({
    components: { RSlider },
    setup: () => {
      const value = ref(args.modelValue ?? 70);
      return { args, value };
    },
    template: `<div style="padding: 32px; min-width: 360px;">
      <RSlider v-model="value" v-bind="args">
        <template #value="{ value, percent }">
          {{ value }} <span style="opacity: 0.6">· {{ Math.round(percent) }}%</span>
        </template>
      </RSlider>
    </div>`,
  }),
};

export const Disabled: Story = {
  args: { modelValue: 60, valuePosition: "right", disabled: true },
};
