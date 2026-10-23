import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed, defineComponent, nextTick, ref } from "vue";
import { createI18n } from "vue-i18n";
import { useScanProviders } from ".";

vi.mock("@/v2/data/adapters/legacy/stores/heartbeat", () => ({
  default: () => ({
    value: {
      METADATA_SOURCES: {
        HASHEOUS_API_ENABLED: true,
        PLAYMATCH_API_ENABLED: true,
      },
    },
    getMetadataOptionsByPriority: () =>
      ["igdb", "ra", "gamelist", "hasheous", "playmatch"].map((value) => ({
        value,
        name: value,
        logo_path: "",
        disabled: "",
      })),
    getEnabledMetadataOptions: () => [],
  }),
}));

const selection = vi.hoisted(() => ({ select: vi.fn() }));
vi.mock("@/v2/composables/useSystemLanguage", () => ({
  useSystemLanguage: () => ({
    currentValue: {
      set value(next: string) {
        selection.select(next);
      },
    },
  }),
}));

function setup(initialLocale = "en") {
  const hashes = ref(true);
  const i18n = createI18n({
    legacy: false,
    locale: initialLocale,
    messages: {
      fr_FR: {},
      en: {
        scan: {
          "requires-hashes": "Hashes required: {source}",
          "disabled-by-admin": "Disabled",
          "playmatch-requires-igdb": "IGDB required",
        },
      },
    },
    missingWarn: false,
    fallbackWarn: false,
  });
  let providers!: ReturnType<typeof useScanProviders>;
  const wrapper = mount(
    defineComponent({
      setup() {
        providers = useScanProviders(computed(() => hashes.value));
        return () => null;
      },
    }),
    {
      global: {
        plugins: [i18n],
      },
    },
  );
  return { providers, hashes, wrapper, i18n };
}

describe("scan provider selection", () => {
  beforeEach(() => {
    localStorage.clear();
    selection.select.mockReset();
  });
  it("materializes each enabled All group and permits explicit discovery without providers", () => {
    const { providers, wrapper } = setup();
    expect(
      providers.effectiveMetadataSources.value.map((source) => source.value),
    ).toEqual(["igdb", "gamelist", "ra"]);
    providers.generalAllSelected.value = false;
    providers.specificAllSelected.value = false;
    expect(providers.effectiveMetadataSources.value).toEqual([]);
    wrapper.unmount();
  });
  it("gates hash matchers by hashing and IGDB selection", async () => {
    const { providers, hashes, wrapper } = setup();
    expect(
      providers.hashMatchers.value.every((matcher) =>
        providers.isHashMatcherOn(matcher),
      ),
    ).toBe(true);
    providers.generalAllSelected.value = false;
    expect(
      providers.hashMatchers.value.find(
        (matcher) => matcher.value === "playmatch",
      )?.blockedReason,
    ).toBe("IGDB required");
    hashes.value = false;
    await nextTick();
    expect(
      providers.hashMatchers.value.every(
        (matcher) => !providers.isHashMatcherOn(matcher),
      ),
    ).toBe(true);
    expect(
      providers.specificProviders.value.find((source) => source.value === "ra")
        ?.disabled,
    ).toBe("Hashes required: ra");
    wrapper.unmount();
  });
  it("restores saved provider preferences without enabling an unrelated group", () => {
    localStorage.setItem("scan.metadataSources", JSON.stringify(["gamelist"]));
    const { providers, wrapper } = setup();
    expect(providers.generalAllSelected.value).toBe(false);
    expect(
      providers.metadataSources.value.map((source) => source.value),
    ).toEqual(["gamelist"]);
    expect(
      providers.effectiveMetadataSources.value.map((source) => source.value),
    ).toEqual(["gamelist", "ra"]);
    wrapper.unmount();
  });
  it.each([
    ["de_DE", "de-DE"],
    ["fr_FR", "fr-FR"],
    ["en_US", "en-US"],
    ["", "en"],
  ])(
    "uses selected UI %s despite a stale stored scan language",
    (ui, expected) => {
      localStorage.setItem("scan.metadataLocale", "ru_RU");
      const { providers, wrapper, i18n } = setup(ui);
      expect(providers.metadataLocale.value).toBe(expected);
      const accepted = { metadata_locale: providers.metadataLocale.value };
      i18n.global.locale.value = "fr_FR";
      expect(accepted.metadata_locale).toBe(expected);
      expect(providers.metadataLocale.value).toBe("fr-FR");
      expect(selection.select).not.toHaveBeenCalled();
      wrapper.unmount();
    },
  );
  it("routes compatible language control writes through the UI authority", () => {
    const { providers, wrapper } = setup();
    providers.metadataLocale.value = "de_DE";
    expect(selection.select).toHaveBeenCalledWith("de_DE");
    expect(localStorage.getItem("scan.metadataLocale")).toBeNull();
    wrapper.unmount();
  });
});
