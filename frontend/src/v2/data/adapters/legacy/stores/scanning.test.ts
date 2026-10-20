import { describe, expect, it } from "vitest";
import { transportScanStats } from "@/v2/data/adapters/legacy/stores/scanning";

describe("scan stats transport", () => {
  it("preserves unavailable facts and an unknown game total", () => {
    expect(transportScanStats(undefined)).toBeUndefined();
    const stats = transportScanStats({ scanned_roms: 3, provider_requests: 0 });
    expect(stats).toEqual({ scanned_roms: 3, provider_requests: 0 });
    expect(stats).not.toHaveProperty("total_roms");
    expect(stats).not.toHaveProperty("metadata_cache_hits");
  });

  it("retains independent global game, request and cache units", () => {
    const facts = {
      total_roms: 105,
      inventory_checked: 105,
      inventory_unchanged: 100,
      unresolved_games: 9,
      metadata_retry_games: 2,
      provider_requests: 5,
      metadata_cache_hits: 0,
    };
    const stats = transportScanStats(facts);
    expect(stats).toEqual(facts);
    expect(stats).not.toBe(facts);
    if (stats) stats.provider_requests = 6;
    expect(facts.provider_requests).toBe(5);
  });
});
