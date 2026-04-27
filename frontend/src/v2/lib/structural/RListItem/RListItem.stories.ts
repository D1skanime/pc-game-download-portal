import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RList from "../RList/RList.vue";
import RListItem from "./RListItem.vue";

const meta: Meta<typeof RListItem> = {
  title: "Structural/RListItem",
  component: RListItem,
  argTypes: {
    title: { control: "text" },
    subtitle: { control: "text" },
    prependIcon: { control: "text" },
    appendIcon: { control: "text" },
    prependAvatar: { control: "text" },
    active: { control: "boolean" },
    disabled: { control: "boolean" },
    density: {
      control: "select",
      options: ["default", "comfortable", "compact"],
    },
    color: { control: "text" },
    rounded: { control: "text" },
  },
  render: (args) => ({
    components: { RList, RListItem },
    setup: () => ({ args }),
    template: `
      <div style="width: 280px; border: 1px solid var(--r-color-border); border-radius: var(--r-radius-md); padding: var(--r-space-2); background: var(--r-color-bg-elevated)">
        <RList>
          <RListItem v-bind="args" />
        </RList>
      </div>
    `,
  }),
};

export default meta;

type Story = StoryObj<typeof RListItem>;

export const Default: Story = {
  args: { title: "Plain item" },
};

export const WithIcon: Story = {
  args: { title: "With prepend icon", prependIcon: "mdi-play" },
};

export const TwoLine: Story = {
  args: {
    title: "Two-line row",
    subtitle: "Subtitle lives here",
    prependIcon: "mdi-star",
  },
};

export const Active: Story = {
  args: { title: "Active state", prependIcon: "mdi-cog", active: true },
};

export const Gallery: Story = {
  render: () => ({
    components: { RList, RListItem },
    template: `
      <div style="width: 280px; border: 1px solid var(--r-color-border); border-radius: var(--r-radius-md); padding: var(--r-space-2); background: var(--r-color-bg-elevated)">
        <RList>
          <RListItem title="Plain item" />
          <RListItem prepend-icon="mdi-play" title="With prepend icon" />
          <RListItem
            prepend-icon="mdi-star"
            title="Two-line row"
            subtitle="Subtitle lives here"
          />
          <RListItem
            prepend-icon="mdi-cog"
            title="Active state"
            active
          />
        </RList>
      </div>
    `,
  }),
};
