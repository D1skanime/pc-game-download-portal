import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref } from "vue";
import RDialog from "@/v2/lib/overlays/RDialog/RDialog.vue";
import { closeTopEscapable } from "@/v2/lib/overlays/RDialog/escapeStack";
import LocalizedDescriptionEditor from "./LocalizedDescriptionEditor.vue";

const mocks = vi.hoisted(() => ({
  rom: vi.fn(),
  component: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
}));
const language = ref("de_DE");
vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    locale: language,
    availableLocales: ["de_DE", "fr_FR", "en_US"],
    t: (key: string, params?: Record<string, string>) =>
      key + (params ? JSON.stringify(params) : ""),
  }),
}));
vi.mock("@/v2/data/adapters/legacy/services/api/rom", () => ({
  default: {
    updateManualDescription: mocks.rom,
    updatePcComponentManualDescription: mocks.component,
  },
}));
vi.mock("@/v2/composables/useSnackbar", () => ({ useSnackbar: () => mocks }));

const stubs = {
  RBtn: {
    name: "RBtn",
    emits: ["click"],
    props: ["disabled", "loading"],
    template:
      "<button :disabled='disabled' :aria-busy='loading' @click='$emit(\"click\")'><slot /></button>",
  },
  RSelect: {
    name: "RSelect",
    props: ["modelValue", "disabled", "items", "label"],
    template:
      "<select :value='modelValue' :disabled='disabled' :aria-label='label' @change='$emit(\"update:modelValue\", $event.target.value)'><option v-for='item in items' :key='item'>{{ item }}</option></select>",
  },
  RTextField: {
    name: "RTextField",
    props: ["modelValue", "disabled", "hint", "label"],
    template:
      "<label>{{ label }}<textarea :value='modelValue' :disabled='disabled' @input='$emit(\"update:modelValue\", $event.target.value)' /><span>{{ hint }}</span></label>",
  },
};
const wrappers: ReturnType<typeof mount>[] = [];
function setup(props = {}) {
  const wrapper = mount(LocalizedDescriptionEditor, {
    attachTo: document.body,
    props: {
      romId: 41,
      expectedVersion: "v1",
      canEdit: true,
      provider: "steam",
      ...props,
    },
    global: { stubs },
  });
  wrappers.push(wrapper);
  return wrapper;
}
function button(wrapper: ReturnType<typeof setup>, action: string) {
  return wrapper
    .findAll("button")
    .find((item) => item.text() === "rom.description-" + action)!;
}
function deferred() {
  let resolve!: (value: {
    data: {
      locale: string;
      description: string | null;
      expected_version: string;
    };
  }) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<{
    data: {
      locale: string;
      description: string | null;
      expected_version: string;
    };
  }>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
beforeEach(() => {
  vi.clearAllMocks();
  language.value = "de_DE";
});
afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount();
});

