import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { SimpleRom } from "@/stores/roms";
import RGameCard from "./RGameCard.vue";

const sampleRom = {
  id: 1,
  name: "Super Mario World",
  fs_name_no_ext: "Super Mario World (USA)",
  platform_display_name: "Super Nintendo",
  platform_custom_name: null,
  platform_slug: "snes",
  path_cover_large: null,
  path_cover_small: null,
  url_cover: null,
  regions: ["US"],
  languages: ["en"],
} as unknown as SimpleRom;

const meta: Meta<typeof RGameCard> = {
  title: "Media/RGameCard",
  component: RGameCard,
  argTypes: {
    showPlatform: { control: "boolean" },
    showTitle: { control: "boolean" },
    selected: { control: "boolean" },
  },
};

export default meta;

type Story = StoryObj<typeof RGameCard>;

export const Default: Story = {
  render: (args) => ({
    components: { RGameCard },
    setup: () => ({ args, rom: sampleRom }),
    template: `<div style="width:180px"><RGameCard :rom="rom" v-bind="args" /></div>`,
  }),
};

export const Selected: Story = {
  ...Default,
  args: { selected: true },
};

export const Grid: Story = {
  render: () => ({
    components: { RGameCard },
    setup: () => {
      const roms: SimpleRom[] = [
        {
          ...sampleRom,
          id: 1,
          name: "Super Mario World",
          platform_slug: "snes",
        } as SimpleRom,
        {
          ...sampleRom,
          id: 2,
          name: "Chrono Trigger",
          platform_slug: "snes",
        } as SimpleRom,
        {
          ...sampleRom,
          id: 3,
          name: "Legend of Zelda: A Link to the Past",
          platform_slug: "snes",
        } as SimpleRom,
        {
          ...sampleRom,
          id: 4,
          name: "Earthbound",
          platform_slug: "snes",
        } as SimpleRom,
        {
          ...sampleRom,
          id: 5,
          name: "Super Metroid",
          platform_slug: "snes",
        } as SimpleRom,
        {
          ...sampleRom,
          id: 6,
          name: "F-Zero",
          platform_slug: "snes",
        } as SimpleRom,
      ];
      return { roms };
    },
    template: `
      <div style="display:grid;grid-template-columns:repeat(3,180px);gap:1.5rem">
        <RGameCard v-for="rom in roms" :key="rom.id" :rom="rom" />
      </div>
    `,
  }),
};
