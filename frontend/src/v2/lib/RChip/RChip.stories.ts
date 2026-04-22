import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RChip from "./RChip.vue";

const meta: Meta<typeof RChip> = {
  title: "Primitives/RChip",
  component: RChip,
  argTypes: {
    variant: {
      control: "select",
      options: ["flat", "text", "elevated", "tonal", "outlined", "plain"],
    },
    color: { control: "text" },
    size: {
      control: "select",
      options: ["x-small", "small", "default", "large", "x-large"],
    },
    label: { control: "boolean" },
    closable: { control: "boolean" },
    prependIcon: { control: "text" },
  },
  render: (args) => ({
    components: { RChip },
    setup: () => ({ args }),
    template: `<RChip v-bind="args">{{ args.text ?? 'Action' }}</RChip>`,
  }),
};

export default meta;

type Story = StoryObj<typeof RChip>;

export const Default: Story = {};
export const WithIcon: Story = { args: { prependIcon: "mdi-star" } };
export const Success: Story = { args: { color: "success" } };
export const Outlined: Story = { args: { variant: "outlined" } };
export const Label: Story = { args: { label: true, prependIcon: "mdi-tag" } };
export const Closable: Story = {
  args: { closable: true, color: "primary" },
  render: (args) => ({
    components: { RChip },
    setup: () => ({ args }),
    template: `<RChip v-bind="args">Filter: Genre</RChip>`,
  }),
};
