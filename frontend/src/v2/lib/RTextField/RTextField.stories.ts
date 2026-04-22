import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import RTextField from "./RTextField.vue";

const meta: Meta<typeof RTextField> = {
  title: "Forms/RTextField",
  component: RTextField,
  argTypes: {
    variant: {
      control: "select",
      options: [
        "filled",
        "outlined",
        "plain",
        "underlined",
        "solo",
        "solo-inverted",
        "solo-filled",
      ],
    },
    density: {
      control: "select",
      options: ["default", "comfortable", "compact"],
    },
    type: { control: "text" },
    label: { control: "text" },
    prependInnerIcon: { control: "text" },
    appendInnerIcon: { control: "text" },
    clearable: { control: "boolean" },
    disabled: { control: "boolean" },
    loading: { control: "boolean" },
    hint: { control: "text" },
    error: { control: "boolean" },
    errorMessages: { control: "text" },
  },
  render: (args) => ({
    components: { RTextField },
    setup: () => {
      const value = ref("");
      return { args, value };
    },
    template: `
      <div style="width: 360px">
        <RTextField v-model="value" v-bind="args" />
      </div>
    `,
  }),
};

export default meta;

type Story = StoryObj<typeof RTextField>;

export const Default: Story = {
  args: { label: "Username", prependInnerIcon: "mdi-account" },
};

export const Password: Story = {
  args: {
    label: "Password",
    type: "password",
    prependInnerIcon: "mdi-lock",
    appendInnerIcon: "mdi-eye",
  },
};

export const Underlined: Story = {
  args: {
    label: "Username",
    variant: "underlined",
    prependInnerIcon: "mdi-account",
  },
};

export const WithError: Story = {
  args: {
    label: "Email",
    error: true,
    errorMessages: "Must be a valid email address",
    prependInnerIcon: "mdi-email",
  },
};

export const Loading: Story = {
  args: { label: "Searching…", loading: true },
};
