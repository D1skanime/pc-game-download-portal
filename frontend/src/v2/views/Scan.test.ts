import { mount, shallowMount, flushPromises } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { createI18n } from "vue-i18n";
import OperationStatusPanel from "@/v2/components/Scan/OperationStatusPanel.vue";
import type { ScanOperationSnapshot } from "@/v2/data/contracts";
import ScanView from "@/v2/views/Scan.vue";

const namespaces = import.meta.glob<Record<string, string>>(
  "../../locales/*/scan.json",
  { eager: true, import: "default" },
);
const locales = process.env.PGDP_TEST_LOCALES?.split(",") ?? ["en_US", "de_DE"];
const states: ScanOperationSnapshot["state"][] = [
  "accepted",
  "queued",
  "running",
  "stopping",
  "cancelled",
  "interrupted",
  "recovering",
  "blocked",
  "failed",
  "completed",
  "completed-with-warnings",
];
function snapshot(
  state: ScanOperationSnapshot["state"],
): ScanOperationSnapshot {
  return {
    id: "one",
    request_key: "key",
    job_id: "job",
    attempt_id: "attempt",
    state,
    version: 1,
    intentional_cancel: state === "cancelled",
    dispatch_pending: false,
    created_at: "",
    updated_at: "",
    items: [],
    scan_stats: {},
  };
}
const stubs = {
  RAlert: { template: '<div role="alert"><slot /></div>' },
  RBtn: {
    props: ["disabled"],
    template: '<button :disabled="disabled"><slot /></button>',
  },
  RCheckbox: {
    props: ["modelValue", "label"],
    emits: ["update:modelValue"],
    template:
      '<label>{{ label }}<input type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" /></label>',
  },
  RProgressLinear: {
    props: ["indeterminate"],
    template: '<progress :data-indeterminate="indeterminate" />',
  },
};
function mountPanel(locale = "en_US", overrides = {}) {
  const dictionary = namespaces["../../locales/" + locale + "/scan.json"];
  expect(dictionary, "missing real scan locale " + locale).toBeTruthy();
  return mount(OperationStatusPanel, {
    props: {
      snapshot: snapshot("queued"),
      status: "queued",
      checking: false,
      uncertain: false,
      disconnected: false,
      reconciling: false,
      actionError: null,
      canManage: true,
      ...overrides,
    },
    global: {
      plugins: [
        createI18n({
          legacy: false,
          locale,
          fallbackLocale: false,
          messages: { [locale]: { scan: dictionary } },
        }),
      ],
      stubs,
    },
  });
}
describe("Scan persistent recovery controls", () => {
  it.each(locales)(
    "renders every confirmed state and translated causes/actions in %s",
    async (locale) => {
      const dictionary = namespaces["../../locales/" + locale + "/scan.json"];
      const panel = mountPanel(locale);
      for (const state of states) {
        await panel.setProps({ snapshot: snapshot(state), status: state });
        expect(panel.get('[role="status"]').text()).toBe(
          dictionary["recovery-" + state],
        );
        expect(panel.text()).not.toContain("scan.recovery-");
      }
      for (const cause of [
        "dispatch_unavailable",
        "source_changed",
        "mapping_changed",
        "metadata_timeout",
        "worker_failed",
      ]) {
        await panel.setProps({
          snapshot: { ...snapshot("blocked"), cause_code: cause },
          status: "blocked",
        });
        expect(panel.find('[role="alert"]').exists()).toBe(true);
        expect(panel.text()).not.toContain("scan.recovery-");
        expect(panel.text()).not.toContain(cause);
      }
      panel.unmount();
    },
  );
  it("shows indeterminate progress for unknown totals and an independent disconnected notice", () => {
    const panel = mountPanel("en_US", {
      snapshot: snapshot("running"),
      status: "running",
      disconnected: true,
    });
    expect(panel.get("progress").attributes("data-indeterminate")).toBe("true");
    expect(panel.text()).not.toContain("0 of 0");
    expect(panel.text()).toContain("Connection lost");
    expect(panel.emitted("stop")).toBeUndefined();
    panel.unmount();
  });
  it("retains retry-status during uncertain acceptance and disables stop while stopping", async () => {
    const panel = mountPanel("en_US", {
      uncertain: true,
      actionError: "acceptance-uncertain",
    });
    await panel
      .findAll("button")
      .find((button) => button.text() === "Retry status")!
      .trigger("click");
    expect(panel.emitted("retryStatus")).toHaveLength(1);
    await panel.setProps({
      status: "stopping",
      uncertain: false,
      actionError: null,
    });
    expect(
      panel
        .findAll("button")
        .find((button) => button.text() === "Stop")!
        .attributes("disabled"),
    ).toBeDefined();
    panel.unmount();
  });
  it("resumes only after a user action and retries only selected warning IDs", async () => {
    const panel = mountPanel("en_US", {
      snapshot: snapshot("cancelled"),
      status: "cancelled",
    });
    expect(panel.emitted("resume")).toBeUndefined();
    await panel
      .findAll("button")
      .find((button) => button.text() === "Resume")!
      .trigger("click");
    expect(panel.emitted("resume")).toHaveLength(1);
    await panel.setProps({
      status: "completed-with-warnings",
      snapshot: {
        ...snapshot("completed-with-warnings"),
        items: [
          {
            id: 7,
            target_key: "Affected game",
            mapping_id: 1,
            expected_revision: 1,
            relative_path: "game",
            provider: "steam",
            outcome: "warning",
            attempt_id: "attempt",
          },
          {
            id: 8,
            target_key: "Successful game",
            mapping_id: 1,
            expected_revision: 1,
            relative_path: "other",
            provider: "steam",
            outcome: "completed",
            attempt_id: "attempt",
          },
        ],
      },
    });
    expect(panel.text()).toContain("Affected game");
    expect(panel.text()).not.toContain("Successful game");
    await panel.get('input[type="checkbox"]').setValue(true);
    await panel
      .findAll("button")
      .find((button) => button.text() === "Retry selected metadata")!
      .trigger("click");
    expect(panel.emitted("retry")).toEqual([[["7"]]]);
    panel.unmount();
  });
});

