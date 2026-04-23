import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RList from "../RList/RList.vue";
import RListItem from "./RListItem.vue";

const meta: Meta<typeof RListItem> = {
  title: "Structural/RListItem",
  component: RListItem,
};

export default meta;

type Story = StoryObj<typeof RListItem>;

export const Basic: Story = {
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