describe("localized description editor", () => {
  it("never previews legacy scalar or copies English/base fallback into the exact draft", () => {
    const wrapper = setup({
      fallbackDescription: "Forbidden legacy",
      manualMetadata: {
        descriptions: { de: "Base manual", en: "English manual" },
      },
    });
    expect(wrapper.get("textarea").element.value).toBe("");
    expect(wrapper.text()).not.toContain("Forbidden legacy");
    expect(wrapper.text()).toContain("Base manual");
    expect(wrapper.text()).toContain("rom.description-source-localized");
    expect(button(wrapper, "save").attributes("disabled")).toBeDefined();
  });
  it("renders safe ScreenScraper French preview with actual language and source", () => {
    const wrapper = setup({
      provider: "screenscraper",
      ssMetadata: {
        text_variants: {
          fr: {
            source_language: "fr",
            summary: "<img src=x onerror=alert(1)>",
          },
        },
      },
    });
    language.value = "fr_FR";
    return flushPromises().then(() => {
      expect(wrapper.text()).toContain("ScreenScraper");
      expect(wrapper.text()).toContain("<img src=x onerror=alert(1)>");
      expect(wrapper.find("img").exists()).toBe(false);
      expect(
        wrapper.get("[data-testid='description-preview']").attributes("lang"),
      ).toBe("fr");
      expect(wrapper.get("textarea").element.value).toBe("");
    });
  });
  it("shows explicit English fallback and keeps the German draft empty", () => {
    const wrapper = setup({
      steamMetadata: {
        text_variants: {
          en: { source_language: "english", summary: "English provider" },
        },
      },
    });
    expect(wrapper.text()).toContain("rom.description-language-fallback");
    expect(
      wrapper.get("[data-testid='description-preview']").attributes("lang"),
    ).toBe("en");
    expect(wrapper.get("textarea").element.value).toBe("");
  });
  it.each(["de", "fr"])(
    "prefers %s provider over manual English without mutating it",
    async (tag) => {
      language.value = tag;
      const manualMetadata = { descriptions: { en: "  Protected English  " } };
      const wrapper = setup({
        manualMetadata,
        steamMetadata: {
          text_variants: {
            [tag]: {
              source_language: tag === "de" ? "german" : "french",
              summary: "Requested provider",
            },
          },
        },
      });
      expect(wrapper.text()).toContain("Requested provider");
      expect(wrapper.get("textarea").element.value).toBe("");
      expect(manualMetadata.descriptions.en).toBe("  Protected English  ");
    },
  );
  it("blocks dirty locale changes, retains text and original version across refresh", async () => {
    const request = deferred();
    mocks.rom.mockReturnValueOnce(request.promise);
    const wrapper = setup({
      manualMetadata: { descriptions: { "de-DE": "Original" } },
    });
    await wrapper.get("textarea").setValue("Draft");
    expect(wrapper.get("select").attributes("disabled")).toBeDefined();
    wrapper
      .getComponent({ name: "RSelect" })
      .vm.$emit("update:modelValue", "fr-FR");
    language.value = "en_US";
    await wrapper.setProps({
      expectedVersion: "v2",
      manualMetadata: { descriptions: { "de-DE": "Remote" } },
    });
    await button(wrapper, "save").trigger("click");
    expect(mocks.rom).toHaveBeenCalledWith({
      romId: 41,
      payload: {
        locale: "de-DE",
        description: "Draft",
        expected_version: "v1",
      },
    });
    expect(wrapper.get("textarea").element.value).toBe("Draft");
    expect(button(wrapper, "save").attributes("disabled")).toBeDefined();
    expect(wrapper.get("textarea").attributes("disabled")).toBeDefined();
    request.resolve({
      data: { locale: "de-DE", description: "Draft", expected_version: "v3" },
    });
    await flushPromises();
    expect(wrapper.emitted("saved")).toEqual([["de-DE", "Draft"]]);
  });
  it("retains draft on conflict/failure and cancel restores the original baseline", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    mocks.rom.mockRejectedValueOnce(new Error("409"));
    const wrapper = setup({
      manualMetadata: { descriptions: { "de-DE": "Original" } },
    });
    await wrapper.get("textarea").setValue("Draft");
    await button(wrapper, "save").trigger("click");
    await flushPromises();
    expect(wrapper.get("textarea").element.value).toBe("Draft");
    expect(wrapper.emitted("saved")).toBeUndefined();
    expect(mocks.error).toHaveBeenCalledOnce();
    const cancel = button(wrapper, "cancel");
    cancel.element.focus();
    await cancel.trigger("click");
    expect(wrapper.get("textarea").element.value).toBe("Original");
    expect(document.activeElement).toBe(cancel.element);
    vi.restoreAllMocks();
  });
  it("clears only exact manual entry via the existing component update adapter", async () => {
    const manualMetadata = {
      descriptions: { "de-DE": "Exact", de: "Base", en: "English" },
    };
    mocks.component.mockResolvedValueOnce({
      data: { locale: "de-DE", description: null, expected_version: "v2" },
    });
    const wrapper = setup({ componentId: 7, manualMetadata });
    expect(button(wrapper, "reset").attributes("disabled")).toBeUndefined();
    await button(wrapper, "reset").trigger("click");
    await button(wrapper, "save").trigger("click");
    await flushPromises();
    expect(mocks.component).toHaveBeenCalledWith({
      romId: 41,
      componentId: 7,
      payload: { locale: "de-DE", description: null, expected_version: "v1" },
    });
    expect(manualMetadata.descriptions).toEqual({
      "de-DE": "Exact",
      de: "Base",
      en: "English",
    });
  });
  it("ignores old entity response and resets draft ownership", async () => {
    const old = deferred();
    mocks.rom.mockReturnValueOnce(old.promise);
    const wrapper = setup();
    await wrapper.get("textarea").setValue("Old draft");
    await button(wrapper, "save").trigger("click");
    await wrapper.setProps({
      romId: 42,
      manualMetadata: { descriptions: { "de-DE": "New baseline" } },
      expectedVersion: "v9",
    });
    expect(wrapper.get("textarea").element.value).toBe("New baseline");
    await wrapper.get("textarea").setValue("New draft");
    old.resolve({
      data: {
        locale: "de-DE",
        description: "Old draft",
        expected_version: "v2",
      },
    });
    await flushPromises();
    expect(wrapper.get("textarea").element.value).toBe("New draft");
    expect(wrapper.emitted("saved")).toBeUndefined();
    expect(mocks.success).not.toHaveBeenCalled();
  });
  it("does not authorize save without edit scope or captured version", async () => {
    const wrapper = setup({ canEdit: false, expectedVersion: null });
    expect(wrapper.get("textarea").attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("rom.description-read-only");
    wrapper
      .getComponent({ name: "RTextField" })
      .vm.$emit("update:modelValue", "Bypass");
    await flushPromises();
    wrapper.findAllComponents({ name: "RBtn" })[2].vm.$emit("click");
    await flushPromises();
    expect(mocks.rom).not.toHaveBeenCalled();
  });
});

