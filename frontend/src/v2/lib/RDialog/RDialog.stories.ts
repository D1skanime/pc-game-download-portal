import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import RBtn from "../RBtn/RBtn.vue";
import RDialog from "./RDialog.vue";

const meta: Meta<typeof RDialog> = {
  title: "Overlays/RDialog",
  component: RDialog,
  argTypes: {
    icon: { control: "text" },
    width: { control: "text" },
    height: { control: "text" },
    loadingCondition: { control: "boolean" },
    emptyStateCondition: { control: "boolean" },
    emptyStateType: {
      control: "select",
      options: [null, "game", "platform", "firmware"],
    },
    expandContentOnEmptyState: { control: "boolean" },
    scrollContent: { control: "boolean" },
    showRommIcon: { control: "boolean" },
  },
};

export default meta;

type Story = StoryObj<typeof RDialog>;

export const Basic: Story = {
  args: { width: "420", icon: "mdi-information" },
  render: (args) => ({
    components: { RDialog, RBtn },
    setup() {
      const open = ref(false);
      return { args, open };
    },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 48px; background: #07070f; min-height: 300px;">
        <RBtn @click="open = true">Open dialog</RBtn>
        <RDialog v-bind="args" v-model="open">
          <template #header>
            <span>Dialog title</span>
          </template>
          <template #content>
            <p>This is the dialog body. Keep content concise and actionable.</p>
          </template>
          <template #footer>
            <RBtn variant="text" @click="open = false">Cancel</RBtn>
            <div style="flex:1" />
            <RBtn color="primary" @click="open = false">Confirm</RBtn>
          </template>
        </RDialog>
      </div>
    `,
  }),
};

export const Loading: Story = {
  args: {
    width: "420",
    height: "240",
    icon: "mdi-loading",
    loadingCondition: true,
  },
  render: (args) => ({
    components: { RDialog, RBtn },
    setup() {
      const open = ref(false);
      return { args, open };
    },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 48px; background: #07070f; min-height: 300px;">
        <RBtn @click="open = true">Open loading dialog</RBtn>
        <RDialog v-bind="args" v-model="open">
          <template #header>
            <span>Fetching…</span>
          </template>
        </RDialog>
      </div>
    `,
  }),
};

export const WithToolbarAndFooter: Story = {
  args: { width: "520", icon: "mdi-pencil" },
  render: (args) => ({
    components: { RDialog, RBtn },
    setup() {
      const open = ref(false);
      return { args, open };
    },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 48px; background: #07070f; min-height: 300px;">
        <RBtn @click="open = true">Open full dialog</RBtn>
        <RDialog v-bind="args" v-model="open">
          <template #header><span>Edit ROM</span></template>
          <template #toolbar>
            <small style="color: rgba(255,255,255,0.55)">Super Mario World · Super Nintendo</small>
          </template>
          <template #content>
            <p>Body content with form fields would go here.</p>
          </template>
          <template #footer>
            <RBtn variant="text" @click="open = false">Cancel</RBtn>
            <div style="flex:1" />
            <RBtn color="primary" @click="open = false">Save</RBtn>
          </template>
        </RDialog>
      </div>
    `,
  }),
};
