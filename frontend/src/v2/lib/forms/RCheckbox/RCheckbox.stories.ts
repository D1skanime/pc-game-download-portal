import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import RCheckbox from "./RCheckbox.vue";

const meta: Meta<typeof RCheckbox> = {
  title: "Forms/RCheckbox",
  component: RCheckbox,
  argTypes: {
    label: { control: "text" },
    color: { control: "text" },
    density: {
      control: "select",
      options: ["default", "comfortable", "compact"],
    },
    disabled: { control: "boolean" },
    indeterminate: { control: "boolean" },
  },
  render: (args) => ({
    components: { RCheckbox },
    setup: () => {
      const value = ref(false);
      return { args, value };
    },
    template: `<RCheckbox v-model="value" v-bind="args" />`,
  }),
};

export default meta;

type Story = StoryObj<typeof RCheckbox>;

export const Default: Story = {
  args: { label: "Remember me" },
};

export const Checked: Story = {
  render: (args) => ({
    components: { RCheckbox },
    setup: () => {
      const value = ref(true);
      return { args, value };
    },
    template: `<RCheckbox v-model="value" v-bind="args" />`,
  }),
  args: { label: "Auto-login next time" },
};
