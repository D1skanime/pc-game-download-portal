import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RCard from "./RCard.vue";

const meta: Meta<typeof RCard> = {
  title: "Primitives/RCard",
  component: RCard,
  argTypes: {
    variant: {
      control: "select",
      options: ["flat", "elevated", "tonal", "outlined", "text", "plain"],
    },
    title: { control: "text" },
    subtitle: { control: "text" },
    loading: { control: "boolean" },
  },
};

export default meta;

type Story = StoryObj<typeof RCard>;

export const Default: Story = {
  render: (args) => ({
    components: { RCard },
    setup: () => ({ args }),
    template: `
      <RCard v-bind="args" style="width: 360px; padding: var(--r-space-5);">
        Content goes here. RCard has a muted border and elevated background
        from the v2 tokens.
      </RCard>
    `,
  }),
};

export const WithTitle: Story = {
  args: { title: "Recent scans", subtitle: "Last 24 hours" },
  render: (args) => ({
    components: { RCard },
    setup: () => ({ args }),
    template: `
      <RCard v-bind="args" style="width: 360px;">
        <div style="padding: var(--r-space-5);">Card body</div>
      </RCard>
    `,
  }),
};

export const Outlined: Story = {
  args: { variant: "outlined" },
  render: (args) => ({
    components: { RCard },
    setup: () => ({ args }),
    template: `<RCard v-bind="args" style="width: 360px; padding: var(--r-space-5);">Outlined card</RCard>`,
  }),
};
