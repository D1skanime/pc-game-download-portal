import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { PcComponentSchema } from "@/__generated__";
import { ROUTES } from "@/plugins/router";
import PcComponents from "./PcComponents.vue";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRouter: () => ({ push }),
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string) =>
      ({
        "rom.pc-components": "PC components",
        "rom.pc-base-game": "Main game",
        "rom.pc-updates": "Updates",
        "rom.category-dlc": "DLC",
        "rom.pc-hotfixes": "Hotfixes",
        "rom.pc-language-packs": "Language packs",
        "rom.pc-extras": "Extras",
        "rom.pc-needs-classification": "Needs classification",
      })[key] ?? key,
  }),
}));

const componentGroups = [
  {
    id: 1,
    relative_path: "Game",
    kind: "base",
    manifest_members: [
      {
        id: 1,
        relative_path: "Game/game.exe",
        size_bytes: 1024,
        sha256: "a".repeat(64),
      },
    ],
  },
  { id: 2, relative_path: "Updates", kind: "update", manifest_members: [] },
  { id: 3, relative_path: "DLC", kind: "dlc", manifest_members: [] },
  { id: 4, relative_path: "Hotfix", kind: "hotfix", manifest_members: [] },
  {
    id: 5,
    relative_path: "Language",
    kind: "language_pack",
    manifest_members: [],
  },
  { id: 6, relative_path: "Extras", kind: "extra", manifest_members: [] },
  { id: 7, relative_path: "Unknown", kind: "unresolved", manifest_members: [] },
] satisfies PcComponentSchema[];

describe("PcComponents", () => {
  beforeEach(() => push.mockReset());

  it("uses the main game label instead of the technical base folder name", () => {
    const wrapper = mount(PcComponents, {
      props: {
        components: [
          {
            id: 1,
            relative_path: "base",
            kind: "base",
            manifest_members: [],
          },
        ],
        romId: 1,
      },
      global: {
        stubs: {
          RCollapsible: {
            props: ["title"],
            template: "<section :data-title='title'><slot /></section>",
          },
        },
      },
    });

    expect(
      wrapper.get("[data-testid='pc-component-base']").attributes("data-title"),
    ).toBe("Main game");
  });

  it("renders PC component groups in the operator review order", async () => {
    const wrapper = mount(PcComponents, {
      props: { components: componentGroups, romId: 1 },
      global: {
        stubs: {
          RCollapsible: false,
          PcMetadataReview: {
            props: ["romId", "componentId"],
            template:
              "<div :data-testid='`dlc-review-${componentId}`'><slot /></div>",
          },
        },
      },
    });

    expect(wrapper.text()).toContain("Main game");
    expect(wrapper.text()).toContain("Needs classification");
    expect(
      wrapper
        .findAll("[data-testid='pc-component-group']")
        .map((group) => group.get(".pc-components__group-heading").text()),
    ).toEqual([
      "Main game",
      "Updates",
      "DLC",
      "Hotfixes",
      "Language packs",
      "Extras",
      "Needs classification",
    ]);

    await wrapper.get("[data-testid='pc-component-Game']").trigger("click");
    expect(wrapper.text()).toContain("Game/game.exe");
    expect(wrapper.text()).toContain("1 KB");
    expect(wrapper.text()).toContain("a".repeat(64));
    await wrapper.get("[data-testid='pc-component-DLC']").trigger("click");
    expect(wrapper.find("[data-testid='dlc-review-3']").exists()).toBe(true);
  });

  it("opens only DLC components at their parent-owned detail routes", async () => {
    const wrapper = mount(PcComponents, {
      props: { components: componentGroups, romId: 42 },
      global: {
        stubs: {
          RCollapsible: { template: "<section><slot /></section>" },
          RBtn: {
            template: "<button @click='$emit(\"click\")'><slot /></button>",
          },
        },
      },
    });

    const controls = wrapper.findAll("[data-testid='open-pc-dlc-details']");
    expect(controls).toHaveLength(1);
    await controls[0].trigger("click");

    expect(push).toHaveBeenCalledWith({
      name: ROUTES.PC_DLC,
      params: { rom: 42, component: 3 },
    });
    expect(wrapper.text()).not.toContain("DetailsUpdates");
  });
});
