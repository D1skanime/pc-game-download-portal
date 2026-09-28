import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  "src/v2/components/GameDetails/MediaTab.vue",
  "utf8",
);

describe("MediaTab soundtrack access", () => {
  it("keeps the soundtrack panel available so an empty game can receive uploads", () => {
    expect(source).toContain('<SoundtrackPanel :rom="rom"');
    expect(source).not.toContain("!rom.has_soundtrack");
  });
});
