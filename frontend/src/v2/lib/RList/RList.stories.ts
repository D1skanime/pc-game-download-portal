import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RListItem from "../RListItem/RListItem.vue";
import RList from "./RList.vue";

const meta: Meta<typeof RList> = {
  title: "Structural/RList",
  component: RList,
};

export default meta;

type Story = StoryObj<typeof RList>;

export const Navigation: Story = {
  render: () => ({
    components: { RList, RListItem },
    template: `
      <div style="width: 280px; border: 1px solid var(--r-color-border); border-radius: var(--r-radius-md); padding: var(--r-space-2); background: var(--r-color-bg-elevated)">
        <RList nav>
          <RListItem prepend-icon="mdi-home" title="Home" active />
          <RListItem prepend-icon="mdi-controller" title="Platforms" />
          <RListItem prepend-icon="mdi-bookmark-box-multiple" title="Collections" />
          <RListItem prepend-icon="mdi-magnify" title="Search" />
          <RListItem prepend-icon="mdi-cog" title="Settings" />
        </RList>
      </div>
    `,
  }),
};
