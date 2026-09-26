import { mount } from "@vue/test-utils";
/* eslint-disable vue/one-component-per-file */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick } from "vue";
import type {
  DownloadTransferResponse,
  PcComponentSchema,
} from "@/__generated__";
import DownloadManager from "./DownloadManager.vue";
import DownloadSelectionDialog from "./DownloadSelectionDialog.vue";
import DownloadTransferHistory from "./DownloadTransferHistory.vue";

const { list, get, enhancedSupported } = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  enhancedSupported: vi.fn(),
}));

vi.mock("@/services/api/downloadTransfers", () => ({
  default: { list, get },
}));

vi.mock("@/v2/composables/useBrowserDownloadQueue", () => ({
  isEnhancedDownloadSupported: enhancedSupported,
}));

const translations: Record<string, string> = {
  "common.cancel": "Cancel",
  "rom.download-browser-mode": "Standard browser download",
  "rom.download-cancelled": "Cancelled",
  "rom.download-components": "Download components",
  "rom.download-game": "Download game",
  "rom.download-expired":
    "This download is no longer available. Prepare it again.",
  "rom.download-failed": "Download failed",
  "rom.download-failed-description":
    "RomM could not continue this file. Check your connection and folder permission, then retry.",
  "rom.download-file": "Download file",
  "rom.download-handed-to-browser": "Handed to browser",
  "rom.download-no-complete-set": "No complete download set is available",
  "rom.download-optional-file": "Optional file",
  "rom.pc-base-game": "Main game",
  "rom.download-queued": "Queued",
  "rom.download-required-missing":
    "This selection is incomplete. Add the required components shown above before starting the download.",
  "rom.download-served": "Served by RomM",
  "rom.download-stale": "Source changed. Prepare the download again.",
  "rom.download-start": "Start download",
  "rom.download-state-downloading": "Downloading",
  "rom.download-verified": "Verified",
};

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string) => translations[key] ?? key,
  }),
}));

const RDialogStub = defineComponent({
  props: {
    modelValue: { type: Boolean, required: true },
    fullscreenOnMobile: { type: Boolean, default: true },
  },
  template: `
    <section
      v-if="modelValue"
      role="dialog"
      :data-fullscreen-on-mobile="fullscreenOnMobile"
    >
      <h2><slot name="header" /></h2>
      <div><slot name="content" /></div>
      <footer><slot name="footer" /></footer>
    </section>
  `,
});

