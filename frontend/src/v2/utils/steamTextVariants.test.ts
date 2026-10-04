import { describe, expect, it } from "vitest";
import type { SteamMetadataSchema } from "@/__generated__";
import { getLocaleBaseTag, resolveSteamTextVariant } from "./steamTextVariants";

const steamMetadata: SteamMetadataSchema = {
  text_variants: {
    de: {
      source_language: "german",
      summary: "Deutsche Steam-Beschreibung",
    },
    en: {
      source_language: "english",
      summary: "English Steam description",
    },
  },
};

describe("getLocaleBaseTag", () => {
  it("normalizes underscore and hyphen locale tags to lower-case base tags", () => {
    expect(getLocaleBaseTag("de_DE")).toBe("de");
    expect(getLocaleBaseTag("en-GB")).toBe("en");
    expect(getLocaleBaseTag(" TR ")).toBe("tr");
  });
});

describe("resolveSteamTextVariant", () => {
  it("selects the selected base language, including English regional locales", () => {
    expect(
      resolveSteamTextVariant({
        steamMetadata,
        legacySummary: "Legacy summary",
        locale: "de_DE",
        steamSummaryIsAuthoritative: true,
      }),
    ).toBe("Deutsche Steam-Beschreibung");
    expect(
      resolveSteamTextVariant({
        steamMetadata,
        legacySummary: "Legacy summary",
        locale: "en_GB",
        steamSummaryIsAuthoritative: true,
      }),
    ).toBe("English Steam description");
  });

  it("uses English when the selected language has no stored Steam variant", () => {
    expect(
      resolveSteamTextVariant({
        steamMetadata,
        legacySummary: "Legacy summary",
        locale: "fr_FR",
        steamSummaryIsAuthoritative: true,
      }),
    ).toBe("English Steam description");
  });

  it("uses a valid legacy summary only after unavailable Steam variants", () => {
    expect(
      resolveSteamTextVariant({
        steamMetadata: {
          text_variants: {
            de: { source_language: "german", summary: " " },
            en: { source_language: "english", summary: null },
          },
        },
        legacySummary: "Legacy summary",
        locale: "de_DE",
        steamSummaryIsAuthoritative: true,
      }),
    ).toBe("Legacy summary");
  });

  it("rejects malformed variants instead of selecting them", () => {
    expect(
      resolveSteamTextVariant({
        steamMetadata: {
          text_variants: {
            de: { source_language: "", summary: "Malformed summary" },
            en: { source_language: "english", summary: "English fallback" },
          },
        },
        legacySummary: "Legacy summary",
        locale: "de_DE",
        steamSummaryIsAuthoritative: true,
      }),
    ).toBe("English fallback");
  });

  it("keeps manual or non-Steam authoritative summaries", () => {
    expect(
      resolveSteamTextVariant({
        steamMetadata,
        legacySummary: "Operator-authored summary",
        locale: "de_DE",
        steamSummaryIsAuthoritative: false,
      }),
    ).toBe("Operator-authored summary");
  });
});
