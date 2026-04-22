import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RCover from "./RCover.vue";

const meta: Meta<typeof RCover> = {
  title: "Media/RCover",
  component: RCover,
  argTypes: {
    src: { control: "text" },
    fallbackSrc: { control: "text" },
    alt: { control: "text" },
    aspectRatio: { control: "text" },
    rounded: {
      control: "select",
      options: ["sm", "md", "lg"],
    },
    placeholder: { control: "text" },
  },
  render: (args) => ({
    components: { RCover },
    setup: () => ({ args }),
    template: `<div style="width:180px"><RCover v-bind="args" /></div>`,
  }),
};

export default meta;

type Story = StoryObj<typeof RCover>;

export const Placeholder: Story = {
  args: { placeholder: "Super Mario Bros." },
};

export const WithImage: Story = {
  args: {
    src: "/assets/isotipo.svg",
    alt: "RomM logo",
    aspectRatio: "1 / 1",
  },
};

export const BrokenSrcFallsBack: Story = {
  args: {
    src: "/does-not-exist.jpg",
    placeholder: "Cover unavailable",
  },
};
