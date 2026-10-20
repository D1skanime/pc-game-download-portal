import { beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "@/stores/users";
import { resolveSetupRoute } from "./index";

const fake = vi.hoisted(() => ({ getStatus: vi.fn() }));
vi.mock("@/services/api/setup", () => ({ default: fake }));
const context = {
  route: "home",
  fullPath: "/",
  connected: true,
  showWizard: false,
  user: null as User | null,
};
describe("authenticated setup routing", () => {
  beforeEach(() => vi.clearAllMocks());
  it("sends anonymous recovery to login, preserving the return route", async () => {
    expect(await resolveSetupRoute({ ...context, route: "setup" })).toEqual({
      name: "login",
      query: { next: "/setup" },
    });
    expect(fake.getStatus).not.toHaveBeenCalled();
  });
  it("resumes an incomplete administrator and allows explicit completion", async () => {
    const user = { role: "admin" } as User;
    fake.getStatus.mockResolvedValue({ data: { setup_complete: false } });
    expect(await resolveSetupRoute({ ...context, user })).toEqual({
      name: "setup",
    });
    fake.getStatus.mockResolvedValue({ data: { setup_complete: true } });
    expect(
      await resolveSetupRoute({ ...context, user, route: "setup" }),
    ).toBeUndefined();
  });
  it("never queries admin recovery for a viewer or loops on an outage", async () => {
    expect(
      await resolveSetupRoute({
        ...context,
        route: "setup",
        user: { role: "user" } as User,
      }),
    ).toEqual({ name: "home" });
    expect(fake.getStatus).not.toHaveBeenCalled();
    fake.getStatus.mockRejectedValue(new Error("offline"));
    expect(
      await resolveSetupRoute({ ...context, user: { role: "admin" } as User }),
    ).toBeUndefined();
  });
});
