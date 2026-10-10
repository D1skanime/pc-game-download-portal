import { describe, expect, it, vi } from "vitest";
import { resolveManualDescription, useManualDescription } from "./index";

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
