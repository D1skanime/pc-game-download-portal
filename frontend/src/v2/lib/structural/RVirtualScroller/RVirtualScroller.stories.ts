import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RVirtualScroller from "./RVirtualScroller.vue";

const meta: Meta<typeof RVirtualScroller> = {
  title: "Structural/RVirtualScroller",
  component: RVirtualScroller,
  argTypes: {
    itemHeight: { control: "number" },
    height: { control: "text" },
  },
};

export default meta;

type Story = StoryObj<typeof RVirtualScroller>;

const longList = Array.from({ length: 5000 }, (_, i) => ({
  id: i,
  label: `Row ${i + 1}`,
}));

export const FiveThousandRows: Story = {
  args: {
    items: longList,
    itemHeight: 44,
    height: 480,
  },
  render: (args) => ({
    components: { RVirtualScroller },
    setup: () => ({ args }),
    template: `
      <div style="width: 320px; border: 1px solid var(--r-color-border); border-radius: var(--r-radius-md); background: var(--r-color-bg-elevated)">
        <RVirtualScroller v-bind="args">
          <template #default="{ item, index }">
            <div style="display:flex;align-items:center;padding:0 var(--r-space-3);height:44px;border-bottom:1px solid var(--r-color-border);font-size:var(--r-font-size-sm);">
              <span style="opacity:0.5;width:48px">#{{ index }}</span>
              <span>{{ item.label }}</span>
            </div>
          </template>
        </RVirtualScroller>
      </div>
    `,
  }),
};
