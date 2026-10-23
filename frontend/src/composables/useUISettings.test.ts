import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";

const mocks = vi.hoisted(() => ({
  update: vi.fn(),
  fetch: vi.fn(),
  auth: {} as {
    user: { id: number; ui_settings?: Record<string, string> } | null;
    setCurrentUser: ReturnType<typeof vi.fn>;
  },
}));
vi.mock("@/services/api/user", () => ({
  default: { updateUser: mocks.update, fetchCurrentUser: mocks.fetch },
}));
vi.mock("@/stores/auth", () => ({ default: () => mocks.auth }));
vi.mock("pinia", () => ({
  storeToRefs: (store: typeof mocks.auth) => ({
    user: {
      get value() {
        return store.user;
      },
    },
  }),
}));

describe("explicit locale profile persistence", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.resetAllMocks();
    localStorage.clear();
    mocks.auth = reactive({ user: { id: 1 }, setCurrentUser: vi.fn() });
  });
  it("saves once despite the existing local preference watcher", async () => {
    mocks.update.mockResolvedValue({
      data: { id: 1, ui_settings: { locale: "fr_FR" } },
    });
    const { useUISettings } = await import("./useUISettings");
    const settings = useUISettings();
    expect(await settings.setLocale("fr_FR")).toBe(true);
    await flushPromises();
    expect(mocks.update).toHaveBeenCalledTimes(1);
    expect(JSON.parse(mocks.update.mock.calls[0][0].ui_settings).locale).toBe(
      "fr_FR",
    );
  });
  it("returns profile failure while preserving the acknowledged local preference", async () => {
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    mocks.update.mockRejectedValue(new Error("profile unavailable"));
    mocks.fetch.mockResolvedValue({
      data: { id: 1, ui_settings: { locale: "en_US" } },
    });
    const { useUISettings } = await import("./useUISettings");
    const settings = useUISettings();
    expect(await settings.setLocale("de_DE")).toBe(false);
    expect(settings.locale.value).toBe("de_DE");
    expect(mocks.fetch).toHaveBeenCalledTimes(1);
    expect(mocks.auth.setCurrentUser).toHaveBeenCalledWith({
      id: 1,
      ui_settings: { locale: "en_US" },
    });
    log.mockRestore();
  });
  it("does not publish a previous identity's profile response", async () => {
    let finish!: () => void;
    mocks.update.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = () =>
            resolve({ data: { id: 1, ui_settings: { locale: "de_DE" } } });
        }),
    );
    const { useUISettings } = await import("./useUISettings");
    const settings = useUISettings();
    const saving = settings.setLocale("de_DE");
    await flushPromises();
    mocks.auth.user = { id: 2 };
    finish();
    expect(await saving).toBe(false);
    expect(mocks.auth.setCurrentUser).not.toHaveBeenCalled();
  });
});
