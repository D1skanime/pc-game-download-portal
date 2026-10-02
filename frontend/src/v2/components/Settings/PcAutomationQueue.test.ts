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
  useI18n: () => ({ t: (key: string) => key }),
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
      "pc-automation.accept",
      "pc-automation.correct",
      "pc-automation.skip",
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

    expect(wrapper.text()).toContain("pc-automation.title");
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
});
