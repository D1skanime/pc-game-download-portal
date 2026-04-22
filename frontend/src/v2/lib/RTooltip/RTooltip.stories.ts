import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RBtn from "../RBtn/RBtn.vue";
import RTooltip from "./RTooltip.vue";

const meta: Meta<typeof RTooltip> = {
  title: "Structural/RTooltip",
  component: RTooltip,
};

export default meta;

type Story = StoryObj<typeof RTooltip>;

export const OnButton: Story = {
  render: () => ({
    components: { RTooltip, RBtn },
    template: `
      <div style="padding: 3rem">
        <RTooltip text="Save your progress" location="top">
          <template #activator="{ props }">
            <RBtn v-bind="props" prepend-icon="mdi-content-save">Save</RBtn>
          </template>
        </RTooltip>
      </div>
    `,
  }),
};
