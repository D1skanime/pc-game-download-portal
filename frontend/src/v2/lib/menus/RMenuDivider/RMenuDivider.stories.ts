import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RMenuItem from "../RMenuItem/RMenuItem.vue";
import RMenuPanel from "../RMenuPanel/RMenuPanel.vue";
import RMenuDivider from "./RMenuDivider.vue";

// RMenuDivider exposes no props — it's a 1px hairline between menu groups.
const meta: Meta<typeof RMenuDivider> = {
  title: "Menus/RMenuDivider",
  component: RMenuDivider,
  argTypes: {},
};

export default meta;

type Story = StoryObj<typeof RMenuDivider>;

export const BetweenGroups: Story = {
  render: () => ({
    components: { RMenuPanel, RMenuItem, RMenuDivider },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 40px; background: #07070f;">
        <RMenuPanel width="240px">
          <RMenuItem icon="mdi-play" label="Play" />
          <RMenuItem icon="mdi-download-outline" label="Download" />
          <RMenuDivider />
          <RMenuItem icon="mdi-heart-outline" label="Favorite" />
          <RMenuItem icon="mdi-bookmark-plus-outline" label="Add to collection" />
          <RMenuDivider />
          <RMenuItem icon="mdi-trash-can-outline" label="Delete…" variant="danger" />
        </RMenuPanel>
      </div>
    `,
  }),
};
