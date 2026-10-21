import { describe, expect, it, vi } from "vitest";
import {
  resolveDescription,
  resolveManualDescription,
  resolveProviderDescription,
  useManualDescription,
} from "./index";

const mocks = vi.hoisted(() => ({
  apiPut: vi.fn(),
  updateManualDescription: vi.fn(),
  updatePcComponentManualDescription: vi.fn(),
}));

vi.mock("@/services/api", () => ({
  default: { put: mocks.apiPut },
}));

vi.mock("@/services/api/rom", () => ({
  default: {
    updateManualDescription: mocks.updateManualDescription,
    updatePcComponentManualDescription:
      mocks.updatePcComponentManualDescription,
  },
}));

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

  it("prefers manual English before provider English", () => {
    expect(
      resolveManualDescription({
        manualMetadata: { descriptions: { en: "Manuelles Englisch" } },
        steamMetadata,
        legacySummary: "Legacy summary",
        locale: "fr-FR",
      }),
    ).toBe("Manuelles Englisch");
  });

  it("resolves an exact ScreenScraper locale before provider English", () => {
    expect(
      resolveManualDescription({
        manualMetadata: { descriptions: {} },
        steamMetadata: {
          text_variants: {
            en: { source_language: "english", summary: "Steam English" },
          },
        },
        ssMetadata: {
          text_variants: {
            fr: {
              source_language: "fr",
              summary: "ScreenScraper français",
            },
          },
        },
        legacySummary: "Legacy summary",
        locale: "fr-FR",
      }),
    ).toBe("ScreenScraper français");
  });
});

describe("useManualDescription mutations", () => {
  it("delegates ROM and component writes through the shared ROM service", async () => {
    const payload = {
      locale: "de-DE",
      description: "Manuelle Beschreibung",
      expected_version: "2026-10-09T22:37:10Z",
    };
    const response = {
      data: {
        locale: payload.locale,
        description: payload.description,
        expected_version: "2026-10-09T22:38:10Z",
      },
    };
    mocks.apiPut.mockResolvedValue(response);
    mocks.updateManualDescription.mockResolvedValueOnce(response);
    mocks.updatePcComponentManualDescription.mockResolvedValueOnce(response);

    const { updateRomDescription, updateComponentDescription } =
      useManualDescription();

    await expect(updateRomDescription(41, payload)).resolves.toEqual(
      response.data,
    );
    await expect(updateComponentDescription(41, 7, payload)).resolves.toEqual(
      response.data,
    );

    expect(mocks.updateManualDescription).toHaveBeenCalledWith({
      romId: 41,
      payload,
    });
    expect(mocks.updatePcComponentManualDescription).toHaveBeenCalledWith({
      romId: 41,
      componentId: 7,
      payload,
    });
    expect(mocks.apiPut).not.toHaveBeenCalled();
  });
});

describe("requested language precedence and provenance", () => {
  it("uses German provider text before protected manual English without mutation", () => {
    const manualMetadata = { descriptions: { en: "  Protected English  " } };
    expect(
      resolveManualDescription({
        manualMetadata,
        steamMetadata: {
          text_variants: {
            de: { source_language: "german", summary: "Deutsch" },
          },
        },
        locale: "de-DE",
        legacySummary: "Legacy",
      }),
    ).toBe("Deutsch");
    expect(manualMetadata.descriptions.en).toBe("  Protected English  ");
  });

  it("rejects a German slot whose actual source language is English", () => {
    expect(
      resolveProviderDescription({
        steamMetadata: {
          text_variants: {
            de: {
              source_language: "english",
              summary: "Wrongly tagged English",
            },
          },
        },
        ssMetadata: null,
        locale: "de-DE",
      }),
    ).toBeNull();
  });
});

