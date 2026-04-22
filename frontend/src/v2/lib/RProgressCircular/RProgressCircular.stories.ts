import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RProgressCircular from "./RProgressCircular.vue";

const meta: Meta<typeof RProgressCircular> = {
  title: "Primitives/RProgressCircular",
  component: RProgressCircular,
  argTypes: {
    size: { control: "number" },
    width: { control: "number" },
    color: { control: "text" },
    indeterminate: { control: "boolean" },
    modelValue: { control: { type: "range", min: 0, max: 100 } },
  },
};

export default meta;

type Story = StoryObj<typeof RProgressCircular>;

export const Indeterminate: Story = {
  args: { indeterminate: true, size: 32 },
};

export const Determinate: Story = {
  args: { indeterminate: false, modelValue: 65, size: 48, width: 4 },
};
