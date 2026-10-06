import { describe, expect, it } from "vitest";
import type { MediaPolicy } from "./contracts";
import { evaluateMediaPolicy } from "./mediaPolicy";

describe("media policy", () => {
  it("keeps neutral and localized media in separate slots", () => {
    const policy: MediaPolicy = {
      mode: "missing-only",
      targets: [
        { role: "cover", provider: "steam" },
        { role: "cover", locale: "de-DE", region: "DE", provider: "steam" },
      ],
    };

    const decisions = evaluateMediaPolicy({
      policy,
      current: [],
      candidates: [
        {
          role: "cover",
          locale: "en-US",
          region: "US",
          provider: "steam",
          value: "localized-cover",
        },
        {
          role: "cover",
          provider: "steam",
          value: "neutral-cover",
        },
      ],
    });

    expect(decisions).toEqual([
      expect.objectContaining({
        role: "cover",
        kind: "neutral",
        decision: "write",
        value: "neutral-cover",
      }),
      expect.objectContaining({
        role: "cover",
        kind: "localized",
        locale: "de-DE",
        region: "DE",
        decision: "unchanged",
      }),
    ]);
  });

  it("protects owned local media and makes fallback media read-only", () => {
    const policy: MediaPolicy = {
      mode: "provider-replace",
      targets: [{ role: "screenshot", locale: "de-DE", provider: "igdb" }],
    };

    const decisions = evaluateMediaPolicy({
      policy,
      current: [
        {
          role: "screenshot",
          locale: "de-DE",
          provider: "local",
          value: "owned-shot",
          ownership: "manual",
        },
      ],
      candidates: [
        {
          role: "screenshot",
          locale: "en-US",
          provider: "igdb",
          value: "fallback-shot",
        },
      ],
      fallbackLocales: ["en-US"],
    });

    expect(decisions).toEqual([
      expect.objectContaining({
        role: "screenshot",
        kind: "localized",
        decision: "protected",
      }),
    ]);
  });
});
