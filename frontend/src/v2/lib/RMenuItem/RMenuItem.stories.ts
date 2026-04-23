import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RMenuPanel from "../RMenuPanel/RMenuPanel.vue";
import RMenuItem from "./RMenuItem.vue";

const meta: Meta<typeof RMenuItem> = {
  title: "Menus/RMenuItem",
  component: RMenuItem,
};

export default meta;

type Story = StoryObj<typeof RMenuItem>;

export const Variants: Story = {
  render: () => ({
    components: { RMenuPanel, RMenuItem },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 40px; background: #07070f;">
        <RMenuPanel width="240px">
          <RMenuItem label="Default" icon="mdi-play" />
          <RMenuItem label="With subtitle" icon="mdi-download-outline" />
          <RMenuItem label="Active (favorited)" icon="mdi-heart" variant="active" />
          <RMenuItem label="Danger / destructive" icon="mdi-trash-can-outline" variant="danger" />
          <RMenuItem label="Disabled" icon="mdi-cog-outline" disabled />
        </RMenuPanel>
      </div>
    `,
  }),
};

export const WithNavigation: Story = {
  render: () => ({
    components: { RMenuPanel, RMenuItem },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 40px; background: #07070f;">
        <RMenuPanel width="240px">
          <RMenuItem to="/platforms" icon="mdi-gamepad-variant-outline" label="Platforms" />
          <RMenuItem href="https://romm.app" icon="mdi-open-in-new" label="External link" />
        </RMenuPanel>
      </div>
    `,
  }),
};
