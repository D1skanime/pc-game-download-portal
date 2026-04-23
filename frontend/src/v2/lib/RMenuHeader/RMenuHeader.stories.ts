import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RMenuDivider from "../RMenuDivider/RMenuDivider.vue";
import RMenuItem from "../RMenuItem/RMenuItem.vue";
import RMenuPanel from "../RMenuPanel/RMenuPanel.vue";
import RMenuHeader from "./RMenuHeader.vue";

const meta: Meta<typeof RMenuHeader> = {
  title: "Menus/RMenuHeader",
  component: RMenuHeader,
};

export default meta;

type Story = StoryObj<typeof RMenuHeader>;

export const GameContext: Story = {
  render: () => ({
    components: { RMenuPanel, RMenuHeader, RMenuItem, RMenuDivider },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 40px; background: #07070f;">
        <RMenuPanel width="260px">
          <RMenuHeader title="Super Mario World" subtitle="Super Nintendo">
            <template #art>
              <div style="width:38px;height:51px;border-radius:5px;background:linear-gradient(135deg,#3f2a7c,#1a1a2e);" />
            </template>
          </RMenuHeader>
          <RMenuDivider />
          <RMenuItem icon="mdi-play" label="Play" />
          <RMenuItem icon="mdi-download-outline" label="Download" />
        </RMenuPanel>
      </div>
    `,
  }),
};

export const UserMenuCompact: Story = {
  render: () => ({
    components: { RMenuPanel, RMenuHeader, RMenuItem, RMenuDivider },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 40px; background: #07070f;">
        <RMenuPanel width="240px">
          <RMenuHeader compact title="zurdi" subtitle="Admin">
            <template #art>
              <span style="width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#a18fff,#6043c8);display:grid;place-items:center;font-size:11px;font-weight:700;color:#fff;">ZU</span>
            </template>
          </RMenuHeader>
          <RMenuDivider />
          <RMenuItem icon="mdi-account-outline" label="Profile" />
          <RMenuItem icon="mdi-cog-outline" label="Interface" />
          <RMenuDivider />
          <RMenuItem icon="mdi-logout" label="Log out" variant="danger" />
        </RMenuPanel>
      </div>
    `,
  }),
};
