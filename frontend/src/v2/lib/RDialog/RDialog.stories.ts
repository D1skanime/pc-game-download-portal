import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import RBtn from "../RBtn/RBtn.vue";
import RDialog from "./RDialog.vue";

const meta: Meta<typeof RDialog> = {
  title: "Overlays/RDialog",
  component: RDialog,
};

export default meta;

type Story = StoryObj<typeof RDialog>;

export const Basic: Story = {
  render: () => ({
    components: { RDialog, RBtn },
    setup() {
      const open = ref(false);
      return { open };
    },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 48px; background: #07070f; min-height: 300px;">
        <RBtn @click="open = true">Open dialog</RBtn>
        <RDialog v-model="open" width="420" icon="mdi-information">
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
  render: () => ({
    components: { RDialog, RBtn },
    setup() {
      const open = ref(false);
      return { open };
    },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 48px; background: #07070f; min-height: 300px;">
        <RBtn @click="open = true">Open loading dialog</RBtn>
        <RDialog
          v-model="open"
          width="420"
          height="240"
          icon="mdi-loading"
          :loading-condition="true"
        >
          <template #header>
            <span>Fetching…</span>
          </template>
        </RDialog>
      </div>
    `,
  }),
};

export const WithToolbarAndFooter: Story = {
  render: () => ({
    components: { RDialog, RBtn },
    setup() {
      const open = ref(false);
      return { open };
    },
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 48px; background: #07070f; min-height: 300px;">
        <RBtn @click="open = true">Open full dialog</RBtn>
        <RDialog v-model="open" width="520" icon="mdi-pencil">
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
