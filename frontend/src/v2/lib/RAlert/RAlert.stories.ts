import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RAlert from "./RAlert.vue";

const meta: Meta<typeof RAlert> = {
  title: "Primitives/RAlert",
  component: RAlert,
  argTypes: {
    type: {
      control: "select",
      options: [undefined, "success", "info", "warning", "error"],
    },
    variant: {
      control: "select",
      options: ["flat", "elevated", "tonal", "outlined", "text"],
    },
    closable: { control: "boolean" },
    title: { control: "text" },
    text: { control: "text" },
  },
  render: (args) => ({
    components: { RAlert },
    setup: () => ({ args }),
    template: `<div style="width:480px"><RAlert v-bind="args" /></div>`,
  }),
};

export default meta;

type Story = StoryObj<typeof RAlert>;

export const Success: Story = {
  args: { type: "success", text: "Reset link sent to your email." },
};

export const Info: Story = {
  args: { type: "info", text: "Library scan is in progress." },
};

export const Warning: Story = {
  args: {
    type: "warning",
    title: "Hash calculation disabled",
    text: "ROMs will not be fingerprinted during this scan.",
  },
};

export const Error: Story = {
  args: { type: "error", text: "Unable to reach the server." },
};

export const Closable: Story = {
  args: { type: "info", text: "You can dismiss me.", closable: true },
};
