import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RDivider from "./RDivider.vue";

const meta: Meta<typeof RDivider> = {
  title: "Primitives/RDivider",
  component: RDivider,
  argTypes: {
    vertical: { control: "boolean" },
    inset: { control: "boolean" },
    thickness: { control: "text" },
  },
  render: (args) => ({
    components: { RDivider },
    setup: () => ({ args }),
    template: `<div style="width:320px"><RDivider v-bind="args" /></div>`,
  }),
};

export default meta;

type Story = StoryObj<typeof RDivider>;

export const Default: Story = {};

export const WithText: Story = {
  render: (args) => ({
    components: { RDivider },
    setup: () => ({ args }),
    template: `
      <div style="width:320px;color:var(--r-color-fg)">
        <RDivider v-bind="args">or</RDivider>
      </div>
    `,
  }),
};

export const Vertical: Story = {
  args: { vertical: true },
  render: (args) => ({
    components: { RDivider },
    setup: () => ({ args }),
    template: `
      <div style="height:60px;display:flex;align-items:center;gap:1rem;color:var(--r-color-fg)">
        <span>left</span><RDivider v-bind="args" /><span>right</span>
      </div>
    `,
  }),
};
