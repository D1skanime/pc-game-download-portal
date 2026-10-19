import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SetupRecoverySnapshot } from "@/__generated__";
import { useSetupRecovery } from "./index";

const fake = vi.hoisted(() => ({
  getStatus: vi.fn(),
  assignFolders: vi.fn(),
  createUser: vi.fn(),
  login: vi.fn(),
  refetch: vi.fn(),
  fetchHeartbeat: vi.fn(),
  fetchCurrentUser: vi.fn(),
  auth: { user: null as { id: number } | null },
  heartbeat: { value: { SYSTEM: { SHOW_SETUP_WIZARD: true } } },
}));
vi.mock("@/services/api/setup", () => ({ default: fake }));
vi.mock("@/v2/data/adapters/legacy/services/api/user", () => ({
  default: fake,
}));
vi.mock("@/v2/data/adapters/legacy/services/api/identity", () => ({
  default: fake,
}));
vi.mock("@/v2/data/adapters/legacy/services/api", () => ({
  refetchCSRFToken: fake.refetch,
}));
vi.mock("@/v2/data/adapters/legacy/stores/auth", () => ({
  default: () => ({
    get user() {
      return fake.auth.user;
    },
    fetchCurrentUser: fake.fetchCurrentUser,
  }),
}));
vi.mock("@/v2/data/adapters/legacy/stores/heartbeat", () => ({
  default: () => ({
    ...fake.heartbeat,
    fetchHeartbeat: fake.fetchHeartbeat,
  }),
}));
const mapping = {
  folder_name: "Windows",
  platform_slug: "win",
  mapping_id: 1,
  relative_path: "Windows",
};
function state(complete = false): SetupRecoverySnapshot {
  return {
    enrolled: true,
    setup_complete: complete,
    current_step: complete ? "complete" : "folders",
    saved_assignments: complete ? [mapping] : [],
    missing_assignments: [],
    root_health: { reachable: true, readable: true, non_writable: true },
    cause_code: null,
    next_action: complete ? "start_first_scan" : "assign_missing",
  };
}
const admin = () => ({
  username: "newadmin",
  email: "",
  password: "private-in-memory",
  repeatPassword: "private-in-memory",
});
describe("setup server reconciliation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fake.auth.user = null;
    fake.heartbeat.value.SYSTEM.SHOW_SETUP_WIZARD = true;
    fake.getStatus.mockResolvedValue({ data: state() });
    fake.createUser.mockResolvedValue({ data: { id: 1 } });
    fake.fetchCurrentUser.mockImplementation(async () => {
      fake.auth.user = { id: 1 };
    });
  });
  it("retains an enrolled account after response loss and requests login without a second create", async () => {
    fake.createUser.mockImplementation(async () => {
      fake.heartbeat.value.SYSTEM.SHOW_SETUP_WIZARD = false;
      throw new Error("response lost");
    });
    const recovery = useSetupRecovery();
    const draft = admin();
    await recovery.finish(draft, [mapping]);
    expect(recovery.loginRequired.value).toBe(true);
    await recovery.finish(draft, [mapping]);
    expect(fake.createUser).toHaveBeenCalledTimes(1);
    expect(fake.assignFolders).not.toHaveBeenCalled();
  });
  it("logs in once, clears passwords and reconciles a committed assignment response loss", async () => {
    const recovery = useSetupRecovery();
    const draft = admin();
    fake.assignFolders.mockImplementation(async () => {
      fake.getStatus.mockResolvedValue({ data: state(true) });
      throw new Error("response lost");
    });
    await recovery.finish(draft, [mapping]);
    expect(recovery.complete.value).toBe(true);
    expect(draft.password).toBe("");
    expect(draft.repeatPassword).toBe("");
    await recovery.finish(draft, [mapping]);
    expect(fake.createUser).toHaveBeenCalledTimes(1);
    expect(fake.assignFolders).toHaveBeenCalledTimes(1);
  });
  it("restores saved assignments and never repeats persisted work", async () => {
    fake.auth.user = { id: 1 };
    fake.getStatus.mockResolvedValue({ data: state(true) });
    const recovery = useSetupRecovery();
    await recovery.retryCheck();
    expect(recovery.mergeDraft({ Windows: null, Other: "dos" })).toEqual({
      Windows: "win",
      Other: "dos",
    });
    await recovery.finish(admin(), [mapping]);
    expect(fake.createUser).not.toHaveBeenCalled();
    expect(fake.assignFolders).not.toHaveBeenCalled();
  });
  it("retry check is read-only and retains root failure", async () => {
    fake.auth.user = { id: 1 };
    fake.getStatus.mockResolvedValue({
      data: { ...state(), cause_code: "root_unreadable" },
    });
    const recovery = useSetupRecovery();
    await recovery.retryCheck();
    expect(recovery.cause.value).toBe("root_unreadable");
    expect(fake.assignFolders).not.toHaveBeenCalled();
  });
});
