import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { UpdateRom } from "@/v2/data/adapters/legacy/services/api/rom";
import { isValidYoutubeVideoId } from "@/v2/utils/validation";
import AdditionalDetails from "./AdditionalDetails.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

describe("AdditionalDetails YouTube metadata", () => {
  it("exposes actionable validation for an invalid YouTube video ID", () => {
    const wrapper = shallowMount(AdditionalDetails, {
      props: {
        rom: {
          manual_metadata: { youtube_video_id: "too-short" },
        } as UpdateRom,
      },
    });

    const field = wrapper.findComponent({ name: "RTextField" });
    const rules = field.props("rules") as Array<
      (value: unknown) => true | string
    >;

    expect(field.props("hideDetails")).not.toBe(true);
    expect(rules).toHaveLength(1);
    expect(rules[0]("too-short")).toBe(
      "This YouTube ID is not supported. Use the 11-character video ID.",
    );
    expect(rules[0]("dQw4w9WgXcQ")).toBe(true);
  });

  it("allows an empty value but rejects IDs that cannot be saved", () => {
    expect(isValidYoutubeVideoId(null)).toBe(true);
    expect(isValidYoutubeVideoId("too-short")).toBe(false);
    expect(isValidYoutubeVideoId("dQw4w9WgXcQ")).toBe(true);
  });
});
