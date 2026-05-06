import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import RCheckbox from "./RCheckbox.vue";

const meta: Meta<typeof RCheckbox> = {
  title: "Forms/RCheckbox",
  component: RCheckbox,
  argTypes: {
    label: { control: "text" },
    size: { control: "inline-radio", options: ["sm", "md"] },
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

export const Indeterminate: Story = {
  args: { label: "Some items selected", indeterminate: true },
};

export const Disabled: Story = {
  args: { label: "Disabled checkbox", disabled: true },
};

export const DisabledChecked: Story = {
  render: (args) => ({
    components: { RCheckbox },
    setup: () => {
      const value = ref(true);
      return { args, value };
    },
    template: `<RCheckbox v-model="value" v-bind="args" />`,
  }),
  args: { label: "Disabled and checked", disabled: true },
};

export const Small: Story = {
  args: { label: "Small checkbox", size: "sm" },
};

export const NoLabel: Story = {
  args: {},
};

export const Error: Story = {
  render: (args) => ({
    components: { RCheckbox },
    setup: () => {
      const value = ref(false);
      return { args, value };
    },
    template: `<RCheckbox v-model="value" v-bind="args" :error="true" error-messages="This field is required" />`,
  }),
  args: { label: "I agree to the terms" },
};

export const Group: Story = {
  render: () => ({
    components: { RCheckbox },
    setup: () => {
      const a = ref(true);
      const b = ref(false);
      const c = ref(false);
      return { a, b, c };
    },
    template: `
      <div style="display: flex; flex-direction: column; gap: 4px;">
        <RCheckbox v-model="a" label="Option A" hide-details />
        <RCheckbox v-model="b" label="Option B" hide-details />
        <RCheckbox v-model="c" label="Option C (longer label that wraps to test alignment)" hide-details />
      </div>
    `,
  }),
};
