import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RImg from "./RImg.vue";

const meta: Meta<typeof RImg> = {
  title: "Primitives/RImg",
  component: RImg,
  argTypes: {
    src: { control: "text" },
    width: { control: "text" },
    height: { control: "text" },
    cover: { control: "boolean" },
  },
};

export default meta;

type Story = StoryObj<typeof RImg>;

export const Logo: Story = {
  args: { src: "/assets/isotipo.svg", width: 80, alt: "RomM logo" },
};
