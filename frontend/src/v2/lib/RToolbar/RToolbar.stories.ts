import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RBtn from "../RBtn/RBtn.vue";
import RIcon from "../RIcon/RIcon.vue";
import RToolbar from "./RToolbar.vue";

const meta: Meta<typeof RToolbar> = {
  title: "Structural/RToolbar",
  component: RToolbar,
};

export default meta;

type Story = StoryObj<typeof RToolbar>;

export const WithTitleAndActions: Story = {
  render: () => ({
    components: { RToolbar, RBtn, RIcon },
    template: `
      <div style="width: 720px">
        <RToolbar title="Platforms">
          <template #append>
            <RBtn variant="text" prepend-icon="mdi-filter">Filters</RBtn>
            <RBtn variant="text" prepend-icon="mdi-sort">Sort</RBtn>
          </template>
        </RToolbar>
      </div>
    `,
  }),
};
