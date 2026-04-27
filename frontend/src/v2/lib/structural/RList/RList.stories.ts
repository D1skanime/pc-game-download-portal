import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RListItem from "../RListItem/RListItem.vue";
import RList from "./RList.vue";

const meta: Meta<typeof RList> = {
  title: "Structural/RList",
  component: RList,
  argTypes: {
    density: {
      control: "select",
      options: ["default", "comfortable", "compact"],
    },
    nav: { control: "boolean" },
    lines: {
      control: "select",
      options: ["one", "two", "three", false],
    },
    rounded: { control: "text" },
    color: { control: "text" },
    bgColor: { control: "text" },
  },
};

export default meta;

type Story = StoryObj<typeof RList>;

export const Navigation: Story = {
  args: { nav: true },
  render: (args) => ({
    components: { RList, RListItem },
    setup: () => ({ args }),
    template: `
      <div style="width: 280px; border: 1px solid var(--r-color-border); border-radius: var(--r-radius-md); padding: var(--r-space-2); background: var(--r-color-bg-elevated)">
        <RList v-bind="args">
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
