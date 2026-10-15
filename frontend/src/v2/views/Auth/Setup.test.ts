import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Setup from "./Setup.vue";

const {
  router,
  createUser,
  login,
  updateUser,
  bootstrapLegacy,
  fetchCurrentUser,
  fetchHeartbeat,
  refetchCSRFToken,
} = vi.hoisted(() => ({
  router: { push: vi.fn() },
  createUser: vi.fn(),
  login: vi.fn(),
  updateUser: vi.fn(),
  bootstrapLegacy: vi.fn(),
  fetchCurrentUser: vi.fn(),
  fetchHeartbeat: vi.fn(),
  refetchCSRFToken: vi.fn(),
}));

vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRouter: () => router,
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ warning: vi.fn(), error: vi.fn(), info: vi.fn() }),
}));
vi.mock("@/v2/data/adapters/legacy/services/api/setup", () => ({
  default: { getLibraryInfo: vi.fn().mockResolvedValue({ data: null }) },
}));
vi.mock("@/v2/data/adapters/legacy/services/api/user", () => ({
  default: { createUser, updateUser },
}));
vi.mock("@/v2/data/adapters/legacy/services/api/identity", () => ({
  default: { login },
}));
vi.mock("@/v2/data/adapters/legacy/services/api", () => ({ refetchCSRFToken }));
vi.mock("@/v2/data/adapters/legacy/stores/auth", () => ({
  default: () => ({ fetchCurrentUser }),
}));
vi.mock("@/v2/data/adapters/legacy/stores/heartbeat", () => ({
  default: () => ({ fetchHeartbeat }),
}));
vi.mock("@/services/api/storage", () => ({ default: { bootstrapLegacy } }));

function mountSetup() {
  const wrapper = mount(Setup, {
    global: {
      stubs: {
        SetupStepPlatforms: true,
        SetupStepAdmin: true,
        SetupStepMetadata: true,
        RImg: true,
        RSteps: true,
        RSpinner: true,
        RIcon: true,
        RBtn: {
          props: ["disabled", "loading"],
          template: '<button :disabled="disabled"><slot /></button>',
        },
      },
    },
  });
  wrapper.vm.step = 3;
  wrapper.vm.adminUser = {
    username: "admin",
    email: "admin@example.test",
    password: "password123",
    repeatPassword: "password123",
  };
  wrapper.vm.adminFormValid = true;
  return wrapper;
}

beforeEach(() => {
  vi.clearAllMocks();
  createUser.mockResolvedValue({ data: { id: 7 } });
  login.mockResolvedValue({});
  updateUser.mockResolvedValue({});
  refetchCSRFToken.mockResolvedValue(undefined);
  fetchCurrentUser.mockResolvedValue(undefined);
  fetchHeartbeat.mockResolvedValue(undefined);
  bootstrapLegacy.mockResolvedValue({
    data: {
      storage_root: { name: "Games" },
      mappings: [
        { platform_id: 42, platform_fs_slug: "win", relative_path: "pc" },
      ],
    },
  });
});

describe("fresh setup storage handoff", () => {
  it("authenticates, refreshes session state, bootstraps, and opens the server mapping", async () => {
    const wrapper = mountSetup();
    await wrapper.vm.$nextTick();
    await wrapper.findAll("button").at(-1)?.trigger("click");
    await flushPromises();
    expect(createUser).toHaveBeenCalledOnce();
    expect(login).toHaveBeenCalledWith("admin", "password123");
    expect(refetchCSRFToken).toHaveBeenCalledOnce();
    expect(fetchCurrentUser).toHaveBeenCalledOnce();
    expect(fetchHeartbeat).toHaveBeenCalledOnce();
    expect(bootstrapLegacy).toHaveBeenCalledOnce();
    expect(router.push).toHaveBeenCalledWith({
      name: "platform-storage-mapping",
      params: { platformId: 42 },
    });
    expect(router.push).not.toHaveBeenCalledWith({ name: "home" });
    expect(router.push).not.toHaveBeenCalledWith({ name: "login" });
  });

  it("keeps setup retryable when bootstrap returns no mapping", async () => {
    bootstrapLegacy.mockResolvedValueOnce({
      data: { storage_root: { name: "Games" }, mappings: [] },
    });
    const wrapper = mountSetup();
    await wrapper.vm.$nextTick();
    await wrapper.findAll("button").at(-1)?.trigger("click");
    await flushPromises();
    expect(router.push).not.toHaveBeenCalled();
    expect(wrapper.vm.submitting).toBe(false);
  });
});
