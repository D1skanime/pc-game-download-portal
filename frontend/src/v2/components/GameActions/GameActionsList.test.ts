import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { SimpleRom } from "@/stores/roms";
import GameActionsList from "./GameActionsList.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

type Flags = {
  canPlay: boolean;
  canShareQR: boolean;
  canOpenInFlashpoint: boolean;
  canManageCollections: boolean;
  canRemoveFromContinuePlaying: boolean;
  canMatch: boolean;
  canRefresh: boolean;
  canEdit: boolean;
  canDelete: boolean;
};

const flags: Flags = {
  canPlay: true,
  canShareQR: false,
  canOpenInFlashpoint: false,
  canManageCollections: true,
  canRemoveFromContinuePlaying: false,
  canMatch: true,
  canRefresh: true,
  canEdit: true,
  canDelete: true,
};

vi.mock("@/v2/composables/useGameActions", () => ({
  useGameActions: (getRom: () => SimpleRom | null) =>
    new Proxy(
      {},
      {
        get(_target, prop: string) {
          if (prop in flags) {
            return {
              get value() {
                return flags[prop as keyof Flags];
              },
            };
          }
          if (prop === "canShowCopyDownloadLink") {
            return {
              get value() {
                const rom = getRom();
                return (
                  rom?.platform_fs_slug !== "pc" && rom?.platform_slug !== "pc"
                );
              },
            };
          }
          if (prop === "isFavorited") return { value: false };
          return vi.fn();
        },
      },
    ),
}));

const RMenuItem = {
  props: ["label"],
  template: `<li class="item">{{ label }}</li>`,
};
const RDivider = { template: `<hr class="divider" />` };

function mountList(
  overrides: Partial<Flags> = {},
  rom: Partial<SimpleRom> = {},
) {
  Object.assign(flags, overrides);
  return mount(GameActionsList, {
    props: { rom: { id: 1, ...rom } as SimpleRom },
    global: { stubs: { RMenuItem, RDivider } },
  });
}

function labels(wrapper: ReturnType<typeof mountList>) {
  return wrapper.findAll(".item").map((w) => w.text());
}

describe("GameActionsList — permission gating", () => {
  it("offers the write and destructive actions to a user who holds them", () => {
    const wrapper = mountList({
      canMatch: true,
      canRefresh: true,
      canEdit: true,
      canDelete: true,
    });
    expect(labels(wrapper)).toEqual(
      expect.arrayContaining([
        "rom.match-rom",
        "rom.refresh-metadata",
        "common.edit",
        "common.delete",
      ]),
    );
  });

  it("hides them (and their dividers) from a read-only user", () => {
    const wrapper = mountList({
      canMatch: false,
      canRefresh: false,
      canEdit: false,
      canDelete: false,
    });
    const shown = labels(wrapper);
    expect(shown).not.toContain("rom.match-rom");
    expect(shown).not.toContain("rom.refresh-metadata");
    expect(shown).not.toContain("common.edit");
    expect(shown).not.toContain("common.delete");
    // Only the divider between the primary and per-user groups survives.
    expect(wrapper.findAll(".divider")).toHaveLength(1);
    // Read-only users keep the actions they can actually perform.
    expect(shown).toContain("rom.download");
    expect(shown).toContain("rom.add-to-favorites");
  });

  it("keeps the metadata divider when only some metadata actions are held", () => {
    const wrapper = mountList({
      canMatch: false,
      canRefresh: false,
      canEdit: true,
      canDelete: false,
    });
    expect(labels(wrapper)).toContain("common.edit");
    expect(wrapper.findAll(".divider")).toHaveLength(2);
  });

  it("hides copy-link for a real PC ROM", () => {
    const wrapper = mountList(
      {},
      {
        platform_slug: "win",
        platform_fs_slug: "pc",
      },
    );

    expect(labels(wrapper)).not.toContain("rom.copy-link");
    expect(labels(wrapper)).toContain("rom.download");
  });

  it("keeps copy-link for a non-PC ROM", () => {
    const wrapper = mountList(
      {},
      {
        platform_slug: "snes",
        platform_fs_slug: "snes",
      },
    );

    expect(labels(wrapper)).toContain("rom.copy-link");
    expect(labels(wrapper)).toContain("rom.download");
  });
});
