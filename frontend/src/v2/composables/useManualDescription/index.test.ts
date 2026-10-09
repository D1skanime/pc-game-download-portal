import { describe, expect, it } from "vitest";
import { resolveManualDescription } from "./index";

describe("resolveManualDescription", () => {
  const steamMetadata = {
    text_variants: {
      en: { source_language: "english", summary: "English provider text" },
      de: { source_language: "german", summary: "German provider text" },
    },
  };

  it("keeps manual descriptions locale-scoped and lets them win over providers", () => {
    const source = {
      manualMetadata: { descriptions: { "de-DE": "Manuelle Beschreibung" } },
      steamMetadata,
      legacySummary: "Legacy summary",
    };

    expect(resolveManualDescription({ ...source, locale: "de-DE" })).toBe(
      "Manuelle Beschreibung",
    );
    expect(resolveManualDescription({ ...source, locale: "en-US" })).toBe(
      "English provider text",
    );
  });

  it("falls back to provider text and then legacy text after clearing manual text", () => {
    const source = {
      manualMetadata: { descriptions: {} },
      steamMetadata,
      legacySummary: "Legacy summary",
    };

    expect(resolveManualDescription({ ...source, locale: "de-DE" })).toBe(
      "German provider text",
    );
    expect(
      resolveManualDescription({
        ...source,
        locale: "fr-FR",
        providerSummaryIsAuthoritative: false,
      }),
    ).toBe("Legacy summary");
  });

  it("uses a language manual description for regional locales", () => {
    expect(
      resolveManualDescription({
        manualMetadata: { descriptions: { de: "Deutsch" } },
        steamMetadata,
        legacySummary: "Legacy summary",
        locale: "de-AT",
      }),
    ).toBe("Deutsch");
  });
});
