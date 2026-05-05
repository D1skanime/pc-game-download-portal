import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import RExpansionPanel from "./RExpansionPanel.vue";

const meta: Meta<typeof RExpansionPanel> = {
  title: "Structural/RExpansionPanel",
  component: RExpansionPanel,
  argTypes: {
    title: { control: "text" },
    icon: { control: "text" },
    defaultOpen: { control: "boolean" },
    disabled: { control: "boolean" },
  },
  render: (args) => ({
    components: { RExpansionPanel },
    setup: () => {
      const open = ref(args.defaultOpen ?? false);
      return { args, open };
    },
    template: `
      <RExpansionPanel v-model="open" v-bind="args">
        <p style="margin: 0; font-size: 13px; line-height: 1.6; color: var(--r-color-fg-secondary);">
          This is the content of the panel. Clicking the header toggles the open state.
          The grid-row trick interpolates height without measuring pixels.
        </p>
      </RExpansionPanel>
    `,
  }),
};

export default meta;
type Story = StoryObj<typeof RExpansionPanel>;

export const Default: Story = { args: { title: "More details" } };
export const Open: Story = {
  args: { title: "Already open", defaultOpen: true },
};
export const WithIcon: Story = {
  args: { title: "With leading icon", icon: "mdi-information-outline" },
};
export const Disabled: Story = {
  args: { title: "Locked", disabled: true },
};
