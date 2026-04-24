import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RAvatar from "./RAvatar.vue";

const meta: Meta<typeof RAvatar> = {
  title: "Primitives/RAvatar",
  component: RAvatar,
  argTypes: {
    size: { control: "text" },
    color: { control: "text" },
    image: { control: "text" },
    icon: { control: "text" },
    rounded: { control: "text" },
    variant: {
      control: "select",
      options: ["flat", "elevated", "tonal", "outlined", "text", "plain"],
    },
  },
};

export default meta;

type Story = StoryObj<typeof RAvatar>;

export const Initial: Story = {
  args: { color: "primary", size: 40 },
  render: (args) => ({
    components: { RAvatar },
    setup: () => ({ args }),
    template: `<RAvatar v-bind="args">YZ</RAvatar>`,
  }),
};

export const Icon: Story = {
  args: { icon: "mdi-account", color: "primary", size: 40 },
};

export const Image: Story = {
  args: { image: "/assets/isotipo.svg", size: 48 },
};

export const Rounded: Story = {
  args: { color: "accent", rounded: "lg", size: 40 },
  render: (args) => ({
    components: { RAvatar },
    setup: () => ({ args }),
    template: `<RAvatar v-bind="args">R</RAvatar>`,
  }),
};
