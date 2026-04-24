import type { Meta, StoryObj } from "@storybook/vue3";
import { ref } from "vue";
import RSliderBtnGroup from "./RSliderBtnGroup.vue";

// Storybook's Meta<typeof Component> struggles with <script setup generic>,
// so we widen the component type here — runtime behaviour is unaffected.
const meta: Meta = {
  title: "Library/RSliderBtnGroup",
  // Cast needed: <script setup generic> types aren't compatible with
  // Storybook's ConcreteComponent constraint.
  component: RSliderBtnGroup as unknown as Meta["component"],
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["segmented", "tab"],
    },
    disabled: { control: "boolean" },
    ariaLabel: { control: "text" },
  },
  parameters: {
    docs: {
      description: {
        component:
          "Segmented control / tab pill with a sliding indicator. Consumer controls the active id via `v-model`; for nav-style tabs, items may declare a `to` path and render as router-links.",
      },
    },
  },
};
export default meta;

type Story = StoryObj;

export const Segmented: Story = {
  args: { variant: "segmented" },
  render: (args) => ({
    components: { RSliderBtnGroup },
    setup() {
      const layout = ref<"grid" | "list">("grid");
      return { args, layout };
    },
    template: `
      <RSliderBtnGroup
        v-bind="args"
        :model-value="layout"
        :items="[
          { id: 'grid', icon: 'mdi-view-grid-outline', ariaLabel: 'Grid', title: 'Grid' },
          { id: 'list', icon: 'mdi-view-list', ariaLabel: 'List', title: 'List' },
        ]"
        @update:model-value="(v) => (layout = v)"
      />
    `,
  }),
};

export const Tab: Story = {
  args: { variant: "tab" },
  render: (args) => ({
    components: { RSliderBtnGroup },
    setup() {
      const active = ref<"home" | "favorites" | "platforms">("home");
      return { args, active };
    },
    template: `
      <RSliderBtnGroup
        v-bind="args"
        :model-value="active"
        :items="[
          { id: 'home', label: 'Home' },
          { id: 'favorites', label: 'Favorites' },
          { id: 'platforms', label: 'Platforms' },
        ]"
        @update:model-value="(v) => (active = v)"
      />
    `,
  }),
};

export const Disabled: Story = {
  args: { variant: "segmented" },
  render: (args) => ({
    components: { RSliderBtnGroup },
    setup() {
      const group = ref<"none" | "letter">("none");
      return { args, group };
    },
    template: `
      <RSliderBtnGroup
        v-bind="args"
        :model-value="group"
        :items="[
          { id: 'none', icon: 'mdi-view-agenda-outline', ariaLabel: 'Flat' },
          { id: 'letter', icon: 'mdi-alphabetical-variant', ariaLabel: 'By letter', disabled: true },
        ]"
        @update:model-value="(v) => (group = v)"
      />
    `,
  }),
};