describe("resolveDescription typed policy", () => {
  const steamMetadata = {
    text_variants: {
      de: { source_language: "german", summary: "Deutsch" },
      fr: { source_language: "french", summary: "Français" },
      en: { source_language: "english", summary: "English" },
    },
  };
  it("has no scalar-only fallback and defaults an unset preference to English", () => {
    const legacy = { summary: "Legacy", legacySummary: "Legacy" };
    expect(resolveDescription({ ...legacy, provider: null })).toEqual({
      text: null,
      requestedLocale: "en",
      resolvedLocale: null,
      source: "none",
      match: "empty",
    });
    expect(legacy).toEqual({ summary: "Legacy", legacySummary: "Legacy" });
    expect(resolveDescription({ provider: "steam", steamMetadata }).text).toBe(
      "English",
    );
  });
  it.each([
    ["de_DE", "de-DE", "de", "Deutsch"],
    ["fr-FR", "fr-FR", "fr", "Français"],
  ])(
    "resolves provider %s before manual English",
    (locale, requestedLocale, resolvedLocale, text) => {
      const manualMetadata = {
        descriptions: { en: "  Protected English  ", ja: "保護" },
      };
      const before = JSON.stringify(manualMetadata);
      expect(
        resolveDescription({
          provider: "steam",
          locale,
          steamMetadata,
          manualMetadata,
        }),
      ).toEqual({
        text,
        requestedLocale,
        resolvedLocale,
        source: "steam",
        match: "base",
      });
      expect(JSON.stringify(manualMetadata)).toBe(before);
    },
  );
  it("preserves exact and base manual priority and skips empty exact entries", () => {
    const manualMetadata = {
      descriptions: { "de-DE": " Genau ", de: "Basis", en: "English" },
    };
    expect(
      resolveDescription({
        provider: "steam",
        locale: "de-DE",
        steamMetadata,
        manualMetadata,
      }),
    ).toMatchObject({
      text: "Genau",
      resolvedLocale: "de-DE",
      source: "manual",
      match: "exact",
    });
    manualMetadata.descriptions["de-DE"] = "  ";
    expect(
      resolveDescription({
        provider: "steam",
        locale: "de-DE",
        steamMetadata,
        manualMetadata,
      }),
    ).toMatchObject({
      text: "Basis",
      resolvedLocale: "de",
      source: "manual",
      match: "base",
    });
  });
  it("distinguishes manual and provider English fallback with actual regional locale", () => {
    expect(
      resolveDescription({
        provider: "steam",
        locale: "it-IT",
        steamMetadata,
        manualMetadata: {
          descriptions: { en: " ", "en-GB": "Manual English" },
        },
      }),
    ).toMatchObject({
      text: "Manual English",
      resolvedLocale: "en-GB",
      source: "manual",
      match: "english_fallback",
    });
    const regional = {
      text_variants: {
        "en-US": { source_language: "english", summary: "US English" },
      },
    };
    expect(
      resolveDescription({
        provider: "steam",
        locale: "de-DE",
        steamMetadata: regional,
      }),
    ).toMatchObject({
      resolvedLocale: "en-US",
      source: "steam",
      match: "english_fallback",
    });
    expect(
      resolveDescription({
        provider: "steam",
        locale: "en-GB",
        steamMetadata: regional,
      }),
    ).toMatchObject({
      requestedLocale: "en-GB",
      resolvedLocale: "en-US",
      match: "base",
    });
  });
  it("selects only the explicitly eligible platform provider", () => {
    const ssMetadata = {
      text_variants: {
        fr: { source_language: "fr", summary: "Console français" },
      },
    };
    expect(
      resolveDescription({
        provider: "screenscraper",
        locale: "fr-FR",
        steamMetadata,
        ssMetadata,
      }),
    ).toMatchObject({
      text: "Console français",
      source: "screenscraper",
      resolvedLocale: "fr",
      match: "base",
    });
    expect(
      resolveDescription({
        provider: null,
        locale: "fr",
        steamMetadata,
        ssMetadata,
      }).match,
    ).toBe("empty");
    expect(
      resolveDescription({
        provider: "screenscraper",
        locale: "de",
        steamMetadata,
      }).match,
    ).toBe("empty");
  });
  it("keeps parent and component resolution isolated and locale reads make no requests", () => {
    mocks.apiPut.mockClear();
    mocks.updateManualDescription.mockClear();
    mocks.updatePcComponentManualDescription.mockClear();
    const parent = { descriptions: { de: "Parent" } };
    for (const locale of ["de-DE", "fr-FR", "en-US"]) {
      expect(
        resolveDescription({
          provider: "steam",
          locale,
          manualMetadata: parent,
        }).source,
      ).toBe(locale === "de-DE" ? "manual" : "none");
      expect(resolveDescription({ provider: "steam", locale }).match).toBe(
        "empty",
      );
    }
    expect(mocks.apiPut).not.toHaveBeenCalled();
    expect(mocks.updateManualDescription).not.toHaveBeenCalled();
    expect(mocks.updatePcComponentManualDescription).not.toHaveBeenCalled();
  });
});
