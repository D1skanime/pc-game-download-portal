import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { UpdateRom } from "@/v2/data/adapters/legacy/services/api/rom";
import { isValidYoutubeVideoId } from "@/v2/utils/validation";
import AdditionalDetails from "./AdditionalDetails.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

describe("AdditionalDetails YouTube metadata", () => {
  it("allows an empty value but rejects IDs that cannot be saved", () => {
    expect(isValidYoutubeVideoId(null)).toBe(true);
    expect(isValidYoutubeVideoId("too-short")).toBe(false);
    expect(isValidYoutubeVideoId("dQw4w9WgXcQ")).toBe(true);
  });
});
