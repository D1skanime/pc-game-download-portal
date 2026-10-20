import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import { createI18n } from "vue-i18n";
import Setup from "./Setup.vue";

const fake = vi.hoisted(() => ({
  discoverFolders: vi.fn(),
  retryCheck: vi.fn(),
  finish: vi.fn(),
  push: vi.fn(),
  scan: vi.fn(),
}));
const complete = ref(false),
  cause = ref<string | null>(null),
  loginRequired = ref(false),
  enrolled = ref(false);
vi.mock("@/plugins/router", () => ({
  ROUTES: { LOGIN: "login", SCAN: "scan" },
}));
vi.mock("vue-router", () => ({ useRouter: () => ({ push: fake.push }) }));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ error: vi.fn() }),
}));
vi.mock("@/services/api/setup", () => ({
  default: { discoverFolders: fake.discoverFolders },
}));
vi.mock("@/v2/composables/useSetupRecovery", () => ({
  useSetupRecovery: () => ({
    complete,
    cause,
    loginRequired,
    enrolled,
    busy: ref(false),
    retryCheck: fake.retryCheck,
    finish: fake.finish,
    mergeDraft: (draft: object) => draft,
  }),
}));
const namespaces = import.meta.glob<Record<string, string>>(
  "../../../locales/*/setup.json",
  { eager: true, import: "default" },
);
const locales = process.env.PGDP_TEST_LOCALES?.split(",") ?? ["en_US", "de_DE"];
const stubs = {
  RBtn: {
    props: ["disabled", "to"],
    template:
      '<button :disabled="disabled" :data-route="to?.name"><slot /></button>',
  },
  RAlert: { template: '<div role="alert"><slot /></div>' },
  RSteps: true,
  RSpinner: true,
  RIcon: true,
  SetupStepAdmin: true,
  SetupStepMetadata: true,
  SetupStepPlatforms: {
    props: ["draft"],
    emits: ["update:draft"],
    template:
      "<button data-testid=\"assign\" @click=\"$emit('update:draft', { Windows: 'win' })\">Assign</button>",
  },
};
function mountSetup(locale = "en_US") {
  const dictionary = namespaces["../../../locales/" + locale + "/setup.json"];
  expect(dictionary, "missing real setup locale " + locale).toBeTruthy();
  return mount(Setup, {
    global: {
      stubs,
      plugins: [
        createI18n({
          legacy: false,
          locale,
          fallbackLocale: false,
          messages: {
            [locale]: { setup: dictionary, common: { "try-again": "Retry" } },
          },
        }),
      ],
    },
  });
}
beforeEach(() => {
  vi.clearAllMocks();
  complete.value = false;
  cause.value = null;
  loginRequired.value = false;
  enrolled.value = true;
  fake.discoverFolders.mockResolvedValue({
    data: {
      root_label: "Games",
      folders: [
        {
          name: "Windows",
          relative_path: "Windows",
          association: "known",
          suggested_platform: "win",
        },
      ],
      platform_options: [{ slug: "win", display_name: "Windows" }],
    },
  });
});
describe("mounted setup recovery", () => {
  it.each(locales)(
    "renders real recovery copy and accessible actions in %s",
    async (locale) => {
      complete.value = true;
      const panel = mountSetup(locale);
      await flushPromises();
      expect(panel.text()).toContain(
        namespaces["../../../locales/" + locale + "/setup.json"][
          "recovery-complete"
        ],
      );
      expect(panel.find('button[data-route="scan"]').exists()).toBe(true);
      expect(fake.scan).not.toHaveBeenCalled();
      complete.value = false;
      cause.value = "root_unreadable";
      await flushPromises();
      expect(panel.get('[role="alert"]').text()).toContain(
        namespaces["../../../locales/" + locale + "/setup.json"][
          "recovery-root"
        ],
      );
      expect(panel.text()).not.toContain("setup.recovery-");
      panel.unmount();
    },
  );
  it("finishes existing setup without account form or automatic navigation/scan", async () => {
    const panel = mountSetup();
    await flushPromises();
    await panel
      .findAll("button")
      .find((button) => button.text() === "Next")!
      .trigger("click");
    await panel
      .findAll("button")
      .find((button) => button.text() === "Finish")!
      .trigger("click");
    await flushPromises();
    expect(fake.finish).toHaveBeenCalledTimes(1);
    expect(fake.push).not.toHaveBeenCalled();
    expect(fake.scan).not.toHaveBeenCalled();
    panel.unmount();
  });
  it("keeps persistent errors, supports GET-only retry, and links enrollment recovery to login", async () => {
    cause.value = "root_unreadable";
    loginRequired.value = true;
    const panel = mountSetup();
    await flushPromises();
    expect(panel.find('button[data-route="login"]').exists()).toBe(true);
    await panel
      .findAll("button")
      .find((button) => button.text() === "Retry check")!
      .trigger("click");
    await flushPromises();
    expect(fake.retryCheck).toHaveBeenCalledTimes(2);
    expect(panel.get('[role="status"]').text()).toContain("already exists");
    expect(panel.get('[role="alert"]').text()).toContain("root");
    expect(fake.finish).not.toHaveBeenCalled();
    panel.unmount();
  });
});
