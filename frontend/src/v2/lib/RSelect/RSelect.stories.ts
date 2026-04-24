import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import RSelect from "./RSelect.vue";

const meta: Meta<typeof RSelect> = {
  title: "Forms/RSelect",
  component: RSelect,
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
    label: { control: "text" },
    multiple: { control: "boolean" },
    clearable: { control: "boolean" },
    disabled: { control: "boolean" },
    readonly: { control: "boolean" },
  },
  render: (args) => ({
    components: { RSelect },
    setup: () => {
      const value = ref<string | string[]>(args.multiple ? [] : "");
      return { args, value };
    },
    template: `<div style="width:320px"><RSelect v-model="value" v-bind="args" /></div>`,
  }),
};

export default meta;

type Story = StoryObj<typeof RSelect>;

const regions = [
  { title: "North America", value: "na" },
  { title: "Europe", value: "eu" },
  { title: "Japan", value: "jp" },
  { title: "Asia", value: "asia" },
];

export const Default: Story = {
  args: { label: "Region", items: regions },
};

export const Multiple: Story = {
  args: {
    label: "Regions",
    items: regions,
    multiple: true,
    chips: true,
    closableChips: true,
  },
};
