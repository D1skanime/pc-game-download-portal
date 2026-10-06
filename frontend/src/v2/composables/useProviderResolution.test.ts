import { describe, expect, it } from "vitest";
import {
  normalizeLocale,
  resolveProviderContributions,
  resolveProviderSelection,
  withActualProviderLocale,
} from "./useProviderResolution";

const options = [
  { value: "igdb" },
  { value: "steam" },
  { value: "ra", disabled: "requires key" },
  { value: "launchbox" },
  { value: "hasheous" },
  { value: "playmatch" },
];

describe("shared provider resolution", () => {
  it("expands All without producing an empty provider request", () => {
    expect(
      resolveProviderSelection({
        options,
        selected: [],
        allSelected: true,
        calculateHashes: true,
        hasheousEnabled: true,
        playmatchEnabled: true,
      }),
    ).toMatchObject({
      providers: ["igdb", "steam", "launchbox", "hasheous"],
      fallbackProviders: ["playmatch"],
    });
  });

  it("keeps hash matcher gates consistent across operation surfaces", () => {
    const input = {
      options,
      selected: ["steam"],
      calculateHashes: false,
      hasheousEnabled: true,
      playmatchEnabled: true,
    };
    expect(resolveProviderSelection(input)).toMatchObject({
      providers: ["steam"],
      fallbackProviders: [],
      disabledReasons: { playmatch: "requires-igdb" },
    });
  });

  it("plans independent IGDB identity and Steam localized contributions", () => {
    expect(
      resolveProviderContributions({
        providers: ["igdb", "steam"],
        fields: [
          { field: "name", locale: "en-US" },
          { field: "summary", locale: "de-DE" },
        ],
        metadataLocale: "de_de",
        region: "DE",
      }),
    ).toEqual([
      {
        provider: "igdb",
        fields: ["name", "summary"],
        locale: "de-DE",
        region: "DE",
        role: "identity",
      },
      {
        provider: "steam",
        fields: ["name", "summary"],
        locale: "de-DE",
        region: "DE",
        role: "localized",
      },
    ]);
  });

  it("records the actual provider locale without relabeling it", () => {
    expect(
      withActualProviderLocale(
        {
          provider: "steam",
          locale: "de-DE",
          ownership: "provider",
        },
        "en_US",
      ).locale,
    ).toBe("en-US");
    expect(normalizeLocale("EN_us")).toBe("en-US");
  });
});
