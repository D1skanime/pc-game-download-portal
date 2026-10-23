import { describe, expect, it } from "vitest";
import {
  descriptionLocale,
  descriptionPresentation,
  providerCandidates,
  type DescriptionResolution,
} from "@/v2/composables/useManualDescription/provenance";

describe("description provider provenance", () => {
  it("accepts old valid pairs and optional serialized null evidence", () => {
    expect(
      providerCandidates(
        {
          text_variants: {
            de: { source_language: "german", summary: " Old German " },
            fr: {
              source_language: "french",
              requested_language: null,
              language_evidence: null,
              summary: "French",
            },
          },
        },
        "steam",
      ),
    ).toEqual([
      { text: "Old German", locale: "de", source: "steam" },
      { text: "French", locale: "fr", source: "steam" },
    ]);
  });
  it.each([
    { source_language: "english", summary: "Invalid" },
    {
      source_language: "german",
      requested_language: "english",
      summary: "Invalid",
    },
    {
      source_language: "german",
      language_evidence: "guessed",
      summary: "Invalid",
    },
    { source_language: "de", summary: "Invalid" },
    { summary: "Invalid" },
    { source_language: "german", summary: "  " },
  ])("rejects unsupported or contradictory Steam slot evidence %j", (slot) => {
    expect(
      providerCandidates({ text_variants: { de: slot } }, "steam"),
    ).toEqual([]);
  });
  it("accepts explicit provider slot evidence without guessing prose language", () => {
    expect(
      providerCandidates(
        {
          text_variants: {
            de: {
              source_language: "german",
              requested_language: "german",
              language_evidence: "provider_slot",
              summary: "Stored text is not classified by NLP",
            },
          },
        },
        "steam",
      )[0]?.locale,
    ).toBe("de");
  });
  it("requires ScreenScraper actual source locale to match the entire slot", () => {
    expect(
      providerCandidates(
        {
          text_variants: {
            "fr-FR": { source_language: "fr_FR", summary: "Français" },
            de: { source_language: "en", summary: "Invalid" },
            "de-DE": { source_language: "de", summary: "Ambiguous region" },
          },
        },
        "screenscraper",
      ),
    ).toEqual([{ text: "Français", locale: "fr-FR", source: "screenscraper" }]);
  });
  it("rejects malformed locale tags and unsupported language slots", () => {
    expect(descriptionLocale("de-<script>")).toBeNull();
    expect(
      providerCandidates(
        {
          text_variants: {
            "de-<script>": { source_language: "german", summary: "Invalid" },
            xx: { source_language: "unknown", summary: "Invalid" },
          },
        },
        "steam",
      ),
    ).toEqual([]);
  });
});

describe("shared description presentation keys", () => {
  const base: DescriptionResolution = {
    text: "Deutsch",
    requestedLocale: "de-DE",
    resolvedLocale: "de",
    source: "steam",
    match: "base",
  };
  const labels = {
    source: "Steam",
    language: "Deutsch",
    requestedLanguage: "Deutsch",
  };
  it("uses localized source copy for exact/base results", () => {
    for (const match of ["exact", "base"] as const)
      expect(descriptionPresentation({ ...base, match }, labels)).toEqual({
        key: "rom.description-source-localized",
        params: { source: "Steam", language: "Deutsch" },
      });
  });
  it("uses explicit requested and actual language only for English fallback", () => {
    expect(
      descriptionPresentation(
        { ...base, resolvedLocale: "en-GB", match: "english_fallback" },
        { ...labels, language: "English (UK)" },
      ),
    ).toEqual({
      key: "rom.description-language-fallback",
      params: {
        requestedLanguage: "Deutsch",
        source: "Steam",
        language: "English (UK)",
      },
    });
  });
  it("uses the existing no-source label for empty results", () => {
    expect(
      descriptionPresentation(
        {
          ...base,
          text: null,
          resolvedLocale: null,
          source: "none",
          match: "empty",
        },
        labels,
      ),
    ).toEqual({ key: "rom.description-source-empty", params: {} });
  });
});
