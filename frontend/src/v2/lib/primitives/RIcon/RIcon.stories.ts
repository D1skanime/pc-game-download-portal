import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RIcon from "./RIcon.vue";

const meta: Meta<typeof RIcon> = {
  title: "Primitives/RIcon",
  component: RIcon,
  argTypes: {
    icon: { control: "text" },
    size: { control: "text" },
    color: { control: "text" },
  },
};

export default meta;

type Story = StoryObj<typeof RIcon>;

export const Default: Story = {
  args: { icon: "mdi-controller" },
};

export const Colored: Story = {
  args: { icon: "mdi-heart", color: "romm-red", size: "32" },
};

export const Large: Story = {
  args: { icon: "mdi-controller-classic", size: "48" },
};

export const Gallery: Story = {
  render: () => ({
    components: { RIcon },
    template: `
      <div style="display:flex;gap:1rem;align-items:center">
        <RIcon icon="mdi-home" />
        <RIcon icon="mdi-controller" color="primary" />
        <RIcon icon="mdi-star" color="romm-gold" size="28" />
        <RIcon icon="mdi-trash-can-outline" color="romm-red" />
        <RIcon icon="mdi-check-circle" color="romm-green" />
      </div>
    `,
  }),
};
