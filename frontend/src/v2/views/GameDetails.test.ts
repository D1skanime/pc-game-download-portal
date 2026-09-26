import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("GameDetails", () => {
  it("passes the current parent ROM id to OverviewTab", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain(':parent-rom-id="currentRom.id"');
  });

  it("labels the PC download tab for players instead of the internal model", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain('label: t("rom.game-downloads")');
  });

  it("loads archive-set policy before enabling PC downloads", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain("download-archive-sets");
    expect(source).toContain(':archive-sets="archiveSets"');
    expect(source).toContain(':archive-sets-state="archiveSetsState"');
  });

  it("keeps the patcher tab out of PC game details", () => {
    const source = readFileSync("src/v2/views/GameDetails.vue", "utf8");

    expect(source).toContain(
      '...(isPcRom.value ? [] : [{ id: "patcher", label: t("common.patcher") }])',
    );
    expect(source).toMatch(
      /<PatcherTab\s+v-if="tab === 'patcher' && !isPcRom"\s+:rom="currentRom"\s+\/>/,
    );
  });
});
