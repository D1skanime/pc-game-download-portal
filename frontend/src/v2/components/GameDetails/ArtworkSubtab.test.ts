import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  "src/v2/components/GameDetails/ArtworkSubtab.vue",
  "utf8",
);

describe("ArtworkSubtab owned artwork management", () => {
  it("keeps artwork candidates distinct from ordered background placements", () => {
    expect(source).toContain("ownedArtwork");
    expect(source).toContain("backgrounds");
    expect(source).toContain("hasPlacement");
    expect(source).toContain("togglePlacement");
    expect(source).toContain("replaceOwnedMediaPlacements");
    expect(source).toContain('t("rom.backgrounds")');
    expect(source).toContain('t("rom.add-as-background")');
    expect(source).toContain('t("rom.remove-as-background")');
  });

  it("uses the owned-media upload and deletion lifecycle", () => {
    expect(source).toContain("RDropzone");
    expect(source).toContain("uploadOwnedMedia");
    expect(source).toContain('role: "artwork"');
    expect(source).toContain('tone: "danger"');
    expect(source).toContain("deleteOwnedMedia");
    expect(source).toContain("romsStore.refreshRom");
  });

  it("restores authoritative state before reporting an ordering conflict", () => {
    expect(source).toContain("response?.status === 409");
    expect(source).toContain("await refreshCanonical()");
    expect(source).toContain("common.move-up");
    expect(source).toContain("common.move-down");
  });
});
