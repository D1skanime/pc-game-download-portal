import { flushPromises, mount } from "@vue/test-utils";
import mitt from "mitt";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref, type Component } from "vue";

const mocks = vi.hoisted(() => ({
  fetchQueue: vi.fn(),
  accept: vi.fn(),
  skip: vi.fn(),
  batchAccept: vi.fn(),
  snackbar: { error: vi.fn(), success: vi.fn() },
  route: {
    path: "/settings/administration",
    query: {} as Record<string, string>,
  },
  router: { replace: vi.fn() },
  store: {
    items: [] as unknown[],
    loading: false,
    error: null,
    total: 0,
    outstandingCount: 0,
    hasMore: false,
    progress: 0,
    selection: new Set<number>(),
    actionLoadingIds: new Set<number>(),
    batchLoading: false,
    selectedGroupIsSafe: false,
  },
}));

const canReview = ref(true);

const queueItem = {
  id: 4,
  rom_id: 8,
  component_id: 12,
  component_kind: "dlc",
  target_kind: "component",
  normalized_query: "Road to the Black Sea",
  source_name: "DLC/Road to the Black Sea",
  source_path: "pc/roms/Euro Truck Simulator 2/DLC/Road to the Black Sea",
  main_game_label: "Euro Truck Simulator 2",
  candidate_fingerprint: "steam:42",
  candidate_title: "Road to the Black Sea",
  candidate_cover_url: "https://example.test/cover.jpg",
  provider: "steam",
  reason: "unique DLC title match",
  state: "pending",
  expected_queue_version: "2026-10-02T00:00:00Z",
  expected_target_version: "2026-10-02T00:00:00Z",
} as const;

vi.mock("@/stores/pcAutomation", () => ({
  default: () => ({
    ...mocks.store,
    fetchQueue: mocks.fetchQueue,
    accept: mocks.accept,
    skip: mocks.skip,
    batchAccept: mocks.batchAccept,
    toggleSelection: vi.fn(),
    clearSelection: vi.fn(),
  }),
}));

vi.mock("@/v2/composables/useCan", () => ({
  useCan: () => canReview,
}));

vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => mocks.snackbar,
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string, values?: { title?: string }) =>
      ({
        "settings.pc-automation.unnamed-candidate": "Unbenannter Eintrag",
        "settings.pc-automation.main-game": "Main game",
        "settings.pc-automation.source-name": "Source name",
        "settings.pc-automation.source-path": "Source path",
      })[key] ?? (values?.title ? `${key}: ${values.title}` : key),
  }),
}));

vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRoute: () => mocks.route,
  useRouter: () => mocks.router,
}));

vi.mock("@/stores/auth", () => ({
  default: () => ({ scopes: [] }),
}));

const modules = import.meta.glob("./PcAutomationQueue.vue", { eager: true });
const Queue = modules["./PcAutomationQueue.vue"] as
  { default: Component } | undefined;
const administrationModules = import.meta.glob(
  "../../views/Settings/Administration.vue",
  { eager: true },
);
const Administration = administrationModules[
  "../../views/Settings/Administration.vue"
] as { default: Component } | undefined;

function mountQueue() {
  if (!Queue) return null;
  return mount(Queue.default, {
    global: {
      provide: { emitter: mitt() },
      stubs: {
        RBtn: {
          props: ["disabled", "loading"],
          template:
            "<button v-bind='$attrs' :disabled='disabled' :data-loading='loading' @click='$emit(\"click\")'><slot /></button>",
        },
        RProgressLinear: true,
        RSkeletonBlock: true,
      },
    },
  });
}

