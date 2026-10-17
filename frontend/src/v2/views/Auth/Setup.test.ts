import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Setup from "./Setup.vue";

const mocks = vi.hoisted(() => ({
  router: { push: vi.fn() },
  createUser: vi.fn(),
  login: vi.fn(),
  discoverFolders: vi.fn(),
  assignFolders: vi.fn(),
  fetchCurrentUser: vi.fn(),
  fetchHeartbeat: vi.fn(),
  refetchCSRFToken: vi.fn(),
}));
vi.mock("vue-i18n", () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRouter: () => mocks.router,
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ warning: vi.fn(), error: vi.fn(), info: vi.fn() }),
}));
vi.mock("@/services/api/setup", () => ({
  default: {
    discoverFolders: mocks.discoverFolders,
    assignFolders: mocks.assignFolders,
  },
}));
vi.mock("@/v2/data/adapters/legacy/services/api/user", () => ({
  default: { createUser: mocks.createUser },
}));
vi.mock("@/v2/data/adapters/legacy/services/api/identity", () => ({
  default: { login: mocks.login },
}));
vi.mock("@/v2/data/adapters/legacy/services/api", () => ({
  refetchCSRFToken: mocks.refetchCSRFToken,
}));
vi.mock("@/v2/data/adapters/legacy/stores/auth", () => ({
  default: () => ({ fetchCurrentUser: mocks.fetchCurrentUser }),
}));
vi.mock("@/v2/data/adapters/legacy/stores/heartbeat", () => ({
  default: () => ({ fetchHeartbeat: mocks.fetchHeartbeat }),
}));

type SetupVm = {
  step: 1 | 2 | 3;
  adminUser: {
    username: string;
    email: string;
    password: string;
    repeatPassword: string;
  };
  adminFormValid: boolean;
  folderDraft: Record<string, string | null>;
};
const discovery = {
  root_label: "Games",
  folders: [
    {
      name: "Known",
      relative_path: "Known",
      association: "known",
      suggested_platform: "windows",
    },
    {
      name: "Mystery",
      relative_path: "Mystery",
      association: "unknown",
      suggested_platform: null,
    },
  ],
  platform_options: [
    { slug: "windows", display_name: "Windows" },
    { slug: "linux", display_name: "Linux" },
  ],
};

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
  const vm = wrapper.vm as Partial<SetupVm> as SetupVm;
  vm.step = 3;
  vm.adminUser = {
    username: "admin",
    email: "admin@example.test",
    password: "password123",
    repeatPassword: "password123",
  };
  vm.adminFormValid = true;
  return wrapper;
}
beforeEach(() => {
  vi.clearAllMocks();
  mocks.discoverFolders.mockResolvedValue({ data: discovery });
  mocks.createUser.mockResolvedValue({ data: { id: 7 } });
  mocks.login.mockResolvedValue({});
  mocks.refetchCSRFToken.mockResolvedValue(undefined);
  mocks.fetchCurrentUser.mockResolvedValue(undefined);
  mocks.fetchHeartbeat.mockResolvedValue(undefined);
});
describe("setup folder assignment flow", () => {
  it("discovers folders and does not finish with an incomplete draft", async () => {
    const wrapper = mountSetup();
    await flushPromises();
    expect(mocks.discoverFolders).toHaveBeenCalledOnce();
    await wrapper.findAll("button").at(-1)?.trigger("click");
    await flushPromises();
    expect(mocks.assignFolders).not.toHaveBeenCalled();
    expect(mocks.router.push).not.toHaveBeenCalled();
  });
  it("authenticates, assigns once, and continues only when the server is ready", async () => {
    mocks.assignFolders.mockResolvedValue({
      data: {
        ready: true,
        mappings: [],
        root_health: { reachable: true, readable: true, non_writable: true },
      },
    });
    const wrapper = mountSetup();
    await flushPromises();
    const vm = wrapper.vm as Partial<SetupVm> as SetupVm;
    vm.folderDraft = { Known: "windows", Mystery: "linux" };
    await wrapper.findAll("button").at(-1)?.trigger("click");
    await flushPromises();
    expect(mocks.assignFolders).toHaveBeenCalledWith([
      { folder_name: "Known", platform_slug: "windows" },
      { folder_name: "Mystery", platform_slug: "linux" },
    ]);
    expect(mocks.router.push).toHaveBeenCalledWith({ name: "home" });
  });
  it("assigns the read-only library before bootstrapping legacy platform state", async () => {
    const events: string[] = [];
    mocks.fetchCurrentUser.mockImplementation(async () => {
      events.push("current-user");
    });
    mocks.fetchHeartbeat.mockImplementation(async () => {
      events.push("heartbeat");
    });
    mocks.assignFolders.mockImplementation(async () => {
      events.push("assign");
      return {
        data: {
          ready: true,
          mappings: [],
          root_health: { reachable: true, readable: true, non_writable: true },
        },
      };
    });
    const wrapper = mountSetup();
    await flushPromises();
    const vm = wrapper.vm as Partial<SetupVm> as SetupVm;
    vm.folderDraft = { Known: "windows", Mystery: "linux" };
    await wrapper.findAll("button").at(-1)?.trigger("click");
    await flushPromises();
    expect(events.indexOf("assign")).toBeLessThan(
      events.indexOf("current-user"),
    );
  });
  it("keeps the draft and route unchanged when assignment is not ready", async () => {
    mocks.assignFolders.mockResolvedValue({
      data: {
        ready: false,
        mappings: [],
        root_health: { reachable: true, readable: true, non_writable: false },
      },
    });
    const wrapper = mountSetup();
    await flushPromises();
    const vm = wrapper.vm as Partial<SetupVm> as SetupVm;
    vm.folderDraft = { Known: "windows", Mystery: "linux" };
    await wrapper.findAll("button").at(-1)?.trigger("click");
    await flushPromises();
    expect(mocks.router.push).not.toHaveBeenCalled();
    expect(vm.folderDraft).toEqual({ Known: "windows", Mystery: "linux" });
  });
});
