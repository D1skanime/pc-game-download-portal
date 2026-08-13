import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import Upload from "./Upload.vue";

const { getSupportedPlatforms, uploadPlatform, uploadRoms } = vi.hoisted(
  () => ({
    getSupportedPlatforms: vi.fn(),
    uploadPlatform: vi.fn(),
    uploadRoms: vi.fn(),
  }),
);

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

vi.mock("vue-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue-router")>()),
  useRoute: () => ({ query: {} }),
}));

vi.mock("@/services/api/platform", () => ({
  default: {
    getSupportedPlatforms,
    uploadPlatform,
  },
}));

vi.mock("@/services/api/rom", () => ({
  default: { uploadRoms },
}));

vi.mock("@/services/socket", () => ({
  default: { connected: true, connect: vi.fn(), emit: vi.fn() },
}));

vi.mock("@/stores/heartbeat", () => ({
  default: () => ({ getEnabledMetadataOptions: () => [] }),
}));

vi.mock("@/stores/scanning", () => ({
  default: () => ({ setScanning: vi.fn() }),
}));

vi.mock("@/stores/upload", () => ({
  default: () => ({ reset: vi.fn() }),
}));

vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  }),
}));

describe("source-read-only upload route", () => {
  it("renders no upload, platform creation, dropzone, or file control", async () => {
    getSupportedPlatforms.mockResolvedValueOnce({ data: [] });
    const wrapper = mount(Upload, {
      global: {
        stubs: {
          PlatformSelect: {
            props: ["modelValue", "items", "itemKey"],
            emits: ["update:modelValue"],
            template:
              '<button class="platform-select" :data-item-key="itemKey" @click="$emit(\'update:modelValue\', \'3do\')" />',
          },
          RDropzone: {
            emits: ["files"],
            template:
              "<button class=\"dropzone\" @click=\"$emit('files', [{ name: 'game.rom', size: 3 }])\" />",
          },
          RBtn: {
            props: ["disabled"],
            emits: ["click"],
            template:
              '<button class="upload" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
          },
          RChip: true,
          RIcon: true,
        },
      },
    });

    await flushPromises();
    expect(wrapper.find(".platform-select").exists()).toBe(false);
    expect(wrapper.find(".dropzone").exists()).toBe(false);
    expect(wrapper.find(".upload").exists()).toBe(false);
    expect(wrapper.find('input[type="file"]').exists()).toBe(false);
    expect(uploadPlatform).not.toHaveBeenCalled();
    expect(uploadRoms).not.toHaveBeenCalled();
  });
});
