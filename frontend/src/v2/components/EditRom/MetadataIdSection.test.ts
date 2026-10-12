import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { UpdateRom } from "@/v2/data/adapters/legacy/services/api/rom";
import MetadataIdSection from "./MetadataIdSection.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

describe("MetadataIdSection", () => {
  it("exposes the Steam App ID and binds its numeric value", () => {
    const wrapper = shallowMount(MetadataIdSection, {
      props: {
        rom: { steam_id: 730 } as UpdateRom,
      },
    });

    const steamField = wrapper
      .findAllComponents({ name: "RTextField" })
      .find((field) => field.props("label") === "rom.provider-steam-id");

    expect(steamField).toBeDefined();
    expect(steamField?.props("modelValue")).toBe("730");
  });

  it("exposes actionable validation for an invalid YouTube video ID", () => {
    const wrapper = shallowMount(MetadataIdSection, {
      props: {
        rom: {
          manual_metadata: { youtube_video_id: "too-short" },
        } as UpdateRom,
      },
    });

    const field = wrapper
      .findAllComponents({ name: "RTextField" })
      .find((candidate) => candidate.props("label") === "rom.youtube-video-id");
    const rules = field?.props("rules") as Array<
      (value: unknown) => true | string
    >;

    expect(rules).toHaveLength(1);
    expect(rules[0]("too-short")).toBe(
      "This YouTube ID is not supported. Use the 11-character video ID.",
    );
    expect(rules[0]("dQw4w9WgXcQ")).toBe(true);
  });

  it("emits manual metadata when the YouTube video ID changes", () => {
    const wrapper = shallowMount(MetadataIdSection, {
      props: {
        rom: {
          manual_metadata: { youtube_video_id: "oldValue123" },
        } as UpdateRom,
      },
    });

    const youtubeField = wrapper
      .findAllComponents({ name: "RTextField" })
      .find((field) => field.props("label") === "rom.youtube-video-id");

    youtubeField?.vm.$emit("update:modelValue", "newValue123");

    expect(wrapper.emitted("update:rom")?.[0]?.[0]).toMatchObject({
      manual_metadata: { youtube_video_id: "newValue123" },
    });
  });

  it("shows the provider YouTube video ID when no manual override exists", () => {
    const wrapper = shallowMount(MetadataIdSection, {
      props: {
        rom: { youtube_video_id: "jNY7AEQ59-8" } as UpdateRom,
      },
    });

    const youtubeField = wrapper
      .findAllComponents({ name: "RTextField" })
      .find((field) => field.props("label") === "rom.youtube-video-id");

    expect(youtubeField?.props("modelValue")).toBe("jNY7AEQ59-8");
  });

  it("exposes the YouTube video ID in the metadata IDs tab", () => {
    const wrapper = shallowMount(MetadataIdSection, {
      props: {
        rom: {
          manual_metadata: { youtube_video_id: "dQw4w9WgXcQ" },
        } as UpdateRom,
      },
    });

    const youtubeField = wrapper
      .findAllComponents({ name: "RTextField" })
      .find((field) => field.props("label") === "rom.youtube-video-id");

    expect(youtubeField).toBeDefined();
    expect(youtubeField?.props("modelValue")).toBe("dQw4w9WgXcQ");
  });
});
