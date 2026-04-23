import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RTable from "./RTable.vue";

const meta: Meta<typeof RTable> = {
  title: "Data/RTable",
  component: RTable,
};

export default meta;

type Story = StoryObj<typeof RTable>;

const HEADERS = [
  { title: "Title", key: "name", align: "start", sortable: true },
  { title: "Size", key: "size", align: "start", sortable: true },
  { title: "Added", key: "added", align: "start", sortable: true },
  { title: "⭐", key: "rating", align: "start", sortable: true },
] as const;

const ITEMS = [
  {
    id: 1,
    name: "Super Mario World",
    size: "512 KB",
    added: "2024-03-14",
    rating: 9.4,
  },
  {
    id: 2,
    name: "Chrono Trigger",
    size: "4.0 MB",
    added: "2024-01-02",
    rating: 9.8,
  },
  {
    id: 3,
    name: "Earthbound",
    size: "3.0 MB",
    added: "2024-05-21",
    rating: 9.3,
  },
  {
    id: 4,
    name: "Secret of Mana",
    size: "2.0 MB",
    added: "2024-07-09",
    rating: 9.0,
  },
  {
    id: 5,
    name: "Final Fantasy VI",
    size: "3.0 MB",
    added: "2024-02-18",
    rating: 9.6,
  },
];

export const ClientSide: Story = {
  render: () => ({
    components: { RTable },
    setup: () => ({ HEADERS, ITEMS }),
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 32px; background: #07070f;">
        <RTable
          variant="client"
          :headers="HEADERS"
          :items="ITEMS"
          item-value="id"
          hover
          hide-default-footer
        />
      </div>
    `,
  }),
};

export const WithSelection: Story = {
  render: () => ({
    components: { RTable },
    setup: () => ({ HEADERS, ITEMS }),
    template: `
      <div class="r-v2 r-v2-dark" style="padding: 32px; background: #07070f;">
        <RTable
          variant="client"
          :headers="HEADERS"
          :items="ITEMS"
          item-value="id"
          show-select
          hover
          hide-default-footer
        />
      </div>
    `,
  }),
};