it("restores attached trigger focus after an exact-only clear becomes empty", async () => {
  mocks.rom.mockResolvedValueOnce({
    data: { locale: "de-DE", description: null, expected_version: "v2" },
  });
  const Harness = defineComponent({
    setup() {
      const open = ref(false);
      return () =>
        h("div", [
          h(
            "button",
            {
              "data-testid": "stable-edit-trigger",
              onClick: () => {
                open.value = true;
              },
            },
            "Edit",
          ),
          h(
            RDialog,
            {
              modelValue: open.value,
              "onUpdate:modelValue": (value: boolean) => {
                open.value = value;
              },
            },
            {
              content: () =>
                h(LocalizedDescriptionEditor, {
                  romId: 41,
                  expectedVersion: "v1",
                  canEdit: true,
                  provider: null,
                  manualMetadata: { descriptions: { "de-DE": "Exact only" } },
                  onSaved: () => {
                    open.value = false;
                  },
                }),
            },
          ),
        ]);
    },
  });
  const wrapper = mount(Harness, {
    attachTo: document.body,
    global: { stubs },
  });
  wrappers.push(wrapper);
  const trigger = wrapper.get<HTMLButtonElement>(
    "[data-testid='stable-edit-trigger']",
  );
  trigger.element.focus();
  await trigger.trigger("click");
  await flushPromises();
  const action = (name: string) =>
    Array.from(document.querySelectorAll<HTMLButtonElement>("button")).find(
      (element) => element.textContent === "rom.description-" + name,
    )!;
  expect(document.activeElement).not.toBe(trigger.element);
  action("reset").click();
  await flushPromises();
  action("save").click();
  await flushPromises();
  expect(document.activeElement).toBe(trigger.element);
  expect(trigger.element.isConnected).toBe(true);
  await trigger.trigger("click");
  await flushPromises();
  window.dispatchEvent(
    new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
  );
  await flushPromises();
  expect(document.activeElement).toBe(trigger.element);
  await trigger.trigger("click");
  await flushPromises();
  closeTopEscapable();
  await flushPromises();
  expect(document.activeElement).toBe(trigger.element);

  expect(mocks.rom).toHaveBeenCalledWith({
    romId: 41,
    payload: { locale: "de-DE", description: null, expected_version: "v1" },
  });
});
