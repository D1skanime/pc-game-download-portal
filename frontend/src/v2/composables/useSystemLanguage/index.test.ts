import { mount, flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, ref } from "vue";
import { createI18n } from "vue-i18n";
import { useSystemLanguage } from ".";

const mocks = vi.hoisted(() => ({
  update: vi.fn(),
  fetch: vi.fn(),
  save: vi.fn(),
  error: vi.fn(),
  auth: {
    user: { id: 1 } as { id: number } | null,
    scopes: ["platforms.write", "me.write"],
  },
  config: { CONFIG_FILE_WRITABLE: true, SCAN_LANGUAGE_PRIORITY: ["en"] },
}));
vi.mock("@/services/api/config", () => ({
  default: { updateScanLanguage: mocks.update },
}));
vi.mock("@/v2/data/adapters/legacy/stores/config", () => ({
  default: () => ({ config: mocks.config, fetchConfig: mocks.fetch }),
}));
vi.mock("@/v2/data/adapters/legacy/stores/auth", () => ({
  default: () => mocks.auth,
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ error: mocks.error }),
}));
vi.mock("@/composables/useUISettings", () => ({
  useUISettings: () => ({ locale: ref("en_US"), setLocale: mocks.save }),
}));
vi.mock("@/v2/data/adapters/legacy/stores/language", () => ({
  default: () => ({
    selectedLanguage: { value: "en_US", name: "English" },
    languages: ["en_US", "de_DE", "fr_FR"].map((value) => ({
      value,
      name: value,
    })),
  }),
}));

function setup() {
  const i18n = createI18n({
    legacy: false,
    locale: "en_US",
    missingWarn: false,
    fallbackWarn: false,
  });
  let language!: ReturnType<typeof useSystemLanguage>;
  const wrapper = mount(
    defineComponent({
      setup() {
        language = useSystemLanguage();
        return () => null;
      },
    }),
    { global: { plugins: [i18n] } },
  );
  return { language, wrapper, i18n };
}

