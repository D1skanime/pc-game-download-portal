import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RVirtualScroller from "./RVirtualScroller.vue";

const meta: Meta<typeof RVirtualScroller> = {
  title: "Structural/RVirtualScroller",
  component: RVirtualScroller,
  argTypes: {
    overscan: { control: "number" },
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
    getItemHeight: () => 44,
    overscan: 25,
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

// Variable per-row heights — exercises binary search and exact offsets.
const variableList = Array.from({ length: 1000 }, (_, i) => ({
  id: i,
  label: `Row ${i + 1}`,
  size: i % 5 === 0 ? "tall" : "short",
}));

export const VariableHeights: Story = {
  args: {
    items: variableList,
    getItemHeight: (item: unknown) =>
      (item as { size: string }).size === "tall" ? 80 : 32,
    overscan: 12,
    height: 480,
  },
  render: (args) => ({
    components: { RVirtualScroller },
    setup: () => ({ args }),
    template: `
      <div style="width: 320px; border: 1px solid var(--r-color-border); border-radius: var(--r-radius-md); background: var(--r-color-bg-elevated)">
        <RVirtualScroller v-bind="args">
          <template #default="{ item, index }">
            <div :style="{
              display: 'flex',
              alignItems: 'center',
              padding: '0 var(--r-space-3)',
              height: item.size === 'tall' ? '80px' : '32px',
              borderBottom: '1px solid var(--r-color-border)',
              fontSize: 'var(--r-font-size-sm)',
              fontWeight: item.size === 'tall' ? 'var(--r-font-weight-semibold)' : 'normal',
            }">
              <span style="opacity:0.5;width:48px">#{{ index }}</span>
              <span>{{ item.label }} ({{ item.size }})</span>
            </div>
          </template>
        </RVirtualScroller>
      </div>
    `,
  }),
};
