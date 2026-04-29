import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RPlatformIcon from "./RPlatformIcon.vue";

const meta: Meta<typeof RPlatformIcon> = {
  title: "Media/RPlatformIcon",
  component: RPlatformIcon,
  argTypes: {
    name: { control: "text" },
    src: { control: "text" },
    size: { control: "number" },
    title: { control: "text" },
    showTooltip: { control: "boolean" },
  },
};

export default meta;

type Story = StoryObj<typeof RPlatformIcon>;

export const Known: Story = { args: { name: "snes", size: 40 } };
export const Unknown: Story = { args: { name: "does-not-exist", size: 40 } };
export const Row: Story = {
  render: () => ({
    components: { RPlatformIcon },
    template: `
      <div style="display:flex;gap:.5rem;align-items:center">
        <RPlatformIcon name="snes" />
        <RPlatformIcon name="nes" />
        <RPlatformIcon name="gba" />
        <RPlatformIcon name="ps1" />
        <RPlatformIcon name="mystery" />
      </div>
    `,
  }),
};
