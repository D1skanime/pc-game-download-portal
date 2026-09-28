import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  "src/v2/components/GameDetails/ScreenshotsSubtab.vue",
  "utf8",
);

describe("ScreenshotsSubtab provider candidates", () => {
  it("keeps candidate existence separate from overview and background placement", () => {
    expect(source).toContain("providerScreenshots");
    expect(source).toContain("hasPlacement");
    expect(source).toContain('"overview"');
    expect(source).toContain('"background"');
    expect(source).toContain("setOwnedMediaPlacement");
    expect(source).toContain("removeOwnedMediaPlacement");
  });

  it("uses guarded owned-media mutations with conflict recovery", () => {
    expect(source).toContain("useCan");
    expect(source).toContain('tone: "danger"');
    expect(source).toContain("deleteOwnedMedia");
    expect(source).toContain("refreshOwnedMedia");
    expect(source).toContain("response?.status === 409");
    expect(source).toContain("romsStore.refreshRom");
  });

  it("keeps previews contained and action controls out of the lightbox trigger", () => {
    expect(source).toContain("RCarousel");
    expect(source).toContain("providerLightboxOpen");
    expect(source).toContain("@click.stop");
    expect(source).toContain("aria-label");
    expect(source).toContain("RSkeletonBlock");
  });
});
