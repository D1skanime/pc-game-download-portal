import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RAvatar from "../RAvatar/RAvatar.vue";
import RIcon from "../RIcon/RIcon.vue";
import RBadge from "./RBadge.vue";

const meta: Meta<typeof RBadge> = {
  title: "Primitives/RBadge",
  component: RBadge,
  argTypes: {
    content: { control: "text" },
    color: { control: "text" },
    icon: { control: "text" },
    location: {
      control: "select",
      options: [
        "top",
        "bottom",
        "start",
        "end",
        "top start",
        "top end",
        "bottom start",
        "bottom end",
      ],
    },
    dot: { control: "boolean" },
    inline: { control: "boolean" },
    bordered: { control: "boolean" },
  },
};

export default meta;

type Story = StoryObj<typeof RBadge>;

export const Count: Story = {
  args: { content: "7", color: "error" },
  render: (args) => ({
    components: { RBadge, RIcon },
    setup: () => ({ args }),
    template: `
      <RBadge v-bind="args">
        <RIcon icon="mdi-bell" size="28" />
      </RBadge>
    `,
  }),
};

export const Dot: Story = {
  args: {
    dot: true,
    color: "success",
    content: "test",
  },
  render: (args) => ({
    components: { RBadge, RAvatar },
    setup: () => ({ args }),
    template: `
      <RBadge v-bind="args">
        <RAvatar color="primary" size="40">YZ</RAvatar>
      </RBadge>
    `,
  }),
};
