import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RBtn from "../RBtn/RBtn.vue";
import RList from "../RList/RList.vue";
import RListItem from "../RListItem/RListItem.vue";
import RMenu from "./RMenu.vue";

const meta: Meta<typeof RMenu> = {
  title: "Structural/RMenu",
  component: RMenu,
};

export default meta;

type Story = StoryObj<typeof RMenu>;

export const UserMenu: Story = {
  render: () => ({
    components: { RMenu, RBtn, RList, RListItem },
    template: `
      <div style="padding: 2rem">
        <RMenu>
          <template #activator="{ props }">
            <RBtn v-bind="props" variant="outlined" prepend-icon="mdi-account">
              Account
            </RBtn>
          </template>
          <RList style="background: var(--r-color-bg-elevated); border: 1px solid var(--r-color-border); border-radius: var(--r-radius-md); padding: var(--r-space-2); min-width: 220px">
            <RListItem prepend-icon="mdi-account-circle" title="Profile" />
            <RListItem prepend-icon="mdi-palette" title="Theme" />
            <RListItem prepend-icon="mdi-logout" title="Log out" />
          </RList>
        </RMenu>
      </div>
    `,
  }),
};
