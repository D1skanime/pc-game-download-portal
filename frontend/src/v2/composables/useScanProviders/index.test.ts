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

function setup() {
  const hashes = ref(true);
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
        plugins: [
          createI18n({
            legacy: false,
            locale: "en",
            messages: {
              en: {
                scan: {
                  "requires-hashes": "Hashes required: {source}",
                  "disabled-by-admin": "Disabled",
                  "playmatch-requires-igdb": "IGDB required",
                },
              },
            },
          }),
        ],
      },
    },
  );
  return { providers, hashes, wrapper };
}

describe("scan provider selection", () => {
  beforeEach(() => localStorage.clear());
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
});