const controls = vi.hoisted(() => ({
  start: vi.fn(),
  cancel: vi.fn(),
  retryStatus: vi.fn(),
  loadMore: vi.fn(),
}));
vi.mock("@/v2/composables/useCan", async () => {
  const { ref } = await import("vue");
  return { useCan: () => ref(false) };
});
vi.mock("@/v2/composables/useLibraryOperation", async () => {
  const { ref } = await import("vue");
  return {
    useLibraryOperation: () => ({
      ...controls,
      snapshot: ref({ ...snapshot("completed"), items: [] }),
      checking: ref(false),
      uncertain: ref(false),
      disconnected: ref(false),
      reconciling: ref(false),
      actionError: ref(null),
      status: ref("completed"),
      busy: ref(false),
      hasMore: ref(true),
      loadingMore: ref(false),
    }),
  };
});
vi.mock("@/v2/composables/useScanProviders", async () => {
  const { ref } = await import("vue");
  return {
    useScanProviders: () =>
      Object.fromEntries(
        [
          "storedMetadataSources",
          "metadataSources",
          "hashMatchers",
          "generalProviders",
          "specificProviders",
          "effectiveMetadataSources",
        ].map((key) => [key, ref([])]),
      ),
  };
});
vi.mock("@/v2/data/adapters/legacy/stores/scanning", async () => {
  const { defineStore } = await import("pinia");
  return {
    default: defineStore("test-scanning", {
      state: () => ({ scanning: false, scanningPlatforms: [], scanStats: {} }),
      actions: { reset: vi.fn() },
    }),
  };
});
vi.mock("@/v2/data/adapters/legacy/stores/platforms", async () => {
  const { defineStore } = await import("pinia");
  return {
    default: defineStore("test-platforms", {
      state: () => ({ allPlatforms: [], scannablePlatforms: [] }),
      actions: { fetchPlatforms: vi.fn() },
    }),
  };
});
vi.mock("@/v2/data/adapters/legacy/stores/config", async () => {
  const { defineStore } = await import("pinia");
  return {
    default: defineStore("test-config", {
      state: () => ({ config: { SKIP_HASH_CALCULATION: true } }),
    }),
  };
});
vi.mock("@/v2/data/adapters/legacy/services/api/storage", () => ({
  default: { getMappingsReadiness: vi.fn().mockResolvedValue({ ready: true }) },
}));
describe("Scan view existing-owner integration", () => {
  it("restores status without submitting and forwards paging and permissions", async () => {
    const wrapper = shallowMount(ScanView, {
      global: {
        plugins: [
          createPinia(),
          createI18n({
            legacy: false,
            locale: "en_US",
            messages: {
              en_US: { scan: namespaces["../../locales/en_US/scan.json"] },
            },
          }),
        ],
      },
    });
    await flushPromises();
    const panel = wrapper.findComponent(OperationStatusPanel);
    expect(controls.start).not.toHaveBeenCalled();
    expect(panel.props("canManage")).toBe(false);
    expect(panel.props("hasMore")).toBe(true);
    panel.vm.$emit("loadMore");
    expect(controls.loadMore).toHaveBeenCalledOnce();
    panel.vm.$emit("retryStatus");
    expect(controls.retryStatus).toHaveBeenCalledOnce();
    expect(controls.start).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
