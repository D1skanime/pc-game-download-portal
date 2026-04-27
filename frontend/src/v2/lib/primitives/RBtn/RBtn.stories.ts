import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RBtn from "./RBtn.vue";

const meta: Meta<typeof RBtn> = {
  title: "Primitives/RBtn",
  component: RBtn,
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
    density: {
      control: "select",
      options: ["default", "comfortable", "compact"],
    },
    rounded: { control: "text" },
    type: {
      control: "select",
      options: ["button", "submit", "reset"],
    },
    icon: { control: "text" },
    loading: { control: "boolean" },
    disabled: { control: "boolean" },
    block: { control: "boolean" },
    ripple: { control: "boolean" },
    prependIcon: { control: "text" },
    appendIcon: { control: "text" },
  },
  render: (args) => ({
    components: { RBtn },
    setup: () => ({ args }),
    template: `<RBtn v-bind="args">{{ args.default ?? 'Click me' }}</RBtn>`,
  }),
};

export default meta;

type Story = StoryObj<typeof RBtn>;

export const Default: Story = {};

export const Primary: Story = {
  args: { color: "primary", variant: "flat" },
};

export const Outlined: Story = {
  args: { variant: "outlined" },
};

export const Text: Story = {
  args: { variant: "text" },
};

export const WithPrependIcon: Story = {
  args: { prependIcon: "mdi-login" },
  render: (args) => ({
    components: { RBtn },
    setup: () => ({ args }),
    template: `<RBtn v-bind="args">Log in</RBtn>`,
  }),
};

export const Loading: Story = {
  args: { loading: true },
  render: (args) => ({
    components: { RBtn },
    setup: () => ({ args }),
    template: `<RBtn v-bind="args">Working…</RBtn>`,
  }),
};

export const Disabled: Story = {
  args: { disabled: true },
};

export const Block: Story = {
  args: { block: true, prependIcon: "mdi-send" },
  render: (args) => ({
    components: { RBtn },
    setup: () => ({ args }),
    template: `<div style="width: 360px"><RBtn v-bind="args">Submit</RBtn></div>`,
  }),
};
