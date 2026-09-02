import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("GameDetails", () => {
  it("passes the current parent ROM id to OverviewTab", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain(':parent-rom-id="currentRom.id"');
  });
});
