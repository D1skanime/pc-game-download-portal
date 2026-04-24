import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import RRating from "./RRating.vue";

const meta: Meta<typeof RRating> = {
  title: "Forms/RRating",
  component: RRating,
  argTypes: {
    length: { control: "number" },
    size: { control: "text" },
    color: { control: "text" },
    density: {
      control: "select",
      options: ["default", "comfortable", "compact"],
    },
    readonly: { control: "boolean" },
    halfIncrements: { control: "boolean" },
    hover: { control: "boolean" },
  },
  render: (args) => ({
    components: { RRating },
    setup: () => {
      const value = ref(3.5);
      return { args, value };
    },
    template: `<RRating v-model="value" v-bind="args" />`,
  }),
};

export default meta;

type Story = StoryObj<typeof RRating>;

export const Default: Story = { args: { halfIncrements: true, hover: true } };
export const Readonly: Story = { args: { readonly: true } };
export const Large: Story = { args: { size: "large" } };