const RCheckboxStub = defineComponent({
  props: {
    modelValue: { type: Boolean, default: false },
    label: { type: String, default: "" },
    disabled: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  template: `
    <label>
      <input
        type="checkbox"
        :checked="modelValue"
        :disabled="disabled"
        :aria-label="label"
        @change="$emit('update:modelValue', $event.target.checked)"
      />
      <span>{{ label }}</span>
    </label>
  `,
});

const RBtnStub = defineComponent({
  props: { disabled: { type: Boolean, default: false } },
  emits: ["click"],
  template:
    '<button type="button" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
});

const RCollapsibleStub = defineComponent({
  props: {
    title: { type: String, default: "" },
    modelValue: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  template: `
    <section>
      <button
        type="button"
        :aria-expanded="modelValue"
        @click="$emit('update:modelValue', !modelValue)"
      >{{ title }}</button>
      <div v-if="modelValue"><slot /></div>
    </section>
  `,
});

const selectionGlobal = {
  stubs: {
    RDialog: RDialogStub,
    RCheckbox: RCheckboxStub,
    RBtn: RBtnStub,
    RCollapsible: RCollapsibleStub,
    DownloadModeSelector: {
      template:
        '<label data-testid="download-mode"><input type="radio" aria-label="Standard browser download" />Standard browser download</label>',
    },
  },
};

const components = [
  {
    id: 1,
    relative_path: "Game",
    kind: "base",
    manifest_members: [],
  },
] satisfies PcComponentSchema[];

function session(
  itemStatus: string,
  mode: "standard" | "enhanced" = "standard",
): DownloadTransferResponse {
  return {
    schema_version: 1,
    id: `opaque-${itemStatus}`,
    manifest_id: "manifest-a",
    parent_session_id: null,
    attempt_no: 1,
    rom_id: 7,
    mode,
    status: "active",
    selected_items: 1,
    selected_bytes: 1024,
    observed_bytes: itemStatus === "served" ? 1024 : 0,
    started_at: "2026-09-18T08:00:00Z",
    last_activity_at: "2026-09-18T08:01:00Z",
    ended_at: null,
    items: [
      {
        id: 42,
        manifest_member_id: `member-${itemStatus}`,
        destination: `game/${itemStatus}.bin`,
        expected_bytes: 1024,
        observed_bytes: itemStatus === "served" ? 1024 : 0,
        status: itemStatus,
        started_at: "2026-09-18T08:00:00Z",
        last_activity_at: "2026-09-18T08:01:00Z",
        ended_at: null,
      },
    ],
    events: [],
  };
}

describe("browser download accessibility and truthful state contract", () => {
  beforeEach(() => {
    list.mockReset();
    get.mockReset();
    list.mockResolvedValue({ data: [] });
    get.mockResolvedValue({ data: session("handed_to_browser") });
    enhancedSupported.mockReturnValue(false);
    document.documentElement.className = "";
    document.documentElement.removeAttribute("data-input");
    document.documentElement.removeAttribute("data-bp");
  });

  it.each(["r-v2-dark", "r-v2-light"])(
    "keeps native controls reachable in %s across keyboard, touch, and pad fixtures",
    async (theme) => {
      document.documentElement.classList.add("r-v2", theme);
      for (const input of ["key", "touch", "pad"] as const) {
        document.documentElement.dataset.input = input;
        const wrapper = mount(DownloadSelectionDialog, {
          props: {
            modelValue: false,
            components,
            archiveSets: [
              {
                id: 1,
                name: "Complete game",
                members: [
                  {
                    component_id: 1,
                    manifest_member_id: 11,
                    position: 1,
                    required: true,
                  },
                ],
              },
            ],
          },
          global: selectionGlobal,
        });

        await wrapper.setProps({ modelValue: true });
        await nextTick();
        expect(
          wrapper
            .get('[role="dialog"]')
            .attributes("data-fullscreen-on-mobile"),
        ).toBe("true");
        expect(wrapper.findAll("input")).toHaveLength(2);
        expect(wrapper.findAll("button")).toHaveLength(2);
        expect(wrapper.find("input[type=radio]").attributes("aria-label")).toBe(
          "Standard browser download",
        );
        wrapper.unmount();
      }
    },
  );

  it("blocks an incomplete required set and keeps the start control native-disabled", async () => {
    const wrapper = mount(DownloadSelectionDialog, {
      props: {
        modelValue: false,
        components: [],
        archiveSets: [
          {
            id: 1,
            name: "Complete game",
            members: [
              {
                component_id: 1,
                manifest_member_id: 11,
                position: 1,
                required: true,
              },
            ],
          },
        ],
      },
      global: selectionGlobal,
    });

    await wrapper.setProps({ modelValue: true });
    await nextTick();
    expect(wrapper.text()).toContain("This selection is incomplete");
    expect(wrapper.findAll("button")[1].attributes("disabled")).toBeDefined();
    await wrapper.findAll("button")[1].trigger("click");
    expect(wrapper.emitted("start")).toBeUndefined();
  });

  it("activates a complete set through native checkbox and button events", async () => {
    const wrapper = mount(DownloadSelectionDialog, {
      props: {
        modelValue: false,
        components,
        archiveSets: [
          {
            id: 1,
            name: "Complete game",
            members: [
              {
                component_id: 1,
                manifest_member_id: 11,
                position: 1,
                required: true,
              },
            ],
          },
        ],
      },
      global: selectionGlobal,
    });

    await wrapper.setProps({ modelValue: true });
    await nextTick();
    const setControl = wrapper.find("input[type=checkbox]");
    await setControl.trigger("change");
    await wrapper.findAll("button")[1].trigger("click");
    expect(wrapper.emitted("start")?.[0]?.[0]).toEqual({
      archiveSetId: 1,
      selectedMemberIds: [11],
      componentIds: [1],
      mode: "standard",
    });
  });

  it("shows component files and submits only the checked files without an archive policy", async () => {
    const wrapper = mount(DownloadSelectionDialog, {
      props: {
        modelValue: false,
        components: [
          {
            id: 1,
            relative_path: "base",
            kind: "base",
            manifest_members: [
              {
                id: 11,
                relative_path: "base/game.iso",
                size_bytes: 4096,
                sha256: "a".repeat(64),
              },
              {
                id: 12,
                relative_path: "base/readme.txt",
                size_bytes: 128,
                sha256: "b".repeat(64),
              },
            ],
          },
        ],
        archiveSets: [],
      },
      global: selectionGlobal,
    });

    await wrapper.setProps({ modelValue: true });
    await nextTick();
    expect(wrapper.text()).not.toContain("base/game.iso");
    expect(wrapper.text()).not.toContain("base/readme.txt");

    await wrapper.find('[aria-expanded="false"]').trigger("click");
    expect(wrapper.text()).toContain("base/game.iso");
    expect(wrapper.text()).toContain("base/readme.txt");

    const fileControls = wrapper.findAll("input[type=checkbox]");
    expect(fileControls).toHaveLength(3);
    await fileControls[2].setValue(false);
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "Start download")
      ?.trigger("click");

    expect(wrapper.emitted("start")?.[0]?.[0]).toEqual({
      archiveSetId: undefined,
      selectedMemberIds: [11],
      componentIds: [1],
      mode: "standard",
    });
  });

  it("uses a human component label for optional files instead of the manifest ID", async () => {
    const wrapper = mount(DownloadSelectionDialog, {
      props: {
        modelValue: false,
        components,
        archiveSets: [
          {
            id: 1,
            name: "Complete game",
            members: [
              {
                component_id: 1,
                manifest_member_id: 11,
                position: 1,
                required: false,
              },
            ],
          },
        ],
      },
      global: selectionGlobal,
    });

    await wrapper.setProps({ modelValue: true });
    await nextTick();
    expect(wrapper.text()).toContain("Optional file Main game");
    expect(wrapper.text()).not.toContain("11");
  });

  it("uses only truthful status vocabulary and never exposes source values", () => {
    const wrapper = mount(DownloadTransferHistory, {
      props: {
        sessions: [
          session("handed_to_browser"),
          session("served"),
          session("verified", "enhanced"),
          session("stale"),
          session("cancelled"),
          session("expired"),
          session("failed"),
        ],
      },
    });

    const text = wrapper.text();
    expect(text).toContain("Handed to browser");
    expect(text).toContain("Served by RomM");
    expect(text).toContain("Verified");
    expect(text).toContain("Source changed. Prepare the download again.");
    expect(text).toContain("Cancelled");
    expect(text).toContain(
      "This download is no longer available. Prepare it again.",
    );
    expect(text).toContain("Download failed");
    expect(text).not.toMatch(
      /(NAS|local|saved|downloaded|completed|checksum|resumable|https?:\/\/|token|opaque-)/i,
    );
  });

  it("maps standard verified observations away from the enhanced-only claim", () => {
    const wrapper = mount(DownloadTransferHistory, {
      props: { sessions: [session("verified", "standard")] },
    });

    expect(wrapper.text()).toContain("Download failed");
    expect(wrapper.text()).not.toContain("Verified");
  });

  it("keeps the history styling on semantic theme tokens", () => {
    const source = readFileSync(
      resolve(
        process.cwd(),
        "src/v2/components/GameDetails/DownloadTransferHistory.vue",
      ),
      "utf8",
    );

    expect(source).toContain("var(--r-color-fg-secondary)");
    expect(source).toContain("var(--r-color-fg-muted)");
    expect(source).not.toMatch(/#[0-9a-f]{3,8}\b/i);
    expect(source).not.toMatch(/rgba?\(/i);
  });

  it("does not advertise enhanced mode when the capability seam is unavailable", () => {
    const wrapper = mount(DownloadManager, {
      props: { romId: 7, items: [] },
    });

    expect(wrapper.text()).not.toContain("Enhanced folder download");
  });
});
