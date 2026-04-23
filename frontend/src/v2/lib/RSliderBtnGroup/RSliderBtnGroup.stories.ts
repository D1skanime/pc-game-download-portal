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
  render: () => ({
    components: { RSliderBtnGroup },
    setup() {
      const layout = ref<"grid" | "list">("grid");
      return { layout };
    },
    template: `
      <RSliderBtnGroup
        :model-value="layout"
        :items="[
          { id: 'grid', icon: 'mdi-view-grid-outline', ariaLabel: 'Grid', title: 'Grid' },
          { id: 'list', icon: 'mdi-view-list', ariaLabel: 'List', title: 'List' },
        ]"
        variant="segmented"
        @update:model-value="(v) => (layout = v)"
      />
    `,
  }),
};

export const Tab: Story = {
  render: () => ({
    components: { RSliderBtnGroup },
    setup() {
      const active = ref<"home" | "favorites" | "platforms">("home");
      return { active };
    },
    template: `
      <RSliderBtnGroup
        :model-value="active"
        :items="[
          { id: 'home', label: 'Home' },
          { id: 'favorites', label: 'Favorites' },
          { id: 'platforms', label: 'Platforms' },
        ]"
        variant="tab"
        @update:model-value="(v) => (active = v)"
      />
    `,
  }),
};

export const Disabled: Story = {
  render: () => ({
    components: { RSliderBtnGroup },
    setup() {
      const group = ref<"none" | "letter">("none");
      return { group };
    },
    template: `
      <RSliderBtnGroup
        :model-value="group"
        :items="[
          { id: 'none', icon: 'mdi-view-agenda-outline', ariaLabel: 'Flat' },
          { id: 'letter', icon: 'mdi-alphabetical-variant', ariaLabel: 'By letter', disabled: true },
        ]"
        variant="segmented"
        @update:model-value="(v) => (group = v)"
      />
    `,
  }),
};
