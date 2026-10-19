import { flushPromises, shallowMount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import Scan from "./Scan.vue";

const api = vi.hoisted(() => ({
  start: vi.fn().mockResolvedValue(undefined),
  getMappingsReadiness: vi.fn().mockResolvedValue({ ready: true }),
}));
vi.mock("pinia", async (importOriginal) => ({
  ...(await importOriginal<typeof import("pinia")>()),
  storeToRefs: (store: object) => store,
}));
vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key, locale: ref("de-DE") }),
}));
vi.mock("@/v2/composables/useCan", () => ({
  useCan: () => ref(true),
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ error: vi.fn() }),
}));
vi.mock("@/v2/composables/useLibraryOperation", () => ({
  useLibraryOperation: () => ({
    snapshot: ref(null),
    checking: ref(false),
    uncertain: ref(false),
    disconnected: ref(false),
    reconciling: ref(false),
    actionError: ref(null),
    status: ref("idle"),
    busy: ref(false),
    start: api.start,
  }),
}));
vi.mock("@/v2/composables/useScanProviders", () => ({
  useScanProviders: () => ({
    storedMetadataSources: ref([]),
    metadataSources: ref([{ value: "igdb" }]),
    effectiveMetadataSources: ref([{ value: "igdb" }]),
    metadataLocale: ref("en-US"),
    launchboxRemoteEnabled: ref(false),
    isLaunchboxSelected: ref(false),
    hashMatchers: ref([]),
    isHashMatcherOn: () => false,
    setHashMatcher: vi.fn(),
    generalProviders: ref([]),
    specificProviders: ref([]),
    generalAllSelected: ref(false),
    specificAllSelected: ref(false),
  }),
}));
vi.mock("@/v2/data/adapters/legacy/services/api/storage", () => ({
  default: { getMappingsReadiness: api.getMappingsReadiness },
}));
vi.mock("@/v2/data/adapters/legacy/stores/config", () => ({
  default: () => ({ config: ref({ SKIP_HASH_CALCULATION: false }) }),
}));
vi.mock("@/v2/data/adapters/legacy/stores/platforms", () => ({
  default: () => ({
    scannablePlatforms: ref([{ id: 3, fs_slug: "win", display_name: "PC" }]),
    allPlatforms: [{ id: 3 }],
  }),
}));
vi.mock("@/v2/data/adapters/legacy/stores/scanning", () => ({
  default: () => ({
    scanning: ref(false),
    scanningPlatforms: ref([{ id: 3, roms: [{ id: 41 }] }]),
    scanStats: ref({}),
    reset: vi.fn(),
  }),
}));

describe("Scan collection selection request", () => {
  beforeEach(() => api.start.mockClear());

  it.each(["media", "update", "hashes", "complete"])(
    "uses filesystem discovery for explicit child selection while %s is selected",
    async (mode) => {
      const wrapper = shallowMount(Scan);
      await flushPromises();
      const typeSelect = wrapper
        .findAllComponents({ name: "RSelect" })
        .find((select) =>
          select
            .props("items")
            ?.some((item: { value: string }) => item.value === "quick"),
        )!;
      expect(typeSelect).toBeDefined();
      typeSelect.vm.$emit("update:modelValue", mode);
      const collectionPromotion = {
        parent_rom_id: 41,
        mapping_id: 12,
        expected_revision: 3,
        parent_relative_path: "Castlevania",
        selected_child_relative_path: "Castlevania/Belmonts.Curse",
      };
      wrapper
        .getComponent({ name: "ScanPlatform" })
        .vm.$emit("scan-subfolder", {
          platformFsSlug: "win",
          relativePath: collectionPromotion.selected_child_relative_path,
          collectionPromotion,
        });
      await flushPromises();
      expect(api.start).toHaveBeenCalledOnce();
      expect(api.start.mock.calls[0][0]).toMatchObject({
        kind: "discovery",
        scanType: "quick",
        collectionPromotion,
        scope: {
          kind: "filesystem",
          platformFsSlugs: ["win"],
          relativePaths: { win: "Castlevania/Belmonts.Curse" },
        },
        metadataPolicy: { mode: "missing-only" },
        mediaPolicy: { mode: "missing-only" },
        providerPolicy: { providers: ["igdb"], launchboxRemoteEnabled: false },
      });
      expect(api.start.mock.calls[0][0].metadataOnly).not.toBe(true);
      expect(api.start.mock.calls[0][0].mediaOnly).not.toBe(true);
      wrapper.unmount();
    },
  );
});
