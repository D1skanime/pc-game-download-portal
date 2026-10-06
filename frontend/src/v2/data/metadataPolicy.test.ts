import { describe, expect, it } from "vitest";
import type { MetadataPolicy } from "./contracts";
import { evaluateMetadataPolicy } from "./metadataPolicy";

const policy: MetadataPolicy = {
  mode: "provider-replace",
  fields: [
    { field: "summary", locale: "de-DE", provider: "steam" },
    { field: "title", locale: "en-US" },
  ],
};

describe("metadata policy", () => {
  it("protects manual values by default and records the provider region", () => {
    const decisions = evaluateMetadataPolicy({
      policy,
      current: [
        {
          field: "summary",
          locale: "de-DE",
          region: "DE",
          value: "Manuelle Beschreibung",
          ownership: "manual",
        },
      ],
      candidates: [
        {
          field: "summary",
          locale: "de-DE",
          region: "DE",
          provider: "steam",
          value: "Provider description",
        },
      ],
      region: "DE",
    });

    expect(decisions[0]).toMatchObject({
      field: "summary",
      locale: "de-DE",
      provider: "steam",
      region: "DE",
      decision: "protected",
    });
  });

  it("keeps fallback locale display-only and does not fill the requested slot", () => {
    const decisions = evaluateMetadataPolicy({
      policy: {
        mode: "missing-only",
        fields: [{ field: "summary", locale: "de-DE", provider: "steam" }],
      },
      current: [],
      candidates: [
        {
          field: "summary",
          locale: "en-US",
          provider: "steam",
          value: "English fallback",
        },
      ],
      fallbackLocales: ["en-US"],
    });

    expect(decisions).toEqual([
      expect.objectContaining({
        field: "summary",
        locale: "de-DE",
        provider: "steam",
        decision: "fallback-read-only",
      }),
    ]);
  });

  it("evaluates provider precedence independently for each locale and region", () => {
    const decisions = evaluateMetadataPolicy({
      policy: {
        mode: "provider-replace",
        fields: [
          { field: "title", locale: "de-DE" },
          { field: "title", locale: "en-US" },
        ],
      },
      current: [],
      candidates: [
        {
          field: "title",
          locale: "de-DE",
          region: "DE",
          provider: "steam",
          value: "Steam DE",
        },
        {
          field: "title",
          locale: "de-DE",
          region: "DE",
          provider: "igdb",
          value: "IGDB DE",
        },
        {
          field: "title",
          locale: "en-US",
          region: "US",
          provider: "steam",
          value: "Steam US",
        },
      ],
      providerOrder: ["igdb", "steam"],
      region: "DE",
    });

    expect(decisions).toEqual([
      expect.objectContaining({
        field: "title",
        locale: "de-DE",
        provider: "igdb",
        region: "DE",
        decision: "write",
        value: "IGDB DE",
      }),
      expect.objectContaining({
        field: "title",
        locale: "en-US",
        provider: "steam",
        region: "US",
        decision: "write",
        value: "Steam US",
      }),
    ]);
  });
});
