import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RBtn from "@/v2/lib/primitives/RBtn/RBtn.vue";
import RIcon from "@/v2/lib/primitives/RIcon/RIcon.vue";
import RToolbar from "./RToolbar.vue";

const meta: Meta<typeof RToolbar> = {
  title: "Structural/RToolbar",
  component: RToolbar,
  argTypes: {
    title: { control: "text" },
    color: { control: "text" },
    density: {
      control: "select",
      options: ["default", "comfortable", "compact"],
    },
    flat: { control: "boolean" },
    height: { control: "text" },
    rounded: { control: "text" },
  },
};

export default meta;

type Story = StoryObj<typeof RToolbar>;

export const WithTitleAndActions: Story = {
  args: { title: "Platforms" },
  render: (args) => ({
    components: { RToolbar, RBtn, RIcon },
    setup: () => ({ args }),
    template: `
      <div style="width: 720px">
        <RToolbar v-bind="args">
          <template #append>
            <RBtn variant="text" prepend-icon="mdi-filter">Filters</RBtn>
            <RBtn variant="text" prepend-icon="mdi-sort">Sort</RBtn>
          </template>
        </RToolbar>
      </div>
    `,
  }),
};
