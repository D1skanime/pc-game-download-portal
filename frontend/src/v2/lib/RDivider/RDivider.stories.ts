import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RDivider from "./RDivider.vue";

const meta: Meta<typeof RDivider> = {
  title: "Primitives/RDivider",
  component: RDivider,
};

export default meta;

type Story = StoryObj<typeof RDivider>;

export const Default: Story = {
  render: () => ({
    components: { RDivider },
    template: `<div style="width:320px"><RDivider /></div>`,
  }),
};

export const WithText: Story = {
  render: () => ({
    components: { RDivider },
    template: `
      <div style="width:320px;color:var(--r-color-fg)">
        <RDivider>or</RDivider>
      </div>
    `,
  }),
};

export const Vertical: Story = {
  render: () => ({
    components: { RDivider },
    template: `
      <div style="height:60px;display:flex;align-items:center;gap:1rem;color:var(--r-color-fg)">
        <span>left</span><RDivider vertical /><span>right</span>
      </div>
    `,
  }),
};