describe("system language authority", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.auth.user = { id: 1 };
    mocks.auth.scopes = ["platforms.write", "me.write"];
    mocks.config.CONFIG_FILE_WRITABLE = true;
    mocks.config.SCAN_LANGUAGE_PRIORITY = ["en"];
    mocks.fetch.mockImplementation(async () => mocks.config);
    mocks.save.mockResolvedValue(true);
    mocks.update.mockImplementation(async (payload) => {
      mocks.config.SCAN_LANGUAGE_PRIORITY = payload.language_priority;
      return { data: { language_priority: payload.language_priority } };
    });
  });
  it("commits authorized global language with CAS before applying personal UI", async () => {
    const { language, wrapper, i18n } = setup();
    language.currentValue.value = "de_DE";
    await flushPromises();
    expect(mocks.update).toHaveBeenCalledWith({
      language_priority: ["de", "en"],
      expected_language_priority: ["en"],
    });
    expect(mocks.fetch).toHaveBeenCalled();
    expect(i18n.global.locale.value).toBe("de_DE");
    expect(mocks.save).toHaveBeenCalledWith("de_DE");
    wrapper.unmount();
  });
  it("keeps ME_WRITE personal and anonymous choices away from global config", async () => {
    mocks.auth.scopes = ["me.write"];
    const { language, wrapper, i18n } = setup();
    language.currentValue.value = "fr_FR";
    await flushPromises();
    expect(mocks.update).not.toHaveBeenCalled();
    expect(i18n.global.locale.value).toBe("fr_FR");
    expect(mocks.save).toHaveBeenCalledWith("fr_FR");
    wrapper.unmount();
  });
  it.each([409, 403, 500])(
    "retains acknowledged UI and reports config failure %i",
    async (status) => {
      mocks.update.mockRejectedValue({ response: { status } });
      const { language, wrapper, i18n } = setup();
      language.currentValue.value = "fr_FR";
      await flushPromises();
      expect(i18n.global.locale.value).toBe("en_US");
      expect(mocks.save).not.toHaveBeenCalled();
      expect(mocks.error).toHaveBeenCalled();
      wrapper.unmount();
    },
  );
  it("coalesces rapid choices and waits for acknowledged predecessor", async () => {
    let finish!: () => void;
    mocks.update.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = () => {
            mocks.config.SCAN_LANGUAGE_PRIORITY = ["de", "en"];
            resolve({ data: { language_priority: ["de", "en"] } });
          };
        }),
    );
    const { language, wrapper, i18n } = setup();
    language.currentValue.value = "de_DE";
    await flushPromises();
    language.currentValue.value = "en_US";
    language.currentValue.value = "fr_FR";
    await flushPromises();
    expect(mocks.update).toHaveBeenCalledTimes(1);
    finish();
    await flushPromises();
    expect(mocks.update).toHaveBeenLastCalledWith({
      language_priority: ["fr", "en", "de"],
      expected_language_priority: ["de", "en"],
    });
    expect(i18n.global.locale.value).toBe("fr_FR");
    expect(mocks.save).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });
  it("does not write globally after permission revocation during authority refresh", async () => {
    mocks.fetch.mockImplementationOnce(async () => {
      mocks.auth.scopes = ["me.write"];
      return mocks.config;
    });
    const { language, wrapper, i18n } = setup();
    language.currentValue.value = "de_DE";
    await flushPromises();
    expect(mocks.update).not.toHaveBeenCalled();
    expect(i18n.global.locale.value).toBe("en_US");
    expect(mocks.error).toHaveBeenCalled();
    wrapper.unmount();
  });
  it("retains global commit on profile failure and exposes that failure separately", async () => {
    mocks.save.mockResolvedValue(false);
    const { language, wrapper, i18n } = setup();
    language.currentValue.value = "fr_FR";
    await flushPromises();
    expect(mocks.config.SCAN_LANGUAGE_PRIORITY[0]).toBe("fr");
    expect(mocks.update).toHaveBeenCalledTimes(1);
    expect(i18n.global.locale.value).toBe("fr_FR");
    expect(mocks.error).toHaveBeenCalledWith(
      "settings.language: settings.failed",
    );
    wrapper.unmount();
  });
  it("allows anonymous local choice without a shared write", async () => {
    mocks.auth.user = null;
    mocks.auth.scopes = [];
    const { language, wrapper, i18n } = setup();
    language.currentValue.value = "de_DE";
    await flushPromises();
    expect(mocks.update).not.toHaveBeenCalled();
    expect(i18n.global.locale.value).toBe("de_DE");
    wrapper.unmount();
  });
  it.each(["unmount", "user-change"])(
    "ignores stale config callbacks after %s",
    async (change) => {
      let finish!: () => void;
      mocks.update.mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finish = () =>
              resolve({ data: { language_priority: ["de", "en"] } });
          }),
      );
      const { language, wrapper, i18n } = setup();
      language.currentValue.value = "de_DE";
      await flushPromises();
      if (change === "unmount") wrapper.unmount();
      else mocks.auth.user = { id: 2 };
      finish();
      await flushPromises();
      expect(mocks.save).not.toHaveBeenCalled();
      expect(i18n.global.locale.value).toBe("en_US");
      wrapper.unmount();
    },
  );
  it("rejects readonly config without applying UI and retries after a refetch", async () => {
    mocks.config.CONFIG_FILE_WRITABLE = false;
    const { language, wrapper, i18n } = setup();
    language.currentValue.value = "de_DE";
    await flushPromises();
    expect(mocks.update).not.toHaveBeenCalled();
    expect(i18n.global.locale.value).toBe("en_US");
    mocks.config.CONFIG_FILE_WRITABLE = true;
    language.currentValue.value = "fr_FR";
    await flushPromises();
    expect(i18n.global.locale.value).toBe("fr_FR");
    wrapper.unmount();
  });
  it("keeps an acknowledged predecessor when the newest queued selection fails", async () => {
    let finish!: () => void;
    mocks.update
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finish = () => {
              mocks.config.SCAN_LANGUAGE_PRIORITY = ["de", "en"];
              resolve({ data: { language_priority: ["de", "en"] } });
            };
          }),
      )
      .mockRejectedValueOnce(new Error("conflict"));
    const { language, wrapper, i18n } = setup();
    language.currentValue.value = "de_DE";
    await flushPromises();
    language.currentValue.value = "fr_FR";
    finish();
    await flushPromises();
    expect(i18n.global.locale.value).toBe("de_DE");
    expect(mocks.config.SCAN_LANGUAGE_PRIORITY).toEqual(["de", "en"]);
    expect(mocks.save).toHaveBeenCalledWith("de_DE");
    wrapper.unmount();
  });
});