describe("PcAutomationQueue", () => {
  beforeEach(() => {
    mocks.fetchQueue.mockReset();
    mocks.accept.mockReset();
    mocks.skip.mockReset();
    mocks.batchAccept.mockReset();
    mocks.snackbar.error.mockReset();
    mocks.snackbar.success.mockReset();
    canReview.value = true;
    mocks.route.query = {};
    mocks.router.replace.mockReset();
    Object.assign(mocks.store, {
      items: [],
      loading: false,
      error: null,
      total: 0,
      outstandingCount: 0,
      hasMore: false,
      progress: 0,
      selection: new Set<number>(),
      actionLoadingIds: new Set<number>(),
      batchLoading: false,
      selectedGroupIsSafe: false,
    });
  });

  it("provides distinct loading and empty queue states", async () => {
    const wrapper = mountQueue();

    expect(wrapper).not.toBeNull();
    await flushPromises();
    expect(mocks.fetchQueue).toHaveBeenCalledWith({ reset: true });
  });

  it("does not render review controls without the edit permission", () => {
    canReview.value = false;
    const wrapper = mountQueue();

    expect(wrapper?.find("[data-testid='pc-automation-queue']").exists()).toBe(
      false,
    );
  });

  it("renders source details for parent and component rows", () => {
    const parentItem = {
      ...queueItem,
      id: 3,
      component_id: null,
      component_kind: null,
      target_kind: "parent",
      source_name: "Euro Truck Simulator 2.exe",
      source_path: "pc/roms/Euro Truck Simulator 2.exe",
      main_game_label: "Euro Truck Simulator 2",
    } as const;
    mocks.store.items = [parentItem, queueItem];
    const wrapper = mountQueue()!;

    expect(wrapper.get("[data-testid='pc-automation-row-3']").text()).toContain(
      "Source name: Euro Truck Simulator 2.exeSource path: pc/roms/Euro Truck Simulator 2.exeMain game: Euro Truck Simulator 2",
    );
    expect(wrapper.get("[data-testid='pc-automation-row-4']").text()).toContain(
      "Source name: DLC/Road to the Black SeaSource path: pc/roms/Euro Truck Simulator 2/DLC/Road to the Black SeaMain game: Euro Truck Simulator 2",
    );
  });

  it("keeps row actions in native order and hands correction to MatchRomDialog", async () => {
    mocks.store.items = [queueItem];
    const emitter = mitt();
    const openMatcher = vi.fn();
    emitter.on("showPcMatchRomDialog", openMatcher);
    const wrapper = mount(Queue!.default, {
      global: {
        provide: { emitter },
        stubs: {
          RBtn: {
            props: ["disabled", "loading"],
            template:
              "<button v-bind='$attrs' :disabled='disabled' @click='$emit(\"click\")'><slot /></button>",
          },
          RProgressLinear: true,
          RSkeletonBlock: true,
        },
      },
    });

    expect(wrapper.get("[data-testid='pc-automation-row-4']").text()).toContain(
      "Road to the Black Sea",
    );
    const actions = wrapper
      .findAll("[data-testid='pc-automation-row-4'] button")
      .map((button) => button.attributes("aria-label"));
    expect(actions).toEqual([
      "settings.pc-automation.accept: Road to the Black Sea",
      "settings.pc-automation.correct: Road to the Black Sea",
      "settings.pc-automation.skip: Road to the Black Sea",
    ]);

    await wrapper
      .findAll("[data-testid='pc-automation-row-4'] button")[1]
      .trigger("click");
    expect(openMatcher).toHaveBeenCalledWith(
      expect.objectContaining({
        target: expect.objectContaining({
          kind: "component",
          componentId: 12,
          componentKind: "dlc",
        }),
      }),
    );
  });

  it("renders the localized fallback for missing and blank candidate titles", async () => {
    mocks.store.items = [
      { ...queueItem, id: 5, candidate_title: null },
      { ...queueItem, id: 6, candidate_title: "   " },
    ];
    const emitter = mitt();
    const openMatcher = vi.fn();
    emitter.on("showPcMatchRomDialog", openMatcher);
    const wrapper = mount(Queue!.default, {
      global: {
        provide: { emitter },
        stubs: {
          RBtn: {
            props: ["disabled", "loading"],
            template:
              "<button v-bind='$attrs' :disabled='disabled' @click='$emit(\"click\")'><slot /></button>",
          },
          RProgressLinear: true,
          RSkeletonBlock: true,
        },
      },
    });

    for (const id of [5, 6]) {
      const row = wrapper.get(`[data-testid='pc-automation-row-${id}']`);
      expect(row.text()).toContain("Unbenannter Eintrag");
      expect(row.find("img").attributes("alt")).toBe("Unbenannter Eintrag");
      expect(row.findAll("button")[0].attributes("aria-label")).toContain(
        "Unbenannter Eintrag",
      );
    }

    await wrapper
      .get("[data-testid='pc-automation-row-5']")
      .findAll("button")[1]
      .trigger("click");
    expect(openMatcher).toHaveBeenCalledWith(
      expect.objectContaining({
        target: expect.objectContaining({ label: "Unbenannter Eintrag" }),
      }),
    );
  });

  it("surfaces rejected review actions without optimistic queue changes", async () => {
    mocks.store.items = [queueItem];
    mocks.accept.mockRejectedValueOnce({
      response: { data: { detail: "stale review" } },
    });
    const wrapper = mountQueue()!;

    await wrapper
      .findAll("[data-testid='pc-automation-row-4'] button")[0]
      .trigger("click");
    await flushPromises();

    expect(mocks.accept).toHaveBeenCalledWith(queueItem);
    expect(mocks.snackbar.error).toHaveBeenCalledWith(
      "stale review",
      expect.any(Object),
    );
  });

  it("enables batch acceptance only for the store-validated local group", () => {
    mocks.store.items = [queueItem];
    const unsafe = mountQueue()!;
    expect(
      unsafe.get(".r-v2-pc-automation__batch button").attributes("disabled"),
    ).toBeDefined();

    mocks.store.selectedGroupIsSafe = true;
    const safe = mountQueue()!;
    expect(
      safe.get(".r-v2-pc-automation__batch button").attributes("disabled"),
    ).toBeUndefined();
  });

  it("keeps the permitted queue tab in the route query and removes denied deep links", async () => {
    const wrapper = mount(Administration!.default, {
      global: {
        stubs: {
          RTabNav: {
            props: ["modelValue", "items"],
            template:
              '<button data-testid=\'automation-tab\' @click=\'$emit("update:modelValue", "pc-automation")\'>{{ items.map((item) => item.label).join(" ") }}</button>',
          },
          UsersSection: true,
          PermissionGroupsSection: true,
          TasksSection: true,
          PcAutomationQueue: true,
          CreateUserDialog: true,
          EditUserDialog: true,
          InviteLinkDialog: true,
          GroupFormDialog: true,
        },
      },
    });

    expect(wrapper.text()).toContain("settings.pc-automation.title");
    await wrapper.get("[data-testid='automation-tab']").trigger("click");
    await flushPromises();
    expect(mocks.router.replace).toHaveBeenCalledWith(
      expect.objectContaining({ query: { tab: "pc-automation" } }),
    );

    canReview.value = false;
    await flushPromises();
    expect(mocks.router.replace).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: { tab: "users" } }),
    );
  });
  it("renders each queue item as a structured review list row", () => {
    mocks.store.items = [queueItem];
    const wrapper = mountQueue()!;
    const row = wrapper.get("[data-testid='pc-automation-row-4']");
    const checkbox = row.get("[data-testid='pc-automation-select']");
    const content = row.get("[data-testid='pc-automation-content']");
    expect(row.get("[data-testid='pc-automation-title']").element.tagName).toBe(
      "H3",
    );
    expect(row.classes()).toContain("r-v2-pc-automation__row");
    expect(
      row.get("[data-testid='pc-automation-actions']").classes(),
    ).toContain("r-v2-pc-automation__actions");
    expect(
      checkbox.element.compareDocumentPosition(content.element) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    const sourceFields = row.findAll(
      "[data-testid='pc-automation-source-field']",
    );
    expect(sourceFields).toHaveLength(3);
    expect(
      sourceFields.map((field) =>
        field.find(".r-v2-pc-automation__source-label").text(),
      ),
    ).toEqual(["Source name:", "Source path:", "Main game:"]);
    expect(sourceFields.map((field) => field.text())).toEqual([
      "Source name: DLC/Road to the Black Sea",
      "Source path: pc/roms/Euro Truck Simulator 2/DLC/Road to the Black Sea",
      "Main game: Euro Truck Simulator 2",
    ]);
    expect(
      row.get("[data-testid='pc-automation-tags']").findAll(".r-chip"),
    ).toHaveLength(3);
    const reason = row.get("[data-testid='pc-automation-reason']");
    expect(reason.element.tagName).toBe("DETAILS");
    expect(reason.get("summary").text()).toContain(
      "settings.pc-automation.review-required",
    );
  });
});
